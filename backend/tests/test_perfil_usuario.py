"""Perfil do usuário: autoedição restrita (telefone + cor), foto de perfil PNG/JPEG validada pelos bytes (5 MB),
isolamento entre empresas, nosniff, caminho seguro e último acesso."""

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
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.services.usuario_avatar_service import AVATAR_MAX_BYTES, inspecionar_avatar

ME = "/usuarios/me"
AVATAR = "/usuarios/me/avatar"


# ------------------------------------------------------------------ builders (sem Pillow)
def _chunk(tipo: bytes, dados: bytes) -> bytes:
    return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)


def png(largura: int = 64, altura: int = 48, *, cor: int = 0) -> bytes:
    linha = b"\x00" + bytes([cor]) * (largura * 3)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(linha * altura))
        + _chunk(b"IEND", b"")
    )


def jpeg(largura: int = 80, altura: int = 60, *, preenchimento: int = 32) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc0" + struct.pack(">H", 11) + b"\x08" + struct.pack(">HH", altura, largura) + b"\x01\x01\x11\x00"
    sos = b"\xff\xda" + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x3f\x00"
    return b"\xff\xd8" + app0 + sof + sos + b"\x12" * preenchimento + b"\xff\xd9"


def _upload(client: TestClient, conteudo: bytes, nome: str = "foto.png", tipo: str = "image/png"):
    return client.post(AVATAR, files={"arquivo": (nome, conteudo, tipo)})


def _client_de(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)}"
    return cliente


def _usuario(db: Session, empresa: Empresa, perfil: str = "operador") -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"p-{sufixo}", nome=f"Perfil {sufixo}",
        email=f"perfil-{sufixo}@teste.local", perfil_base=perfil, acesso_sistema=True, status="ativo",
        is_system_account=False, created_at=agora, updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _arquivos() -> set[str]:
    raiz = Path(demanda_arquivo_service.UPLOADS_ROOT)
    return {str(p.relative_to(raiz)) for p in raiz.rglob("*") if p.is_file()} if raiz.exists() else set()


# ------------------------------------------------------------------ leitura / telefone
def test_usuario_le_o_proprio_perfil(client_operador: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_operador.get(ME)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == usuario_operador.id
    assert corpo["nome"] == usuario_operador.nome and corpo["email"] == usuario_operador.email
    assert "ultimoAcesso" in corpo


@pytest.mark.parametrize(
    "entrada,esperado",
    [("(11) 91234-5678", "11912345678"), ("11 3333-4444", "1133334444"), ("+55 (11) 91234-5678", "+5511912345678"), ("  ", None), ("", None)],
)
def test_atualiza_telefone_normalizado(client_operador: TestClient, entrada: str, esperado: str | None) -> None:
    resposta = client_operador.patch(ME, json={"telefone": entrada})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["telefone"] == esperado
    assert client_operador.get(ME).json()["telefone"] == esperado


@pytest.mark.parametrize("ruim", ["abc", "12", "1234567", "11 99999-99a9", "1" * 16, "<script>"])
def test_telefone_invalido_422(client_operador: TestClient, ruim: str) -> None:
    assert client_operador.patch(ME, json={"telefone": ruim}).status_code == 422


@pytest.mark.parametrize(
    "campo,valor",
    [("nome", "Outro Nome"), ("sobrenome", "X"), ("email", "novo@teste.local"), ("perfilBase", "admin"), ("perfil", "admin"),
     ("status", "inativo"), ("departamentoId", str(uuid.uuid4())), ("empresaId", str(uuid.uuid4())), ("permissoes", ["x"]),
     ("acessoSistema", False), ("cargo", "Diretor"), ("cpf", "123"), ("usuarioId", str(uuid.uuid4()))],
)
def test_campos_proibidos_no_autoatendimento_422(client_operador: TestClient, usuario_operador: Usuario, db_session: Session, campo: str, valor) -> None:
    nome, email, perfil = usuario_operador.nome, usuario_operador.email, usuario_operador.perfil_base
    resposta = client_operador.patch(ME, json={"telefone": "11912345678", campo: valor})
    assert resposta.status_code == 422, resposta.text
    db_session.refresh(usuario_operador)
    assert (usuario_operador.nome, usuario_operador.email, usuario_operador.perfil_base) == (nome, email, perfil)
    assert usuario_operador.telefone != "11912345678", "nada é aplicado quando o corpo é recusado"


def test_nao_altera_outro_usuario_e_tenant_isolado(app, client_operador: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    de_la = _usuario(db_session, outra_empresa)
    mesmo_tenant = _usuario(db_session, empresa)
    client_operador.patch(ME, json={"telefone": "11912345678"})
    db_session.refresh(de_la)
    db_session.refresh(mesmo_tenant)
    assert de_la.telefone is None and mesmo_tenant.telefone is None


def test_edicao_administrativa_continua_funcionando(client_admin: TestClient, usuario_operador: Usuario, db_session: Session) -> None:
    resposta = client_admin.patch(f"/usuarios/{usuario_operador.id}", json={"telefone": "11999990000"})
    assert resposta.status_code == 200, resposta.text
    db_session.refresh(usuario_operador)
    assert usuario_operador.telefone == "11999990000"


# ------------------------------------------------------------------ avatar: aceitos
def test_upload_png_e_jpeg_validos(client_operador: TestClient) -> None:
    r1 = _upload(client_operador, png())
    assert r1.status_code == 200, r1.text
    assert r1.json()["fotoUrl"].startswith("/usuarios/") and "/avatar?v=" in r1.json()["fotoUrl"]
    r2 = _upload(client_operador, jpeg(), "foto.jpg", "image/jpeg")
    assert r2.status_code == 200, r2.text
    assert r2.json()["fotoUrl"] != r1.json()["fotoUrl"], "a versão muda a cada troca"


def test_servir_avatar_com_headers_seguros_e_cache_por_versao(client_operador: TestClient, usuario_operador: Usuario) -> None:
    conteudo = png(cor=9)
    url = _upload(client_operador, conteudo).json()["fotoUrl"]
    resposta = client_operador.get(url)
    assert resposta.status_code == 200
    assert resposta.content == conteudo
    assert resposta.headers["content-type"] == "image/png"
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert "immutable" in resposta.headers["cache-control"]
    sem_versao = client_operador.get(f"/usuarios/{usuario_operador.id}/avatar")
    assert "immutable" not in sem_versao.headers["cache-control"]
    assert "uploads" not in resposta.text.lower()


def test_jpeg_servido_com_mime_canonico(client_operador: TestClient) -> None:
    url = _upload(client_operador, jpeg(), "x.jpeg", "image/jpeg").json()["fotoUrl"]
    assert client_operador.get(url).headers["content-type"] == "image/jpeg"


def test_nome_do_arquivo_nunca_vira_caminho(client_operador: TestClient, usuario_operador: Usuario) -> None:
    antes = _arquivos()
    assert _upload(client_operador, png(), "../../etc/passwd.png").status_code == 200
    novos = _arquivos() - antes
    assert len(novos) == 1
    caminho = novos.pop().replace("\\", "/")
    assert caminho.startswith(f"usuarios/{usuario_operador.empresa_id}/{usuario_operador.id}/")
    assert "passwd" not in caminho and ".." not in caminho


def test_qualquer_proporcao_e_aceita(client_operador: TestClient) -> None:
    assert _upload(client_operador, png(512, 512)).status_code == 200
    assert _upload(client_operador, png(1200, 300)).status_code == 200


# ------------------------------------------------------------------ avatar: recusados
@pytest.mark.parametrize(
    "conteudo,nome,tipo",
    [
        (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "a.svg", "image/svg+xml"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", "a.png", "image/png"),  # SVG disfarçado de PNG
        (b"<html><script>1</script></html>", "a.png", "image/png"),
        (b"%PDF-1.4\n%%EOF", "a.png", "image/png"),
        (b"MZ\x90\x00\x03", "a.jpg", "image/jpeg"),
        (b"GIF89a\x01\x00\x01\x00\x00\x00\x00;", "a.gif", "image/gif"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "a.webp", "image/webp"),
        (b"", "vazio.png", "image/png"),
    ],
)
def test_formatos_recusados_422(client_operador: TestClient, conteudo: bytes, nome: str, tipo: str) -> None:
    antes = _arquivos()
    assert _upload(client_operador, conteudo, nome, tipo).status_code == 422
    assert _arquivos() == antes, "recusa não deixa arquivo"


def test_mime_falso_ou_extensao_falsa_422(client_operador: TestClient) -> None:
    assert _upload(client_operador, png(), "foto.png", "image/jpeg").status_code == 422  # MIME declarado ≠ bytes
    assert _upload(client_operador, png(), "foto.jpg", "image/png").status_code == 422  # extensão ≠ bytes
    assert _upload(client_operador, jpeg(), "foto.png", "image/jpeg").status_code == 422
    assert _upload(client_operador, png(), "foto.exe", "image/png").status_code == 422


def test_acima_de_5mb_413(client_operador: TestClient) -> None:
    grande = png() + b"\x00" * (AVATAR_MAX_BYTES + 10)
    assert _upload(client_operador, grande).status_code == 413
    exato_limite = jpeg(preenchimento=AVATAR_MAX_BYTES - 200)
    assert len(exato_limite) <= AVATAR_MAX_BYTES
    assert _upload(client_operador, exato_limite, "g.jpg", "image/jpeg").status_code == 200


def test_arquivos_truncados_ou_corrompidos_422(client_operador: TestClient) -> None:
    base = png()
    corrompido = bytearray(base)
    corrompido[24] ^= 0x01  # bit do IHDR com a CRC intacta
    for ruim, nome, tipo in [
        (base[:-5], "a.png", "image/png"),  # sem IEND
        (base[:20], "a.png", "image/png"),
        (bytes(corrompido), "a.png", "image/png"),  # CRC do cabeçalho
        (jpeg()[:-2], "a.jpg", "image/jpeg"),  # sem EOI
        (jpeg()[:30], "a.jpg", "image/jpeg"),  # segmento cortado
        (b"\xff\xd8\xff\xe0" + b"\x00" * 10 + b"\xff\xd9", "a.jpg", "image/jpeg"),  # sem SOF
    ]:
        assert _upload(client_operador, ruim, nome, tipo).status_code == 422, nome


def test_dimensoes_absurdas_422() -> None:
    from app.services.usuario_avatar_service import AvatarInvalidoError

    with pytest.raises(AvatarInvalidoError):
        inspecionar_avatar(png(10_001, 1))
    with pytest.raises(AvatarInvalidoError):
        inspecionar_avatar(png(0, 5))


def test_recusa_nao_altera_a_foto_atual(client_operador: TestClient) -> None:
    url = _upload(client_operador, png(cor=1)).json()["fotoUrl"]
    antes = _arquivos()
    assert _upload(client_operador, b"lixo").status_code == 422
    assert client_operador.get(ME).json()["fotoUrl"] == url
    assert _arquivos() == antes


# ------------------------------------------------------------------ troca / remoção
def test_troca_remove_o_arquivo_antigo_e_muda_a_versao(client_operador: TestClient) -> None:
    antes = _arquivos()
    url1 = _upload(client_operador, png(cor=1)).json()["fotoUrl"]
    primeiro = _arquivos() - antes
    url2 = _upload(client_operador, jpeg(), "f.jpg", "image/jpeg").json()["fotoUrl"]
    depois = _arquivos() - antes
    assert len(primeiro) == 1 and len(depois) == 1 and primeiro != depois
    assert url1 != url2
    assert client_operador.get(url2).status_code == 200


def test_remover_foto_apaga_arquivo_e_volta_ao_fallback(client_operador: TestClient, usuario_operador: Usuario, db_session: Session) -> None:
    antes = _arquivos()
    _upload(client_operador, png())
    resposta = client_operador.delete(AVATAR)
    assert resposta.status_code == 200
    assert resposta.json()["fotoUrl"] is None
    assert _arquivos() == antes
    db_session.refresh(usuario_operador)
    assert usuario_operador.foto_perfil_storage_key is None and usuario_operador.foto_perfil_mime_type is None
    assert client_operador.get(f"/usuarios/{usuario_operador.id}/avatar").status_code == 404
    assert client_operador.delete(AVATAR).status_code == 200  # idempotente


def test_falha_de_banco_nao_deixa_arquivo_orfao_e_preserva_a_foto(client_operador: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    url = _upload(client_operador, png(cor=1)).json()["fotoUrl"]
    antes = _arquivos()

    def estourar(self, db, usuario):  # noqa: ANN001
        raise RuntimeError("falha de banco simulada")

    with monkeypatch.context() as patch:  # `undo()` desfaria também o isolamento de uploads (autouse)
        patch.setattr("app.services.usuario_avatar_service.UsuarioRepository.update", estourar)
        with pytest.raises(RuntimeError):
            _upload(client_operador, png(cor=2))
    assert _arquivos() == antes, "o arquivo novo foi descartado e o antigo preservado"
    assert client_operador.get(ME).json()["fotoUrl"] == url


# ------------------------------------------------------------------ tenant / autoria do avatar
def test_avatar_de_colega_da_mesma_empresa_e_visivel_mas_nao_de_outra_empresa(app, client_operador: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa) -> None:
    colega = _usuario(db_session, empresa)
    cliente_colega = _client_de(app, colega)
    url = _upload(cliente_colega, png()).json()["fotoUrl"]
    assert client_operador.get(url).status_code == 200  # mesma empresa

    estranho = _client_de(app, _usuario(db_session, outra_empresa))
    assert estranho.get(url).status_code == 404  # tenant isolado
    assert estranho.get(f"/usuarios/{uuid.uuid4()}/avatar").status_code == 404  # inexistente = mesma resposta


def test_so_a_propria_foto_e_alterada(app, client_operador: TestClient, db_session: Session, empresa: Empresa) -> None:
    colega = _usuario(db_session, empresa)
    _upload(client_operador, png())
    db_session.refresh(colega)
    assert colega.foto_perfil_storage_key is None
    assert client_operador.post(f"/usuarios/{colega.id}/avatar", files={"arquivo": ("a.png", png(), "image/png")}).status_code in (404, 405)


def test_exige_autenticacao(app) -> None:
    anonimo = TestClient(app)
    assert anonimo.post(AVATAR, files={"arquivo": ("a.png", png(), "image/png")}).status_code in (401, 403)
    assert anonimo.get(f"/usuarios/{uuid.uuid4()}/avatar").status_code in (401, 403)
    assert anonimo.patch(ME, json={"telefone": "11912345678"}).status_code in (401, 403)


def test_foto_aparece_no_diretorio_e_o_google_continua_como_fallback(client_operador: TestClient, usuario_operador: Usuario, db_session: Session) -> None:
    usuario_operador.foto_url = "https://lh3.googleusercontent.com/a/x"
    db_session.flush()
    assert client_operador.get(ME).json()["fotoUrl"] == "https://lh3.googleusercontent.com/a/x"
    url = _upload(client_operador, png()).json()["fotoUrl"]
    itens = client_operador.get("/usuarios/diretorio").json()
    meu = next(i for i in itens if i["id"] == usuario_operador.id)
    assert meu["fotoUrl"] == url
    client_operador.delete(AVATAR)
    assert client_operador.get(ME).json()["fotoUrl"] == "https://lh3.googleusercontent.com/a/x"


# ------------------------------------------------------------------ último acesso
def test_ultimo_acesso_vem_do_ultimo_login_do_proprio_usuario(client_operador: TestClient, usuario_operador: Usuario, db_session: Session) -> None:
    assert client_operador.get(ME).json()["ultimoAcesso"] is None
    agora = datetime.now(timezone.utc)
    for ip, quando in (("10.0.0.1", agora.replace(microsecond=0)), ("10.0.0.2", agora.replace(microsecond=0))):
        db_session.add(Evento(
            id=str(uuid.uuid4()), empresa_id=usuario_operador.empresa_id, tipo="auth.login_sucesso", entidade_tipo="auth",
            entidade_id=usuario_operador.id, usuario_id=usuario_operador.id, payload={"ip_address": ip},
            occurred_at=quando, created_at=quando,
        ))
    db_session.flush()
    acesso = client_operador.get(ME).json()["ultimoAcesso"]
    assert acesso["ip"] in ("10.0.0.1", "10.0.0.2") and acesso["em"]
    # evento de OUTRO usuário nunca aparece
    outro_ip = db_session.scalars(select(Evento).where(Evento.usuario_id == usuario_operador.id)).all()
    assert len(outro_ip) == 2
