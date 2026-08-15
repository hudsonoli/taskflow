from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SequenciaOperacional(Base):
    """Contador **contínuo** — não reinicia na virada do ano.

    ## Por que não usar `sequencias_referencia`

    Aquela tabela é chaveada por `(empresa_id, tipo_entidade, **ano**)`, e o `ano` faz parte
    da identidade do contador: é justamente o que produz o reinício anual de
    D26000001 → D27000001. Seis domínios e a suíte inteira dependem disso.

    O número operacional é outra grandeza: `#2063` continua `#15843` em 2027, sem reiniciar.
    Injetar aqui um ano-sentinela (`0`) faria a coluna mentir — e convenção que mente é o tipo
    de coisa que alguém "conserta" seis meses depois. Uma tabela de três colunas é mais barata
    que essa ambiguidade.

    ## Escopo de uso

    Genérica no formato — `(empresa_id, tipo_entidade)` — mas com **um consumidor só nesta
    fase**: `"demanda"`. Não generalizar antes de existir o segundo caso real.

    ## Semente

    Nasce vazia. O número de go-live entra por `app/cli/inicializar_numero_operacional.py`,
    **não pelo `seed_all`**: continuidade com o iClips é dado de produção, não de reconstrução
    de banco. Base recém-criada começa em 1.
    """

    __tablename__ = "sequencias_operacionais"
    __table_args__ = (
        UniqueConstraint("empresa_id", "tipo_entidade", name="uq_sequencias_operacionais_empresa_tipo"),
        # Reforça no banco a regra que o CLI aplica: número operacional nunca é negativo.
        CheckConstraint("ultimo_numero >= 0", name="ck_sequencias_operacionais_ultimo_numero"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    tipo_entidade: Mapped[str] = mapped_column(String(32), nullable=False)
    ultimo_numero: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
