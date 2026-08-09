from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referencias import gerar_proxima_referencia
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.projeto import Projeto
from app.models.projeto_departamento import ProjetoDepartamento
from app.models.projeto_equipe_membro import ProjetoEquipeMembro
from app.models.projeto_responsavel import ProjetoResponsavel
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.departamento_repository import DepartamentoRepository
from app.repositories.projeto_repository import ProjetoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.projeto import ProjetoCreate, ProjetoDiretorioRead, ProjetoRead, ProjetoUpdate
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "projeto"

STATUS_ARQUIVADO = "arquivado"
STATUS_PADRAO = "planejamento"

# Um usuário nestes estados não pode ser DEFINIDO como responsável/membro novo. Vínculo
# histórico continua valendo — mesma regra de Cliente e Departamento.
STATUS_USUARIO_INVALIDO = {"arquivado", "inativo", "bloqueado"}

_CAMPOS_SIMPLES = (
    "campanha",
    "descricao",
    "resumo",
    "data_inicio",
    "data_fim_prevista",
    "modelo_campanha_id",
    "prioridade",
)


class ProjetoNotFoundError(ValueError):
    pass


class ProjetoConflictError(ValueError):
    pass


class ProjetoArquivadoConflictError(ValueError):
    """Nome já pertence a um projeto arquivado do mesmo cliente — a UI oferece restaurar em
    vez de mostrar erro de duplicidade (ver docs/padrao-arquivamento.md)."""

    def __init__(self, message: str, *, projeto_arquivado_id: str) -> None:
        super().__init__(message)
        self.projeto_arquivado_id = projeto_arquivado_id


class ProjetoInvalidTransitionError(ValueError):
    pass


class ProjetoClienteInvalidoError(ValueError):
    """Cliente inexistente, de outra empresa ou arquivado (vínculo novo)."""


class ProjetoUsuarioInvalidoError(ValueError):
    """Responsável ou membro inexistente, de outra empresa ou em status inválido."""


class ProjetoDepartamentoInvalidoError(ValueError):
    """Departamento inexistente, de outra empresa ou arquivado (vínculo novo)."""


class ProjetoService:
    def __init__(
        self,
        repository: ProjetoRepository | None = None,
        cliente_repository: ClienteRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        departamento_repository: DepartamentoRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or ProjetoRepository()
        self.cliente_repository = cliente_repository or ClienteRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.departamento_repository = departamento_repository or DepartamentoRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_projeto(
        self,
        db: Session,
        data: ProjetoCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str | None = None,
    ) -> Projeto:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(data.nome)
        cliente_id = str(data.cliente_id) if data.cliente_id else None
        responsavel_ids = [str(uid) for uid in (data.responsavel_ids or [])]
        departamento_ids = [str(did) for did in (data.departamento_responsavel_ids or [])]
        equipe = data.equipe or []

        try:
            if cliente_id is not None:
                self._ensure_cliente_valido(db, empresa_id, cliente_id)
            for usuario_id in responsavel_ids:
                self._ensure_usuario_valido(db, empresa_id, usuario_id)
            for departamento_id in departamento_ids:
                self._ensure_departamento_valido(db, empresa_id, departamento_id)
            for membro in equipe:
                self._ensure_usuario_valido(db, empresa_id, str(membro.usuario_id))

            self._ensure_nome_disponivel(
                db, empresa_id=empresa_id, cliente_id=cliente_id, nome_normalizado=nome_normalizado
            )

            # Contador, entidade, vínculos e eventos na MESMA transação: se algo falhar
            # abaixo, o incremento da sequência sofre rollback junto e o número não é queimado.
            referencia = gerar_proxima_referencia(
                db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE
            )

            projeto = Projeto(
                id=str(uuid4()),
                empresa_id=empresa_id,
                # Sem código legado, o codigoInterno deriva do código de referência —
                # continua único por empresa e não consome outra sequência.
                codigo_interno=referencia.codigo_referencia,
                codigo_referencia=referencia.codigo_referencia,
                ano_referencia=referencia.ano_referencia,
                sequencial_referencia=referencia.sequencial_referencia,
                nome=data.nome,
                nome_normalizado=nome_normalizado,
                status=data.status or STATUS_PADRAO,
                cliente_id=cliente_id,
                modelo_campanha=[item.model_dump(by_alias=False) for item in (data.modelo_campanha or [])],
                created_at=now,
                updated_at=now,
                **{campo: getattr(data, campo) for campo in _CAMPOS_SIMPLES},
            )
            self.repository.create(db, projeto)

            for usuario_id in responsavel_ids:
                self.repository.adicionar_responsavel(
                    db, ProjetoResponsavel(projeto_id=projeto.id, usuario_id=usuario_id, created_at=now)
                )
            for departamento_id in departamento_ids:
                self.repository.adicionar_departamento(
                    db,
                    ProjetoDepartamento(
                        projeto_id=projeto.id, departamento_id=departamento_id, created_at=now
                    ),
                )
            for membro in equipe:
                self.repository.adicionar_membro(
                    db,
                    ProjetoEquipeMembro(
                        projeto_id=projeto.id,
                        usuario_id=str(membro.usuario_id),
                        funcao=membro.funcao,
                        created_at=now,
                    ),
                )

            self._publish_event(db, projeto, DomainEventType.PROJETO_CRIADO, actor_usuario_id, occurred_at=now)
            for usuario_id in responsavel_ids:
                self._publish_event(
                    db, projeto, DomainEventType.PROJETO_RESPONSAVEL_ADICIONADO, actor_usuario_id,
                    extra_payload={"usuarioId": usuario_id}, occurred_at=now,
                )
            for departamento_id in departamento_ids:
                self._publish_event(
                    db, projeto, DomainEventType.PROJETO_DEPARTAMENTO_ADICIONADO, actor_usuario_id,
                    extra_payload={"departamentoId": departamento_id}, occurred_at=now,
                )
            for membro in equipe:
                self._publish_event(
                    db, projeto, DomainEventType.PROJETO_MEMBRO_ADICIONADO, actor_usuario_id,
                    extra_payload={"usuarioId": str(membro.usuario_id)}, occurred_at=now,
                )

            db.commit()
            db.refresh(projeto)
            return projeto
        except IntegrityError:
            # Corrida: dois inserts passaram pelo check antes de qualquer commit. Reconsulta
            # para distinguir conflito comum de conflito-arquivado.
            db.rollback()
            self._levantar_conflito(
                db, empresa_id=empresa_id, cliente_id=cliente_id, nome_normalizado=nome_normalizado
            )
            raise ProjetoConflictError("nome já cadastrado para este cliente") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_projetos(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        cliente_id: str | None = None,
        departamento_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Projeto]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            status=status,
            search=search,
            cliente_id=cliente_id,
            departamento_id=departamento_id,
            limit=limit,
            offset=offset,
        )

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Projeto]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    def get_projeto(self, db: Session, projeto_id: str) -> Projeto:
        projeto = self.repository.get_by_id(db, projeto_id)
        if projeto is None:
            raise ProjetoNotFoundError("Projeto não encontrado")
        return projeto

    # ----------------------------------------------------------------------------------
    # Alteração
    # ----------------------------------------------------------------------------------

    def update_projeto(
        self,
        db: Session,
        projeto_id: str,
        data: ProjetoUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Projeto:
        projeto = self.get_projeto(db, projeto_id)
        updates = data.model_dump(exclude_unset=True)
        campos_alterados: list[str] = []
        eventos_vinculo: list[tuple[DomainEventType, dict]] = []

        try:
            if projeto.status == STATUS_ARQUIVADO:
                raise ProjetoInvalidTransitionError(
                    "Projeto arquivado não pode ser editado — restaure-o antes"
                )

            # Nome e cliente afetam a mesma constraint, então a checagem considera os dois
            # valores FINAIS, não só o que mudou.
            nome_final = updates.get("nome", projeto.nome)
            nome_normalizado_final = self._normalizar_nome(nome_final)
            cliente_final = projeto.cliente_id
            if "cliente_id" in updates:
                cliente_final = str(updates["cliente_id"]) if updates["cliente_id"] else None

            if (
                nome_normalizado_final != projeto.nome_normalizado
                or cliente_final != projeto.cliente_id
            ):
                if cliente_final is not None and cliente_final != projeto.cliente_id:
                    self._ensure_cliente_valido(db, projeto.empresa_id, cliente_final)
                self._ensure_nome_disponivel(
                    db,
                    empresa_id=projeto.empresa_id,
                    cliente_id=cliente_final,
                    nome_normalizado=nome_normalizado_final,
                    excluir_id=projeto.id,
                )

            if "nome" in updates and updates["nome"] != projeto.nome:
                projeto.nome = updates["nome"]
                projeto.nome_normalizado = nome_normalizado_final
                campos_alterados.append("nome")

            if "cliente_id" in updates and cliente_final != projeto.cliente_id:
                projeto.cliente_id = cliente_final
                campos_alterados.append("clienteId")

            if "status" in updates and updates["status"] is not None and updates["status"] != projeto.status:
                projeto.status = updates["status"]
                campos_alterados.append("status")

            if "modelo_campanha" in updates:
                novos = [
                    item if isinstance(item, dict) else item.model_dump()
                    for item in (updates["modelo_campanha"] or [])
                ]
                if novos != (projeto.modelo_campanha or []):
                    projeto.modelo_campanha = novos
                    campos_alterados.append("modeloCampanha")

            for campo in _CAMPOS_SIMPLES:
                if campo not in updates:
                    continue
                if updates[campo] != getattr(projeto, campo):
                    setattr(projeto, campo, updates[campo])
                    campos_alterados.append(campo)

            if "responsavel_ids" in updates:
                eventos_vinculo += self._sincronizar_responsaveis(
                    db, projeto, [str(uid) for uid in (updates["responsavel_ids"] or [])]
                )
            if "departamento_responsavel_ids" in updates:
                eventos_vinculo += self._sincronizar_departamentos(
                    db, projeto, [str(did) for did in (updates["departamento_responsavel_ids"] or [])]
                )
            if "equipe" in updates:
                eventos_vinculo += self._sincronizar_equipe(db, projeto, updates["equipe"] or [])

            if eventos_vinculo:
                campos_alterados.append("vinculos")

            if campos_alterados:
                now = agora_utc()
                projeto.updated_at = now
                self.repository.update(db, projeto)
                self._publish_event(
                    db, projeto, DomainEventType.PROJETO_ALTERADO, actor_usuario_id,
                    extra_payload={"camposAlterados": campos_alterados}, occurred_at=now,
                )
                for tipo, payload in eventos_vinculo:
                    self._publish_event(db, projeto, tipo, actor_usuario_id, extra_payload=payload, occurred_at=now)

            db.commit()
            db.refresh(projeto)
            return projeto
        except IntegrityError:
            db.rollback()
            raise ProjetoConflictError("nome já cadastrado para este cliente") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Arquivamento — ver docs/padrao-arquivamento.md. Nunca há delete físico.
    # ----------------------------------------------------------------------------------

    def arquivar_projeto(
        self,
        db: Session,
        projeto_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str | None = None,
    ) -> Projeto:
        projeto = self.get_projeto(db, projeto_id)
        try:
            if projeto.status == STATUS_ARQUIVADO:
                raise ProjetoInvalidTransitionError("Projeto já está arquivado")

            now = agora_utc()
            projeto.status_anterior_arquivamento = projeto.status
            projeto.status = STATUS_ARQUIVADO
            projeto.arquivado_at = now
            projeto.arquivado_por_usuario_id = actor_usuario_id
            projeto.motivo_arquivamento = motivo_arquivamento
            projeto.restaurado_at = None
            projeto.restaurado_por_usuario_id = None
            projeto.updated_at = now

            self.repository.update(db, projeto)
            self._publish_event(
                db, projeto, DomainEventType.PROJETO_ARQUIVADO, actor_usuario_id,
                extra_payload={"motivoArquivamento": motivo_arquivamento}, occurred_at=now,
            )
            db.commit()
            db.refresh(projeto)
            return projeto
        except Exception:
            db.rollback()
            raise

    def restaurar_projeto(
        self, db: Session, projeto_id: str, *, actor_usuario_id: str | None = None
    ) -> Projeto:
        projeto = self.get_projeto(db, projeto_id)
        try:
            if projeto.status != STATUS_ARQUIVADO:
                raise ProjetoInvalidTransitionError("Somente projeto arquivado pode ser restaurado")

            # Não há checagem de nome aqui, de propósito: arquivar não libera o nome. A linha
            # arquivada continua ocupando `(empresa_id, cliente_id, nome_normalizado)`, e a
            # UNIQUE impede fisicamente que outro registro assuma o mesmo trio — é por isso
            # que recriar o nome devolve ProjetoArquivadoConflictError em vez de criar. Logo,
            # restaurar nunca encontra conflito, e uma verificação aqui seria código morto.
            now = agora_utc()
            projeto.status = projeto.status_anterior_arquivamento or STATUS_PADRAO
            projeto.restaurado_at = now
            projeto.restaurado_por_usuario_id = actor_usuario_id
            projeto.arquivado_at = None
            projeto.arquivado_por_usuario_id = None
            projeto.motivo_arquivamento = None
            projeto.status_anterior_arquivamento = None
            projeto.updated_at = now

            self.repository.update(db, projeto)
            self._publish_event(
                db, projeto, DomainEventType.PROJETO_RESTAURADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(projeto)
            return projeto
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Serialização
    # ----------------------------------------------------------------------------------

    def to_read(self, db: Session, projeto: Projeto) -> ProjetoRead:
        return ProjetoRead.model_validate(
            {
                **self._campos_base(projeto),
                "responsavelIds": self.repository.listar_responsavel_ids(db, projeto.id),
                "departamentoResponsavelIds": self.repository.listar_departamento_ids(db, projeto.id),
                "equipe": [
                    {"usuarioId": m.usuario_id, "funcao": m.funcao}
                    for m in self.repository.listar_equipe(db, projeto.id)
                ],
            }
        )

    def to_read_lote(self, db: Session, projetos: list[Projeto]) -> list[ProjetoRead]:
        """Três queries para a página inteira, em vez de três por linha."""
        ids = [p.id for p in projetos]
        responsaveis = self.repository.listar_responsavel_ids_em_lote(db, ids)
        departamentos = self.repository.listar_departamento_ids_em_lote(db, ids)
        equipes = self.repository.listar_equipe_em_lote(db, ids)
        return [
            ProjetoRead.model_validate(
                {
                    **self._campos_base(projeto),
                    "responsavelIds": responsaveis.get(projeto.id, []),
                    "departamentoResponsavelIds": departamentos.get(projeto.id, []),
                    "equipe": [
                        {"usuarioId": m.usuario_id, "funcao": m.funcao}
                        for m in equipes.get(projeto.id, [])
                    ],
                }
            )
            for projeto in projetos
        ]

    def to_diretorio_read_lote(self, projetos: list[Projeto]) -> list[ProjetoDiretorioRead]:
        return [
            ProjetoDiretorioRead.model_validate(
                {
                    "id": projeto.id,
                    "codigoInterno": projeto.codigo_interno,
                    "codigoReferencia": projeto.codigo_referencia,
                    "sequencialReferencia": projeto.sequencial_referencia,
                    "nome": projeto.nome,
                    "status": projeto.status,
                    "clienteId": projeto.cliente_id,
                }
            )
            for projeto in projetos
        ]

    @staticmethod
    def _campos_base(projeto: Projeto) -> dict:
        return {
            "id": projeto.id,
            "empresaId": projeto.empresa_id,
            "codigoInterno": projeto.codigo_interno,
            "codigoReferencia": projeto.codigo_referencia,
            "anoReferencia": projeto.ano_referencia,
            "sequencialReferencia": projeto.sequencial_referencia,
            "nome": projeto.nome,
            "campanha": projeto.campanha,
            "descricao": projeto.descricao,
            "resumo": projeto.resumo,
            "status": projeto.status,
            "prioridade": projeto.prioridade,
            "clienteId": projeto.cliente_id,
            "dataInicio": projeto.data_inicio,
            "dataFimPrevista": projeto.data_fim_prevista,
            "modeloCampanhaId": projeto.modelo_campanha_id,
            "modeloCampanha": projeto.modelo_campanha or [],
            "createdAt": projeto.created_at,
            "updatedAt": projeto.updated_at,
            "arquivadoAt": projeto.arquivado_at,
            "arquivadoPorUsuarioId": projeto.arquivado_por_usuario_id,
            "motivoArquivamento": projeto.motivo_arquivamento,
            "restauradoAt": projeto.restaurado_at,
            "restauradoPorUsuarioId": projeto.restaurado_por_usuario_id,
            "statusAnteriorArquivamento": projeto.status_anterior_arquivamento,
        }

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _ensure_nome_disponivel(
        self,
        db: Session,
        *,
        empresa_id: str,
        cliente_id: str | None,
        nome_normalizado: str,
        excluir_id: str | None = None,
    ) -> None:
        """Nome é único POR CLIENTE — ver docstring de app/models/projeto.py."""
        existente = self.repository.get_by_cliente_e_nome(
            db,
            empresa_id=empresa_id,
            cliente_id=cliente_id,
            nome_normalizado=nome_normalizado,
            excluir_id=excluir_id,
        )
        if existente is None:
            return
        if existente.status == STATUS_ARQUIVADO:
            raise ProjetoArquivadoConflictError(
                "Já existe um projeto arquivado com este nome para este cliente",
                projeto_arquivado_id=existente.id,
            )
        raise ProjetoConflictError("Já existe um projeto com este nome para este cliente")

    def _levantar_conflito(
        self, db: Session, *, empresa_id: str, cliente_id: str | None, nome_normalizado: str
    ) -> None:
        existente = self.repository.get_by_cliente_e_nome(
            db, empresa_id=empresa_id, cliente_id=cliente_id, nome_normalizado=nome_normalizado
        )
        if existente is not None and existente.status == STATUS_ARQUIVADO:
            raise ProjetoArquivadoConflictError(
                "Já existe um projeto arquivado com este nome para este cliente",
                projeto_arquivado_id=existente.id,
            ) from None

    def _ensure_cliente_valido(self, db: Session, empresa_id: str, cliente_id: str) -> None:
        cliente = self.cliente_repository.get_by_id(db, cliente_id)
        # Cross-tenant é tratado como "não encontrado" — não vaza existência.
        if cliente is None or cliente.empresa_id != empresa_id:
            raise ProjetoClienteInvalidoError("Cliente não encontrado nesta empresa")
        if cliente.status == STATUS_ARQUIVADO:
            raise ProjetoClienteInvalidoError(
                "Cliente arquivado não aceita novos vínculos — restaure-o antes"
            )

    def _ensure_usuario_valido(self, db: Session, empresa_id: str, usuario_id: str) -> None:
        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id:
            raise ProjetoUsuarioInvalidoError("Usuário não encontrado nesta empresa")
        if usuario.status in STATUS_USUARIO_INVALIDO:
            raise ProjetoUsuarioInvalidoError(
                f"Usuário com status '{usuario.status}' não pode ser vinculado ao projeto"
            )

    def _ensure_departamento_valido(self, db: Session, empresa_id: str, departamento_id: str) -> None:
        departamento = self.departamento_repository.get_by_id(db, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id:
            raise ProjetoDepartamentoInvalidoError("Departamento não encontrado nesta empresa")
        if departamento.status == STATUS_ARQUIVADO:
            raise ProjetoDepartamentoInvalidoError(
                "Departamento arquivado não aceita novos vínculos — restaure-o antes"
            )

    def _sincronizar_responsaveis(
        self, db: Session, projeto: Projeto, desejados: list[str]
    ) -> list[tuple[DomainEventType, dict]]:
        atuais = set(self.repository.listar_responsavel_ids(db, projeto.id))
        alvo = set(desejados)
        adicionar, remover = sorted(alvo - atuais), sorted(atuais - alvo)

        # Só o que ENTRA é validado: vínculo histórico com alguém depois inativado é
        # preservado, mas não pode ser criado de novo.
        for usuario_id in adicionar:
            self._ensure_usuario_valido(db, projeto.empresa_id, usuario_id)

        now = agora_utc()
        for usuario_id in adicionar:
            self.repository.adicionar_responsavel(
                db, ProjetoResponsavel(projeto_id=projeto.id, usuario_id=usuario_id, created_at=now)
            )
        for usuario_id in remover:
            self.repository.remover_responsavel(db, projeto_id=projeto.id, usuario_id=usuario_id)

        return [
            (DomainEventType.PROJETO_RESPONSAVEL_ADICIONADO, {"usuarioId": uid}) for uid in adicionar
        ] + [(DomainEventType.PROJETO_RESPONSAVEL_REMOVIDO, {"usuarioId": uid}) for uid in remover]

    def _sincronizar_departamentos(
        self, db: Session, projeto: Projeto, desejados: list[str]
    ) -> list[tuple[DomainEventType, dict]]:
        atuais = set(self.repository.listar_departamento_ids(db, projeto.id))
        alvo = set(desejados)
        adicionar, remover = sorted(alvo - atuais), sorted(atuais - alvo)

        for departamento_id in adicionar:
            self._ensure_departamento_valido(db, projeto.empresa_id, departamento_id)

        now = agora_utc()
        for departamento_id in adicionar:
            self.repository.adicionar_departamento(
                db,
                ProjetoDepartamento(
                    projeto_id=projeto.id, departamento_id=departamento_id, created_at=now
                ),
            )
        for departamento_id in remover:
            self.repository.remover_departamento(
                db, projeto_id=projeto.id, departamento_id=departamento_id
            )

        return [
            (DomainEventType.PROJETO_DEPARTAMENTO_ADICIONADO, {"departamentoId": did})
            for did in adicionar
        ] + [
            (DomainEventType.PROJETO_DEPARTAMENTO_REMOVIDO, {"departamentoId": did})
            for did in remover
        ]

    def _sincronizar_equipe(
        self, db: Session, projeto: Projeto, desejados: list
    ) -> list[tuple[DomainEventType, dict]]:
        """Reconcilia a equipe. `funcao` alterada não gera evento de entrada/saída — é
        alteração do vínculo, coberta pelo `projeto.alterado`."""
        atuais = {m.usuario_id: m for m in self.repository.listar_equipe(db, projeto.id)}
        # `model_dump()` devolve os nomes de CAMPO (`usuario_id`), não os aliases da API
        # (`usuarioId`) — o dicionário que chega aqui vem de `data.model_dump(exclude_unset=True)`.
        alvo = {
            (str(m["usuario_id"]) if isinstance(m, dict) else str(m.usuario_id)): (
                m.get("funcao") if isinstance(m, dict) else m.funcao
            )
            for m in desejados
        }

        adicionar = sorted(set(alvo) - set(atuais))
        remover = sorted(set(atuais) - set(alvo))

        for usuario_id in adicionar:
            self._ensure_usuario_valido(db, projeto.empresa_id, usuario_id)

        now = agora_utc()
        for usuario_id in adicionar:
            self.repository.adicionar_membro(
                db,
                ProjetoEquipeMembro(
                    projeto_id=projeto.id,
                    usuario_id=usuario_id,
                    funcao=alvo[usuario_id],
                    created_at=now,
                ),
            )
        for usuario_id in remover:
            self.repository.remover_membro(db, projeto_id=projeto.id, usuario_id=usuario_id)

        # Função alterada em quem permaneceu.
        for usuario_id in sorted(set(alvo) & set(atuais)):
            if atuais[usuario_id].funcao != alvo[usuario_id]:
                atuais[usuario_id].funcao = alvo[usuario_id]
                db.add(atuais[usuario_id])
        db.flush()

        return [(DomainEventType.PROJETO_MEMBRO_ADICIONADO, {"usuarioId": uid}) for uid in adicionar] + [
            (DomainEventType.PROJETO_MEMBRO_REMOVIDO, {"usuarioId": uid}) for uid in remover
        ]

    def _publish_event(
        self,
        db: Session,
        projeto: Projeto,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": projeto.empresa_id,
            "projeto_id": projeto.id,
            "codigo_referencia": projeto.codigo_referencia,
            "timestamp": timestamp.isoformat(),
            "status": projeto.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=projeto.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=projeto.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
