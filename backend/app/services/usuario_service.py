from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.usuario import Usuario
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioCreate, UsuarioDiretorioRead, UsuarioRead, UsuarioUpdate
from app.services.empresa_service import STATUS_ARQUIVADA as EMPRESA_STATUS_ARQUIVADA
from app.services.empresa_service import STATUS_INATIVA as EMPRESA_STATUS_INATIVA
from app.services.domain_event_publisher import DomainEventPublisher

# Padrão de arquivamento (soft-delete permanente) — contrato completo documentado em
# docs/padrao-arquivamento.md. Ao migrar Cliente/Fornecedor, copiar de lá, não daqui.

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_BLOQUEADO = "bloqueado"
STATUS_ARQUIVADO = "arquivado"

# Campos de perfil rico que Create/Update aceitam e que são copiados 1:1 pro model — nunca
# inclui "is_system_account" (não existe no schema de entrada, ver app/schemas/usuario.py).
_PERFIL_FIELDS = (
    "telefone",
    "cpf",
    "data_nascimento",
    "cep",
    "bairro",
    "endereco_completo",
    "cidade",
    "uf",
    "contatos",
    "cargo",
    "foto_url",
    "lider_departamento",
    "valor_recebido_mensal_centavos",
    "horas_trabalho_aproximadas",
    "observacoes",
    "cor_identificacao",
)


class UsuarioNotFoundError(ValueError):
    pass


class UsuarioConflictError(ValueError):
    pass


class UsuarioArquivadoConflictError(ValueError):
    """E-mail ou código interno já pertence a um usuário arquivado — ver
    docs/padrao-arquivamento.md. Carrega o ID do registro arquivado pra a UI oferecer
    restaurar em vez de só mostrar um erro de duplicidade."""

    def __init__(self, message: str, *, usuario_arquivado_id: str) -> None:
        super().__init__(message)
        self.usuario_arquivado_id = usuario_arquivado_id


class UsuarioInvalidTransitionError(ValueError):
    pass


class UsuarioInvalidEmpresaError(ValueError):
    pass


class UsuarioDepartamentoInvalidoError(ValueError):
    """Departamento inexistente, de outra empresa ou arquivado (novo vínculo)."""


class UsuarioSystemAccountProtegidoError(ValueError):
    """A conta de sistema (is_system_account=true) não pode ser editada, inativada,
    reativada, bloqueada ou desbloqueada por nenhum caminho de API — proteção incondicional."""

    pass


class UsuarioService:
    def __init__(
        self,
        repository: UsuarioRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or UsuarioRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def create_usuario(
        self,
        db: Session,
        data: UsuarioCreate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        empresa_id = str(data.empresa_id)
        email = self._normalize_email(data.email)
        now = datetime.now(timezone.utc)
        perfil_kwargs = {field: getattr(data, field) for field in _PERFIL_FIELDS}
        # Departamento é relacionamento real. O schema já garante formato UUID; aqui
        # validamos existência, tenant e status antes de gravar.
        departamento_id = str(data.departamento_id) if data.departamento_id else None
        if departamento_id is not None:
            self._ensure_departamento_valido(db, empresa_id, departamento_id)
        if perfil_kwargs.get("contatos") is not None:
            perfil_kwargs["contatos"] = [contato.model_dump() for contato in data.contatos]

        usuario = Usuario(
            id=str(uuid4()),
            empresa_id=empresa_id,
            codigo_interno=data.codigo_interno,
            nome=data.nome,
            email=email,
            perfil_base=data.perfil_base,
            acesso_sistema=data.acesso_sistema,
            status=STATUS_ATIVO,
            created_at=now,
            updated_at=now,
            inativado_at=None,
            inativado_por_usuario_id=None,
            motivo_inativacao=None,
            departamento_id=departamento_id,
            **perfil_kwargs,
        )

        try:
            self._ensure_empresa_accepts_usuario(db, empresa_id)
            self._ensure_codigo_interno_available(db, empresa_id, usuario.codigo_interno)
            self._ensure_email_available(db, empresa_id, usuario.email)
            self.repository.create(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_CRIADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except IntegrityError:
            # Corrida entre duas criações concorrentes com o mesmo e-mail/código: os checks
            # acima passaram pros dois antes de qualquer um commitar. Reconsulta pra decidir
            # entre conflito comum e conflito-arquivado (ver docs/padrao-arquivamento.md).
            db.rollback()
            existing = self.repository.get_by_email(
                db, empresa_id=empresa_id, email=usuario.email
            ) or self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=usuario.codigo_interno)
            if existing is not None and existing.status == STATUS_ARQUIVADO:
                raise UsuarioArquivadoConflictError(
                    "Já existe um usuário arquivado com este e-mail/código interno",
                    usuario_arquivado_id=existing.id,
                ) from None
            raise UsuarioConflictError("e-mail ou codigoInterno já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def list_usuarios(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        perfil_base: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Usuario]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            status=status,
            perfil_base=perfil_base,
            search=search,
            limit=limit,
            offset=offset,
        )

    def list_diretorio(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        departamento_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Usuario]:
        # Sem status explícito, devolve todo mundo exceto arquivado (o repository já filtra
        # isso na query SQL) — referências históricas a usuário inativo/bloqueado ainda
        # precisam resolver nome/avatar. Filtrar só "ativo" é responsabilidade de quem monta
        # a lista de opções selecionáveis (picker), não deste endpoint.
        return self.repository.list_diretorio(
            db,
            empresa_id=empresa_id,
            status=status,
            departamento_id=departamento_id,
            search=search,
            limit=limit,
            offset=offset,
        )

    def get_usuario(self, db: Session, usuario_id: str) -> Usuario:
        """Busca administrativa (GET /usuarios/{id}) — a conta de sistema nunca é visível
        aqui, mesmo por ID direto."""
        usuario = self.repository.get_by_id_visible(db, usuario_id)
        if usuario is None:
            raise UsuarioNotFoundError("Usuário não encontrado")
        return usuario

    def get_me(self, db: Session, usuario_id: str) -> Usuario:
        """Busca irrestrita do próprio perfil — usada por GET /usuarios/me. Buscar a si
        mesmo não é "ser listado", então a conta de sistema também consegue chamar isto."""
        usuario = self.repository.get_by_id(db, usuario_id)
        if usuario is None:
            raise UsuarioNotFoundError("Usuário não encontrado")
        return usuario

    def update_usuario(
        self,
        db: Session,
        usuario_id: str,
        data: UsuarioUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            self._ensure_not_system_account(usuario)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "codigo_interno" in updates and updates["codigo_interno"] != usuario.codigo_interno:
                self._ensure_codigo_interno_available(
                    db,
                    usuario.empresa_id,
                    updates["codigo_interno"],
                    exclude_id=usuario.id,
                )
                usuario.codigo_interno = updates["codigo_interno"]
                changed_fields.append("codigoInterno")

            if "nome" in updates and updates["nome"] != usuario.nome:
                usuario.nome = updates["nome"]
                changed_fields.append("nome")

            if "email" in updates:
                email = self._normalize_email(updates["email"])
                if email != usuario.email:
                    self._ensure_email_available(db, usuario.empresa_id, email, exclude_id=usuario.id)
                    usuario.email = email
                    changed_fields.append("email")

            if "perfil_base" in updates and updates["perfil_base"] != usuario.perfil_base:
                usuario.perfil_base = updates["perfil_base"]
                changed_fields.append("perfilBase")

            if "acesso_sistema" in updates and updates["acesso_sistema"] != usuario.acesso_sistema:
                usuario.acesso_sistema = updates["acesso_sistema"]
                changed_fields.append("acessoSistema")

            if "departamento_id" in updates:
                novo_departamento = str(updates["departamento_id"]) if updates["departamento_id"] else None
                if novo_departamento != usuario.departamento_id:
                    if novo_departamento is not None:
                        self._ensure_departamento_valido(db, usuario.empresa_id, novo_departamento)
                    usuario.departamento_id = novo_departamento
                    changed_fields.append("departamentoId")

            for field in _PERFIL_FIELDS:
                if field not in updates:
                    continue
                value = updates[field]
                if field == "contatos" and value is not None:
                    value = [contato if isinstance(contato, dict) else contato.model_dump() for contato in value]
                if value != getattr(usuario, field):
                    setattr(usuario, field, value)
                    changed_fields.append(field)

            if changed_fields:
                now = datetime.now(timezone.utc)
                usuario.updated_at = now
                self.repository.update(db, usuario)
                self._publish_event(
                    db,
                    usuario,
                    DomainEventType.USUARIO_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def inativar_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        motivo_inativacao: str | None = None,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            self._ensure_not_system_account(usuario)
            if usuario.status == STATUS_INATIVO:
                raise UsuarioInvalidTransitionError("Usuário já está inativo")
            if usuario.status == STATUS_ARQUIVADO:
                raise UsuarioInvalidTransitionError("Usuário arquivado não pode ser inativado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_INATIVO
            usuario.updated_at = now
            usuario.inativado_at = now
            usuario.inativado_por_usuario_id = actor_usuario_id
            usuario.motivo_inativacao = motivo_inativacao
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_INATIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def reativar_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            self._ensure_not_system_account(usuario)
            if usuario.status == STATUS_ATIVO:
                raise UsuarioInvalidTransitionError("Usuário já está ativo")
            if usuario.status == STATUS_BLOQUEADO:
                raise UsuarioInvalidTransitionError("Usuário bloqueado deve ser desbloqueado")
            if usuario.status == STATUS_ARQUIVADO:
                raise UsuarioInvalidTransitionError("Usuário arquivado não pode ser reativado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_ATIVO
            usuario.updated_at = now
            usuario.inativado_at = None
            usuario.inativado_por_usuario_id = None
            usuario.motivo_inativacao = None
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_REATIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def bloquear_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            self._ensure_not_system_account(usuario)
            if usuario.status == STATUS_BLOQUEADO:
                raise UsuarioInvalidTransitionError("Usuário já está bloqueado")
            if usuario.status == STATUS_ARQUIVADO:
                raise UsuarioInvalidTransitionError("Usuário arquivado não pode ser bloqueado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_BLOQUEADO
            usuario.updated_at = now
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_BLOQUEADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def desbloquear_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Usuario:
        try:
            usuario = self.get_usuario(db, usuario_id)
            self._ensure_not_system_account(usuario)
            if usuario.status != STATUS_BLOQUEADO:
                raise UsuarioInvalidTransitionError("Somente usuário bloqueado pode ser desbloqueado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_ATIVO
            usuario.updated_at = now
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_DESBLOQUEADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def excluir_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> Usuario:
        """"Excluir" = arquivar (soft-delete permanente) — nunca apaga a linha nem troca o
        ID. Ver docs/padrao-arquivamento.md."""
        try:
            usuario = self.get_usuario(db, usuario_id)
            self._ensure_not_system_account(usuario)
            if usuario.status == STATUS_ARQUIVADO:
                raise UsuarioInvalidTransitionError("Usuário já está arquivado")

            now = datetime.now(timezone.utc)
            usuario.status_anterior_arquivamento = usuario.status
            usuario.status = STATUS_ARQUIVADO
            usuario.updated_at = now
            usuario.arquivado_at = now
            usuario.arquivado_por_usuario_id = actor_usuario_id
            usuario.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_ARQUIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def restaurar_usuario(
        self,
        db: Session,
        usuario_id: str,
        *,
        actor_usuario_id: str,
    ) -> Usuario:
        """Restaura sempre para "inativo" — nunca reativa sozinho, mesmo que o status antes
        do arquivamento fosse "ativo"/"bloqueado". Reativar é uma ação administrativa
        explícita separada (reativar_usuario). Ver docs/padrao-arquivamento.md."""
        try:
            usuario = self.get_usuario(db, usuario_id)
            self._ensure_not_system_account(usuario)
            if usuario.status != STATUS_ARQUIVADO:
                raise UsuarioInvalidTransitionError("Somente usuário arquivado pode ser restaurado")

            now = datetime.now(timezone.utc)
            usuario.status = STATUS_INATIVO
            usuario.updated_at = now
            usuario.restaurado_at = now
            usuario.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, usuario)
            self._publish_event(db, usuario, DomainEventType.USUARIO_RESTAURADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception:
            db.rollback()
            raise

    def to_read(self, usuario: Usuario) -> UsuarioRead:
        return UsuarioRead(
            id=usuario.id,
            empresaId=usuario.empresa_id,
            codigoInterno=usuario.codigo_interno,
            nome=usuario.nome,
            email=usuario.email,
            perfilBase=usuario.perfil_base,
            acessoSistema=usuario.acesso_sistema,
            status=usuario.status,
            telefone=usuario.telefone,
            cpf=usuario.cpf,
            dataNascimento=usuario.data_nascimento,
            cep=usuario.cep,
            bairro=usuario.bairro,
            enderecoCompleto=usuario.endereco_completo,
            cidade=usuario.cidade,
            uf=usuario.uf,
            contatos=usuario.contatos,
            departamentoId=usuario.departamento_id,
            cargo=usuario.cargo,
            fotoUrl=usuario.foto_url,
            liderDepartamento=usuario.lider_departamento,
            valorRecebidoMensalCentavos=usuario.valor_recebido_mensal_centavos,
            horasTrabalhoAproximadas=usuario.horas_trabalho_aproximadas,
            observacoes=usuario.observacoes,
            corIdentificacao=usuario.cor_identificacao,
            createdAt=usuario.created_at,
            updatedAt=usuario.updated_at,
            inativadoAt=usuario.inativado_at,
            inativadoPorUsuarioId=usuario.inativado_por_usuario_id,
            motivoInativacao=usuario.motivo_inativacao,
            arquivadoAt=usuario.arquivado_at,
            arquivadoPorUsuarioId=usuario.arquivado_por_usuario_id,
            motivoArquivamento=usuario.motivo_arquivamento,
            restauradoAt=usuario.restaurado_at,
            restauradoPorUsuarioId=usuario.restaurado_por_usuario_id,
            statusAnteriorArquivamento=usuario.status_anterior_arquivamento,
        )

    def to_diretorio_read(self, usuario: Usuario) -> UsuarioDiretorioRead:
        return UsuarioDiretorioRead(
            id=usuario.id,
            codigoInterno=usuario.codigo_interno,
            nome=usuario.nome,
            status=usuario.status,
            cargo=usuario.cargo,
            departamentoId=usuario.departamento_id,
            fotoUrl=usuario.foto_url,
            corIdentificacao=usuario.cor_identificacao,
        )

    def _ensure_empresa_accepts_usuario(self, db: Session, empresa_id: str) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None:
            raise UsuarioInvalidEmpresaError("Empresa não encontrada")
        if empresa.status == EMPRESA_STATUS_INATIVA:
            raise UsuarioInvalidEmpresaError("Empresa inativa não permite criação de usuário")
        if empresa.status == EMPRESA_STATUS_ARQUIVADA:
            raise UsuarioInvalidEmpresaError("Empresa arquivada não permite criação de usuário")

    def _ensure_codigo_interno_available(
        self,
        db: Session,
        empresa_id: str,
        codigo_interno: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existing = self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=codigo_interno)
        if existing is not None and existing.id != exclude_id:
            if existing.status == STATUS_ARQUIVADO:
                raise UsuarioArquivadoConflictError(
                    "codigoInterno já pertence a um usuário arquivado",
                    usuario_arquivado_id=existing.id,
                )
            raise UsuarioConflictError("codigoInterno já cadastrado para esta Empresa")

    def _ensure_email_available(
        self,
        db: Session,
        empresa_id: str,
        email: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existing = self.repository.get_by_email(db, empresa_id=empresa_id, email=email)
        if existing is not None and existing.id != exclude_id:
            if existing.status == STATUS_ARQUIVADO:
                raise UsuarioArquivadoConflictError(
                    "email já pertence a um usuário arquivado",
                    usuario_arquivado_id=existing.id,
                )
            raise UsuarioConflictError("email já cadastrado para esta Empresa")

    def _ensure_departamento_valido(self, db: Session, empresa_id: str, departamento_id: str) -> None:
        """Departamento precisa existir, ser da MESMA empresa e não estar arquivado.

        Cross-tenant é tratado como "não encontrado" — não vaza a existência de
        departamento de outra empresa. Vínculo histórico com departamento arquivado é
        preservado: esta checagem só roda quando o vínculo está sendo criado ou alterado.
        """
        from app.repositories.departamento_repository import DepartamentoRepository

        departamento = DepartamentoRepository().get_by_id(db, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id:
            raise UsuarioDepartamentoInvalidoError("Departamento não encontrado nesta empresa")
        if departamento.status == "arquivado":
            raise UsuarioDepartamentoInvalidoError(
                "Departamento arquivado não aceita novos vínculos — restaure-o antes"
            )

    @staticmethod
    def _ensure_not_system_account(usuario: Usuario) -> None:
        if usuario.is_system_account:
            raise UsuarioSystemAccountProtegidoError(
                "Conta de sistema não pode ser editada, inativada, reativada, bloqueada, "
                "desbloqueada, excluída ou restaurada"
            )

    def _publish_event(
        self,
        db: Session,
        usuario: Usuario,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": usuario.empresa_id,
            "usuario_id": usuario.id,
            "timestamp": timestamp.isoformat(),
            "perfil_base": usuario.perfil_base,
            "status": usuario.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=usuario.empresa_id,
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
