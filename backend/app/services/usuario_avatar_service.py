"""Foto de perfil do usuário (PNG ou JPEG até 5 MB).

Mesma disciplina do logo da empresa: os BYTES mandam (assinatura, estrutura, fim de arquivo); extensão e
Content-Type declarados só podem concordar com eles; o nome enviado nunca vira caminho (o nome físico é
gerado aqui); o arquivo fica no volume de uploads — nunca no banco; troca = grava novo → persiste → remove o
anterior, e falha de banco descarta o arquivo novo. Sem biblioteca de imagem: nada é decodificado.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.services import demanda_arquivo_service

AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_LADO_MAX = 10_000  # trava contra "bomba de descompressão" no navegador; não exige dimensão exata

MIME_PNG = "image/png"
MIME_JPEG = "image/jpeg"
_EXTENSOES_POR_MIME = {MIME_PNG: {".png"}, MIME_JPEG: {".jpg", ".jpeg"}}
_EXTENSAO_FISICA = {MIME_PNG: ".png", MIME_JPEG: ".jpg"}
_PASTA = "usuarios"

_PNG_ASSINATURA = b"\x89PNG\r\n\x1a\n"
_PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"
# marcadores SOFn (início de quadro) — exceto DHT (C4), JPG (C8) e DAC (CC)
_JPEG_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


class AvatarInvalidoError(ValueError):
    """Foto recusada (formato, integridade ou declaração incoerente) — vira 422."""


class AvatarMuitoGrandeError(ValueError):
    """Foto acima de `AVATAR_MAX_BYTES` — vira 413."""


class AvatarNaoEncontradoError(ValueError):
    """Usuário sem foto própria (ou arquivo ausente do disco) — vira 404."""


def _inspecionar_png(conteudo: bytes) -> tuple[int, int]:
    if len(conteudo) < 33 or conteudo[8:12] != b"\x00\x00\x00\x0d" or conteudo[12:16] != b"IHDR":
        raise AvatarInvalidoError("PNG inválido: cabeçalho IHDR ausente ou corrompido.")
    (crc_declarado,) = struct.unpack(">I", conteudo[29:33])
    if zlib.crc32(conteudo[12:29]) & 0xFFFFFFFF != crc_declarado:
        raise AvatarInvalidoError("PNG inválido: cabeçalho corrompido.")
    if not conteudo.endswith(_PNG_IEND):
        raise AvatarInvalidoError("PNG inválido: arquivo truncado.")
    largura, altura = struct.unpack(">II", conteudo[16:24])
    return largura, altura


def _inspecionar_jpeg(conteudo: bytes) -> tuple[int, int]:
    """Percorre os segmentos até o início da varredura (SOS), validando tamanhos e achando as dimensões
    no marcador SOF. Exige o fim de arquivo (EOI) — um JPEG cortado não termina em FFD9."""
    if len(conteudo) < 4 or conteudo[:3] != b"\xff\xd8\xff":
        raise AvatarInvalidoError("JPEG inválido: assinatura ausente.")
    if not conteudo.rstrip(b"\x00").endswith(b"\xff\xd9"):
        raise AvatarInvalidoError("JPEG inválido: arquivo truncado.")
    posicao = 2
    dimensoes: tuple[int, int] | None = None
    while posicao + 4 <= len(conteudo):
        if conteudo[posicao] != 0xFF:
            raise AvatarInvalidoError("JPEG inválido: estrutura corrompida.")
        marcador = conteudo[posicao + 1]
        if marcador == 0xFF:  # preenchimento
            posicao += 1
            continue
        if marcador in (0x01, *range(0xD0, 0xD9)):  # marcadores sem comprimento
            posicao += 2
            continue
        (comprimento,) = struct.unpack(">H", conteudo[posicao + 2 : posicao + 4])
        if comprimento < 2 or posicao + 2 + comprimento > len(conteudo):
            raise AvatarInvalidoError("JPEG inválido: segmento truncado.")
        if marcador in _JPEG_SOF:
            if comprimento < 8:
                raise AvatarInvalidoError("JPEG inválido: quadro corrompido.")
            altura, largura = struct.unpack(">HH", conteudo[posicao + 5 : posicao + 9])
            dimensoes = (largura, altura)
        if marcador == 0xDA:  # SOS — dados comprimidos a partir daqui
            break
        posicao += 2 + comprimento
    if dimensoes is None:
        raise AvatarInvalidoError("JPEG inválido: dimensões ausentes.")
    return dimensoes


def inspecionar_avatar(conteudo: bytes) -> tuple[str, int, int]:
    """(mime canônico, largura, altura) lidos dos bytes. Levanta `AvatarInvalidoError` se não for um
    PNG/JPEG íntegro."""
    if conteudo.startswith(_PNG_ASSINATURA):
        largura, altura = _inspecionar_png(conteudo)
        mime = MIME_PNG
    elif conteudo.startswith(b"\xff\xd8"):
        largura, altura = _inspecionar_jpeg(conteudo)
        mime = MIME_JPEG
    else:
        raise AvatarInvalidoError("Formato não aceito: envie um arquivo PNG ou JPEG.")
    if largura < 1 or altura < 1:
        raise AvatarInvalidoError("Imagem inválida: dimensões nulas.")
    if largura > AVATAR_LADO_MAX or altura > AVATAR_LADO_MAX:
        raise AvatarInvalidoError(f"Imagem grande demais (máximo {AVATAR_LADO_MAX} px de lado).")
    return mime, largura, altura


def validar_avatar(conteudo: bytes, *, nome_arquivo: str | None, content_type: str | None) -> str:
    """Valida tudo e devolve o MIME canônico (os bytes mandam)."""
    if not conteudo:
        raise AvatarInvalidoError("Arquivo vazio.")
    if len(conteudo) > AVATAR_MAX_BYTES:
        raise AvatarMuitoGrandeError("Arquivo acima do limite de 5 MB.")
    mime, _largura, _altura = inspecionar_avatar(conteudo)
    extensao = Path(nome_arquivo or "").suffix.lower()
    if extensao and extensao not in _EXTENSOES_POR_MIME[mime]:
        raise AvatarInvalidoError("A extensão do arquivo não corresponde ao seu conteúdo.")
    declarado = (content_type or "").split(";")[0].strip().lower()
    if declarado and declarado != mime:
        raise AvatarInvalidoError("O tipo declarado do arquivo não corresponde ao seu conteúdo.")
    return mime


def versao_do_avatar(storage_key: str | None) -> str | None:
    """Identificador gerado do arquivo (sem pasta e sem extensão) — vai na URL para quebrar o cache."""
    return Path(storage_key).stem[:16] if storage_key else None


def url_do_avatar(usuario: Usuario) -> str | None:
    """Caminho (relativo à API) da foto própria, ou `None`. Não expõe o caminho do arquivo."""
    versao = versao_do_avatar(usuario.foto_perfil_storage_key)
    return f"/usuarios/{usuario.id}/avatar?v={versao}" if versao else None


class UsuarioAvatarService:
    def __init__(self, repository: UsuarioRepository | None = None) -> None:
        self.repository = repository or UsuarioRepository()

    @staticmethod
    def _raiz() -> Path:
        # lido na hora da chamada: a fixture autouse dos testes redireciona UPLOADS_ROOT
        return Path(demanda_arquivo_service.UPLOADS_ROOT)

    def _remover_arquivo(self, chave: str | None) -> None:
        if not chave:
            return
        try:
            (self._raiz() / chave).unlink(missing_ok=True)
        except OSError:
            pass  # arquivo órfão não derruba a operação; a referência já foi trocada

    def salvar(
        self, db: Session, usuario: Usuario, *, conteudo: bytes, nome_arquivo: str | None, content_type: str | None
    ) -> Usuario:
        mime = validar_avatar(conteudo, nome_arquivo=nome_arquivo, content_type=content_type)
        nova_chave = f"{_PASTA}/{usuario.empresa_id}/{usuario.id}/{uuid4().hex}{_EXTENSAO_FISICA[mime]}"
        caminho = self._raiz() / nova_chave
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo)

        chave_antiga = usuario.foto_perfil_storage_key
        usuario.foto_perfil_storage_key = nova_chave
        usuario.foto_perfil_mime_type = mime
        usuario.updated_at = agora_utc()
        try:
            self.repository.update(db, usuario)
            db.commit()
        except Exception:
            db.rollback()
            caminho.unlink(missing_ok=True)  # não deixa o arquivo novo órfão
            raise
        self._remover_arquivo(chave_antiga)
        return usuario

    def remover(self, db: Session, usuario: Usuario) -> Usuario:
        chave_antiga = usuario.foto_perfil_storage_key
        if chave_antiga is None:
            return usuario
        usuario.foto_perfil_storage_key = None
        usuario.foto_perfil_mime_type = None
        usuario.updated_at = agora_utc()
        self.repository.update(db, usuario)
        db.commit()
        self._remover_arquivo(chave_antiga)
        return usuario

    def ler(self, usuario: Usuario) -> tuple[Path, str, str]:
        """(caminho, mime canônico, versão) para servir a foto. Sem foto ou sem arquivo → 404."""
        chave = usuario.foto_perfil_storage_key
        if not chave or not usuario.foto_perfil_mime_type:
            raise AvatarNaoEncontradoError("Usuário sem foto de perfil.")
        caminho = self._raiz() / chave
        if not caminho.is_file():
            raise AvatarNaoEncontradoError("Foto de perfil indisponível.")
        return caminho, usuario.foto_perfil_mime_type, versao_do_avatar(chave) or ""
