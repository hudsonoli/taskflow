"""Interpretação do termo de busca — regra pura (app/core/busca.py).

Testes sem banco: a decisão "isto é texto ou é documento?" tem de ser verificável
isoladamente, senão volta a se espalhar pelo repository.
"""

from __future__ import annotations

import pytest

from app.core.busca import MIN_DIGITOS_DOCUMENTO, interpretar_termo_busca


# --------------------------------------------------------------------------------------
# Texto — a presença de letra decide
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "termo",
    [
        "BRETAS",                 # nome simples
        "Padaria Estrela",        # nome com espaço
        "C26000025",              # codigoReferencia
        "c26000025",              # idem, minúsculo
        "#2001",                  # codigoInterno
        "Cliente 2026",           # nome COM número — não é documento
        "Loja 24h",               # número colado em letra
        "QA FASE2B",              # o incidente
    ],
)
def test_termo_com_letra_nunca_ativa_documento(termo: str) -> None:
    resultado = interpretar_termo_busca(termo)
    assert resultado.texto == termo.strip()
    assert resultado.documento is None, f"{termo!r} não pode virar filtro de documento"


def test_regressao_do_incidente_qa_fase2b() -> None:
    """Regressão explícita.

    `"QA FASE2B"` extraía o dígito "2" e virava `documento_normalizado ILIKE '%2%'`, que
    casa com quase todo CNPJ: a busca devolveu 91 clientes em vez de 3, e uma operação em
    lote sobre esse resultado arquivou 87 registros indevidos.
    """
    resultado = interpretar_termo_busca("QA FASE2B")
    assert resultado.documento is None
    assert resultado.documento != "2"
    assert resultado.texto == "QA FASE2B"


# --------------------------------------------------------------------------------------
# Documento — só sem letras e com dígitos suficientes
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("termo", "esperado"),
    [
        ("39.346.861/0245-08", "39346861024508"),  # CNPJ formatado
        ("39346861024508", "39346861024508"),      # CNPJ cru
        ("123.456.789-01", "12345678901"),         # CPF formatado
        ("0245", "0245"),                          # parcial no mínimo
        ("0245-08", "024508"),                     # parcial com pontuação
    ],
)
def test_termo_sem_letra_com_digitos_suficientes_ativa_documento(termo: str, esperado: str) -> None:
    resultado = interpretar_termo_busca(termo)
    assert resultado.documento == esperado
    assert resultado.texto == termo  # a busca textual continua valendo em paralelo


@pytest.mark.parametrize("termo", ["1", "12", "123", "1-2", "12/3"])
def test_poucos_digitos_nao_ativam_documento(termo: str) -> None:
    """Abaixo do mínimo a busca parcial casaria com quase toda a base."""
    assert interpretar_termo_busca(termo).documento is None


def test_minimo_de_digitos_e_o_limite_exato() -> None:
    assert MIN_DIGITOS_DOCUMENTO == 4
    assert interpretar_termo_busca("1" * (MIN_DIGITOS_DOCUMENTO - 1)).documento is None
    assert interpretar_termo_busca("1" * MIN_DIGITOS_DOCUMENTO).documento == "1" * MIN_DIGITOS_DOCUMENTO


# --------------------------------------------------------------------------------------
# Bordas
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("termo", [None, "", "   "])
def test_termo_vazio(termo: str | None) -> None:
    resultado = interpretar_termo_busca(termo)
    assert resultado.vazio
    assert resultado.documento is None


def test_espacos_das_pontas_sao_removidos() -> None:
    assert interpretar_termo_busca("  BRETAS  ").texto == "BRETAS"


def test_resultado_e_imutavel() -> None:
    """Frozen de propósito: ninguém deve ajustar a decisão depois de tomada."""
    resultado = interpretar_termo_busca("BRETAS")
    with pytest.raises(Exception):
        resultado.documento = "123"  # type: ignore[misc]
