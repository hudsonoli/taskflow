from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaArquivo(Base):
    """Metadado de um arquivo anexado a uma Demanda (Fase 2E.3).

    O conteúdo físico vive em disco (`uploads/demandas/{demanda_id}/{id}{extensao}`); esta
    tabela é só o metadado — nome original, tipo, tamanho e quem enviou. Separação deliberada
    (ver docs/pendencias-arquiteturais.md item 9): o metadado no Postgres não muda se, no
    futuro, o conteúdo migrar de disco local para object storage — só `nome_fisico` passaria a
    significar uma chave de bucket em vez de um nome de arquivo, sem alterar a modelagem.

    `nome_fisico` é **sempre gerado pelo backend** a partir do próprio `id` — nunca derivado de
    `nome_original` (que é entrada do cliente). Isso elimina path traversal por construção: o
    nome físico nunca contém um caractere que não seja o UUID do próprio registro mais a
    extensão validada contra uma lista fechada.

    Sem `empresa_id` próprio, mesmo raciocínio de `DemandaChecklistItem` — isolamento via
    `demanda_id`, resolvido sempre através do escopo da Demanda.
    """

    __tablename__ = "demanda_arquivos"
    __table_args__ = (
        Index("ix_demanda_arquivos_demanda_id", "demanda_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    demanda_id: Mapped[str] = mapped_column(ForeignKey("demandas.id", ondelete="CASCADE"), nullable=False)

    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nome do arquivo em disco, dentro da pasta da própria demanda — não um caminho completo.
    nome_fisico: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    enviado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
