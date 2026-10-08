from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import Row
from sqlalchemy.orm import Session

from app.core.escopo import EscopoDemanda
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.core.identidade_sistema import AUTOR_SISTEMA
from app.models.demanda_arquivo import DemandaArquivo
from app.repositories.demanda_arquivo_repository import DemandaArquivoRepository
from app.schemas.demanda_arquivo import (
    ArquivoCentralDemandaRead,
    ArquivoCentralRead,
    DemandaArquivoRead,
    validar_url_http_https,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "demanda"

# Gerenciador de Arquivos (migration 0036). `link` nunca é aceito no upload multipart
# (ALLOWED_TIPOS_UPLOAD) — tem endpoint dedicado (`criar_link`), porque não compartilha nada
# do fluxo de disco/assinatura/tamanho.
ALLOWED_TIPOS_UPLOAD = frozenset({"anexo", "layout"})
STATUS_LAYOUT_VALORES = frozenset({"novo", "aprovado", "reprovado", "solicitar_alteracao"})
STATUS_LAYOUT_DEFAULT = "novo"
# Preview inline no grid central — só imagem. PDF nunca é inline (ver _DISPOSITION_INLINE
# abaixo, decisão de segurança da Fase S1-B, não alterada aqui); link não tem conteúdo físico.
_CONTENT_TYPES_PREVIEW = frozenset({"image/png", "image/jpeg"})

UPLOADS_ROOT = Path("uploads")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
# Piso de segurança contra upload sem limite enchendo o disco da VPS — não pedido
# explicitamente na instrução da fase, mas é o mesmo tipo de proteção que `_validate_extension`
# já fazia; 20 MB cobre folgado o uso real (imagem/PDF de briefing).
MAX_TAMANHO_BYTES = 20 * 1024 * 1024

# Fase S1-B — `UploadFile.content_type` é o header `Content-Type` da parte multipart,
# inteiramente escolhido por quem envia a requisição: nunca é autoridade de segurança.
# Assinatura real dos bytes (magic number), Python puro — sem `imghdr` (depreciado desde
# 3.11, removido no 3.13), sem `python-magic`/`libmagic` (dependência de sistema
# desproporcional pra validar só 3 formatos fixos). Só os 4 tipos já aceitos pelo domínio.
_ASSINATURAS: dict[str, bytes] = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".pdf": b"%PDF-",
}

# MIME canônico, derivado da extensão JÁ VALIDADA contra `ALLOWED_EXTENSIONS` — nunca do
# header do cliente. É o único valor persistido em `DemandaArquivo.content_type` a partir
# desta fase, e também a única fonte usada no download (ver `resolver_download_seguro`),
# que ignora deliberadamente o `content_type` já gravado (inclusive em registros legados).
_MIME_CANONICO: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}

# PDF é formato ativo (pode embutir JavaScript, `/Launch`, formulário) — nunca inline,
# mesmo sendo um PDF genuíno. PNG/JPEG são bytes de imagem inertes: inline seguro *depois*
# de confirmados por assinatura. Qualquer extensão fora deste mapa (não deveria existir,
# dado que upload já valida contra `ALLOWED_EXTENSIONS`, mas é defesa em profundidade para
# um registro legado inesperado) recebe `False` via `.get(..., False)` no chamador.
_DISPOSITION_INLINE: dict[str, bool] = {
    ".png": True,
    ".jpg": True,
    ".jpeg": True,
    ".pdf": False,
}


class DemandaArquivoNotFoundError(ValueError):
    """Arquivo inexistente **ou de outra Demanda**. Mesmo raciocínio de
    `DemandaChecklistItemNotFoundError` — um erro único para não confirmar a existência de um
    arquivo que quem pediu não pode ver."""


class DemandaArquivoExtensaoInvalidaError(ValueError):
    pass


class DemandaArquivoVazioError(ValueError):
    pass


class DemandaArquivoMuitoGrandeError(ValueError):
    pass


class DemandaArquivoConteudoInvalidoError(ValueError):
    """Bytes reais não começam com a assinatura da extensão declarada (Fase S1-B) — Content-
    Type do cliente nunca decide isto, só a checagem de assinatura em `_validar_assinatura`."""


class DemandaArquivoTipoInvalidoError(ValueError):
    """`tipo` fora de `anexo`/`layout` no upload multipart — mais comum: alguém tentando
    enviar `link` por aqui, que tem endpoint dedicado (`POST .../arquivos/link`)."""


class DemandaArquivoUrlInvalidaError(ValueError):
    """URL de link fora de `http`/`https` (`javascript:`, `data:`, `file:`, etc.) — mesma
    validação do schema (`validar_url_http_https`), reaplicada aqui porque o service nunca
    confia só na borda Pydantic para uma regra de segurança."""


class DemandaArquivoSemConteudoFisicoError(ValueError):
    """Tentativa de baixar um registro `tipo='link'` pelo endpoint de download físico — ele
    não tem `nome_fisico`/conteúdo em disco por definição (ver CHECK
    `ck_demanda_arquivos_fisico_ou_link`)."""


class DemandaArquivoStatusLayoutForaDeTipoError(ValueError):
    """PATCH de `statusLayout` num arquivo que não é `tipo='layout'` — nunca aceito, mesmo
    que o valor de status seja válido."""


class DemandaArquivoStatusLayoutInvalidoError(ValueError):
    pass


def _bytes_correspondem_a_assinatura(conteudo_inicial: bytes, extensao: str) -> bool:
    """Fonte única de verdade da assinatura por extensão — reutilizada pelo upload (onde um
    mismatch vira 422, ver `_validar_assinatura`) e pelo download (onde um mismatch nunca
    bloqueia o arquivo, só rebaixa media_type/disposition, ver `resolver_download_seguro`).
    Extensão fora de `_ASSINATURAS` (nunca ocorre no upload, é o caminho normal de um
    registro histórico com extensão inesperada no download) sempre devolve `False`."""
    assinatura = _ASSINATURAS.get(extensao)
    if assinatura is None:
        return False
    return conteudo_inicial.startswith(assinatura)


def _validar_assinatura(conteudo: bytes, extensao: str) -> None:
    """Só chamada pelo upload, onde `extensao` já passou por `ALLOWED_EXTENSIONS` — mismatch
    aqui é erro do cliente, sempre 422. Mensagem sem detalhe interno (não expõe a assinatura
    esperada nem a recebida)."""
    if not _bytes_correspondem_a_assinatura(conteudo, extensao):
        raise DemandaArquivoConteudoInvalidoError(
            "O conteúdo do arquivo não corresponde ao tipo informado."
        )


class DemandaArquivoService:
    """Recebe a Demanda **já resolvida no escopo de quem chama** — mesma divisão de
    responsabilidade de `DemandaChecklistService`.

    ## Consistência conteúdo físico ⇄ metadado

    Upload escreve o arquivo em disco **antes** de tentar o INSERT: se o banco falhar depois,
    o arquivo recém-escrito é apagado (nunca fica órfão em disco tornando-se invisível e
    inacessível ao mesmo tempo). Se a escrita em disco falhar, nada chega a ser inserido — a
    ordem escolhida (disco primeiro) evita o cenário mais perigoso, que seria um metadado
    apontando para um arquivo que nunca existiu.

    Exclusão inverte a prioridade: o metadado é removido e commitado **primeiro** — é ele a
    fonte da verdade sobre o que existe para quem usa a tela. A remoção física acontece depois,
    melhor esforço; se o arquivo físico já tiver sumido por qualquer razão externa, não é
    tratado como erro — o resultado desejado (arquivo inacessível) já estava garantido pelo
    metadado removido.
    """

    def __init__(
        self,
        repository: DemandaArquivoRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or DemandaArquivoRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def listar(self, db: Session, demanda_id: str) -> list[DemandaArquivo]:
        return self.repository.list_by_demanda(db, demanda_id)

    def _get_arquivo_da_demanda(self, db: Session, demanda_id: str, arquivo_id: str) -> DemandaArquivo:
        arquivo = self.repository.get_by_id(db, arquivo_id)
        if arquivo is None or arquivo.demanda_id != demanda_id:
            raise DemandaArquivoNotFoundError("Arquivo não encontrado")
        return arquivo

    def _pasta_demanda(self, demanda_id: str) -> Path:
        return UPLOADS_ROOT / "demandas" / demanda_id

    def caminho_fisico(self, demanda_id: str, nome_fisico: str) -> Path:
        return self._pasta_demanda(demanda_id) / nome_fisico

    def obter_para_download(self, db: Session, demanda: Demanda, arquivo_id: str) -> tuple[DemandaArquivo, Path]:
        arquivo = self._get_arquivo_da_demanda(db, demanda.id, arquivo_id)
        if arquivo.tipo == "link":
            # Sem nome_fisico por definição (CHECK ck_demanda_arquivos_fisico_ou_link) — o
            # frontend abre `arquivo.url` direto, nunca chama este endpoint pra link.
            raise DemandaArquivoSemConteudoFisicoError(
                "Este registro é um link, não um arquivo físico — não há conteúdo para baixar."
            )
        caminho = self.caminho_fisico(demanda.id, arquivo.nome_fisico)
        # Metadado sem arquivo físico correspondente é uma anomalia de integridade, não uma
        # pergunta de autorização diferente — devolve o mesmo 404 de "não encontrado" em vez
        # de vazar detalhe interno de armazenamento pra quem chama.
        if not caminho.is_file():
            raise DemandaArquivoNotFoundError("Arquivo não encontrado")
        return arquivo, caminho

    async def upload(
        self,
        db: Session,
        demanda: Demanda,
        file: UploadFile,
        *,
        tipo: str = "anexo",
        actor_usuario_id: str | None,
    ) -> DemandaArquivo:
        if tipo not in ALLOWED_TIPOS_UPLOAD:
            raise DemandaArquivoTipoInvalidoError(
                "tipo deve ser 'anexo' ou 'layout' — use POST .../arquivos/link para links."
            )

        nome_original = Path((file.filename or "").strip()).name.strip()
        if not nome_original:
            raise DemandaArquivoVazioError("Nome de arquivo inválido")
        nome_original = nome_original[:255]

        extensao = Path(nome_original).suffix.lower()
        if extensao not in ALLOWED_EXTENSIONS:
            raise DemandaArquivoExtensaoInvalidaError(
                "Tipo de arquivo não permitido. Use PNG, JPG, JPEG ou PDF."
            )

        conteudo = await file.read()
        if not conteudo:
            raise DemandaArquivoVazioError("Arquivo vazio")
        if len(conteudo) > MAX_TAMANHO_BYTES:
            raise DemandaArquivoMuitoGrandeError(
                f"Arquivo maior que o limite permitido ({MAX_TAMANHO_BYTES // (1024 * 1024)} MB)"
            )
        # Fase S1-B — bytes reais contra a assinatura da extensão declarada, ANTES de
        # qualquer escrita em disco. `file.content_type` (header multipart, escolhido por
        # quem envia) nunca é consultado aqui nem usado como MIME final — só a extensão,
        # já validada contra ALLOWED_EXTENSIONS, decide a assinatura esperada e o MIME
        # canônico abaixo.
        _validar_assinatura(conteudo, extensao)
        mime_canonico = _MIME_CANONICO[extensao]

        # Nome físico gerado pelo backend a partir do próprio id — nunca de `nome_original`.
        # Elimina path traversal por construção (ver docstring de app/models/demanda_arquivo.py).
        arquivo_id = str(uuid4())
        nome_fisico = f"{arquivo_id}{extensao}"
        pasta = self._pasta_demanda(demanda.id)
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / nome_fisico
        destino.write_bytes(conteudo)

        try:
            now = agora_utc()
            arquivo = DemandaArquivo(
                id=arquivo_id,
                demanda_id=demanda.id,
                nome_original=nome_original,
                nome_fisico=nome_fisico,
                content_type=mime_canonico,
                tamanho_bytes=len(conteudo),
                enviado_por_usuario_id=actor_usuario_id,
                tipo=tipo,
                status_layout=STATUS_LAYOUT_DEFAULT if tipo == "layout" else None,
                created_at=now,
            )
            self.repository.create(db, arquivo)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_ARQUIVO_ENVIADO, actor_usuario_id,
                extra_payload={"arquivoId": arquivo.id, "nomeOriginal": nome_original}, occurred_at=now,
            )
            db.commit()
            db.refresh(arquivo)
            return arquivo
        except Exception:
            db.rollback()
            destino.unlink(missing_ok=True)
            raise

    def excluir(
        self, db: Session, demanda: Demanda, arquivo_id: str, *, actor_usuario_id: str | None
    ) -> None:
        arquivo = self._get_arquivo_da_demanda(db, demanda.id, arquivo_id)
        # `link` não tem nome_fisico (CHECK ck_demanda_arquivos_fisico_ou_link) — não há
        # caminho nenhum a calcular nem arquivo físico a tentar remover.
        caminho = self.caminho_fisico(demanda.id, arquivo.nome_fisico) if arquivo.nome_fisico else None

        try:
            now = agora_utc()
            self.repository.delete(db, arquivo)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_ARQUIVO_REMOVIDO, actor_usuario_id,
                extra_payload={
                    "arquivoId": arquivo_id,
                    "nomeOriginal": arquivo.nome_original or arquivo.titulo,
                },
                occurred_at=now,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        if caminho is not None:
            # Melhor esforço, depois do commit — ver docstring da classe.
            caminho.unlink(missing_ok=True)

    def criar_link(
        self,
        db: Session,
        demanda: Demanda,
        *,
        titulo: str,
        url: str,
        descricao: str | None,
        actor_usuario_id: str | None,
    ) -> DemandaArquivo:
        """`tipo='link'` — nunca escreve em disco, nunca passa pelas validações de
        extensão/assinatura/tamanho do upload físico (não se aplicam)."""
        titulo = titulo.strip()
        if not titulo:
            raise DemandaArquivoVazioError("Título do link é obrigatório")
        # Revalidado aqui mesmo já validado no schema — o service nunca confia só na borda
        # Pydantic para uma regra de segurança (mesmo princípio de `_validar_assinatura`).
        try:
            url = validar_url_http_https(url)
        except ValueError as exc:
            raise DemandaArquivoUrlInvalidaError(str(exc)) from exc

        try:
            now = agora_utc()
            arquivo = DemandaArquivo(
                id=str(uuid4()),
                demanda_id=demanda.id,
                nome_original=None,
                nome_fisico=None,
                content_type=None,
                tamanho_bytes=None,
                enviado_por_usuario_id=actor_usuario_id,
                tipo="link",
                status_layout=None,
                url=url,
                titulo=titulo,
                descricao=(descricao or "").strip() or None,
                created_at=now,
            )
            self.repository.create(db, arquivo)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_ARQUIVO_ENVIADO, actor_usuario_id,
                extra_payload={"arquivoId": arquivo.id, "nomeOriginal": titulo, "tipo": "link"}, occurred_at=now,
            )
            db.commit()
            db.refresh(arquivo)
            return arquivo
        except Exception:
            db.rollback()
            raise

    def atualizar_status_layout(
        self,
        db: Session,
        demanda: Demanda,
        arquivo_id: str,
        *,
        status_layout: str,
        actor_usuario_id: str | None,
    ) -> DemandaArquivo:
        arquivo = self._get_arquivo_da_demanda(db, demanda.id, arquivo_id)
        if arquivo.tipo != "layout":
            raise DemandaArquivoStatusLayoutForaDeTipoError(
                "Só arquivos do tipo 'layout' têm status de aprovação."
            )
        if status_layout not in STATUS_LAYOUT_VALORES:
            raise DemandaArquivoStatusLayoutInvalidoError("Status de layout inválido")

        try:
            now = agora_utc()
            status_anterior = arquivo.status_layout
            arquivo.status_layout = status_layout
            self.repository.update(db, arquivo)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_ARQUIVO_STATUS_ALTERADO, actor_usuario_id,
                extra_payload={
                    "arquivoId": arquivo_id,
                    "statusAnterior": status_anterior,
                    "statusNovo": status_layout,
                },
                occurred_at=now,
            )
            db.commit()
            db.refresh(arquivo)
            return arquivo
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def resolver_download_seguro(nome_fisico: str, caminho: Path) -> tuple[str, bool]:
        """Fase S1-B, endurecido na revisão pré-merge: devolve `(media_type, inline)` sem
        NUNCA consultar `DemandaArquivo.content_type` persistido — nem o de um upload novo
        (já é sempre o canônico), nem o de um registro histórico (pode ter vindo do header
        do cliente, sem validação, de antes desta fase).

        Extensão sozinha não basta: um registro histórico pode ter extensão `.png` válida
        e bytes reais de HTML (exatamente o ataque reproduzido no diagnóstico S1). Por isso
        esta função também lê — só o prefixo necessário, nunca o arquivo inteiro — e
        confere a assinatura real antes de decidir:

        1. extensão fora de `_ASSINATURAS` → `application/octet-stream` + `attachment`
           (nunca inline com tipo arbitrário);
        2. extensão conhecida mas bytes reais não correspondem → mesmo fallback seguro,
           **sem bloquear o download** — o arquivo continua recuperável, só deixa de ser
           interpretado como o tipo que a extensão sugere;
        3. extensão conhecida e bytes conferem → MIME canônico e disposição normais da
           Política S1-B (PNG/JPEG inline, PDF sempre attachment).

        `FileResponse` faz streaming do arquivo inteiro depois, por conta própria — esta
        leitura curta acontece antes e não interfere nisso."""
        extensao = Path(nome_fisico).suffix.lower()
        assinatura = _ASSINATURAS.get(extensao)
        if assinatura is None:
            return "application/octet-stream", False

        with caminho.open("rb") as arquivo_fisico:
            prefixo = arquivo_fisico.read(len(assinatura))
        if not _bytes_correspondem_a_assinatura(prefixo, extensao):
            return "application/octet-stream", False

        return _MIME_CANONICO[extensao], _DISPOSITION_INLINE[extensao]

    @staticmethod
    def to_read(arquivo: DemandaArquivo, *, remetente_sistema: bool = False) -> DemandaArquivoRead:
        """`remetente_sistema`: o tenant não recebe o id de uma conta de sistema (vira None + `enviadoPorSistema`)."""
        return DemandaArquivoRead(
            id=arquivo.id,
            demandaId=arquivo.demanda_id,
            nomeOriginal=arquivo.nome_original,
            contentType=arquivo.content_type,
            tamanhoBytes=arquivo.tamanho_bytes,
            enviadoPorUsuarioId=None if remetente_sistema else arquivo.enviado_por_usuario_id,
            enviadoPorSistema=remetente_sistema,
            createdAt=arquivo.created_at,
            tipo=arquivo.tipo,
            statusLayout=arquivo.status_layout,
            url=arquivo.url,
            titulo=arquivo.titulo,
            descricao=arquivo.descricao,
        )

    def list_central(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        search: str | None = None,
        cliente_ids=None,
        projeto_ids=None,
        demanda_ids=None,
        tipos=None,
        status_layouts=None,
        usuario_ids=None,
        cliente_ids_excluir=None,
        projeto_ids_excluir=None,
        demanda_ids_excluir=None,
        tipos_excluir=None,
        status_layouts_excluir=None,
        usuario_ids_excluir=None,
        data_inicio=None,
        data_fim=None,
        limit: int = 50,
        offset: int = 0,
        ocultar_remetente_de_sistema: bool = False,
    ) -> list[ArquivoCentralRead]:
        linhas = self.repository.list_central(
            db,
            escopo=escopo,
            search=search,
            cliente_ids=cliente_ids,
            projeto_ids=projeto_ids,
            demanda_ids=demanda_ids,
            tipos=tipos,
            status_layouts=status_layouts,
            usuario_ids=usuario_ids,
            cliente_ids_excluir=cliente_ids_excluir,
            projeto_ids_excluir=projeto_ids_excluir,
            demanda_ids_excluir=demanda_ids_excluir,
            tipos_excluir=tipos_excluir,
            status_layouts_excluir=status_layouts_excluir,
            usuario_ids_excluir=usuario_ids_excluir,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=limit,
            offset=offset,
        )
        return [self._to_central_read(linha, ocultar_remetente_de_sistema=ocultar_remetente_de_sistema) for linha in linhas]

    @staticmethod
    def _to_central_read(linha: Row, *, ocultar_remetente_de_sistema: bool = False) -> ArquivoCentralRead:
        """Monta o item autossuficiente a partir da Row já com todos os JOINs resolvidos
        (ver `DemandaArquivoRepository.list_central`) — nenhum fetch adicional aqui."""
        arquivo: DemandaArquivo = linha[0]
        nome = arquivo.nome_original if arquivo.tipo != "link" else arquivo.titulo
        preview_disponivel = arquivo.tipo in ("anexo", "layout") and arquivo.content_type in _CONTENT_TYPES_PREVIEW
        # Privacidade da conta de sistema: o arquivo e as informações dele continuam; só a identidade do remetente é
        # mascarada para o tenant ("Sistema", sem id). A própria conta de sistema vê o seu nome.
        mascarar = ocultar_remetente_de_sistema and bool(linha.usuario_sistema)
        return ArquivoCentralRead(
            id=arquivo.id,
            demandaId=arquivo.demanda_id,
            nome=nome or "",
            mimeType=arquivo.content_type,
            tamanhoBytes=arquivo.tamanho_bytes,
            tipo=arquivo.tipo,
            statusLayout=arquivo.status_layout,
            url=arquivo.url,
            descricao=arquivo.descricao,
            createdAt=arquivo.created_at,
            enviadoPorUsuarioId=None if mascarar else arquivo.enviado_por_usuario_id,
            enviadoPorSistema=mascarar,
            usuarioNome=AUTOR_SISTEMA if mascarar else linha.usuario_nome,
            demanda=ArquivoCentralDemandaRead(
                id=arquivo.demanda_id,
                numeroOperacional=linha.numero_operacional,
                codigoReferencia=linha.demanda_codigo_referencia,
                nome=linha.demanda_nome,
            ),
            projetoId=linha.projeto_id,
            projetoNome=linha.projeto_nome,
            clienteId=linha.cliente_id,
            clienteNome=linha.cliente_nome,
            previewDisponivel=preview_disponivel,
        )

    def _publish_event(
        self, db: Session, demanda: Demanda, tipo: DomainEventType, actor_usuario_id: str | None,
        *, extra_payload: dict | None = None, occurred_at=None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": demanda.empresa_id,
            "demanda_id": demanda.id,
            "codigo_referencia": demanda.codigo_referencia,
            "timestamp": timestamp.isoformat(),
        }
        if extra_payload:
            payload.update(extra_payload)
        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=demanda.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=demanda.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )
