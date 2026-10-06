from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.configuracao_personalizacao import ConfiguracaoPersonalizacao


class ConfiguracaoPersonalizacaoRepository:
    """Só persistência e consulta — sem validação de imagem, sem disco, sem commit escondido (quem
    chama decide quando commitar; mesmo padrão de ConfiguracaoEmailRepository)."""

    def get_by_empresa(self, db: Session, empresa_id: str) -> ConfiguracaoPersonalizacao | None:
        statement = select(ConfiguracaoPersonalizacao).where(ConfiguracaoPersonalizacao.empresa_id == empresa_id)
        return db.scalars(statement).first()

    def create(self, db: Session, configuracao: ConfiguracaoPersonalizacao) -> ConfiguracaoPersonalizacao:
        db.add(configuracao)
        db.flush()
        return configuracao

    def update(self, db: Session, configuracao: ConfiguracaoPersonalizacao) -> ConfiguracaoPersonalizacao:
        db.add(configuracao)
        db.flush()
        return configuracao

    def delete(self, db: Session, configuracao: ConfiguracaoPersonalizacao) -> None:
        db.delete(configuracao)
        db.flush()
