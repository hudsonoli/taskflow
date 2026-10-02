from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaArquivo(Base):
    """Metadado de um arquivo (ou link) anexado a uma Demanda (Fase 2E.3; Gerenciador de
    Arquivos — Fase 2H.1, migration 0036).

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

    ## `tipo` e o CHECK físico-ou-link

    `tipo` classifica o registro (`anexo`/`layout`/`link`, ver `DemandaArquivoService`).
    `nome_original`/`nome_fisico`/`tamanho_bytes` são obrigatórios para `anexo`/`layout`
    (arquivo físico real) e sempre NULL para `link` (que não tem conteúdo em disco — só
    `url`/`titulo`/`descricao`, obrigatórios nesse caso). `ck_demanda_arquivos_fisico_ou_link`
    garante essa coerência no banco, mesmo padrão de
    `ck_sessoes_trabalho_ativa_sem_fim`/`ck_sessoes_trabalho_encerrada_com_fim` em
    `app/models/sessao_trabalho.py` — nunca confiar só na validação do service.

    `status_layout` só é preenchido quando `tipo == 'layout'` (`ck_...status_layout_so_em_layout`).
    """

    __tablename__ = "demanda_arquivos"
    __table_args__ = (
        Index("ix_demanda_arquivos_demanda_id", "demanda_id"),
        CheckConstraint("tipo IN ('anexo', 'layout', 'link')", name="ck_demanda_arquivos_tipo"),
        CheckConstraint(
            "status_layout IS NULL OR status_layout IN ('novo', 'aprovado', 'reprovado', 'solicitar_alteracao')",
            name="ck_demanda_arquivos_status_layout",
        ),
        CheckConstraint(
            "status_layout IS NULL OR tipo = 'layout'",
            name="ck_demanda_arquivos_status_layout_so_em_layout",
        ),
        CheckConstraint(
            """
            (tipo IN ('anexo', 'layout')
                AND nome_original IS NOT NULL
                AND nome_fisico IS NOT NULL
                AND tamanho_bytes IS NOT NULL
                AND url IS NULL)
            OR
            (tipo = 'link'
                AND nome_original IS NULL
                AND nome_fisico IS NULL
                AND tamanho_bytes IS NULL
                AND url IS NOT NULL
                AND titulo IS NOT NULL)
            """,
            name="ck_demanda_arquivos_fisico_ou_link",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    demanda_id: Mapped[str] = mapped_column(ForeignKey("demandas.id", ondelete="CASCADE"), nullable=False)

    # NULL só para tipo='link' — ver CHECK ck_demanda_arquivos_fisico_ou_link.
    nome_original: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Nome do arquivo em disco, dentro da pasta da própria demanda — não um caminho completo.
    # NULL só para tipo='link'.
    nome_fisico: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # NULL só para tipo='link'.
    tamanho_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enviado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    # Gerenciador de Arquivos (migration 0036) — nenhum destes participa de RBAC.
    tipo: Mapped[str] = mapped_column(String(32), nullable=False, default="anexo", server_default=text("'anexo'"))
    status_layout: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Só para tipo='link': destino externo, nunca um caminho de disco.
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    titulo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
