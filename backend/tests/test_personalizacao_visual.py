"""Personalização visual por Empresa: defaults, RBAC, tenant, leitura pública segura, cores/tema e a
validação (toda no backend) do logo PNG/GIF 320×132 de até 2 MB."""

from __future__ import annotations

import struct
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.demanda_arquivo_service as demanda_arquivo_service
from app.core.security import create_access_token
from app.models.configuracao_personalizacao import ConfiguracaoPersonalizacao
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.services.configuracao_personalizacao_service import (
    LOGO_ALTURA,
    LOGO_LARGURA,
    LOGO_MAX_BYTES,
    ConfiguracaoPersonalizacaoService,
)

ADMIN = "/configuracoes/personalizacao"
PUBLICA = "/personalizacao/publica"


# --------------------------------------------------------------------------------------
# Builders de imagens (sem Pillow): só o necessário para serem arquivos íntegros
# --------------------------------------------------------------------------------------


def _chunk(tipo: bytes, dados: bytes) -> bytes:
    return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)


def png(largura: int = LOGO_LARGURA, altura: int = LOGO_ALTURA, *, cor: int = 0) -> bytes:
    linha = b"\x00" + bytes([cor]) * (largura * 3)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(linha * altura))
        + _chunk(b"IEND", b"")
    )


def gif(largura: int = LOGO_LARGURA, altura: int = LOGO_ALTURA, *, versao: bytes = b"GIF89a", quadros: int = 1) -> bytes:
    cabecalho = versao + struct.pack("<HHBBB", largura, altura, 0x80, 0, 0) + b"\x00\x00\x00\xff\xff\xff"
    loop = b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00" if quadros > 1 else b""
    corpo = b""
    for _ in range(quadros):
        corpo += b"\x21\xf9\x04\x00\x0a\x00\x00\x00" if versao == b"GIF89a" else b""
        corpo += b"\x2c" + struct.pack("<HHHHB", 0, 0, largura, altura, 0) + b"\x02\x02\x44\x01\x00"
    return cabecalho + loop + corpo + b";"


def _upload(client: TestClient, conteudo: bytes, nome: str = "logo.png", tipo: str = "image/png"):
    return client.post(f"{ADMIN}/logo", files={"arquivo": (nome, conteudo, tipo)})


def _cliente_admin_de(app, empresa: Empresa, db: Session) -> TestClient:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"adm-{sufixo}",
        nome="Admin Outra",
        email=f"adm-{sufixo}@outra.local",
        perfil_base="admin",
        acesso_sistema=True,
        status="ativo",
        is_system_account=False,
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {create_access_token(sub=usuario.id, empresa_id=empresa.id, perfil_base='admin')}"
    return cliente


def _arquivos_em_disco() -> set[str]:
    raiz = demanda_arquivo_service.UPLOADS_ROOT
    return {str(p.relative_to(raiz)) for p in raiz.rglob("*") if p.is_file()} if raiz.exists() else set()


# --------------------------------------------------------------------------------------
# Defaults / leitura
# --------------------------------------------------------------------------------------


def test_defaults_sem_linha_e_get_nao_cria(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    resposta = client_admin.get(ADMIN)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {
        "corPrimaria": "#6366f1",
        "corSecundaria": "#7c3aed",
        "tema": "claro",
        "logoDisponivel": False,
        "logoVersao": None,
        "padrao": True,
    }
    assert db_session.scalars(select(ConfiguracaoPersonalizacao).where(ConfiguracaoPersonalizacao.empresa_id == empresa.id)).first() is None


def test_publica_devolve_so_branding(client: TestClient, client_admin: TestClient, empresa: Empresa) -> None:
    client_admin.patch(ADMIN, json={"corPrimaria": "#112233", "tema": "escuro"})
    resposta = client.get(PUBLICA, params={"empresaCodigo": empresa.codigo_interno})  # SEM autenticação
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert set(corpo) == {"corPrimaria", "corSecundaria", "tema", "logoDisponivel", "logoVersao", "padrao"}
    assert corpo["corPrimaria"] == "#112233" and corpo["tema"] == "escuro"
    texto = resposta.text.lower()
    # nenhum id, caminho do servidor ou chave de storage na resposta pública
    assert empresa.id.lower() not in texto and "uploads" not in texto and "storage" not in texto and "/" not in texto


def test_publica_codigo_desconhecido_recebe_padrao_sem_404(client: TestClient) -> None:
    resposta = client.get(PUBLICA, params={"empresaCodigo": "NAO-EXISTE"})
    assert resposta.status_code == 200
    assert resposta.json()["padrao"] is True and resposta.json()["tema"] == "claro"
    assert client.get(f"{PUBLICA}/logo", params={"empresaCodigo": "NAO-EXISTE"}).status_code == 404


def test_publica_exige_codigo(client: TestClient) -> None:
    assert client.get(PUBLICA).status_code == 422


# --------------------------------------------------------------------------------------
# RBAC / tenant
# --------------------------------------------------------------------------------------


def test_rbac_administrativo(client: TestClient, client_admin: TestClient, client_gestor: TestClient, client_operador: TestClient) -> None:
    corpo = {"tema": "escuro"}
    assert client.get(ADMIN).status_code == 401
    assert client.patch(ADMIN, json=corpo).status_code == 401
    assert client_operador.get(ADMIN).status_code == 403
    assert client_operador.patch(ADMIN, json=corpo).status_code == 403
    assert client_operador.delete(ADMIN).status_code == 403
    assert _upload(client_operador, png()).status_code == 403
    assert client_operador.delete(f"{ADMIN}/logo").status_code == 403
    assert client_gestor.patch(ADMIN, json=corpo).status_code == 200
    assert client_admin.get(ADMIN).status_code == 200


def test_empresa_vem_do_token_e_nunca_do_corpo(client_admin: TestClient, outra_empresa: Empresa) -> None:
    resposta = client_admin.patch(ADMIN, json={"empresaId": outra_empresa.id, "tema": "escuro"})
    assert resposta.status_code == 422  # extra="forbid": nenhum empresaId é aceito do cliente


def test_isolamento_entre_empresas(
    app, client: TestClient, client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    admin_b = _cliente_admin_de(app, outra_empresa, db_session)
    assert client_admin.patch(ADMIN, json={"corPrimaria": "#ff0000", "tema": "escuro"}).status_code == 200
    assert _upload(client_admin, png()).status_code == 200

    # B não enxerga nada de A
    assert admin_b.get(ADMIN).json()["padrao"] is True
    publica_b = client.get(PUBLICA, params={"empresaCodigo": outra_empresa.codigo_interno}).json()
    assert publica_b["corPrimaria"] == "#6366f1" and publica_b["logoDisponivel"] is False
    assert client.get(f"{PUBLICA}/logo", params={"empresaCodigo": outra_empresa.codigo_interno}).status_code == 404

    # B altera o seu e A continua intacta
    assert admin_b.patch(ADMIN, json={"tema": "claro", "corSecundaria": "#00ff00"}).status_code == 200
    a = client_admin.get(ADMIN).json()
    assert a["corPrimaria"] == "#ff0000" and a["tema"] == "escuro" and a["corSecundaria"] == "#7c3aed" and a["logoDisponivel"] is True


# --------------------------------------------------------------------------------------
# Cores / tema
# --------------------------------------------------------------------------------------


def test_atualiza_cores_e_tema_parcialmente(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    r1 = client_admin.patch(ADMIN, json={"corPrimaria": "#ABCDEF"})
    assert r1.status_code == 200
    assert r1.json()["corPrimaria"] == "#abcdef" and r1.json()["corSecundaria"] == "#7c3aed" and r1.json()["tema"] == "claro"
    assert r1.json()["padrao"] is False

    r2 = client_admin.patch(ADMIN, json={"tema": "escuro"})
    assert r2.json()["tema"] == "escuro" and r2.json()["corPrimaria"] == "#abcdef"  # o que não foi enviado não muda
    r3 = client_admin.patch(ADMIN, json={"tema": "claro", "corSecundaria": "#010203"})
    assert r3.json()["tema"] == "claro" and r3.json()["corSecundaria"] == "#010203"
    linhas = db_session.scalars(select(ConfiguracaoPersonalizacao).where(ConfiguracaoPersonalizacao.empresa_id == empresa.id)).all()
    assert len(linhas) == 1  # singleton


@pytest.mark.parametrize("valor", ["ff0000", "#fff", "#gggggg", "#12345", "#1234567", "red", "", "rgb(1,2,3)", "#12 456"])
def test_hex_invalido_422(client_admin: TestClient, valor: str) -> None:
    assert client_admin.patch(ADMIN, json={"corPrimaria": valor}).status_code == 422
    assert client_admin.patch(ADMIN, json={"corSecundaria": valor}).status_code == 422


def test_tema_invalido_422(client_admin: TestClient) -> None:
    for tema in ("sistema", "dark", "", "CLARO"):
        assert client_admin.patch(ADMIN, json={"tema": tema}).status_code == 422


def test_so_cores_e_tema_sao_configuraveis(client_admin: TestClient) -> None:
    """Fundo, texto, borda etc. NÃO são configuráveis (contraste controlado pelo design system)."""
    for campo in ("corFundo", "corTexto", "corBorda", "background", "corErro"):
        assert client_admin.patch(ADMIN, json={campo: "#000000"}).status_code == 422


# --------------------------------------------------------------------------------------
# Logo: aceitos
# --------------------------------------------------------------------------------------


def test_png_valido(client_admin: TestClient, client: TestClient, empresa: Empresa) -> None:
    conteudo = png()
    resposta = _upload(client_admin, conteudo)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["logoDisponivel"] is True and corpo["logoVersao"] and corpo["padrao"] is False

    servido = client.get(f"{PUBLICA}/logo", params={"empresaCodigo": empresa.codigo_interno})
    assert servido.status_code == 200
    assert servido.headers["content-type"] == "image/png"
    assert servido.headers["x-content-type-options"] == "nosniff"
    assert servido.content == conteudo


@pytest.mark.parametrize("versao", [b"GIF87a", b"GIF89a"])
def test_gif_valido_87a_e_89a(client_admin: TestClient, client: TestClient, empresa: Empresa, versao: bytes) -> None:
    conteudo = gif(versao=versao)
    resposta = _upload(client_admin, conteudo, "logo.gif", "image/gif")
    assert resposta.status_code == 200, resposta.text
    servido = client.get(f"{PUBLICA}/logo", params={"empresaCodigo": empresa.codigo_interno})
    assert servido.headers["content-type"] == "image/gif" and servido.content == conteudo


def test_gif_animado_e_gravado_byte_a_byte(client_admin: TestClient, client: TestClient, empresa: Empresa) -> None:
    animado = gif(quadros=3)
    assert _upload(client_admin, animado, "anim.GIF", "image/gif").status_code == 200  # extensão em maiúsculas
    servido = client.get(f"{PUBLICA}/logo", params={"empresaCodigo": empresa.codigo_interno}).content
    assert servido == animado  # nada de recompressão/conversão: os quadros continuam lá
    assert servido.count(b"\x2c") >= 3


def test_nome_do_arquivo_nunca_vira_caminho(client_admin: TestClient, empresa: Empresa) -> None:
    antes = _arquivos_em_disco()
    resposta = _upload(client_admin, png(), "../../../etc/passwd.png", "image/png")
    assert resposta.status_code == 200
    novos = _arquivos_em_disco() - antes
    assert len(novos) == 1
    (chave,) = novos
    partes = Path(chave).parts
    assert partes[0] == "personalizacao" and partes[1] == empresa.id
    assert "passwd" not in chave and ".." not in chave
    assert "personalizacao/" not in resposta.text and "uploads" not in resposta.text  # path interno nunca vaza


# --------------------------------------------------------------------------------------
# Logo: recusados
# --------------------------------------------------------------------------------------


def test_dimensao_errada(client_admin: TestClient) -> None:
    for largura, altura in ((321, 132), (320, 133), (132, 320), (640, 264), (1, 1)):
        resposta = _upload(client_admin, png(largura, altura))
        assert resposta.status_code == 422, (largura, altura)
        assert "320" in resposta.json()["detail"]
    assert _upload(client_admin, gif(300, 132), "l.gif", "image/gif").status_code == 422


def test_mime_falso_e_extensao_falsa(client_admin: TestClient) -> None:
    # bytes de GIF dizendo ser PNG (Content-Type e/ou extensão)
    assert _upload(client_admin, gif(), "logo.png", "image/png").status_code == 422
    assert _upload(client_admin, gif(), "logo.gif", "image/png").status_code == 422
    assert _upload(client_admin, png(), "logo.gif", "image/png").status_code == 422
    assert _upload(client_admin, png(), "logo.png", "image/gif").status_code == 422
    # texto/HTML/executável com extensão e MIME de imagem
    assert _upload(client_admin, b"<html><script>alert(1)</script></html>", "logo.png", "image/png").status_code == 422
    assert _upload(client_admin, b"MZ\x90\x00" + b"\x00" * 200, "logo.png", "image/png").status_code == 422
    # PNG de verdade com Content-Type de outra coisa
    assert _upload(client_admin, png(), "logo.png", "text/html").status_code == 422
    assert _upload(client_admin, png(), "logo.html", "image/png").status_code == 422


def test_svg_e_jpeg_recusados(client_admin: TestClient) -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="132"><script>alert(1)</script></svg>'
    assert _upload(client_admin, svg, "logo.svg", "image/svg+xml").status_code == 422
    assert _upload(client_admin, svg, "logo.png", "image/png").status_code == 422
    jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 64 + b"\xff\xd9"
    assert _upload(client_admin, jpeg, "logo.jpg", "image/jpeg").status_code == 422
    assert _upload(client_admin, jpeg, "logo.png", "image/png").status_code == 422
    webp = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 32
    assert _upload(client_admin, webp, "logo.webp", "image/webp").status_code == 422


def test_acima_de_2mb(client_admin: TestClient) -> None:
    grande = png() + b"\x00" * (LOGO_MAX_BYTES + 10)
    assert _upload(client_admin, grande).status_code == 413
    assert _upload(client_admin, b"\x89PNG\r\n\x1a\n" + b"\x00" * LOGO_MAX_BYTES).status_code == 413


def test_vazio_truncado_e_corrompido(client_admin: TestClient) -> None:
    assert _upload(client_admin, b"").status_code == 422
    inteiro = png()
    assert _upload(client_admin, inteiro[:-20]).status_code == 422  # sem IEND
    assert _upload(client_admin, inteiro[:20]).status_code == 422
    corrompido = bytearray(inteiro)
    corrompido[24] ^= 0x01  # altera a profundidade de bits no IHDR (dimensões intactas): o CRC deixa de bater
    assert _upload(client_admin, bytes(corrompido)).status_code == 422
    g = gif()
    assert _upload(client_admin, g[:-1], "l.gif", "image/gif").status_code == 422  # sem trailer
    assert _upload(client_admin, b"GIF89a", "l.gif", "image/gif").status_code == 422


def test_recusa_nao_altera_nada(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    antes = _arquivos_em_disco()
    assert _upload(client_admin, png(10, 10)).status_code == 422
    assert _arquivos_em_disco() == antes
    assert db_session.scalars(select(ConfiguracaoPersonalizacao).where(ConfiguracaoPersonalizacao.empresa_id == empresa.id)).first() is None


# --------------------------------------------------------------------------------------
# Troca, remoção, restauração, cache
# --------------------------------------------------------------------------------------


def test_troca_de_logo_remove_o_antigo_e_muda_a_versao(client_admin: TestClient, client: TestClient, empresa: Empresa) -> None:
    v1 = _upload(client_admin, png(cor=10)).json()["logoVersao"]
    arquivos_1 = _arquivos_em_disco()
    assert len(arquivos_1) == 1

    novo = gif(quadros=2)
    v2 = _upload(client_admin, novo, "novo.gif", "image/gif").json()["logoVersao"]
    assert v1 != v2
    arquivos_2 = _arquivos_em_disco()
    assert len(arquivos_2) == 1 and arquivos_2 != arquivos_1  # o antigo foi apagado, só existe o novo
    servido = client.get(f"{PUBLICA}/logo", params={"empresaCodigo": empresa.codigo_interno})
    assert servido.headers["content-type"] == "image/gif" and servido.content == novo


def test_falha_no_banco_na_troca_preserva_o_logo_anterior(client_admin: TestClient, db_session: Session, empresa: Empresa, monkeypatch) -> None:
    assert _upload(client_admin, png(cor=1)).status_code == 200
    antes = _arquivos_em_disco()
    publica_antes = client_admin.get(ADMIN).json()

    def explode(self, db, configuracao):
        raise RuntimeError("falha simulada do banco")

    resposta = None
    with monkeypatch.context() as patch:  # só este patch: o do diretório de uploads (autouse) continua
        patch.setattr("app.repositories.configuracao_personalizacao_repository.ConfiguracaoPersonalizacaoRepository.update", explode)
        try:
            resposta = _upload(client_admin, png(cor=2))
        except RuntimeError:
            pass
    assert resposta is None or resposta.status_code >= 500
    assert _arquivos_em_disco() == antes  # o arquivo novo foi descartado; o antigo continua
    assert client_admin.get(ADMIN).json()["logoVersao"] == publica_antes["logoVersao"]


def test_cache_busting_e_headers(client_admin: TestClient, client: TestClient, empresa: Empresa) -> None:
    versao = _upload(client_admin, png()).json()["logoVersao"]
    codigo = {"empresaCodigo": empresa.codigo_interno}
    com_versao = client.get(f"{PUBLICA}/logo", params={**codigo, "v": versao})
    assert "immutable" in com_versao.headers["cache-control"]
    sem_versao = client.get(f"{PUBLICA}/logo", params=codigo)
    errada = client.get(f"{PUBLICA}/logo", params={**codigo, "v": "antiga"})
    assert sem_versao.headers["cache-control"] == "no-cache" and errada.headers["cache-control"] == "no-cache"
    for r in (com_versao, sem_versao, errada):
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["content-type"] == "image/png"
    assert client.get(PUBLICA, params=codigo).json()["logoVersao"] == versao


def test_remover_logo(client_admin: TestClient, client: TestClient, empresa: Empresa) -> None:
    _upload(client_admin, png())
    client_admin.patch(ADMIN, json={"tema": "escuro"})
    resposta = client_admin.delete(f"{ADMIN}/logo")
    assert resposta.status_code == 200
    assert resposta.json()["logoDisponivel"] is False and resposta.json()["logoVersao"] is None
    assert resposta.json()["tema"] == "escuro"  # só o logo some
    assert _arquivos_em_disco() == set()
    assert client.get(f"{PUBLICA}/logo", params={"empresaCodigo": empresa.codigo_interno}).status_code == 404
    assert client_admin.delete(f"{ADMIN}/logo").status_code == 200  # idempotente


def test_restaurar_padrao(client_admin: TestClient, client: TestClient, db_session: Session, empresa: Empresa) -> None:
    _upload(client_admin, gif(), "l.gif", "image/gif")
    client_admin.patch(ADMIN, json={"corPrimaria": "#123456", "corSecundaria": "#654321", "tema": "escuro"})
    resposta = client_admin.delete(ADMIN)
    assert resposta.status_code == 200
    assert resposta.json() == {
        "corPrimaria": "#6366f1",
        "corSecundaria": "#7c3aed",
        "tema": "claro",
        "logoDisponivel": False,
        "logoVersao": None,
        "padrao": True,
    }
    assert _arquivos_em_disco() == set()
    assert db_session.scalars(select(ConfiguracaoPersonalizacao).where(ConfiguracaoPersonalizacao.empresa_id == empresa.id)).first() is None
    assert client.get(PUBLICA, params={"empresaCodigo": empresa.codigo_interno}).json()["padrao"] is True
    assert client_admin.delete(ADMIN).status_code == 200  # sem linha: continua OK


def test_restaurar_nao_afeta_outra_empresa(app, client_admin: TestClient, db_session: Session, outra_empresa: Empresa) -> None:
    admin_b = _cliente_admin_de(app, outra_empresa, db_session)
    admin_b.patch(ADMIN, json={"tema": "escuro"})
    _upload(admin_b, png())
    client_admin.patch(ADMIN, json={"tema": "escuro"})
    client_admin.delete(ADMIN)
    b = admin_b.get(ADMIN).json()
    assert b["tema"] == "escuro" and b["logoDisponivel"] is True


# --------------------------------------------------------------------------------------
# Unidade: a inspeção só lê cabeçalhos (sem decodificar pixels)
# --------------------------------------------------------------------------------------


def test_service_inspeciona_cabecalhos() -> None:
    svc = ConfiguracaoPersonalizacaoService
    assert svc is not None
    from app.services.configuracao_personalizacao_service import inspecionar_logo

    assert inspecionar_logo(png()) == ("image/png", LOGO_LARGURA, LOGO_ALTURA)
    assert inspecionar_logo(gif()) == ("image/gif", LOGO_LARGURA, LOGO_ALTURA)
    assert LOGO_MAX_BYTES == 2 * 1024 * 1024
