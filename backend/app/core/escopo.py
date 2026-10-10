"""Escopo operacional — quem enxerga quais demandas, decidido no servidor.

## Por que isto existe

`frontend/src/lib/escopo-operacional.ts` avisa no topo que a autorização de lá *"é SOMENTE
UX. Esconder um item de menu ou bloquear uma rota no cliente NÃO é segurança"*. Enquanto
Demanda era `useState`, o alerta era teórico. Com Demanda persistida, deixar o filtro no
React significaria a API entregar a empresa inteira ao navegador.

Este módulo é o ponto **único** onde as regras de escopo vivem no backend. Nenhum repository
ou rota reimplementa a decisão — todos recebem o `EscopoDemanda` já resolvido.

## Regras transitórias, marcadas como tais

Duas coisas ainda são inferidas em vez de concedidas, porque não existe permissão granular:

- **Head** — resolvido por relação real (`Departamento.responsavel_usuario_id` ou
  `Usuario.lider_departamento` dentro do próprio departamento). Não é frágil, é limitado;
- **Atendimento** — inferido pelo **nome** do departamento. Isto é frágil e está aqui de
  propósito, num lugar só, para sumir quando o módulo de permissões existir.

Ambas reproduzem exatamente o comportamento já aprovado no frontend — a mudança é o *onde*,
não o *quê*.

## O que o cliente pode pedir

O escopo-base vem das permissões de quem chama e **é sempre aplicado**. O parâmetro `escopo`
só **estreita** dentro dele: pedir um escopo ao qual não se tem direito devolve **403**, não
uma lista vazia — lista vazia esconderia erro de permissão.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.departamento import Departamento
from app.models.usuario import Usuario

# REGRA TRANSITÓRIA: "ser do Atendimento" é inferido pelo nome do departamento. Mesmo valor
# que `NOME_DEPARTAMENTO_ATENDIMENTO` no frontend. Some quando houver concessão explícita.
NOME_DEPARTAMENTO_ATENDIMENTO = "atendimento"

# Perfis que enxergam a empresa inteira. Espelha `perfisComAcessoFinanceiro`/administrativo do
# frontend — quando houver permissão granular, vira concessão por pessoa.
PERFIS_VISAO_TOTAL: frozenset[str] = frozenset({"admin", "gestor"})


class EscopoSolicitado(StrEnum):
    """Recorte pedido pelo cliente. Nunca amplia o escopo-base."""

    MEUS = "meus"
    MEU_DEPARTAMENTO = "meu-departamento"
    ATENDIMENTO = "atendimento"
    # Fase 7C: Pauta GLOBAL — visão operacional da empresa inteira (do tenant do token), só para Atendimento, Head e Gestor/Admin.
    PAUTA = "pauta"


class EscopoNaoAutorizadoError(PermissionError):
    """Pediu um recorte a que não tem direito. Vira 403 na rota — nunca lista vazia."""


class EscopoHorasNaoAutorizadoError(PermissionError):
    """Pediu o agregado de horas de um departamento a que não tem direito. Vira 403 na rota."""


@dataclass(frozen=True)
class EscopoDemanda:
    """Resultado da resolução: o que este usuário pode ver.

    `visao_total` verdadeiro dispensa os demais campos — a consulta filtra só por empresa.
    """

    empresa_id: str
    usuario_id: str
    visao_total: bool
    usuario_responsavel: bool = False
    departamento_ids: tuple[str, ...] = ()
    cliente_ids: tuple[str, ...] = ()
    incluir_criadas_por_usuario: bool = False
    # Fase 8C.1 — escopo DERIVADO do Workflow (nada persistido): demandas cuja ETAPA ATUAL (derivada no SQL do snapshot, nunca do template) está
    # atribuída ao usuário individualmente (`etapa_atual_usuario`) ou a um departamento que ele lidera (`etapa_atual_departamento_ids`).
    etapa_atual_usuario: bool = False
    etapa_atual_departamento_ids: tuple[str, ...] = ()

    @property
    def vazio(self) -> bool:
        """Sem visão total e sem nenhum critério: não há o que mostrar.

        Acontece com operador sem departamento e sem demanda atribuída. Devolver lista vazia
        aqui é correto — não é falta de permissão, é ausência de vínculo.
        """
        return not self.visao_total and not (
            self.usuario_responsavel
            or self.departamento_ids
            or self.cliente_ids
            or self.incluir_criadas_por_usuario
            or self.etapa_atual_usuario
            or self.etapa_atual_departamento_ids
        )


def departamentos_como_head(db: Session, usuario: Usuario) -> list[str]:
    """Departamentos dos quais o usuário é head, por **relação real**.

    Head = responsável formal pelo departamento OU marcado como líder dentro do próprio
    departamento. União das duas regras já existentes, para não divergir do comportamento
    aprovado.

    Pública (Fase 2G.10B, D1.1) — além de `resolver_escopo_demanda`/
    `pode_consultar_horas_departamento` neste módulo, também é consumida por
    `require_demandas_criar()` (app/dependencies/permissoes.py) para decidir QUEM pode criar
    Demanda. Fonte única de "o que é Head" no sistema — nenhum outro lugar reimplementa este
    critério.
    """
    statement = select(Departamento.id).where(
        Departamento.empresa_id == usuario.empresa_id,
        Departamento.responsavel_usuario_id == usuario.id,
    )
    ids = list(db.scalars(statement).all())

    if usuario.lider_departamento and usuario.departamento_id:
        if usuario.departamento_id not in ids:
            ids.append(usuario.departamento_id)
    return ids


def pode_consultar_horas_departamento(db: Session, usuario: Usuario, departamento_id: str) -> bool:
    """Quem pode ver o agregado de horas consumidas de um departamento.

    admin/gestor: qualquer departamento da própria empresa (a checagem de "própria empresa"
    é responsabilidade de quem chama — buscar o Departamento já escopado por `empresa_id`
    antes de perguntar isto; ver `SessaoTrabalhoService.horas_departamento`).

    Head: só o(s) departamento(s) do qual é head de verdade — reaproveita
    `departamentos_como_head`, a MESMA resolução usada em `resolver_escopo_demanda`. Não há
    uma segunda definição de Head neste módulo.

    Demais perfis (operador comum, Atendimento sem ser Head): nunca.
    """
    if usuario.perfil_base in PERFIS_VISAO_TOTAL:
        return True
    return departamento_id in departamentos_como_head(db, usuario)


def eh_atendimento(db: Session, usuario: Usuario) -> bool:
    """REGRA TRANSITÓRIA — ver docstring do módulo.

    O **vínculo** do usuário com o departamento é o UUID; só o departamento já resolvido tem
    o nome consultado. Nome nunca decide a quem alguém pertence.
    """
    if not usuario.departamento_id:
        return False
    departamento = db.get(Departamento, usuario.departamento_id)
    if departamento is None or departamento.empresa_id != usuario.empresa_id:
        return False
    return departamento.nome.strip().lower() == NOME_DEPARTAMENTO_ATENDIMENTO


def pode_visualizar_pauta_global(db: Session, usuario: Usuario) -> bool:
    """Quem pode ver a PAUTA GLOBAL (Fase 7C): a visão operacional de todos os departamentos da PRÓPRIA empresa.

    Autorizados, pelas fontes únicas já existentes (nada hardcoded por e-mail, nome ou tenant):
    - admin/gestor (`PERFIS_VISAO_TOTAL`);
    - Head de pelo menos um departamento (`departamentos_como_head`);
    - Atendimento (`eh_atendimento`, a regra transitória por nome do departamento — centralizada aqui, não duplicada).

    Operador comum que não é nada disso NÃO recebe a Pauta global. "Global" significa DENTRO do tenant: o escopo devolvido
    continua preso a `usuario.empresa_id`. Leitura apenas — nenhuma permissão de escrita é concedida por aqui."""
    if usuario.perfil_base in PERFIS_VISAO_TOTAL:
        return True
    if departamentos_como_head(db, usuario):
        return True
    return eh_atendimento(db, usuario)


def clientes_sob_responsabilidade(db: Session, usuario: Usuario) -> list[str]:
    """Clientes onde `usuario` é o responsável comercial direto (`Cliente.
    responsavel_comercial_id`). Sem filtro de status — arquivado ou não, quem decide se um
    Cliente aceita vínculo novo é `_ensure_cliente_valido` (app/services/demanda_service.py),
    não este helper.

    Pública (Fase 2G.10B, D1.2C) — além de `resolver_escopo_demanda` (abaixo), também
    consumida por `DemandaService._ensure_contexto_cliente_permitido_para_atendimento` para
    decidir quais clientes um Atendimento pode usar numa Demanda. Fonte única de "carteira de
    clientes" no sistema — nenhum outro lugar reimplementa este critério."""
    statement = select(Cliente.id).where(
        Cliente.empresa_id == usuario.empresa_id,
        Cliente.responsavel_comercial_id == usuario.id,
    )
    return list(db.scalars(statement).all())


def resolver_escopo_demanda(
    db: Session, usuario: Usuario, solicitado: EscopoSolicitado | None = None
) -> EscopoDemanda:
    """Resolve o que este usuário pode ver, opcionalmente estreitado por `solicitado`.

    Chamado por **toda** consulta de demanda. Não existe caminho que devolva mais do que o
    escopo-base — `GET /demandas` sem parâmetro nenhum já vem filtrado.
    """
    visao_total = usuario.perfil_base in PERFIS_VISAO_TOTAL
    departamentos_head = departamentos_como_head(db, usuario)
    atendimento = eh_atendimento(db, usuario)

    # --- recorte explícito: valida o direito antes de estreitar ------------------------
    if solicitado is EscopoSolicitado.MEU_DEPARTAMENTO:
        if not departamentos_head:
            raise EscopoNaoAutorizadoError(
                "Somente o responsável por um departamento acessa o escopo do departamento"
            )
        return EscopoDemanda(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            visao_total=False,
            departamento_ids=tuple(departamentos_head),
        )

    if solicitado is EscopoSolicitado.PAUTA:
        if not (visao_total or departamentos_head or atendimento):
            raise EscopoNaoAutorizadoError("A Pauta global é restrita a Atendimento, Heads e Gestão")
        # Tenant do token; sem filtro de departamento/responsável/cliente — o cliente só REFINA com filtros.
        return EscopoDemanda(empresa_id=usuario.empresa_id, usuario_id=usuario.id, visao_total=True)

    if solicitado is EscopoSolicitado.ATENDIMENTO:
        if not atendimento:
            raise EscopoNaoAutorizadoError("Escopo de Atendimento é restrito ao departamento de Atendimento")
        return EscopoDemanda(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            visao_total=False,
            usuario_responsavel=True,
            cliente_ids=tuple(clientes_sob_responsabilidade(db, usuario)),
            incluir_criadas_por_usuario=True,
        )

    if solicitado is EscopoSolicitado.MEUS:
        # Sempre permitido: qualquer pessoa pode ver as próprias demandas. Fase 8C.1: inclui também as demandas em que a ETAPA ATUAL do
        # Workflow está atribuída ao usuário INDIVIDUALMENTE (trabalho atribuído a ele); liderança de departamento NÃO entra no Meu Dia.
        return EscopoDemanda(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            visao_total=False,
            usuario_responsavel=True,
            etapa_atual_usuario=True,
        )

    # --- escopo-base, sem recorte -----------------------------------------------------
    if visao_total:
        return EscopoDemanda(empresa_id=usuario.empresa_id, usuario_id=usuario.id, visao_total=True)

    departamentos: list[str] = list(departamentos_head)
    # Operador enxerga também o próprio departamento — é onde o trabalho dele acontece.
    if usuario.departamento_id and usuario.departamento_id not in departamentos:
        departamentos.append(usuario.departamento_id)

    return EscopoDemanda(
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        visao_total=False,
        usuario_responsavel=True,
        departamento_ids=tuple(departamentos),
        cliente_ids=tuple(clientes_sob_responsabilidade(db, usuario)) if atendimento else (),
        incluir_criadas_por_usuario=atendimento,
    )


def resolver_escopo_workflow_atual(db: Session, usuario: Usuario) -> EscopoDemanda:
    """Escopo DERIVADO da etapa atual do Workflow (Fase 8C.1): o que o usuário pode LER e AGIR (concluir/aprovar), além do escopo-base.

    Conceder atribuição operacional sem tornar ninguém `DemandaResponsavel`: vale só enquanto a etapa for a ATUAL, calculada em tempo real sobre o
    snapshot da Demanda — etapa futura, concluída, workflow concluído ou sem etapas não concedem nada, e nada é persistido. Fontes:
    responsável individual da etapa atual e Head real (`departamentos_como_head`) de um departamento responsável por ela. Admin/gestor já têm o
    escopo-base total; Atendimento não ganha nada por ser Atendimento.

    NÃO é um escopo de escrita geral: só as leituras do detalhe/subrecursos e as ações do Workflow o consultam (como FALLBACK do escopo-base).
    PATCH, comentários, uploads, checklist e demais escritas seguem no escopo-base."""
    return EscopoDemanda(
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        visao_total=False,
        etapa_atual_usuario=True,
        etapa_atual_departamento_ids=tuple(departamentos_como_head(db, usuario)),
    )
