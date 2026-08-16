from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Demanda(Base):
    """Demanda — a unidade de trabalho da operação. A interface chama de **Tarefa**.

    Não são entidades diferentes: `/tarefas` renderiza `DemandasView`, e não existe relação
    pai/filho. "Tarefa" é o rótulo; "Demanda" é o nome do domínio, coerente com
    `sessoes_trabalho.demanda_id`, que já existia.

    ## Dois identificadores visíveis, um técnico

    | | Papel | Reinicia por ano? |
    |---|---|---|
    | `id` (UUID) | técnico — PK/FK e rotas. **Nunca exibido** | — |
    | `codigo_referencia` (`T26000001`) | identidade **oficial** | **sim** |
    | `numero_operacional` (`2063`) | identificação **de trabalho** | **não** |

    São independentes: não compartilham dígitos, não derivam um do outro. A primeira demanda
    é `T26000001` **e** `2063` ao mesmo tempo; em 2027 a primeira é `T27000001` e `15843`.

    `numero_operacional` é `integer`, não texto: é número, e vai ser ordenado e comparado como
    tal. A exibição `#2063` é decisão de apresentação. Ele existe por um requisito operacional
    único — a primeira demanda continua a numeração que a equipe já usa no iClips —, semeado
    uma vez por `app/cli/inicializar_numero_operacional.py`.

    **Sem `codigo_interno`**: não haverá importação histórica de Demandas. Mesmo desenho de
    Projeto após a microfase 2D.1 (ver docs/pendencias-arquiteturais.md, item 4).

    ## Sem UNIQUE de nome

    Duas tarefas "Ajuste banner" no mesmo projeto e no mesmo dia são **rotina**. Nome não é
    identidade aqui, e um aviso de duplicidade — como o de Cliente e Fornecedor — viraria
    ruído constante. Analisado, não herdado.

    ## Status sem máquina de estados

    Valida-se apenas o **pertencimento ao conjunto**; qualquer transição entre valores válidos
    é aceita. Toda mudança gera evento `demanda.status_alterado` com `de` e `para` — é o
    evento que permitirá desenhar a política junto do Workflow real, com dado em vez de
    suposição.

    ## `motivo_bloqueio` como coluna, não tabela

    `status` é escalar e só admite um valor: não há bloqueios simultâneos a modelar.
    Obrigatório ao entrar em `bloqueada`, limpo ao sair. **O histórico não se perde** — vive
    nos eventos `demanda.bloqueada` / `.desbloqueada`, que carregam o motivo no payload.

    ## O que ainda não existe

    `workflowEtapas`, `etapaAtualId`, `checklist`, `arquivos`, `comentarios` e `historico`
    entram em 2E.2–2E.4. Nesta fase **não são aceitos na escrita** (422) nem simulados na
    leitura: a API devolve coleções vazias e a interface não oferece controle de edição.

    `prazo_etapa_atual` **é campo manual e independente** — não deriva de `prazoHoras` das
    etapas, e nunca derivou. A Pauta ordena por ele.
    """

    __tablename__ = "demandas"
    __table_args__ = (
        CheckConstraint(
            "status IN ('rascunho', 'planejada', 'em_execucao', 'pausada', 'bloqueada', "
            "'aguardando_cliente', 'concluida', 'cancelada', 'arquivada')",
            name="ck_demandas_status",
        ),
        CheckConstraint("prioridade IN ('baixa', 'media', 'alta')", name="ck_demandas_prioridade"),
        CheckConstraint(
            "data_inicio IS NULL OR data_fim_prevista IS NULL OR data_fim_prevista >= data_inicio",
            name="ck_demandas_periodo",
        ),
        UniqueConstraint("empresa_id", "codigo_referencia", name="uq_demandas_empresa_codigo_referencia"),
        UniqueConstraint(
            "empresa_id", "ano_referencia", "sequencial_referencia", name="uq_demandas_empresa_ano_sequencial"
        ),
        # O piso real do número operacional: mesmo que o contador seja adulterado direto no
        # banco, o INSERT falha em vez de reemitir um número já usado.
        UniqueConstraint("empresa_id", "numero_operacional", name="uq_demandas_empresa_numero_operacional"),
        Index("ix_demandas_empresa_id", "empresa_id"),
        Index("ix_demandas_status", "status"),
        Index("ix_demandas_codigo_referencia", "codigo_referencia"),
        Index("ix_demandas_numero_operacional", "numero_operacional"),
        Index("ix_demandas_cliente_id", "cliente_id"),
        Index("ix_demandas_projeto_id", "projeto_id"),
        Index("ix_demandas_criado_por_usuario_id", "criado_por_usuario_id"),
        Index("ix_demandas_workflow_modelo_id", "workflow_modelo_id"),
        # A Pauta ordena por este campo — índice evita sort em memória a cada abertura.
        Index("ix_demandas_prazo_etapa_atual", "prazo_etapa_atual"),
    )

    # --- identidade ---------------------------------------------------------------
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    codigo_referencia: Mapped[str] = mapped_column(String(16), nullable=False)
    ano_referencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sequencial_referencia: Mapped[int] = mapped_column(Integer, nullable=False)
    numero_operacional: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- conteúdo -----------------------------------------------------------------
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    # Campo legado sem semântica formal documentada em lugar nenhum do sistema. Migra como
    # texto livre; nomear o significado é trabalho de quem conhecer a origem.
    pit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    briefing: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- estado -------------------------------------------------------------------
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    prioridade: Mapped[str] = mapped_column(String(16), nullable=False)
    # Bandeira de prioridade — ativável só por Gestão, heads e Atendimento.
    sinalizada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    motivo_bloqueio: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- relações -----------------------------------------------------------------
    # SET NULL nos dois: arquivar cliente ou projeto nunca pode derrubar a demanda.
    cliente_id: Mapped[str | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )
    projeto_id: Mapped[str | None] = mapped_column(
        ForeignKey("projetos.id", ondelete="SET NULL"), nullable=True
    )
    # Necessário para o escopo de Atendimento ("demandas que eu criei"). Sem esta coluna, a
    # consulta teria de varrer `eventos` a cada listagem — caro e frágil.
    criado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    # Qual WorkflowModelo originou as etapas desta Demanda (ver demanda_workflow_etapas) —
    # só informativo: editar/arquivar o modelo depois nunca altera a Demanda já criada
    # (etapas são materializadas, não lidas do template). SET NULL porque WorkflowModelo
    # nunca é apagado fisicamente, só arquivado, e arquivar não pode derrubar a Demanda.
    workflow_modelo_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_modelos.id", ondelete="SET NULL"), nullable=True
    )

    # --- prazos -------------------------------------------------------------------
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    prazo_etapa_atual: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- ciclo com o cliente ------------------------------------------------------
    enviado_cliente_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prazo_retorno_cliente: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retorno_recebido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_conclusao_enviado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    email_conclusao_data: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- auditoria ----------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
