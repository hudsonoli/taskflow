from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referencias import gerar_proxima_referencia
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.cliente import Cliente
from app.models.cliente_grupo import ClienteGrupo
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.grupo_cliente_repository import GrupoClienteRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.cliente import ClienteCreate, ClienteDiretorioRead, ClienteRead, ClienteUpdate
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "cliente"

STATUS_ATIVO = "ativo"
STATUS_SUSPENSO = "suspenso"
STATUS_INATIVO = "inativo"
STATUS_ARQUIVADO = "arquivado"

# Um usuário nestes estados não pode ser DEFINIDO como responsável comercial novo. Vínculo
# histórico (alguém que era responsável e depois foi inativado) continua valendo — mesma
# regra de DepartamentoService._ensure_responsavel_valido.
STATUS_USUARIO_INVALIDO_COMO_RESPONSAVEL = {"arquivado", "inativo", "bloqueado"}

# Campos simples copiados 1:1 do schema para o model. Fora daqui ficam os que exigem
# tratamento: nome (normalização), contatos (value objects), grupos (N:N) e status.
_CAMPOS_SIMPLES = (
    "razao_social",
    "email",
    "whatsapp",
    "cep",
    "bairro",
    "endereco_completo",
    "cidade",
    "uf",
    "segmento",
    "origem",
    "cliente_referencial",
    "avisar_conclusao_por_email",
    "fee_mensal_centavos",
    "horas_contratadas_mes",
    "observacoes",
    "logo_url",
    "tipo_documento",
    "cor_identificacao",
)


class ClienteNotFoundError(ValueError):
    pass


class ClienteConflictError(ValueError):
    pass


class ClienteInvalidTransitionError(ValueError):
    pass


class ClienteResponsavelInvalidoError(ValueError):
    pass


class ClienteGrupoInvalidoError(ValueError):
    """Grupo inexistente, de outra empresa ou arquivado (vínculo novo)."""


class ClienteService:
    def __init__(
        self,
        repository: ClienteRepository | None = None,
        grupo_repository: GrupoClienteRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or ClienteRepository()
        self.grupo_repository = grupo_repository or GrupoClienteRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_cliente(
        self,
        db: Session,
        data: ClienteCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str | None = None,
    ) -> Cliente:
        """Criação pela API pública. `codigoInterno` é gerado aqui, nunca recebido."""
        return self._criar(
            db,
            data=data,
            empresa_id=empresa_id,
            codigo_interno=None,
            actor_usuario_id=actor_usuario_id,
        )

    def create_cliente_com_codigo_legado(
        self,
        db: Session,
        data: ClienteCreate,
        *,
        empresa_id: str,
        codigo_interno: str,
        actor_usuario_id: str | None = None,
    ) -> Cliente:
        """Só para seeds/importadores: preserva o `codigoInterno` que o mock já usava
        (`#2001`), porque Projeto e Demanda ainda referenciam clientes por ele. Nunca
        exposto na API pública."""
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
        data: ClienteCreate,
        empresa_id: str,
        codigo_interno: str | None,
        actor_usuario_id: str | None,
    ) -> Cliente:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(data.nome)
        documento_normalizado = self._normalizar_documento(data.documento)
        responsavel_id = str(data.responsavel_comercial_id) if data.responsavel_comercial_id else None
        grupo_ids = [str(gid) for gid in (data.grupo_cliente_ids or [])]

        try:
            if responsavel_id is not None:
                self._ensure_responsavel_valido(db, empresa_id, responsavel_id)
            for grupo_id in grupo_ids:
                self._ensure_grupo_valido(db, empresa_id, grupo_id)

            # Contador, entidade, vínculos e eventos na MESMA transação: se qualquer coisa
            # falhar abaixo, o incremento da sequência sofre rollback junto e o número não
            # é queimado.
            referencia = gerar_proxima_referencia(db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE)

            cliente = Cliente(
                id=str(uuid4()),
                empresa_id=empresa_id,
                # Sem código legado (criação pela API), o codigoInterno deriva do código de
                # referência — continua único por empresa e não consome outra sequência.
                codigo_interno=codigo_interno or referencia.codigo_referencia,
                codigo_referencia=referencia.codigo_referencia,
                ano_referencia=referencia.ano_referencia,
                sequencial_referencia=referencia.sequencial_referencia,
                nome=data.nome,
                nome_normalizado=nome_normalizado,
                documento=data.documento,
                documento_normalizado=self._normalizar_documento(data.documento),
                responsavel_comercial_id=responsavel_id,
                contatos=[contato.model_dump(by_alias=False) for contato in (data.contatos or [])],
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
                **{campo: getattr(data, campo) for campo in _CAMPOS_SIMPLES},
            )
            self.repository.create(db, cliente)

            for grupo_id in grupo_ids:
                self.repository.adicionar_grupo(
                    db, ClienteGrupo(cliente_id=cliente.id, grupo_cliente_id=grupo_id, created_at=now)
                )

            self._publish_event(db, cliente, DomainEventType.CLIENTE_CRIADO, actor_usuario_id, occurred_at=now)
            for grupo_id in grupo_ids:
                self._publish_event(
                    db,
                    cliente,
                    DomainEventType.CLIENTE_GRUPO_ADICIONADO,
                    actor_usuario_id,
                    extra_payload={"grupoClienteId": grupo_id},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(cliente)
            return cliente
        except IntegrityError:
            # Corrida: dois inserts concorrentes passaram pelos checks antes de qualquer
            # commit. Reconsulta para distinguir conflito comum de conflito-arquivado.
            # Sem UNIQUE de nome/documento, a única colisão possível é codigoInterno ou
            # o par (ano, sequencial) — ambas indicam corrida real, não duplicidade de
            # negócio.
            db.rollback()
            raise ClienteConflictError("codigoInterno já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_clientes(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        grupo_cliente_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Cliente]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            status=status,
            search=search,
            grupo_cliente_id=grupo_cliente_id,
            limit=limit,
            offset=offset,
        )

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Cliente]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    def get_cliente(self, db: Session, cliente_id: str) -> Cliente:
        cliente = self.repository.get_by_id(db, cliente_id)
        if cliente is None:
            raise ClienteNotFoundError("Cliente não encontrado")
        return cliente

    # ----------------------------------------------------------------------------------
    # Alteração
    # ----------------------------------------------------------------------------------

    def update_cliente(
        self,
        db: Session,
        cliente_id: str,
        data: ClienteUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Cliente:
        cliente = self.get_cliente(db, cliente_id)
        updates = data.model_dump(exclude_unset=True)
        campos_alterados: list[str] = []
        grupos_adicionados: list[str] = []
        grupos_removidos: list[str] = []

        try:
            if cliente.status == STATUS_ARQUIVADO:
                raise ClienteInvalidTransitionError(
                    "Cliente arquivado não pode ser editado — restaure-o antes"
                )

            if "nome" in updates and updates["nome"] != cliente.nome:
                # Sem checagem de unicidade: nome duplicado é permitido (ver model).
                nome_normalizado = self._normalizar_nome(updates["nome"])
                cliente.nome = updates["nome"]
                cliente.nome_normalizado = nome_normalizado
                campos_alterados.append("nome")

            if "documento" in updates and updates["documento"] != cliente.documento:
                cliente.documento = updates["documento"]
                cliente.documento_normalizado = self._normalizar_documento(updates["documento"])
                campos_alterados.append("documento")

            if "responsavel_comercial_id" in updates:
                novo = str(updates["responsavel_comercial_id"]) if updates["responsavel_comercial_id"] else None
                if novo != cliente.responsavel_comercial_id:
                    if novo is not None:
                        self._ensure_responsavel_valido(db, cliente.empresa_id, novo)
                    cliente.responsavel_comercial_id = novo
                    campos_alterados.append("responsavelComercialId")

            if "contatos" in updates:
                novos = [
                    contato if isinstance(contato, dict) else contato.model_dump()
                    for contato in (updates["contatos"] or [])
                ]
                if novos != (cliente.contatos or []):
                    cliente.contatos = novos
                    campos_alterados.append("contatos")

            if "status" in updates and updates["status"] is not None and updates["status"] != cliente.status:
                cliente.status = updates["status"]
                campos_alterados.append("status")

            for campo in _CAMPOS_SIMPLES:
                if campo not in updates:
                    continue
                if updates[campo] != getattr(cliente, campo):
                    setattr(cliente, campo, updates[campo])
                    campos_alterados.append(campo)

            if "grupo_cliente_ids" in updates:
                grupos_adicionados, grupos_removidos = self._sincronizar_grupos(
                    db, cliente, [str(gid) for gid in (updates["grupo_cliente_ids"] or [])]
                )
                if grupos_adicionados or grupos_removidos:
                    campos_alterados.append("grupoClienteIds")

            if campos_alterados:
                now = agora_utc()
                cliente.updated_at = now
                self.repository.update(db, cliente)
                self._publish_event(
                    db,
                    cliente,
                    DomainEventType.CLIENTE_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": campos_alterados},
                    occurred_at=now,
                )
                for grupo_id in grupos_adicionados:
                    self._publish_event(
                        db,
                        cliente,
                        DomainEventType.CLIENTE_GRUPO_ADICIONADO,
                        actor_usuario_id,
                        extra_payload={"grupoClienteId": grupo_id},
                        occurred_at=now,
                    )
                for grupo_id in grupos_removidos:
                    self._publish_event(
                        db,
                        cliente,
                        DomainEventType.CLIENTE_GRUPO_REMOVIDO,
                        actor_usuario_id,
                        extra_payload={"grupoClienteId": grupo_id},
                        occurred_at=now,
                    )

            db.commit()
            db.refresh(cliente)
            return cliente
        except IntegrityError:
            db.rollback()
            raise ClienteConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Arquivamento — ver docs/padrao-arquivamento.md. Nunca há delete físico.
    # ----------------------------------------------------------------------------------

    def arquivar_cliente(
        self,
        db: Session,
        cliente_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str | None = None,
    ) -> Cliente:
        cliente = self.get_cliente(db, cliente_id)
        try:
            if cliente.status == STATUS_ARQUIVADO:
                raise ClienteInvalidTransitionError("Cliente já está arquivado")

            now = agora_utc()
            cliente.status_anterior_arquivamento = cliente.status
            cliente.status = STATUS_ARQUIVADO
            cliente.arquivado_at = now
            cliente.arquivado_por_usuario_id = actor_usuario_id
            cliente.motivo_arquivamento = motivo_arquivamento
            cliente.restaurado_at = None
            cliente.restaurado_por_usuario_id = None
            cliente.updated_at = now

            self.repository.update(db, cliente)
            self._publish_event(
                db,
                cliente,
                DomainEventType.CLIENTE_ARQUIVADO,
                actor_usuario_id,
                extra_payload={"motivoArquivamento": motivo_arquivamento},
                occurred_at=now,
            )
            db.commit()
            db.refresh(cliente)
            return cliente
        except Exception:
            db.rollback()
            raise

    def restaurar_cliente(
        self,
        db: Session,
        cliente_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Cliente:
        cliente = self.get_cliente(db, cliente_id)
        try:
            if cliente.status != STATUS_ARQUIVADO:
                raise ClienteInvalidTransitionError("Somente cliente arquivado pode ser restaurado")

            now = agora_utc()
            cliente.status = cliente.status_anterior_arquivamento or STATUS_ATIVO
            cliente.restaurado_at = now
            cliente.restaurado_por_usuario_id = actor_usuario_id
            cliente.arquivado_at = None
            cliente.arquivado_por_usuario_id = None
            cliente.motivo_arquivamento = None
            cliente.status_anterior_arquivamento = None
            cliente.updated_at = now

            self.repository.update(db, cliente)
            self._publish_event(
                db, cliente, DomainEventType.CLIENTE_RESTAURADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(cliente)
            return cliente
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
        """Clientes parecidos — mesmo nome e/ou mesmo documento.

        Informativo: não há UNIQUE de nome nem de documento e a criação nunca é bloqueada
        (ver docstring de app/models/cliente.py). Deve ser chamado ANTES do INSERT, senão o
        próprio registro aparece no resultado.
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
            bate_documento = bool(documento_normalizado) and outro.documento_normalizado == documento_normalizado
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
                    "nome": outro.nome,
                    "documento": outro.documento,
                    "status": outro.status,
                    "motivo": motivo,
                }
            )
        return avisos

    def to_read(self, db: Session, cliente: Cliente, avisos: list[dict] | None = None) -> ClienteRead:
        return ClienteRead.model_validate(
            {
                **self._campos_base(cliente),
                "grupoClienteIds": self.repository.listar_grupo_ids(db, cliente.id),
                "possiveisDuplicidades": avisos or [],
            }
        )

    def to_read_lote(self, db: Session, clientes: list[Cliente]) -> list[ClienteRead]:
        """Uma query só para os grupos de todos os clientes da página — evita N+1."""
        grupos = self.repository.listar_grupo_ids_em_lote(db, [c.id for c in clientes])
        return [
            ClienteRead.model_validate(
                {**self._campos_base(cliente), "grupoClienteIds": grupos.get(cliente.id, [])}
            )
            for cliente in clientes
        ]

    def to_diretorio_read_lote(self, db: Session, clientes: list[Cliente]) -> list[ClienteDiretorioRead]:
        grupos = self.repository.listar_grupo_ids_em_lote(db, [c.id for c in clientes])
        return [
            ClienteDiretorioRead.model_validate(
                {
                    "id": cliente.id,
                    "codigoInterno": cliente.codigo_interno,
                    "codigoReferencia": cliente.codigo_referencia,
                    "sequencialReferencia": cliente.sequencial_referencia,
                    "nome": cliente.nome,
                    "corIdentificacao": cliente.cor_identificacao,
                    "status": cliente.status,
                    "grupoClienteIds": grupos.get(cliente.id, []),
                    "email": cliente.email,
                    "contatos": cliente.contatos or [],
                    "avisarConclusaoPorEmail": cliente.avisar_conclusao_por_email,
                    "responsavelComercialId": cliente.responsavel_comercial_id,
                }
            )
            for cliente in clientes
        ]

    @staticmethod
    def _campos_base(cliente: Cliente) -> dict:
        return {
            "id": cliente.id,
            "empresaId": cliente.empresa_id,
            "codigoInterno": cliente.codigo_interno,
            "codigoReferencia": cliente.codigo_referencia,
            "anoReferencia": cliente.ano_referencia,
            "sequencialReferencia": cliente.sequencial_referencia,
            "nome": cliente.nome,
            "razaoSocial": cliente.razao_social,
            "tipoDocumento": cliente.tipo_documento,
            "documento": cliente.documento,
            "status": cliente.status,
            "email": cliente.email,
            "whatsapp": cliente.whatsapp,
            "cep": cliente.cep,
            "bairro": cliente.bairro,
            "enderecoCompleto": cliente.endereco_completo,
            "cidade": cliente.cidade,
            "uf": cliente.uf,
            "segmento": cliente.segmento,
            "origem": cliente.origem,
            "responsavelComercialId": cliente.responsavel_comercial_id,
            "clienteReferencial": cliente.cliente_referencial,
            "avisarConclusaoPorEmail": cliente.avisar_conclusao_por_email,
            "feeMensalCentavos": cliente.fee_mensal_centavos,
            "horasContratadasMes": (
                float(cliente.horas_contratadas_mes) if cliente.horas_contratadas_mes is not None else None
            ),
            "observacoes": cliente.observacoes,
            "corIdentificacao": cliente.cor_identificacao,
            "logoUrl": cliente.logo_url,
            "contatos": cliente.contatos or [],
            "createdAt": cliente.created_at,
            "updatedAt": cliente.updated_at,
            "arquivadoAt": cliente.arquivado_at,
            "arquivadoPorUsuarioId": cliente.arquivado_por_usuario_id,
            "motivoArquivamento": cliente.motivo_arquivamento,
            "restauradoAt": cliente.restaurado_at,
            "restauradoPorUsuarioId": cliente.restaurado_por_usuario_id,
            "statusAnteriorArquivamento": cliente.status_anterior_arquivamento,
        }

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _sincronizar_grupos(
        self, db: Session, cliente: Cliente, desejados: list[str]
    ) -> tuple[list[str], list[str]]:
        """Reconcilia o conjunto de grupos. Só valida os que estão ENTRANDO: um vínculo
        histórico com grupo arquivado é preservado, mas não pode ser criado de novo."""
        atuais = set(self.repository.listar_grupo_ids(db, cliente.id))
        alvo = set(desejados)

        adicionar = sorted(alvo - atuais)
        remover = sorted(atuais - alvo)

        for grupo_id in adicionar:
            self._ensure_grupo_valido(db, cliente.empresa_id, grupo_id)

        now = agora_utc()
        for grupo_id in adicionar:
            self.repository.adicionar_grupo(
                db, ClienteGrupo(cliente_id=cliente.id, grupo_cliente_id=grupo_id, created_at=now)
            )
        for grupo_id in remover:
            self.repository.remover_grupo(db, cliente_id=cliente.id, grupo_cliente_id=grupo_id)

        return adicionar, remover

    def _ensure_responsavel_valido(self, db: Session, empresa_id: str, usuario_id: str) -> None:
        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        # Cross-tenant é tratado como "não encontrado" — não vaza a existência de usuário
        # de outra empresa.
        if usuario is None or usuario.empresa_id != empresa_id:
            raise ClienteResponsavelInvalidoError("Responsável comercial não encontrado nesta empresa")
        if usuario.status in STATUS_USUARIO_INVALIDO_COMO_RESPONSAVEL:
            raise ClienteResponsavelInvalidoError(
                f"Usuário com status '{usuario.status}' não pode ser responsável comercial"
            )

    def _ensure_grupo_valido(self, db: Session, empresa_id: str, grupo_cliente_id: str) -> None:
        grupo = self.grupo_repository.get_by_id(db, grupo_cliente_id)
        if grupo is None or grupo.empresa_id != empresa_id:
            raise ClienteGrupoInvalidoError("Grupo de cliente não encontrado nesta empresa")
        if grupo.status == STATUS_ARQUIVADO:
            raise ClienteGrupoInvalidoError(
                "Grupo de cliente arquivado não aceita novos vínculos — restaure-o antes"
            )

    def _publish_event(
        self,
        db: Session,
        cliente: Cliente,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": cliente.empresa_id,
            "cliente_id": cliente.id,
            "codigo_referencia": cliente.codigo_referencia,
            "timestamp": timestamp.isoformat(),
            "status": cliente.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=cliente.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=cliente.id,
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
