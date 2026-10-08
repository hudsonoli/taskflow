from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.administrador_plataforma import AdministradorPlataforma
from app.models.usuario import Usuario


class AdministradorPlataformaRepository:
    def create(self, db: Session, administrador: AdministradorPlataforma) -> AdministradorPlataforma:
        db.add(administrador)
        db.flush()
        return administrador

    def update(self, db: Session, administrador: AdministradorPlataforma) -> AdministradorPlataforma:
        db.add(administrador)
        db.flush()
        return administrador

    def get_by_id(self, db: Session, administrador_id: str) -> AdministradorPlataforma | None:
        return db.get(AdministradorPlataforma, administrador_id)

    def get_by_usuario_id(self, db: Session, usuario_id: str) -> AdministradorPlataforma | None:
        return db.scalars(
            select(AdministradorPlataforma).where(AdministradorPlataforma.usuario_id == usuario_id)
        ).first()

    def empresas_que_hospedam_administrador_ativo(self, db: Session, empresa_ids: list[str]) -> set[str]:
        if not empresa_ids:
            return set()
        return set(
            db.scalars(
                select(Usuario.empresa_id)
                .join(AdministradorPlataforma, AdministradorPlataforma.usuario_id == Usuario.id)
                .where(AdministradorPlataforma.ativo.is_(True), Usuario.empresa_id.in_(empresa_ids))
            ).all()
        )

    def gestores_ativos_por_empresa(self, db: Session, empresa_ids: list[str]) -> dict[str, int]:
        """Gestores que ainda administram a empresa (ativo + acesso, nunca conta de sistema) — UMA consulta."""
        if not empresa_ids:
            return {}
        linhas = db.execute(
            select(Usuario.empresa_id, func.count(Usuario.id))
            .where(
                Usuario.empresa_id.in_(empresa_ids),
                Usuario.perfil_base == "gestor",
                Usuario.status == "ativo",
                Usuario.acesso_sistema.is_(True),
                Usuario.is_system_account.is_(False),
            )
            .group_by(Usuario.empresa_id)
        ).all()
        return {empresa_id: int(total) for empresa_id, total in linhas}
