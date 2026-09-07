from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.configuracao_email import ConfiguracaoEmail


class ConfiguracaoEmailRepository:
    """Só persistência e consulta — sem criptografia, sem SMTP, sem commit escondido (quem
    chama decide quando commitar, mesmo padrão de RegraExpedienteRepository)."""

    def get_by_empresa(self, db: Session, empresa_id: str) -> ConfiguracaoEmail | None:
        statement = select(ConfiguracaoEmail).where(ConfiguracaoEmail.empresa_id == empresa_id)
        return db.scalars(statement).first()

    def create(self, db: Session, configuracao: ConfiguracaoEmail) -> ConfiguracaoEmail:
        db.add(configuracao)
        db.flush()
        return configuracao

    def update(self, db: Session, configuracao: ConfiguracaoEmail) -> ConfiguracaoEmail:
        db.add(configuracao)
        db.flush()
        return configuracao
