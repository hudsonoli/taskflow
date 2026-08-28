"""Materializa o JSONB legado de Modelo de Campanha (`projetos.modelo_campanha`) no snapshot
relacional (`projeto_modelo_campanha`/`projeto_modelo_campanha_itens`) — Fase 2G.5C4.

    python -m app.cli.migrar_modelo_campanha_projetos --dry-run
    python -m app.cli.migrar_modelo_campanha_projetos
    python -m app.cli.migrar_modelo_campanha_projetos --empresa-id <uuid>
    python -m app.cli.migrar_modelo_campanha_projetos --projeto-id <uuid>

`--dry-run` é o modo seguro recomendado: resolve tudo, mas nunca chama `db.add()` para os
objetos do snapshot — não há "flush depois rollback" a se esquecer de fazer, o caminho de
escrita simplesmente não é exercido.

## Formato legado

`projetos.modelo_campanha` é `list[dict] | None`, sem schema no banco (JSONB puro) — a forma
documentada é a do antigo `ProjetoModeloCampanhaItem` (Pydantic, `app/schemas/projeto.py`,
removido do payload do frontend na Fase 2G.5C3 mas ainda é o formato historicamente gravado):

    {
        "id": str,                                    # nunca reaproveitado — ver "Identidade"
        "nome_demanda": str,
        "tipo_tarefa_id": str | None,                  # id legado em TEXTO, não necessariamente UUID
        "tipo_tarefa_nome": str | None,
        "briefing_base": str | None,
        "prioridade_padrao": "baixa" | "media" | "alta",
        "workflow_sugerido_id": str | None,
        "workflow_sugerido_nome": str | None,
        "responsavel_ou_setor_sugerido_id": str | None,
        "responsavel_ou_setor_sugerido_nome": str | None,
    }

Note a ausência de `peca_id`/`peca_nome`: o formato legado NUNCA teve referência a Peça — todo
item migrado nasce com `peca_id`/`peca_nome_snapshot` = NULL. Isso não é uma referência não
resolvida, é ausência de dado histórico: não há nada a resolver.

## `responsavel_ou_setor_sugerido_id` é sempre Departamento

Levantamento da Fase 2G.5C4 confirmou (contra o QA local, `TESTE 2G.1 - workflow real`) que
esse campo legado sempre guardou um id de Departamento, nunca de Usuário — o nome "setor
sugerido" já indicava isso. Resolvido exclusivamente como `responsavel_departamento_id`;
`responsavel_usuario_id` nasce sempre NULL nesta migração (nunca adivinhado).

## `modelo_campanha_id` legado nunca vira proveniência

`projetos.modelo_campanha_id` NÃO é FK confiável para `modelos_campanha.id` (o JSONB era
gravado antes de existir qualquer conceito de Modelo-como-entidade-de-biblioteca; o campo não
tem garantia de apontar pra nada). Nesta CLI ele nunca é lido, nunca resolvido, nunca vira
`modelo_campanha_origem_id` — o cabeçalho migrado nasce sempre com origem/nome-de-origem/
aplicado_at/aplicado_por_usuario_id = NULL (ver docstring de `ProjetoModeloCampanha`, que já
antecipava exatamente esta fase). Não é um "não deu pra resolver desta vez": é uma decisão
estrutural — nenhum dado existe pra popular esses quatro campos com verdade histórica.

## Identidade

Cabeçalho e itens recebem UUID novo, gerado aqui — nunca reaproveita o `id` textual do item
legado (que não é nem único globalmente, nem necessariamente um UUID). A ordem final dos itens
é reconstruída 1..N na ordem em que aparecem no array legado; nenhum campo de ordem legado é
lido (não existe um).

## Referências — lifecycle histórico

TipoTarefa/WorkflowModelo/Departamento são resolvidos se: o valor legado for um UUID
sintaticamente válido, a entidade existir, e pertencer à mesma Empresa do Projeto — SEM exigir
status ativo. Isto é migração histórica (reconstrução de um vínculo que já existia), não
criação de vínculo novo: a regra de "só ativo aceita vínculo novo" de
`ProjetoModeloCampanhaService` não se aplica aqui. Referência que não resolve (formato
inválido, inexistente, ou de outra Empresa) vira FK NULL com o nome histórico do JSONB
preservado quando presente — nunca aborta o Projeto inteiro, sempre registrado como
"referência não resolvida" no relatório.

## Nome snapshot

Sempre prefere o nome já gravado no JSONB (`*_nome`) sobre o nome atual do cadastro, mesmo
quando a referência resolve com sucesso — é o mesmo princípio de nunca recalcular nome
histórico da Fase 2G.5C3. Só cai pro nome atual do cadastro (marcado no relatório como
`via_fallback_atual`) quando o JSONB não trouxe nome nenhum para uma referência que resolveu.

## Idempotência (sem --force)

Se o Projeto já possui um `ProjetoModeloCampanha` — desta CLI ou de uma aplicação real via
`POST /aplicar` — a migração NUNCA cria outro nem sobrescreve o existente. Checado ANTES de
olhar o conteúdo do JSONB: um Projeto com snapshot real (aplicado pela aplicação) e JSONB vazio
é "já possui snapshot", não "sem legado" — a distinção entre as duas causas não importa pro
resultado (nada é criado), mas informa melhor o operador. Não existe `--force` nesta fase: ver
item 6 da Fase 2G.5C4 — sobrescrever um snapshot em uso é decisão administrativa deliberada,
fora deste comando.

## Atomicidade e transação

Por Projeto: cabeçalho + todos os itens são criados juntos, ou nada é criado. Um erro
ESTRUTURAL (JSONB que não é lista, item que não é objeto, `nome_demanda` ausente/vazio,
`prioridade_padrao` fora de baixa/media/alta) aborta SÓ aquele Projeto — os demais continuam
sendo processados. Referência não resolvida NÃO é erro estrutural (vira FK NULL, o Projeto
migra normalmente). Modo real: commit imediatamente após cada Projeto bem-sucedido — nunca uma
transação única pro lote inteiro (reduz o raio de um problema tardio).

Nenhum outro caminho (sem_legado, já possui snapshot, falhou, ou qualquer resultado em
dry-run) chama `db.commit()` nem `db.rollback()`: a garantia de "não escreve" vem inteira de
`_processar_projeto`/`_materializar_item` nunca chamarem `db.add()` nesses casos — não existe
nada pendente pra desfazer. Um `rollback()` "defensivo" ali NÃO seria inofensivo: numa sessão
com trabalho pendente de OUTRO Projeto (commit por Projeto significa que o próximo Projeto já
começa a ser processado antes de qualquer commit dele mesmo) ou, em teste, da própria fixture
que criou o Projeto, um rollback desnecessário reverteria esse trabalho alheio junto — bug real
encontrado escrevendo os testes desta fase (`test_estrutura_corrompida_...` e
`test_dry_run_nao_deixa_commit_persistente`), não uma hipótese.

## Sem evento

Nenhum evento de domínio é publicado. `PROJETO_MODELO_CAMPANHA_APLICADO` representa uma
aplicação operacional real (alguém escolheu um Modelo agora) — fingir isso pra um registro
histórico seria uma mentira no barramento de eventos. Não existe (e não foi criado) um tipo de
evento de migração; se um dia for necessário, é decisão própria, não implícita desta CLI.

## O legado permanece intacto

Em nenhum modo (dry-run ou real) esta CLI apaga ou altera `projetos.modelo_campanha`/
`modelo_campanha_id`. A remoção física é escopo da Fase 2G.5D, não desta.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.db.session import get_session_factory
from app.models.departamento import Departamento
from app.models.empresa import Empresa
# Nunca referenciado diretamente aqui (ver docstring do módulo — origem nunca é resolvida),
# mas precisa estar importado pra registrar a tabela `modelos_campanha` nos metadados do
# SQLAlchemy: `ProjetoModeloCampanha.modelo_campanha_origem_id` é uma FK pra ela, e o flush
# falha com NoReferencedTableError se nada no processo tiver importado o model ainda.
from app.models.modelo_campanha import ModeloCampanha  # noqa: F401
from app.models.peca import Peca  # noqa: F401 — mesma razão: FK de projeto_modelo_campanha_itens.peca_id
from app.models.projeto import Projeto
from app.models.projeto_modelo_campanha import ProjetoModeloCampanha, ProjetoModeloCampanhaItem
from app.models.tipo_tarefa import TipoTarefa
from app.models.workflow_modelo import WorkflowModelo
from app.repositories.projeto_modelo_campanha_repository import ProjetoModeloCampanhaRepository

EXIT_OK = 0
EXIT_ERRO = 1

_PRIORIDADES_VALIDAS = {"baixa", "media", "alta"}

# Campos do item legado que carregam referência — nome do campo no relatório -> (chave do id
# no JSONB, chave do nome no JSONB, model da entidade). `responsavel` sempre resolve como
# Departamento — ver docstring do módulo.
_CAMPOS_REFERENCIA = (
    ("tipo_tarefa", "tipo_tarefa_id", "tipo_tarefa_nome", TipoTarefa),
    ("workflow_modelo", "workflow_sugerido_id", "workflow_sugerido_nome", WorkflowModelo),
    ("responsavel_departamento", "responsavel_ou_setor_sugerido_id", "responsavel_ou_setor_sugerido_nome", Departamento),
)


class MigracaoAbortada(RuntimeError):
    """Motivo para não rodar a migração nenhuma — filtro explícito que não bateu com nada."""


class _ErroEstruturalProjeto(Exception):
    """JSONB do Projeto não tem forma materializável — aborta SÓ este Projeto (ver docstring
    do módulo, seção Atomicidade)."""


# ---------------------------------------------------------------------------------------
# Resultado / relatório
# ---------------------------------------------------------------------------------------


@dataclass
class ReferenciaResolvida:
    id: str | None
    nome_snapshot: str | None
    nome_via_fallback_atual: bool = False
    unresolved_motivo: str | None = None  # "formato_invalido" | "nao_encontrado" | "outra_empresa"


@dataclass
class ItemResultado:
    ordem: int
    nome: str
    referencias_nao_resolvidas: list[str] = field(default_factory=list)
    nomes_via_fallback_atual: list[str] = field(default_factory=list)


@dataclass
class ProjetoResultado:
    projeto_id: str
    codigo_referencia: str
    # "sem_legado" | "ja_migrado" | "migrado" | "falhou"
    status: str
    motivo_falha: str | None = None
    itens: list[ItemResultado] = field(default_factory=list)

    @property
    def quantidade_itens(self) -> int:
        return len(self.itens)

    @property
    def total_referencias_nao_resolvidas(self) -> int:
        return sum(len(item.referencias_nao_resolvidas) for item in self.itens)


@dataclass
class RelatorioMigracao:
    dry_run: bool
    projetos: list[ProjetoResultado] = field(default_factory=list)

    @property
    def analisados(self) -> int:
        return len(self.projetos)

    def _com_status(self, status: str) -> list[ProjetoResultado]:
        return [p for p in self.projetos if p.status == status]

    @property
    def sem_legado(self) -> int:
        return len(self._com_status("sem_legado"))

    @property
    def ja_migrados(self) -> int:
        return len(self._com_status("ja_migrado"))

    @property
    def migrados(self) -> int:
        return len(self._com_status("migrado"))

    @property
    def falharam(self) -> int:
        return len(self._com_status("falhou"))

    @property
    def migraveis(self) -> int:
        """Tinham legado materializável e não estavam já migrados — resultado real (sucesso
        ou falha estrutural) à parte."""
        return self.migrados + self.falharam

    @property
    def itens_materializados(self) -> int:
        return sum(p.quantidade_itens for p in self._com_status("migrado"))

    @property
    def referencias_nao_resolvidas(self) -> int:
        return sum(p.total_referencias_nao_resolvidas for p in self._com_status("migrado"))

    def imprimir(self, output=print) -> None:
        modo = "DRY-RUN (nenhuma escrita)" if self.dry_run else "EXECUÇÃO REAL"
        output(f"=== Migração de Modelo de Campanha legado — {modo} ===")
        output(f"Projetos analisados: {self.analisados}")
        output(f"Sem legado: {self.sem_legado}")
        output(f"Já migrados (snapshot existente, ignorados): {self.ja_migrados}")
        output(f"Migráveis: {self.migraveis}")
        output(f"  Migrados: {self.migrados}")
        output(f"  Falharam: {self.falharam}")
        output(f"Itens materializados: {self.itens_materializados}")
        output(f"Referências não resolvidas: {self.referencias_nao_resolvidas}")

        relevantes = self._com_status("migrado") + self._com_status("falhou")
        if relevantes:
            output("")
            output("--- Por Projeto ---")
            for projeto_resultado in relevantes:
                if projeto_resultado.status == "falhou":
                    output(
                        f"[FALHOU] {projeto_resultado.codigo_referencia} "
                        f"({projeto_resultado.projeto_id}) — {projeto_resultado.motivo_falha}"
                    )
                    continue
                linha = (
                    f"[MIGRADO] {projeto_resultado.codigo_referencia} "
                    f"({projeto_resultado.projeto_id}) — {projeto_resultado.quantidade_itens} item(ns)"
                )
                if projeto_resultado.total_referencias_nao_resolvidas:
                    linha += f", {projeto_resultado.total_referencias_nao_resolvidas} referência(s) não resolvida(s)"
                output(linha)


# ---------------------------------------------------------------------------------------
# Resolução de referência
# ---------------------------------------------------------------------------------------


def _uuid_valido(valor: str) -> bool:
    try:
        uuid.UUID(valor)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _resolver_referencia(
    db: Session, *, empresa_id: str, valor_legado: Any, nome_legado: Any, model_cls: type
) -> ReferenciaResolvida:
    if not valor_legado:
        return ReferenciaResolvida(id=None, nome_snapshot=None)

    nome_legado_str = nome_legado if isinstance(nome_legado, str) and nome_legado.strip() else None

    if not isinstance(valor_legado, str) or not _uuid_valido(valor_legado):
        return ReferenciaResolvida(id=None, nome_snapshot=nome_legado_str, unresolved_motivo="formato_invalido")

    entidade = db.get(model_cls, valor_legado)
    if entidade is None:
        return ReferenciaResolvida(id=None, nome_snapshot=nome_legado_str, unresolved_motivo="nao_encontrado")
    if entidade.empresa_id != empresa_id:
        return ReferenciaResolvida(id=None, nome_snapshot=nome_legado_str, unresolved_motivo="outra_empresa")

    # Resolvida — lifecycle (arquivado/inativo) é aceito de propósito: migração histórica, não
    # vínculo novo (ver docstring do módulo).
    if nome_legado_str:
        return ReferenciaResolvida(id=entidade.id, nome_snapshot=nome_legado_str)
    return ReferenciaResolvida(id=entidade.id, nome_snapshot=entidade.nome, nome_via_fallback_atual=True)


# ---------------------------------------------------------------------------------------
# Materialização
# ---------------------------------------------------------------------------------------


def _materializar_item(
    db: Session, *, empresa_id: str, ordem: int, item_legado: Any
) -> tuple[ProjetoModeloCampanhaItem, ItemResultado]:
    if not isinstance(item_legado, dict):
        raise _ErroEstruturalProjeto(
            f"item na posição {ordem} não é um objeto (tipo recebido: {type(item_legado).__name__})"
        )

    nome_demanda = item_legado.get("nome_demanda")
    if not isinstance(nome_demanda, str) or not nome_demanda.strip():
        raise _ErroEstruturalProjeto(f"item na posição {ordem} sem 'nome_demanda' válido")

    prioridade = item_legado.get("prioridade_padrao", "media")
    if prioridade not in _PRIORIDADES_VALIDAS:
        raise _ErroEstruturalProjeto(
            f"item na posição {ordem} tem 'prioridade_padrao' inválida: {prioridade!r}"
        )

    briefing_base = item_legado.get("briefing_base")
    briefing_padrao = briefing_base.strip() if isinstance(briefing_base, str) and briefing_base.strip() else None

    resolvidas: dict[str, ReferenciaResolvida] = {}
    for campo_relatorio, chave_id, chave_nome, model_cls in _CAMPOS_REFERENCIA:
        resolvidas[campo_relatorio] = _resolver_referencia(
            db,
            empresa_id=empresa_id,
            valor_legado=item_legado.get(chave_id),
            nome_legado=item_legado.get(chave_nome),
            model_cls=model_cls,
        )

    now = agora_utc()
    item_objeto = ProjetoModeloCampanhaItem(
        id=str(uuid.uuid4()),
        projeto_modelo_campanha_id="",  # setado pelo chamador após criar/carregar o cabeçalho
        ordem=ordem,
        nome=nome_demanda.strip(),
        briefing_padrao=briefing_padrao,
        prioridade_padrao=prioridade,
        # Formato legado nunca teve Peça — ver docstring do módulo.
        peca_id=None,
        peca_nome_snapshot=None,
        tipo_tarefa_id=resolvidas["tipo_tarefa"].id,
        tipo_tarefa_nome_snapshot=resolvidas["tipo_tarefa"].nome_snapshot,
        workflow_modelo_id=resolvidas["workflow_modelo"].id,
        workflow_modelo_nome_snapshot=resolvidas["workflow_modelo"].nome_snapshot,
        # responsavel_ou_setor_sugerido_id legado é sempre Departamento — nunca Usuário.
        responsavel_usuario_id=None,
        responsavel_usuario_nome_snapshot=None,
        responsavel_departamento_id=resolvidas["responsavel_departamento"].id,
        responsavel_departamento_nome_snapshot=resolvidas["responsavel_departamento"].nome_snapshot,
        created_at=now,
        updated_at=now,
    )

    item_resultado = ItemResultado(
        ordem=ordem,
        nome=item_objeto.nome,
        referencias_nao_resolvidas=[
            campo for campo, resolvida in resolvidas.items() if resolvida.unresolved_motivo is not None
        ],
        nomes_via_fallback_atual=[
            campo for campo, resolvida in resolvidas.items() if resolvida.nome_via_fallback_atual
        ],
    )
    return item_objeto, item_resultado


def _processar_projeto(
    db: Session, projeto: Projeto, *, dry_run: bool, repository: ProjetoModeloCampanhaRepository
) -> ProjetoResultado:
    # Checado ANTES do conteúdo do JSONB — ver docstring do módulo, seção Idempotência.
    if repository.get_by_projeto_id(db, projeto.id) is not None:
        return ProjetoResultado(projeto_id=projeto.id, codigo_referencia=projeto.codigo_referencia, status="ja_migrado")

    raw = projeto.modelo_campanha
    if raw is None or raw == []:
        return ProjetoResultado(projeto_id=projeto.id, codigo_referencia=projeto.codigo_referencia, status="sem_legado")

    if not isinstance(raw, list):
        return ProjetoResultado(
            projeto_id=projeto.id,
            codigo_referencia=projeto.codigo_referencia,
            status="falhou",
            motivo_falha=f"modelo_campanha não é uma lista (tipo recebido: {type(raw).__name__})",
        )

    try:
        itens_objetos: list[ProjetoModeloCampanhaItem] = []
        itens_resultado: list[ItemResultado] = []
        for ordem, item_legado in enumerate(raw, start=1):
            item_objeto, item_resultado = _materializar_item(
                db, empresa_id=projeto.empresa_id, ordem=ordem, item_legado=item_legado
            )
            itens_objetos.append(item_objeto)
            itens_resultado.append(item_resultado)
    except _ErroEstruturalProjeto as exc:
        return ProjetoResultado(
            projeto_id=projeto.id, codigo_referencia=projeto.codigo_referencia, status="falhou", motivo_falha=str(exc)
        )

    resultado = ProjetoResultado(
        projeto_id=projeto.id, codigo_referencia=projeto.codigo_referencia, status="migrado", itens=itens_resultado
    )

    if dry_run:
        return resultado

    now = agora_utc()
    cabecalho = ProjetoModeloCampanha(
        id=str(uuid.uuid4()),
        projeto_id=projeto.id,
        # Nunca resolvido a partir do modelo_campanha_id legado — ver docstring do módulo.
        modelo_campanha_origem_id=None,
        modelo_campanha_nome_snapshot=None,
        aplicado_at=None,
        aplicado_por_usuario_id=None,
        created_at=now,
        updated_at=now,
    )
    repository.create(db, cabecalho)
    for item_objeto in itens_objetos:
        item_objeto.projeto_modelo_campanha_id = cabecalho.id
    repository.replace_itens(db, projeto_modelo_campanha_id=cabecalho.id, itens=itens_objetos)

    return resultado


# ---------------------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------------------


def _resolver_projetos_alvo(db: Session, *, empresa_id: str | None, projeto_id: str | None) -> list[Projeto]:
    if empresa_id is not None and db.get(Empresa, empresa_id) is None:
        raise MigracaoAbortada(f"Empresa {empresa_id!r} não encontrada.")

    statement = select(Projeto).order_by(Projeto.created_at)
    if empresa_id is not None:
        statement = statement.where(Projeto.empresa_id == empresa_id)
    if projeto_id is not None:
        statement = statement.where(Projeto.id == projeto_id)

    projetos = list(db.scalars(statement).all())

    if projeto_id is not None and not projetos:
        raise MigracaoAbortada(f"Projeto {projeto_id!r} não encontrado" + (f" na Empresa {empresa_id!r}" if empresa_id else "") + ".")

    return projetos


def migrar(
    db: Session, *, dry_run: bool, empresa_id: str | None = None, projeto_id: str | None = None
) -> RelatorioMigracao:
    repository = ProjetoModeloCampanhaRepository()
    projetos = _resolver_projetos_alvo(db, empresa_id=empresa_id, projeto_id=projeto_id)

    relatorio = RelatorioMigracao(dry_run=dry_run)
    for projeto in projetos:
        resultado = _processar_projeto(db, projeto, dry_run=dry_run, repository=repository)
        relatorio.projetos.append(resultado)

        # Transação por Projeto — ver docstring do módulo, seção Atomicidade e transação.
        # Só o caminho de sucesso em modo real chama commit; nenhum outro caminho
        # (sem_legado/ja_migrado/falhou/dry-run) jamais chamou `db.add()` pra este Projeto —
        # não há nada pendente a desfazer. Um `db.rollback()` "defensivo" aqui NÃO é inofensivo:
        # numa sessão com trabalho pendente de outro Projeto (ou, em teste, da própria fixture),
        # ele reverteria esse trabalho alheio junto — a garantia de "dry-run não escreve" já
        # vem inteira de nunca chamar `db.add()`, não de desfazer depois.
        if not dry_run and resultado.status == "migrado":
            db.commit()

    return relatorio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrar_modelo_campanha_projetos",
        description=(
            "Materializa o JSONB legado de Modelo de Campanha em Projetos (projetos.modelo_campanha) "
            "no snapshot relacional (projeto_modelo_campanha)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não escreve nada — só resolve e reporta o que seria feito. Modo recomendado antes de executar de verdade.",
    )
    parser.add_argument("--empresa-id", default=None, help="Restringe a migração a uma única Empresa.")
    parser.add_argument("--projeto-id", default=None, help="Restringe a migração a um único Projeto.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with get_session_factory()() as db:
        try:
            relatorio = migrar(db, dry_run=args.dry_run, empresa_id=args.empresa_id, projeto_id=args.projeto_id)
        except MigracaoAbortada as exc:
            db.rollback()
            print(f"ABORTADO: {exc}", file=sys.stderr)
            return EXIT_ERRO

        relatorio.imprimir()
        return EXIT_ERRO if relatorio.falharam else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
