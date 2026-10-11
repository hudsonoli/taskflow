"""Personalização visual por Empresa: logo, cor principal, cor secundária e tema.

Regras de segurança do logo (todas no BACKEND — o frontend só antecipa a mensagem):
- só PNG e GIF; SVG/JPEG/qualquer outro formato é recusado;
- o formato é decidido pelos BYTES (assinatura + cabeçalho), nunca pela extensão nem pelo
  Content-Type enviado — e os três precisam concordar, ou o upload é recusado;
- dimensão EXATA 320 × 132 px, lida do cabeçalho (IHDR do PNG, tela lógica do GIF), sem
  decodificar nem reprocessar a imagem (GIF animado continua animado: os bytes são gravados como
  chegaram) e sem dependência nova;
- no máximo 2 MB; o nome físico é gerado pelo sistema (o nome enviado nunca vira caminho).
"""

from __future__ import annotations

import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.empresa_slug import validar_slug
from app.models.empresa import Empresa
from app.models.configuracao_personalizacao import (
    COR_PRIMARIA_PADRAO,
    COR_SECUNDARIA_PADRAO,
    TEMA_PADRAO,
    ConfiguracaoPersonalizacao,
)
from app.repositories.configuracao_personalizacao_repository import ConfiguracaoPersonalizacaoRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.configuracao_personalizacao import PersonalizacaoRead, PersonalizacaoUpdate, PublicoEmpresaBrandingRead
from app.services import demanda_arquivo_service

LOGO_LARGURA = 320
LOGO_ALTURA = 132
LOGO_MAX_BYTES = 2 * 1024 * 1024

_PNG_ASSINATURA = b"\x89PNG\r\n\x1a\n"
_PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"
_GIF_ASSINATURAS = (b"GIF87a", b"GIF89a")

MIME_PNG = "image/png"
MIME_GIF = "image/gif"
_EXTENSAO_POR_MIME = {MIME_PNG: ".png", MIME_GIF: ".gif"}
_PASTA = "personalizacao"


class PersonalizacaoLogoInvalidoError(ValueError):
    """Logo recusado (formato, dimensão, integridade ou declaração incoerente) — vira 422."""


class PersonalizacaoLogoMuitoGrandeError(ValueError):
    """Logo acima de `LOGO_MAX_BYTES` — vira 413."""


class PersonalizacaoLogoNaoEncontradoError(ValueError):
    """Sem logo personalizado (ou arquivo ausente do disco) — vira 404."""


def inspecionar_logo(conteudo: bytes) -> tuple[str, int, int]:
    """(mime canônico, largura, altura) lidos dos bytes. Levanta `PersonalizacaoLogoInvalidoError`
    se não for um PNG/GIF íntegro. Não decodifica pixels."""
    if conteudo.startswith(_PNG_ASSINATURA):
        # assinatura (8) + comprimento (4) + "IHDR" (4) + 13 bytes de dados + CRC (4) = 33
        if len(conteudo) < 33 or conteudo[8:12] != b"\x00\x00\x00\x0d" or conteudo[12:16] != b"IHDR":
            raise PersonalizacaoLogoInvalidoError("PNG inválido: cabeçalho IHDR ausente ou corrompido.")
        (crc_declarado,) = struct.unpack(">I", conteudo[29:33])
        if zlib.crc32(conteudo[12:29]) & 0xFFFFFFFF != crc_declarado:
            raise PersonalizacaoLogoInvalidoError("PNG inválido: cabeçalho corrompido.")
        if not conteudo.endswith(_PNG_IEND):
            raise PersonalizacaoLogoInvalidoError("PNG inválido: arquivo truncado.")
        largura, altura = struct.unpack(">II", conteudo[16:24])
        return MIME_PNG, largura, altura
    if conteudo[:6] in _GIF_ASSINATURAS:
        if len(conteudo) < 14:
            raise PersonalizacaoLogoInvalidoError("GIF inválido: arquivo truncado.")
        if not conteudo.endswith(b";"):
            raise PersonalizacaoLogoInvalidoError("GIF inválido: arquivo truncado.")
        largura, altura = struct.unpack("<HH", conteudo[6:10])
        return MIME_GIF, largura, altura
    raise PersonalizacaoLogoInvalidoError("Formato não aceito: envie um arquivo PNG ou GIF.")


def validar_logo(conteudo: bytes, *, nome_arquivo: str | None, content_type: str | None) -> str:
    """Valida tudo e devolve o MIME canônico. Os bytes mandam; extensão e Content-Type declarados
    só podem concordar com eles (nunca decidir)."""
    if not conteudo:
        raise PersonalizacaoLogoInvalidoError("Arquivo vazio.")
    if len(conteudo) > LOGO_MAX_BYTES:
        raise PersonalizacaoLogoMuitoGrandeError("Arquivo acima do limite de 2 MB.")

    mime, largura, altura = inspecionar_logo(conteudo)
    if (largura, altura) != (LOGO_LARGURA, LOGO_ALTURA):
        raise PersonalizacaoLogoInvalidoError(
            f"Dimensão inválida: o logo deve ter exatamente {LOGO_LARGURA} × {LOGO_ALTURA} px "
            f"(enviado: {largura} × {altura})."
        )

    extensao = Path(nome_arquivo or "").suffix.lower()
    if extensao and extensao != _EXTENSAO_POR_MIME[mime]:
        raise PersonalizacaoLogoInvalidoError("A extensão do arquivo não corresponde ao seu conteúdo.")
    declarado = (content_type or "").split(";")[0].strip().lower()
    if declarado and declarado != mime:
        raise PersonalizacaoLogoInvalidoError("O tipo declarado do arquivo não corresponde ao seu conteúdo.")
    return mime


def _versao_do_logo(storage_key: str | None) -> str | None:
    """Versão pública = identificador gerado do arquivo (sem a extensão, sem a pasta). Não expõe o
    caminho; muda a cada troca."""
    if not storage_key:
        return None
    return Path(storage_key).stem[:16]


class ConfiguracaoPersonalizacaoService:
    def __init__(
        self,
        repository: ConfiguracaoPersonalizacaoRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
    ) -> None:
        self.repository = repository or ConfiguracaoPersonalizacaoRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()

    # ------------------------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------------------------

    @staticmethod
    def _para_read(registro: ConfiguracaoPersonalizacao | None) -> PersonalizacaoRead:
        if registro is None:
            return PersonalizacaoRead(
                corPrimaria=COR_PRIMARIA_PADRAO,
                corSecundaria=COR_SECUNDARIA_PADRAO,
                tema=TEMA_PADRAO,
                logoDisponivel=False,
                logoVersao=None,
                padrao=True,
            )
        logo = registro.logo_storage_key is not None
        padrao = (
            not logo
            and registro.cor_primaria == COR_PRIMARIA_PADRAO
            and registro.cor_secundaria == COR_SECUNDARIA_PADRAO
            and registro.tema == TEMA_PADRAO
        )
        return PersonalizacaoRead(
            corPrimaria=registro.cor_primaria,
            corSecundaria=registro.cor_secundaria,
            tema=registro.tema,
            logoDisponivel=logo,
            logoVersao=_versao_do_logo(registro.logo_storage_key),
            padrao=padrao,
        )

    def get_ou_default(self, db: Session, *, empresa_id: str) -> PersonalizacaoRead:
        """Nunca cria a linha: sem registro, devolve os padrões atuais do TaskFlow."""
        return self._para_read(self.repository.get_by_empresa(db, empresa_id))

    def get_publico(self, db: Session, *, empresa_codigo: str) -> PersonalizacaoRead:
        """Branding antes do login. Código de empresa desconhecido devolve os PADRÕES (nunca 404):
        não revela quais códigos existem, e a tela de login nunca fica sem aparência."""
        empresa = self.empresa_repository.get_by_codigo_interno(db, empresa_codigo.strip().upper())
        if empresa is None:
            return self._para_read(None)
        return self._para_read(self.repository.get_by_empresa(db, empresa.id))

    def _empresa_ativa_por_slug(self, db: Session, slug: str) -> Empresa | None:
        """Empresa ATIVA do slug público, ou `None` (slug malformado, reservado, inexistente ou inativa — sem
        diferenciar). Empresa inativa nunca expõe identidade visual nem logo."""
        try:
            slug_valido = validar_slug(slug)
        except ValueError:
            return None
        empresa = self.empresa_repository.get_by_slug(db, slug_valido)
        if empresa is None or empresa.status != "ativa":
            return None
        return empresa

    def get_publico_por_slug(self, db: Session, *, slug: str) -> PublicoEmpresaBrandingRead:
        empresa = self._empresa_ativa_por_slug(db, slug)
        if empresa is None:
            base = self._para_read(None)
            return PublicoEmpresaBrandingRead(**base.model_dump(by_alias=True), disponivel=False, nomeExibicao=None)
        return self.get_publico_da_empresa(db, empresa)

    def get_publico_da_empresa(self, db: Session, empresa: Empresa) -> PublicoEmpresaBrandingRead:
        """Branding público de uma empresa JÁ resolvida por quem chama (ex.: Portal de Aprovação, que a deriva do token — nunca de dado do
        cliente). Quem chama garante que a empresa está ativa."""
        base = self._para_read(self.repository.get_by_empresa(db, empresa.id))
        return PublicoEmpresaBrandingRead(
            **base.model_dump(by_alias=True), disponivel=True, nomeExibicao=empresa.nome_fantasia or empresa.nome
        )

    def ler_logo_da_empresa(self, db: Session, empresa: Empresa) -> tuple[Path, str, str]:
        """(caminho, mime, versão) do logo de uma empresa já resolvida (mesmo contrato de `ler_logo_publico_por_slug`)."""
        return self._logo_da_empresa(db, empresa)

    def ler_logo_publico_por_slug(self, db: Session, *, slug: str) -> tuple[Path, str, str]:
        empresa = self._empresa_ativa_por_slug(db, slug)
        if empresa is None:
            raise PersonalizacaoLogoNaoEncontradoError("Logo não encontrado")
        return self._logo_da_empresa(db, empresa)

    # ------------------------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------------------------

    def _get_ou_criar(self, db: Session, empresa_id: str) -> ConfiguracaoPersonalizacao:
        registro = self.repository.get_by_empresa(db, empresa_id)
        if registro is not None:
            return registro
        agora = datetime.now(timezone.utc)
        return self.repository.create(
            db,
            ConfiguracaoPersonalizacao(
                id=str(uuid4()),
                empresa_id=empresa_id,
                cor_primaria=COR_PRIMARIA_PADRAO,
                cor_secundaria=COR_SECUNDARIA_PADRAO,
                tema=TEMA_PADRAO,
                created_at=agora,
                updated_at=agora,
            ),
        )

    def atualizar(self, db: Session, *, empresa_id: str, payload: PersonalizacaoUpdate) -> PersonalizacaoRead:
        campos = payload.model_dump(exclude_unset=True, exclude_none=True)
        registro = self._get_ou_criar(db, empresa_id)
        if "cor_primaria" in campos:
            registro.cor_primaria = campos["cor_primaria"]
        if "cor_secundaria" in campos:
            registro.cor_secundaria = campos["cor_secundaria"]
        if "tema" in campos:
            registro.tema = campos["tema"]
        registro.updated_at = datetime.now(timezone.utc)
        self.repository.update(db, registro)
        db.commit()
        return self._para_read(registro)

    def restaurar_padrao(self, db: Session, *, empresa_id: str) -> PersonalizacaoRead:
        """Remove logo, cores e tema personalizados (apaga a linha e o arquivo). Não toca em nenhuma
        outra configuração da empresa."""
        registro = self.repository.get_by_empresa(db, empresa_id)
        if registro is None:
            return self._para_read(None)
        chave_antiga = registro.logo_storage_key
        self.repository.delete(db, registro)
        db.commit()
        self._remover_arquivo(chave_antiga)
        return self._para_read(None)

    # ------------------------------------------------------------------------------------
    # Logo
    # ------------------------------------------------------------------------------------

    @staticmethod
    def _caminho(chave: str) -> Path:
        return demanda_arquivo_service.UPLOADS_ROOT / chave

    def _remover_arquivo(self, chave: str | None) -> None:
        if chave:
            self._caminho(chave).unlink(missing_ok=True)

    def salvar_logo(
        self,
        db: Session,
        *,
        empresa_id: str,
        conteudo: bytes,
        nome_arquivo: str | None,
        content_type: str | None,
    ) -> PersonalizacaoRead:
        mime = validar_logo(conteudo, nome_arquivo=nome_arquivo, content_type=content_type)

        # 1) grava o arquivo novo (nome gerado pelo sistema); 2) persiste a referência; 3) só então
        # apaga o antigo. Se o banco falhar, o arquivo novo é descartado e a configuração continua
        # apontando para o logo anterior — nunca para um arquivo inexistente.
        nova_chave = f"{_PASTA}/{empresa_id}/{uuid4().hex}{_EXTENSAO_POR_MIME[mime]}"
        caminho = self._caminho(nova_chave)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo)
        registro = None
        try:
            registro = self._get_ou_criar(db, empresa_id)
            chave_antiga = registro.logo_storage_key
            registro.logo_storage_key = nova_chave
            registro.logo_mime_type = mime
            registro.updated_at = datetime.now(timezone.utc)
            self.repository.update(db, registro)
            db.commit()
        except Exception:
            db.rollback()
            caminho.unlink(missing_ok=True)
            raise
        self._remover_arquivo(chave_antiga)
        return self._para_read(registro)

    def remover_logo(self, db: Session, *, empresa_id: str) -> PersonalizacaoRead:
        registro = self.repository.get_by_empresa(db, empresa_id)
        if registro is None or registro.logo_storage_key is None:
            return self._para_read(registro)
        chave_antiga = registro.logo_storage_key
        registro.logo_storage_key = None
        registro.logo_mime_type = None
        registro.updated_at = datetime.now(timezone.utc)
        self.repository.update(db, registro)
        db.commit()
        self._remover_arquivo(chave_antiga)
        return self._para_read(registro)

    def ler_logo_publico(self, db: Session, *, empresa_codigo: str) -> tuple[Path, str, str]:
        """(caminho físico, mime canônico, versão) do logo da empresa, ou 404. O mime vem do banco
        (gravado a partir dos bytes validados), nunca do nome do arquivo."""
        empresa = self.empresa_repository.get_by_codigo_interno(db, empresa_codigo.strip().upper())
        if empresa is None:
            raise PersonalizacaoLogoNaoEncontradoError("Logo não encontrado")
        return self._logo_da_empresa(db, empresa)

    def _logo_da_empresa(self, db: Session, empresa: Empresa) -> tuple[Path, str, str]:
        registro = self.repository.get_by_empresa(db, empresa.id)
        if registro is None or registro.logo_storage_key is None or registro.logo_mime_type is None:
            raise PersonalizacaoLogoNaoEncontradoError("Logo não encontrado")
        caminho = self._caminho(registro.logo_storage_key)
        if not caminho.is_file():
            raise PersonalizacaoLogoNaoEncontradoError("Logo não encontrado")
        return caminho, registro.logo_mime_type, _versao_do_logo(registro.logo_storage_key) or ""
