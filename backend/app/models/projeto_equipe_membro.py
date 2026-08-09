from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjetoEquipeMembro(Base):
    """Associação Projeto ↔ Usuário alocado, com a função exercida naquele projeto.

    `funcao` ("Direção de arte", "Atendimento") é atributo **do vínculo**, não da pessoa: o
    mesmo usuário pode ser direção de arte num projeto e revisor em outro. Por isso mora
    aqui e não em `usuarios`.

    O mock guardava também `nome`, `departamentoId` e `departamentoNome` replicados dentro
    de cada membro. Isso saiu: nome e departamento vêm por join de `usuarios`, e duplicá-los
    criaria dois lugares para a mesma verdade — o cadastro é atualizado, a cópia não, e a
    tela passa a mostrar o departamento antigo de alguém que mudou de setor.
    """

    __tablename__ = "projeto_equipe_membros"
    __table_args__ = (
        Index("ix_projeto_equipe_membros_usuario_id", "usuario_id"),
    )

    projeto_id: Mapped[str] = mapped_column(
        ForeignKey("projetos.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    funcao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
