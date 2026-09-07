"""Criptografia do segredo SMTP (Fase 2G.7B1) — app/services/configuracao_email_crypto_service.py.

Unitário, sem banco — usa `chave` injetada no construtor (parâmetro que só existe para
teste, ver docstring da classe) em vez de depender de `EMAIL_CONFIG_ENCRYPTION_KEY`."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.services.configuracao_email_crypto_service import (
    ChaveCriptografiaAusenteError,
    ChaveCriptografiaInvalidaError,
    CiphertextInvalidoError,
    ConfiguracaoEmailCryptoService,
)


def test_criptografar_e_descriptografar_roundtrip() -> None:
    service = ConfiguracaoEmailCryptoService(chave=Fernet.generate_key().decode())
    ciphertext = service.criptografar("senha-secreta")
    assert ciphertext != "senha-secreta"
    assert "senha-secreta" not in ciphertext
    assert service.descriptografar(ciphertext) == "senha-secreta"


def test_chave_ausente_levanta_erro_controlado() -> None:
    service = ConfiguracaoEmailCryptoService(chave=None)
    with pytest.raises(ChaveCriptografiaAusenteError):
        service.criptografar("qualquer-senha")


@pytest.mark.parametrize(
    "chave_invalida",
    ["nao-e-uma-chave-fernet", "x" * 44, "12345"],
)
def test_chave_invalida_nao_aceita_string_arbitraria(chave_invalida: str) -> None:
    """Fernet exige 32 bytes urlsafe-base64 — string arbitrária nunca é aceita
    silenciosamente (Fase 2G.7A, item 6). `""` não entra aqui: `_obter_fernet` já trata
    string vazia como "ausente" (`if not chave`), não como "presente mas malformada" — ver
    test_chave_ausente_levanta_erro_controlado, mesma árvore de decisão do resto do domínio
    (omitido/vazio tratados uniformemente como ausência)."""
    service = ConfiguracaoEmailCryptoService(chave=chave_invalida)
    with pytest.raises(ChaveCriptografiaInvalidaError):
        service.criptografar("qualquer-senha")


def test_ciphertext_invalido_levanta_erro_controlado() -> None:
    service = ConfiguracaoEmailCryptoService(chave=Fernet.generate_key().decode())
    with pytest.raises(CiphertextInvalidoError):
        service.descriptografar("isto-nao-e-um-token-fernet-valido")


def test_ciphertext_de_outra_chave_nao_descriptografa() -> None:
    service_a = ConfiguracaoEmailCryptoService(chave=Fernet.generate_key().decode())
    service_b = ConfiguracaoEmailCryptoService(chave=Fernet.generate_key().decode())
    ciphertext = service_a.criptografar("senha")
    with pytest.raises(CiphertextInvalidoError):
        service_b.descriptografar(ciphertext)


def test_mensagem_de_erro_nunca_contem_senha_ciphertext_ou_chave() -> None:
    chave = Fernet.generate_key().decode()
    service = ConfiguracaoEmailCryptoService(chave=chave)
    ciphertext = service.criptografar("senha-marcador-unico-xyz")

    with pytest.raises(CiphertextInvalidoError) as exc_ausente:
        service.descriptografar("ciphertext-corrompido")
    assert "ciphertext-corrompido" not in str(exc_ausente.value)

    service_chave_ausente = ConfiguracaoEmailCryptoService(chave=None)
    with pytest.raises(ChaveCriptografiaAusenteError) as exc_chave:
        service_chave_ausente.descriptografar(ciphertext)
    assert ciphertext not in str(exc_chave.value)
    assert chave not in str(exc_chave.value)
    assert "senha-marcador-unico-xyz" not in str(exc_chave.value)
