from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SlaRegra(Base):
    """Regra de SLA da Empresa (Fase 2G.6B) — cadastro puro: só estrutura/lifecycle. Nenhum
    cálculo de prazo real acontece aqui nem em nenhum outro módulo ainda (ver Fase 2G.6A,
    itens 12-16) — `SlaResolver`/`CalculadoraExpediente` são Fase 2G.6C, integração com
    Demanda (snapshot) é 2G.6D. Este model só persiste o que o cadastro precisa guardar.

    ## Dois compromissos, não um

    `prazo_primeira_resposta_*`/`prazo_resolucao_*` são independentes: 1ª resposta é o tempo
    até o primeiro toque na Demanda, resolução é o tempo até concluir. Nenhum dos dois deriva
    do outro. Combinam com `WorkflowModeloEtapa.quantidade_antes_deadline`/`unidade_prazo` e
    `Demanda.prazo_etapa_atual` sem sobrepor: SLA é compromisso GLOBAL da Demanda (contrato
    com cliente/prioridade), os outros dois são internos ao processo — nenhuma coluna daqui
    lê, escreve ou substitui as de lá (ver relatório 2G.6A, item 14).

    ## Critérios opcionais, nunca obrigatórios

    `prioridade_alvo`/`departamento_id`/`cliente_id` são todos nullable: `NULL` em qualquer um
    significa "qualquer valor serve" para aquele critério — não uma string "todas" gravada no
    banco (o frontend é quem traduz `NULL` para o rótulo). Uma regra com os três `NULL` é a
    default genérica da Empresa; nada impede múltiplas regras genéricas coexistirem —
    `prioridade_regra` decide qual vence (resolução fica pra 2G.6C, `resolver_sla` ainda NÃO
    existe neste módulo).

    ## Sem ON DELETE SET NULL em cliente_id/departamento_id

    Diferente de `Projeto.cliente_id`, aqui NÃO se usa `SET NULL`: se a referência fosse
    removida fisicamente, `SET NULL` transformaria silenciosamente uma regra específica
    ("SLA do Cliente X") numa regra mais genérica ("SLA de qualquer cliente") sem intenção do
    usuário — pior que impedir a operação. Cliente/Departamento nunca são apagados fisicamente
    (soft-delete via `status`), então a FK sem `ondelete` nunca dispara na prática; ela só
    formaliza que, SE algum dia alguém tentasse apagar fisicamente uma dessas entidades
    referenciada aqui, o banco deve recusar, não mutar a regra.

    Arquivado/inativo pode continuar referenciado — a regra de "só ativo aceita vínculo NOVO"
    (mesmo padrão de `ProjetoModeloCampanhaService`/`ProjetoService`) só vale quando o campo
    está sendo definido/trocado, nunca retroativamente sobre um vínculo que já existia.
    """

    __tablename__ = "sla_regras"
    __table_args__ = (
        CheckConstraint(
            "prioridade_alvo IS NULL OR prioridade_alvo IN ('baixa', 'media', 'alta')",
            name="ck_sla_regras_prioridade_alvo",
        ),
        CheckConstraint("prioridade_regra >= 1", name="ck_sla_regras_prioridade_regra"),
        CheckConstraint(
            "prazo_primeira_resposta_quantidade > 0", name="ck_sla_regras_prazo_primeira_resposta_quantidade"
        ),
        CheckConstraint(
            "prazo_primeira_resposta_unidade IN ('minutos', 'horas', 'dias_corridos', 'dias_uteis')",
            name="ck_sla_regras_prazo_primeira_resposta_unidade",
        ),
        CheckConstraint("prazo_resolucao_quantidade > 0", name="ck_sla_regras_prazo_resolucao_quantidade"),
        CheckConstraint(
            "prazo_resolucao_unidade IN ('minutos', 'horas', 'dias_corridos', 'dias_uteis')",
            name="ck_sla_regras_prazo_resolucao_unidade",
        ),
        CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name="ck_sla_regras_status"),
        # Deliberadamente SEM UNIQUE(empresa_id, prioridade_regra) — duas regras podem
        # compartilhar precedência; o desempate é da 2G.6C, não uma restrição de banco.
        UniqueConstraint("empresa_id", "nome_normalizado", name="uq_sla_regras_empresa_nome_normalizado"),
        Index("ix_sla_regras_empresa_id", "empresa_id"),
        Index("ix_sla_regras_status", "status"),
        Index("ix_sla_regras_nome_normalizado", "nome_normalizado"),
        # Índice composto pro futuro filtro de resolução (empresa + status ativo é o caminho
        # de leitura mais quente da 2G.6C) — não inclui prioridade/cliente/departamento ainda
        # pra evitar over-indexing antes de a query real existir (ver relatório 2G.6A, item 21).
        Index("ix_sla_regras_empresa_status", "empresa_id", "status"),
        Index("ix_sla_regras_departamento_id", "departamento_id"),
        Index("ix_sla_regras_cliente_id", "cliente_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # NULL = qualquer prioridade de Demanda combina com esta regra.
    prioridade_alvo: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # NULL = qualquer Departamento/Cliente combina. Sem ondelete — ver docstring da classe.
    departamento_id: Mapped[str | None] = mapped_column(ForeignKey("departamentos.id"), nullable=True)
    cliente_id: Mapped[str | None] = mapped_column(ForeignKey("clientes.id"), nullable=True)

    # Precedência na resolução (2G.6C): menor valor = regra mais específica/prioritária.
    prioridade_regra: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    prazo_primeira_resposta_quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    prazo_primeira_resposta_unidade: Mapped[str] = mapped_column(String(16), nullable=False)
    prazo_resolucao_quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    prazo_resolucao_unidade: Mapped[str] = mapped_column(String(16), nullable=False)

    # Persistido nesta fase só como configuração — a semântica temporal (como combinar com
    # cada unidade acima) é definida e implementada na 2G.6C, nunca aqui.
    considerar_apenas_expediente: Mapped[bool] = mapped_column(nullable=False, default=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Mesmo padrão de
    # TipoTarefa/WorkflowModelo/ModeloCampanha: colunas de ator são String(36) sem FK.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
