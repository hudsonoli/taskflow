from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referencias import gerar_proxima_referencia
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.fornecedor import Fornecedor
from app.repositories.fornecedor_repository import FornecedorRepository
from app.schemas.fornecedor import (
    FornecedorCreate,
    FornecedorDiretorioRead,
    FornecedorRead,
    FornecedorUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "fornecedor"

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_ARQUIVADO = "arquivado"

# Campos simples copiados 1:1 do schema para o model. Fora daqui ficam os que exigem
# tratamento: nome (normalização), documento (normalização) e status.
_CAMPOS_SIMPLES = (
    "categoria",
    "contato_nome",
    "email",
    "whatsapp",
    "site",
    "cep",
    "bairro",
    "endereco_completo",
    "cidade",
    "uf",
    "observacoes",
    "tipo_documento",
    "cor_identificacao",
)


class FornecedorNotFoundError(ValueError):
    pass


class FornecedorConflictError(ValueError):
    pass


class FornecedorInvalidTransitionError(ValueError):
    pass


class FornecedorService:
    def __init__(
        self,
        repository: FornecedorRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or FornecedorRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_fornecedor(
        self,
        db: Session,
        data: FornecedorCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str | None = None,
    ) -> Fornecedor:
        """Criação pela API pública. `codigoInterno` é gerado aqui, nunca recebido."""
        return self._criar(
            db,
            data=data,
            empresa_id=empresa_id,
            codigo_interno=None,
            actor_usuario_id=actor_usuario_id,
        )

    def create_fornecedor_com_codigo_legado(
        self,
        db: Session,
        data: FornecedorCreate,
        *,
        empresa_id: str,
        codigo_interno: str,
        actor_usuario_id: str | None = None,
    ) -> Fornecedor:
        """Só para seeds/importadores: preserva o `codigoInterno` do mock
        (`fornecedor-imp-001`), que é a chave de idempotência do seed. Nunca exposto na API
        pública."""
        return self._criar(
            db,
            data=data,
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            actor_usuario_id=actor_usuario_id,
        )

    def _criar(
        self,
        db: Session,
        *,
        data: FornecedorCreate,
        empresa_id: str,
        codigo_interno: str | None,
        actor_usuario_id: str | None,
    ) -> Fornecedor:
        now = agora_utc()

        try:
            # Contador, entidade e evento na MESMA transação: se qualquer coisa falhar
            # abaixo, o incremento da sequência sofre rollback junto e o número não é
            # queimado.
            referencia = gerar_proxima_referencia(
                db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE
            )

            fornecedor = Fornecedor(
                id=str(uuid4()),
                empresa_id=empresa_id,
                # Sem código legado (criação pela API), o codigoInterno deriva do código de
                # referência — continua único por empresa e não consome outra sequência.
                codigo_interno=codigo_interno or referencia.codigo_referencia,
                codigo_referencia=referencia.codigo_referencia,
                ano_referencia=referencia.ano_referencia,
                sequencial_referencia=referencia.sequencial_referencia,
                nome=data.nome,
                nome_normalizado=self._normalizar_nome(data.nome),
                documento=data.documento,
                documento_normalizado=self._normalizar_documento(data.documento),
                status=data.status,
                created_at=now,
                updated_at=now,
                **{campo: getattr(data, campo) for campo in _CAMPOS_SIMPLES},
            )
            self.repository.create(db, fornecedor)

            self._publish_event(
                db, fornecedor, DomainEventType.FORNECEDOR_CRIADO, actor_usuario_id, occurred_at=now
            )

            db.commit()
            db.refresh(fornecedor)
            return fornecedor
        except IntegrityError:
            # Corrida: dois inserts concorrentes passaram pelos checks antes de qualquer
            # commit. Sem UNIQUE de nome/documento, a única colisão possível é codigoInterno
            # ou o par (ano, sequencial) — ambas indicam corrida real, não duplicidade de
            # negócio.
            db.rollback()
            raise FornecedorConflictError("codigoInterno já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_fornecedores(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Fornecedor]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Fornecedor]:
        """Não inclui arquivados — ver FornecedorRepository.list_diretorio."""
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    def get_fornecedor(self, db: Session, fornecedor_id: str) -> Fornecedor:
        fornecedor = self.repository.get_by_id(db, fornecedor_id)
        if fornecedor is None:
            raise FornecedorNotFoundError("Fornecedor não encontrado")
        return fornecedor

    # ----------------------------------------------------------------------------------
    # Alteração
    # ----------------------------------------------------------------------------------

    def update_fornecedor(
        self,
        db: Session,
        fornecedor_id: str,
        data: FornecedorUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Fornecedor:
        fornecedor = self.get_fornecedor(db, fornecedor_id)
        updates = data.model_dump(exclude_unset=True)
        campos_alterados: list[str] = []

        try:
            if fornecedor.status == STATUS_ARQUIVADO:
                raise FornecedorInvalidTransitionError(
                    "Fornecedor arquivado não pode ser editado — restaure-o antes"
                )

            if "nome" in updates and updates["nome"] != fornecedor.nome:
                # Sem checagem de unicidade: nome duplicado é permitido (ver model).
                fornecedor.nome = updates["nome"]
                fornecedor.nome_normalizado = self._normalizar_nome(updates["nome"])
                campos_alterados.append("nome")

            if "documento" in updates and updates["documento"] != fornecedor.documento:
                fornecedor.documento = updates["documento"]
                fornecedor.documento_normalizado = self._normalizar_documento(updates["documento"])
                campos_alterados.append("documento")

            if "status" in updates and updates["status"] is not None and updates["status"] != fornecedor.status:
                fornecedor.status = updates["status"]
                campos_alterados.append("status")

            for campo in _CAMPOS_SIMPLES:
                if campo not in updates:
                    continue
                if updates[campo] != getattr(fornecedor, campo):
                    setattr(fornecedor, campo, updates[campo])
                    campos_alterados.append(campo)

            if campos_alterados:
                now = agora_utc()
                fornecedor.updated_at = now
                self.repository.update(db, fornecedor)
                self._publish_event(
                    db,
                    fornecedor,
                    DomainEventType.FORNECEDOR_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": campos_alterados},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(fornecedor)
            return fornecedor
        except IntegrityError:
            db.rollback()
            raise FornecedorConflictError("codigoInterno já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Arquivamento — ver docs/padrao-arquivamento.md. Nunca há delete físico.
    # ----------------------------------------------------------------------------------

    def arquivar_fornecedor(
        self,
        db: Session,
        fornecedor_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str | None = None,
    ) -> Fornecedor:
        fornecedor = self.get_fornecedor(db, fornecedor_id)
        try:
            if fornecedor.status == STATUS_ARQUIVADO:
                raise FornecedorInvalidTransitionError("Fornecedor já está arquivado")

            now = agora_utc()
            fornecedor.status_anterior_arquivamento = fornecedor.status
            fornecedor.status = STATUS_ARQUIVADO
            fornecedor.arquivado_at = now
            fornecedor.arquivado_por_usuario_id = actor_usuario_id
            fornecedor.motivo_arquivamento = motivo_arquivamento
            fornecedor.restaurado_at = None
            fornecedor.restaurado_por_usuario_id = None
            fornecedor.updated_at = now

            self.repository.update(db, fornecedor)
            self._publish_event(
                db,
                fornecedor,
                DomainEventType.FORNECEDOR_ARQUIVADO,
                actor_usuario_id,
                extra_payload={"motivoArquivamento": motivo_arquivamento},
                occurred_at=now,
            )
            db.commit()
            db.refresh(fornecedor)
            return fornecedor
        except Exception:
            db.rollback()
            raise

    def restaurar_fornecedor(
        self,
        db: Session,
        fornecedor_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Fornecedor:
        fornecedor = self.get_fornecedor(db, fornecedor_id)
        try:
            if fornecedor.status != STATUS_ARQUIVADO:
                raise FornecedorInvalidTransitionError(
                    "Somente fornecedor arquivado pode ser restaurado"
                )

            now = agora_utc()
            fornecedor.status = fornecedor.status_anterior_arquivamento or STATUS_ATIVO
            fornecedor.restaurado_at = now
            fornecedor.restaurado_por_usuario_id = actor_usuario_id
            fornecedor.arquivado_at = None
            fornecedor.arquivado_por_usuario_id = None
            fornecedor.motivo_arquivamento = None
            fornecedor.status_anterior_arquivamento = None
            fornecedor.updated_at = now

            self.repository.update(db, fornecedor)
            self._publish_event(
                db, fornecedor, DomainEventType.FORNECEDOR_RESTAURADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(fornecedor)
            return fornecedor
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Serialização
    # ----------------------------------------------------------------------------------

    def detectar_possiveis_duplicidades(
        self,
        db: Session,
        *,
        empresa_id: str,
        nome: str,
        documento: str | None,
        excluir_id: str | None = None,
    ) -> list[dict]:
        """Fornecedores parecidos — mesmo nome e/ou mesmo documento.

        Informativo: não há UNIQUE de nome nem de documento e a criação nunca é bloqueada
        (ver docstring de app/models/fornecedor.py). Deve ser chamado ANTES do INSERT, senão
        o próprio registro aparece no resultado.

        Função pura em relação ao service: devolve a lista, não guarda estado. O service é um
        singleton de módulo compartilhado entre requisições concorrentes — guardar avisos em
        `self` seria uma condição de corrida.
        """
        nome_normalizado = self._normalizar_nome(nome)
        documento_normalizado = self._normalizar_documento(documento)

        semelhantes = self.repository.listar_semelhantes(
            db,
            empresa_id=empresa_id,
            nome_normalizado=nome_normalizado,
            documento_normalizado=documento_normalizado,
            excluir_id=excluir_id,
        )

        avisos: list[dict] = []
        for outro in semelhantes:
            bate_nome = outro.nome_normalizado == nome_normalizado
            bate_documento = (
                bool(documento_normalizado) and outro.documento_normalizado == documento_normalizado
            )
            if bate_nome and bate_documento:
                motivo = "nome_documento"
            elif bate_documento:
                motivo = "documento"
            else:
                motivo = "nome"
            avisos.append(
                {
                    "id": outro.id,
                    "codigoReferencia": outro.codigo_referencia,
                    "sequencialReferencia": outro.sequencial_referencia,
                    "nome": outro.nome,
                    "documento": outro.documento,
                    "status": outro.status,
                    "motivo": motivo,
                }
            )
        return avisos

    def to_read(
        self, fornecedor: Fornecedor, avisos: list[dict] | None = None
    ) -> FornecedorRead:
        return FornecedorRead.model_validate(
            {**self._campos_base(fornecedor), "possiveisDuplicidades": avisos or []}
        )

    def to_read_lote(self, fornecedores: list[Fornecedor]) -> list[FornecedorRead]:
        return [
            FornecedorRead.model_validate(self._campos_base(fornecedor))
            for fornecedor in fornecedores
        ]

    def to_diretorio_read_lote(
        self, fornecedores: list[Fornecedor]
    ) -> list[FornecedorDiretorioRead]:
        return [
            FornecedorDiretorioRead.model_validate(
                {
                    "id": fornecedor.id,
                    "codigoInterno": fornecedor.codigo_interno,
                    "codigoReferencia": fornecedor.codigo_referencia,
                    "sequencialReferencia": fornecedor.sequencial_referencia,
                    "nome": fornecedor.nome,
                    "categoria": fornecedor.categoria,
                    "corIdentificacao": fornecedor.cor_identificacao,
                    "status": fornecedor.status,
                }
            )
            for fornecedor in fornecedores
        ]

    @staticmethod
    def _campos_base(fornecedor: Fornecedor) -> dict:
        return {
            "id": fornecedor.id,
            "empresaId": fornecedor.empresa_id,
            "codigoInterno": fornecedor.codigo_interno,
            "codigoReferencia": fornecedor.codigo_referencia,
            "anoReferencia": fornecedor.ano_referencia,
            "sequencialReferencia": fornecedor.sequencial_referencia,
            "nome": fornecedor.nome,
            "tipoDocumento": fornecedor.tipo_documento,
            "documento": fornecedor.documento,
            "status": fornecedor.status,
            "categoria": fornecedor.categoria,
            "contatoNome": fornecedor.contato_nome,
            "email": fornecedor.email,
            "whatsapp": fornecedor.whatsapp,
            "site": fornecedor.site,
            "cep": fornecedor.cep,
            "bairro": fornecedor.bairro,
            "enderecoCompleto": fornecedor.endereco_completo,
            "cidade": fornecedor.cidade,
            "uf": fornecedor.uf,
            "observacoes": fornecedor.observacoes,
            "corIdentificacao": fornecedor.cor_identificacao,
            "createdAt": fornecedor.created_at,
            "updatedAt": fornecedor.updated_at,
            "arquivadoAt": fornecedor.arquivado_at,
            "arquivadoPorUsuarioId": fornecedor.arquivado_por_usuario_id,
            "motivoArquivamento": fornecedor.motivo_arquivamento,
            "restauradoAt": fornecedor.restaurado_at,
            "restauradoPorUsuarioId": fornecedor.restaurado_por_usuario_id,
            "statusAnteriorArquivamento": fornecedor.status_anterior_arquivamento,
        }

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _publish_event(
        self,
        db: Session,
        fornecedor: Fornecedor,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": fornecedor.empresa_id,
            "fornecedor_id": fornecedor.id,
            "codigo_referencia": fornecedor.codigo_referencia,
            "timestamp": timestamp.isoformat(),
            "status": fornecedor.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=fornecedor.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=fornecedor.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()

    @staticmethod
    def _normalizar_documento(documento: str | None) -> str | None:
        """Só dígitos — permite achar '12.345.678/0001-90' digitando '12345678'."""
        if not documento:
            return None
        digitos = "".join(c for c in documento if c.isdigit())
        return digitos or None
