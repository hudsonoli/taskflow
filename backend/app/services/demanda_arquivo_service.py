from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_arquivo import DemandaArquivo
from app.repositories.demanda_arquivo_repository import DemandaArquivoRepository
from app.schemas.demanda_arquivo import DemandaArquivoRead
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "demanda"

UPLOADS_ROOT = Path("uploads")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
# Piso de segurança contra upload sem limite enchendo o disco da VPS — não pedido
# explicitamente na instrução da fase, mas é o mesmo tipo de proteção que `_validate_extension`
# já fazia; 20 MB cobre folgado o uso real (imagem/PDF de briefing).
MAX_TAMANHO_BYTES = 20 * 1024 * 1024


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
        caminho = self.caminho_fisico(demanda.id, arquivo.nome_fisico)
        # Metadado sem arquivo físico correspondente é uma anomalia de integridade, não uma
        # pergunta de autorização diferente — devolve o mesmo 404 de "não encontrado" em vez
        # de vazar detalhe interno de armazenamento pra quem chama.
        if not caminho.is_file():
            raise DemandaArquivoNotFoundError("Arquivo não encontrado")
        return arquivo, caminho

    async def upload(
        self, db: Session, demanda: Demanda, file: UploadFile, *, actor_usuario_id: str | None
    ) -> DemandaArquivo:
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
                content_type=file.content_type,
                tamanho_bytes=len(conteudo),
                enviado_por_usuario_id=actor_usuario_id,
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
        caminho = self.caminho_fisico(demanda.id, arquivo.nome_fisico)

        try:
            now = agora_utc()
            self.repository.delete(db, arquivo)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_ARQUIVO_REMOVIDO, actor_usuario_id,
                extra_payload={"arquivoId": arquivo_id, "nomeOriginal": arquivo.nome_original}, occurred_at=now,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        # Melhor esforço, depois do commit — ver docstring da classe.
        caminho.unlink(missing_ok=True)

    @staticmethod
    def to_read(arquivo: DemandaArquivo) -> DemandaArquivoRead:
        return DemandaArquivoRead(
            id=arquivo.id,
            demandaId=arquivo.demanda_id,
            nomeOriginal=arquivo.nome_original,
            contentType=arquivo.content_type,
            tamanhoBytes=arquivo.tamanho_bytes,
            enviadoPorUsuarioId=arquivo.enviado_por_usuario_id,
            createdAt=arquivo.created_at,
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
