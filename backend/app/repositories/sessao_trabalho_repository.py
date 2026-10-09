"""Repository de SessaoTrabalho.

`get_active_equivalent` e `.list` filtram `usuario_id`/`departamento_id` por comparação
direta de UUID — sem `LOWER`/`TRANSLATE` nem ponte de acentuação (diferente do caso de
Departamento por nome, `0008`; aqui sempre foi id). Pós expand/contract (`0015`–`0018`, ver
`app/models/sessao_trabalho.py`): não há mais coluna textual legada para confundir com a FK.
"""

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.sessao_trabalho import SessaoTrabalho


def _remove_acentos(texto: str) -> str:
    """Mesma regra de `normalize()` em frontend/src/lib/trafego.ts: minúsculas + NFD sem as
    marcas combinantes U+0300–U+036F."""
    decomposto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in decomposto if not 0x300 <= ord(c) <= 0x36F)


def _mapa_acentos() -> tuple[str, str]:
    """Tabela para `translate()` do Postgres (o banco não tem a extensão `unaccent` e esta
    entrega não cria migration): cada letra latina que o NFD decompõe em base ASCII + marcas
    vira a base em minúscula. Gerada do próprio `unicodedata`, então bate com `_remove_acentos`
    para todo o Latin-1 Suplemento/Latin Estendido-A/B e Latin Estendido Adicional."""
    origem: list[str] = []
    destino: list[str] = []
    for codigo in (*range(0x00C0, 0x0250), *range(0x1E00, 0x1F00)):
        caractere = chr(codigo)
        decomposto = unicodedata.normalize("NFD", caractere)
        base = decomposto[0]
        if (
            len(decomposto) > 1
            and base.isascii()
            and base.isalpha()
            and all(0x300 <= ord(c) <= 0x36F for c in decomposto[1:])
        ):
            origem.append(caractere)
            destino.append(base.lower())
    return "".join(origem), "".join(destino)


_ACENTOS_ORIGEM, _ACENTOS_DESTINO = _mapa_acentos()


@dataclass(frozen=True)
class FiltrosSessaoAvancados:
    """Filtros avançados da Central de Tráfego (além de usuário/departamento "é um de" e da busca de Demanda).

    Entre campos diferentes vale AND; dentro de um campo, `x` é "é um de" (OR) e `x_excluir` é "não é um de".
    Cliente, projeto, prioridade e prazo são atributos da DEMANDA da sessão (junção à esquerda, mesma empresa):
    sessão cuja Demanda não existe não casa com "é", e casa com "não é" (NULL não é igual a nenhum valor).
    `prazo_inicio`/`prazo_fim` delimitam `demandas.prazo_etapa_atual` (inclusivo); demanda sem prazo nunca casa.
    """

    usuario_ids_excluir: Sequence[str] | None = None
    departamento_ids_excluir: Sequence[str] | None = None
    cliente_ids: Sequence[str] | None = None
    cliente_ids_excluir: Sequence[str] | None = None
    projeto_ids: Sequence[str] | None = None
    projeto_ids_excluir: Sequence[str] | None = None
    prioridades: Sequence[str] | None = None
    prioridades_excluir: Sequence[str] | None = None
    prazo_inicio: datetime | None = None
    prazo_fim: datetime | None = None

    @property
    def exige_demanda(self) -> bool:
        return any(
            (
                self.cliente_ids,
                self.cliente_ids_excluir,
                self.projeto_ids,
                self.projeto_ids_excluir,
                self.prioridades,
                self.prioridades_excluir,
                self.prazo_inicio,
                self.prazo_fim,
            )
        )


def _lista_demanda(
    clausulas: list[str], parametros: dict, coluna: str, nome: str, incluir: Sequence[str] | None, excluir: Sequence[str] | None
) -> None:
    if incluir:
        clausulas.append(f"{coluna} = ANY(:{nome})")
        parametros[nome] = list(incluir)
    if excluir:
        clausulas.append(f"({coluna} IS NULL OR {coluna} <> ALL(:{nome}_excluir))")
        parametros[f"{nome}_excluir"] = list(excluir)


def _filtros_sessao(
    usuario_ids: Sequence[str] | None,
    departamento_ids: Sequence[str] | None,
    demanda_query: str | None,
    avancados: FiltrosSessaoAvancados | None = None,
) -> tuple[str, list[str], dict]:
    """Filtros de sessão da tela de Tráfego (`filterSessoes` no cliente), compartilhados pelos
    agregados de D3C1 (`indicadores_trafego`) e D3C2 (`carga_trafego`) — a MESMA regra, em um
    lugar só. Devolve `(junção_com_demanda, cláusulas, parâmetros)`; só fragmentos fixos vão para
    o SQL — todo valor do usuário é parâmetro ligado.

    - `usuario_ids`/`departamento_ids`: o campo DA SESSÃO está na lista (sessão sem usuário/
      departamento nunca casa quando o filtro está ativo); vazio/None = sem filtro;
    - `demanda_query`: busca `"<demandaId> #<número> — <nome>"` (ou `"<demandaId> <demandaId>"`
      quando a Demanda não existe), sem acento/caixa, SEM aparar a consulta (o cliente só usa
      `trim()` para decidir se há filtro). Só aplicada se `demanda_query.strip()` não for vazio;
    - `avancados` (`FiltrosSessaoAvancados`): "não é um de" de usuário/departamento e os filtros por atributo da
      Demanda (cliente, projeto, prioridade, prazo). Os que dependem da Demanda ligam a junção abaixo.
    """
    clausulas: list[str] = []
    parametros: dict = {}

    if usuario_ids:
        clausulas.append("s.usuario_id = ANY(:usuario_ids)")
        parametros["usuario_ids"] = list(usuario_ids)
    if departamento_ids:
        clausulas.append("s.departamento_id = ANY(:departamento_ids)")
        parametros["departamento_ids"] = list(departamento_ids)

    if avancados is not None:
        if avancados.usuario_ids_excluir:
            clausulas.append("(s.usuario_id IS NULL OR s.usuario_id <> ALL(:usuario_ids_excluir))")
            parametros["usuario_ids_excluir"] = list(avancados.usuario_ids_excluir)
        if avancados.departamento_ids_excluir:
            clausulas.append("(s.departamento_id IS NULL OR s.departamento_id <> ALL(:departamento_ids_excluir))")
            parametros["departamento_ids_excluir"] = list(avancados.departamento_ids_excluir)
        _lista_demanda(clausulas, parametros, "d.cliente_id", "cliente_ids", avancados.cliente_ids, avancados.cliente_ids_excluir)
        _lista_demanda(clausulas, parametros, "d.projeto_id", "projeto_ids", avancados.projeto_ids, avancados.projeto_ids_excluir)
        _lista_demanda(clausulas, parametros, "d.prioridade", "prioridades", avancados.prioridades, avancados.prioridades_excluir)
        if avancados.prazo_inicio is not None:
            clausulas.append("d.prazo_etapa_atual >= :prazo_inicio")
            parametros["prazo_inicio"] = avancados.prazo_inicio
        if avancados.prazo_fim is not None:
            clausulas.append("d.prazo_etapa_atual <= :prazo_fim")
            parametros["prazo_fim"] = avancados.prazo_fim

    juncao_demanda = ""
    if avancados is not None and avancados.exige_demanda:
        juncao_demanda = "LEFT JOIN demandas d ON d.id = s.demanda_id AND d.empresa_id = s.empresa_id"
    if demanda_query is not None and demanda_query.strip():
        # Demanda é junção À ESQUERDA: sessão cuja Demanda não existe continua no universo
        # (o cliente também a mantinha, casando só pelo próprio `demandaId`). `d.empresa_id`
        # na junção impede cruzar tenants por um id colidente.
        juncao_demanda = "LEFT JOIN demandas d ON d.id = s.demanda_id AND d.empresa_id = s.empresa_id"
        clausulas.append(
            """strpos(
                lower(translate(
                    s.demanda_id || ' ' || COALESCE(d.identificador || ' — ' || d.nome, s.demanda_id),
                    :acentos_origem, :acentos_destino
                )),
                :demanda_query
            ) > 0"""
        )
        parametros["demanda_query"] = _remove_acentos(demanda_query)
        parametros["acentos_origem"] = _ACENTOS_ORIGEM
        parametros["acentos_destino"] = _ACENTOS_DESTINO

    return juncao_demanda, clausulas, parametros


class SessaoTrabalhoRepository:
    def create(self, db: Session, sessao: SessaoTrabalho) -> SessaoTrabalho:
        db.add(sessao)
        db.flush()
        return sessao

    def flush(self, db: Session) -> None:
        db.flush()

    def get_by_id(self, db: Session, sessao_id: str) -> SessaoTrabalho | None:
        return db.get(SessaoTrabalho, sessao_id)

    def demanda_ids_ativas_do_usuario(self, db: Session, *, empresa_id: str, usuario_id: str) -> list[str]:
        """Demandas em que o PRÓPRIO usuário tem uma sessão de trabalho ATIVA agora (Meu Dia). Só ids, ordem estável."""
        statement = (
            select(SessaoTrabalho.demanda_id)
            .where(
                SessaoTrabalho.empresa_id == empresa_id,
                SessaoTrabalho.usuario_id == usuario_id,
                SessaoTrabalho.status == "ativa",
            )
            .distinct()
            .order_by(SessaoTrabalho.demanda_id.asc())
        )
        return list(db.scalars(statement).all())

    def demanda_ids_ativas_da_empresa(self, db: Session, *, empresa_id: str) -> list[str]:
        """Demandas com ALGUMA sessão ativa na empresa (Pauta global: sinal discreto "em execução agora"). Só ids de demanda —
        sem pessoa, sem tempo."""
        statement = (
            select(SessaoTrabalho.demanda_id)
            .where(SessaoTrabalho.empresa_id == empresa_id, SessaoTrabalho.status == "ativa")
            .distinct()
            .order_by(SessaoTrabalho.demanda_id.asc())
        )
        return list(db.scalars(statement).all())

    def equipe_do_departamento_agora(self, db: Session, *, empresa_id: str, departamento_id: str) -> list[dict]:
        """Meu Departamento (Fase 7C): para cada colaborador ATIVO do departamento, em que demandas ele tem sessão de trabalho
        ATIVA agora. Fonte = sessão real (nunca status da demanda, presença ou último acesso). Duas consultas, sem N+1; conta de
        sistema nunca aparece. Não devolve horário nem duração: é "quem está fazendo o quê", não vigilância de tempo."""
        membros = db.execute(
            text(
                """
                SELECT u.id, u.nome, u.cor_identificacao, u.foto_url
                FROM usuarios u
                WHERE u.empresa_id = :empresa_id
                  AND u.departamento_id = :departamento_id
                  AND u.status = 'ativo'
                  AND u.is_system_account = false
                ORDER BY lower(u.nome) ASC, u.id ASC
                """
            ),
            {"empresa_id": empresa_id, "departamento_id": departamento_id},
        ).all()
        if not membros:
            return []
        ativas = db.execute(
            text(
                """
                SELECT s.usuario_id, s.demanda_id, d.numero_operacional, d.identificador, d.nome AS demanda_nome
                FROM sessoes_trabalho s
                LEFT JOIN demandas d ON d.id = s.demanda_id AND d.empresa_id = s.empresa_id
                WHERE s.empresa_id = :empresa_id
                  AND s.status = 'ativa'
                  AND s.usuario_id = ANY(:usuario_ids)
                ORDER BY s.inicio_em ASC, s.id ASC
                """
            ),
            {"empresa_id": empresa_id, "usuario_ids": [membro.id for membro in membros]},
        ).all()
        por_usuario: dict[str, list[dict]] = {}
        for linha in ativas:
            por_usuario.setdefault(linha.usuario_id, []).append(
                {
                    "demandaId": linha.demanda_id,
                    "numeroOperacional": linha.numero_operacional,
                    "identificador": linha.identificador,
                    "nome": linha.demanda_nome,
                }
            )
        return [
            {
                "usuarioId": membro.id,
                "nome": membro.nome,
                "corIdentificacao": membro.cor_identificacao,
                "fotoUrl": membro.foto_url,
                "emExecucao": por_usuario.get(membro.id, []),
            }
            for membro in membros
        ]

    def get_by_evento_inicio_id(self, db: Session, evento_inicio_id: str) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(SessaoTrabalho.evento_inicio_id == evento_inicio_id)
        return db.scalar(statement)

    def get_by_evento_fim_id(self, db: Session, evento_fim_id: str) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(SessaoTrabalho.evento_fim_id == evento_fim_id)
        return db.scalar(statement)

    def get_active_equivalent(
        self,
        db: Session,
        *,
        demanda_id: str,
        usuario_id: str | None,
        departamento_id: str | None,
    ) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(
            SessaoTrabalho.demanda_id == demanda_id,
            SessaoTrabalho.status == "ativa",
        )
        if usuario_id:
            statement = statement.where(SessaoTrabalho.usuario_id == usuario_id)
        else:
            statement = statement.where(
                SessaoTrabalho.usuario_id.is_(None),
                SessaoTrabalho.departamento_id == departamento_id,
            )
        return db.scalar(statement)

    def list(
        self,
        db: Session,
        *,
        empresa_id: str | None = None,
        demanda_id: str | None = None,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        workflow_etapa_id: str | None = None,
        status: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessaoTrabalho]:
        statement = select(SessaoTrabalho)

        if empresa_id:
            statement = statement.where(SessaoTrabalho.empresa_id == empresa_id)
        if demanda_id:
            statement = statement.where(SessaoTrabalho.demanda_id == demanda_id)
        if usuario_id:
            statement = statement.where(SessaoTrabalho.usuario_id == usuario_id)
        if departamento_id:
            statement = statement.where(SessaoTrabalho.departamento_id == departamento_id)
        if workflow_etapa_id:
            statement = statement.where(SessaoTrabalho.workflow_etapa_id == workflow_etapa_id)
        if status:
            statement = statement.where(SessaoTrabalho.status == status)
        if data_inicio:
            statement = statement.where(SessaoTrabalho.inicio_em >= data_inicio)
        if data_fim:
            statement = statement.where(SessaoTrabalho.inicio_em <= data_fim)

        statement = statement.order_by(SessaoTrabalho.inicio_em.desc(), SessaoTrabalho.created_at.desc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def horas_departamento(
        self, db: Session, *, empresa_id: str, departamento_id: str
    ) -> tuple[float, int]:
        """Agregado em SQL — nunca busca sessões individuais para o chamador somar.

        ## Pertencimento (a mesma regra OR que `horasExecutadasPorEscopo` aplicava no
        frontend antes deste endpoint existir, ver `lib/escopo-operacional.ts`)

        Uma sessão conta para o departamento quando:
        - o RESPONSÁVEL (`usuario_id`) tem `usuarios.departamento_id = departamento_id`
          (colaborador definido por vínculo organizacional — decisão aprovada: não por
          responsabilidade em Demanda); OU
        - a sessão foi aberta vinculada diretamente ao departamento (`departamento_id`),
          sem usuário — caso de trabalho não atribuído a uma pessoa específica.

        ## Duração (mesma fórmula do frontend, comparada campo a campo antes de implementar)

        Sessão ENCERRADA usa `duracao_segundos`, já calculado no fechamento — não recalcula.
        Sessão ainda ATIVA (`duracao_segundos IS NULL`) calcula ao vivo:
        `EXTRACT(EPOCH FROM (NOW() - inicio_em))`, com `GREATEST(0, ...)` (mesma defesa que o
        frontend fazia com `Math.max(0, …)` contra relógio adiantado) e `FLOOR(...)` (mesmo
        truncamento de `Math.floor`, não arredondamento). `NOW()` e `inicio_em` são os dois
        `timestamptz` — a subtração já é em UTC, sem conversão de fuso.
        """
        statement = text(
            """
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN s.duracao_segundos IS NOT NULL THEN s.duracao_segundos
                        ELSE GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (NOW() - s.inicio_em))))
                    END
                ), 0) AS segundos_totais,
                COUNT(*) AS sessoes_consideradas
            FROM sessoes_trabalho s
            WHERE s.empresa_id = :empresa_id
              AND (
                s.usuario_id IN (
                    SELECT id FROM usuarios
                    WHERE departamento_id = :departamento_id AND empresa_id = :empresa_id
                )
                OR s.departamento_id = :departamento_id
              )
            """
        )
        resultado = db.execute(
            statement, {"empresa_id": empresa_id, "departamento_id": departamento_id}
        ).one()
        horas_consumidas = float(resultado.segundos_totais) / 3600
        return horas_consumidas, int(resultado.sessoes_consideradas)

    def resumo_trafego(
        self, db: Session, *, empresa_id: str, periodo_inicio: datetime
    ) -> float:
        """D2-D3B — "Horas executadas" da Central de Tráfego, sobre o universo INTEGRAL da
        empresa (sem departamento/usuário) — nunca a listagem paginada de sessões (cap de
        100 no cliente). Técnica de duração igual a `horas_departamento` (acima), mas
        universo e filtro de período são DIFERENTES — não é uma chamada àquele método:

        - `cancelada` é excluída estruturalmente (`horas_departamento` não filtra status,
          `resumo_trafego` precisa);
        - `ativa` sempre entra, SEM filtro de período — reproduz `elapsedSeconds` do
          frontend (`NOW() - inicio_em` inteiro, nunca recortado por `periodo_inicio`);
        - `encerrada` só entra quando `inicio_em >= periodo_inicio` — mesmo campo/predicado
          de `SessaoTrabalhoRepository.list` (`data_inicio`), nunca `fim_em`/overlap. Uma
          sessão que começou antes do período e terminou depois **não conta nada** — não é
          recortada, é excluída por inteiro. Contraintuitivo, mas é a semântica já congelada
          do frontend (`listSessoesTrabalho({dataInicio: ...})`), preservada aqui de
          propósito, não corrigida.
        """
        statement = text(
            """
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN s.duracao_segundos IS NOT NULL THEN s.duracao_segundos
                        ELSE GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (NOW() - s.inicio_em))))
                    END
                ), 0) AS segundos_totais
            FROM sessoes_trabalho s
            WHERE s.empresa_id = :empresa_id
              AND (
                s.status = 'ativa'
                OR (s.status = 'encerrada' AND s.inicio_em >= :periodo_inicio)
              )
            """
        )
        resultado = db.execute(
            statement, {"empresa_id": empresa_id, "periodo_inicio": periodo_inicio}
        ).one()
        return float(resultado.segundos_totais) / 3600

    def indicadores_trafego(
        self,
        db: Session,
        *,
        empresa_id: str,
        periodo_inicio: datetime,
        status: str = "todos",
        usuario_ids: Sequence[str] | None = None,
        departamento_ids: Sequence[str] | None = None,
        demanda_query: str | None = None,
        avancados: FiltrosSessaoAvancados | None = None,
    ) -> dict[str, int]:
        """D2-D3C1 — métricas de `TrafegoResumoCards`/`TempoOperacionalCard`, UMA consulta
        agregada sobre o universo INTEGRAL (nunca a listagem paginada de 100). Reproduz, campo
        a campo, o que `TrafegoView` fazia no cliente com `listSessoesTrabalho` +
        `filterSessoes` + `buildResumo` (comparado antes de implementar):

        ## Universo (mesmo de `resumo_trafego`, D3B)
        - `ativa` entra SEMPRE, sem filtro de período (tempo decorrido real, não recortado);
        - `encerrada` entra se `inicio_em >= periodo_inicio` (campo `inicio_em`, nunca `fim_em`);
        - `cancelada` nunca entra.

        ## Status (semântica atual, preservada — NÃO simplificada)
        `status == "ativa"` → as encerradas deixam de ser buscadas. `"todos"` e `"encerrada"`
        → AMBAS entram: no cliente, as ativas eram buscadas sempre (`listSessoesTrabalho({status:
        "ativa"})` incondicional), então escolher "encerrada" nunca escondeu sessão ativa.

        ## Filtros de sessão (client-side antes, `filterSessoes`)
        - `usuario_ids`/`departamento_ids`: o campo DA SESSÃO está na lista (sessão sem usuário/
          departamento nunca casa quando o filtro está ativo); vazio/None = sem filtro;
        - `demanda_query`: a mesma string de busca do cliente — `"<demandaId> #<número> —
          <nome>"` (ou `"<demandaId> <demandaId>"` quando a Demanda não existe), comparada sem
          acento/caixa, SEM aparar a consulta (o cliente só usa `trim()` para decidir se há
          filtro, não para casar). Só aplicada se `demanda_query.strip()` não for vazio.

        ## Duração
        Encerrada: `duracao_segundos`. Ativa: `GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (NOW() -
        inicio_em))))` — mesma de `horas_departamento`/`resumo_trafego`. Média = arredondada
        (meio sobe, como `Math.round`) sobre sessões ativas + encerradas.

        Contagens distintas ignoram NULL por natureza (`COUNT(DISTINCT x)`) — o mesmo que o
        cliente fazia ao descartar `usuarioId`/`departamentoId` nulos.
        """
        incluir_encerradas = status != "ativa"
        clausulas = ["s.empresa_id = :empresa_id"]
        parametros: dict = {"empresa_id": empresa_id}

        if incluir_encerradas:
            clausulas.append("(s.status = 'ativa' OR (s.status = 'encerrada' AND s.inicio_em >= :periodo_inicio))")
            parametros["periodo_inicio"] = periodo_inicio
        else:
            clausulas.append("s.status = 'ativa'")

        juncao_demanda, clausulas_filtros, parametros_filtros = _filtros_sessao(
            usuario_ids, departamento_ids, demanda_query, avancados
        )
        clausulas.extend(clausulas_filtros)
        parametros.update(parametros_filtros)

        statement = text(
            f"""
            WITH base AS (
                SELECT
                    s.status,
                    s.demanda_id,
                    s.usuario_id,
                    s.departamento_id,
                    CASE
                        WHEN s.duracao_segundos IS NOT NULL THEN s.duracao_segundos
                        ELSE GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (NOW() - s.inicio_em))))
                    END AS duracao
                FROM sessoes_trabalho s
                {juncao_demanda}
                WHERE {" AND ".join(clausulas)}
            )
            SELECT
                COUNT(*) FILTER (WHERE status = 'ativa') AS sessoes_ativas,
                COUNT(*) FILTER (WHERE status = 'encerrada') AS sessoes_encerradas,
                COUNT(DISTINCT demanda_id) AS demandas_distintas,
                COUNT(DISTINCT usuario_id) AS usuarios_distintos,
                COUNT(DISTINCT departamento_id) AS departamentos_distintos,
                COALESCE(SUM(duracao), 0) AS tempo_total,
                COALESCE(MAX(duracao), 0) AS maior_sessao,
                COALESCE(MAX(duracao) FILTER (WHERE status = 'ativa'), 0) AS maior_sessao_ativa
            FROM base
            """
        )
        linha = db.execute(statement, parametros).one()

        total_sessoes = int(linha.sessoes_ativas) + int(linha.sessoes_encerradas)
        tempo_total = int(linha.tempo_total)
        return {
            "sessoes_ativas": int(linha.sessoes_ativas),
            "sessoes_encerradas": int(linha.sessoes_encerradas),
            "demandas_distintas": int(linha.demandas_distintas),
            "usuarios_distintos": int(linha.usuarios_distintos),
            "departamentos_distintos": int(linha.departamentos_distintos),
            "tempo_operacional_estimado_segundos": tempo_total,
            # `Math.round` do cliente: meio sobe (valores sempre ≥ 0 aqui) — em inteiros, sem float.
            "tempo_medio_sessao_segundos": (2 * tempo_total + total_sessoes) // (2 * total_sessoes)
            if total_sessoes
            else 0,
            "maior_sessao_segundos": int(linha.maior_sessao),
            "maior_sessao_ativa_segundos": int(linha.maior_sessao_ativa),
        }

    def carga_trafego(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_ids: Sequence[str] | None = None,
        departamento_ids: Sequence[str] | None = None,
        demanda_query: str | None = None,
        avancados: FiltrosSessaoAvancados | None = None,
    ) -> Mapping[str, Sequence[dict]]:
        """D2-D3C2 — "Carga por usuário/departamento/equipe" da Central de Tráfego: três
        agrupamentos agregados em SQL (3 consultas, NÃO proporcionais ao número de grupos) sobre
        TODAS as sessões ativas — nunca a lista de 100 que o cliente agrupava em
        `buildCarga`/`buildCargaEquipe` (comparado, campo a campo, antes de implementar).

        ## Universo (diferente de D3C1 — e igual ao que o cliente fazia)
        Só sessões `ativa`, SEM período e SEM `status` da tela: no cliente as ativas eram
        buscadas sempre (`listSessoesTrabalho({status: "ativa"})` incondicional) e os três
        rankings só olhavam `ativasFiltradas`. Por isso este agregado NÃO recebe `periodoInicio`
        nem `status` — trocá-los na tela nunca mudou a carga. Aplicam-se os mesmos filtros de
        sessão de D3C1 (`_filtros_sessao`): usuários, departamentos e busca de demanda.

        ## "Carga"
        `tempoAtivoTotalSegundos` = soma do tempo DECORRIDO das sessões ativas do grupo
        (`GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (NOW() - inicio_em))))`, mesma duração de
        `elapsedSeconds`); acompanha `sessoesAtivas` (contagem) e `demandasDistintas`
        (`COUNT(DISTINCT demanda_id)`). O rótulo Livre/Leve/Moderada/Alta e a barra relativa são
        derivados do valor no próprio cliente.

        ## Agrupamento
        - usuário: `usuario_id` DA SESSÃO (sessão sem usuário fica fora do ranking de usuários);
        - departamento: `departamento_id` DA SESSÃO (idem sem departamento) — NÃO o departamento
          do usuário;
        - equipe: não existe `equipe_id` na sessão. A equipe é inferida por `equipe_membros`
          (N:N — o usuário pode estar em várias equipes). O cliente atribuía a sessão à PRIMEIRA
          equipe, em ordem de `nome`, cuja lista de membros contém o usuário
          (`equipes.find(...)` sobre o diretório, que `ORDER BY nome ASC` e INCLUI arquivadas) —
          sessão conta para UMA equipe só, nunca duplica; usuário sem equipe fica fora. Replicado
          com `DISTINCT ON (usuario_id) ... ORDER BY e.nome, e.id`.

        ## Ordenação
        `tempoAtivoTotalSegundos` decrescente. Empate: ordem de primeira aparição na lista que o
        cliente recebia (`inicio_em DESC, created_at DESC`) — i.e. o grupo cuja sessão mais
        recente é mais nova vem antes; depois `id` para ser determinístico.

        Os nomes vêm da MESMA consulta (junção, sem N+1); sem linha correspondente cai no id,
        como o fallback do cliente.
        """
        juncao_demanda, clausulas_filtros, parametros_filtros = _filtros_sessao(
            usuario_ids, departamento_ids, demanda_query, avancados
        )
        clausulas = ["s.empresa_id = :empresa_id", "s.status = 'ativa'", *clausulas_filtros]
        parametros = {"empresa_id": empresa_id, **parametros_filtros}

        base = f"""
            WITH ativas AS (
                SELECT
                    s.usuario_id,
                    s.departamento_id,
                    s.demanda_id,
                    s.inicio_em,
                    s.created_at,
                    GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (NOW() - s.inicio_em)))) AS decorrido
                FROM sessoes_trabalho s
                {juncao_demanda}
                WHERE {" AND ".join(clausulas)}
            )
        """
        agregados = """
                COUNT(*) AS sessoes_ativas,
                COUNT(DISTINCT a.demanda_id) AS demandas_distintas,
                COALESCE(SUM(a.decorrido), 0) AS tempo_total,
                MAX(a.inicio_em) AS ultimo_inicio,
                (ARRAY_AGG(a.created_at ORDER BY a.inicio_em DESC, a.created_at DESC))[1] AS ultimo_created
        """
        ordem = "ORDER BY tempo_total DESC, ultimo_inicio DESC, ultimo_created DESC, id ASC"

        consultas = {
            "usuarios": f"""
                {base}
                SELECT a.usuario_id AS id, COALESCE(u.nome, a.usuario_id) AS nome, {agregados}
                FROM ativas a
                LEFT JOIN usuarios u ON u.id = a.usuario_id AND u.empresa_id = :empresa_id
                WHERE a.usuario_id IS NOT NULL
                GROUP BY a.usuario_id, u.nome
                {ordem}
            """,
            "departamentos": f"""
                {base}
                SELECT a.departamento_id AS id, COALESCE(dep.nome, a.departamento_id) AS nome, {agregados}
                FROM ativas a
                LEFT JOIN departamentos dep ON dep.id = a.departamento_id AND dep.empresa_id = :empresa_id
                WHERE a.departamento_id IS NOT NULL
                GROUP BY a.departamento_id, dep.nome
                {ordem}
            """,
            "equipes": f"""
                {base},
                primeira_equipe AS (
                    SELECT DISTINCT ON (em.usuario_id) em.usuario_id, e.id AS equipe_id, e.nome AS equipe_nome
                    FROM equipe_membros em
                    JOIN equipes e ON e.id = em.equipe_id AND e.empresa_id = :empresa_id
                    WHERE em.usuario_id IN (SELECT usuario_id FROM ativas WHERE usuario_id IS NOT NULL)
                    ORDER BY em.usuario_id, e.nome ASC, e.id ASC
                )
                SELECT pe.equipe_id AS id, pe.equipe_nome AS nome, {agregados}
                FROM ativas a
                JOIN primeira_equipe pe ON pe.usuario_id = a.usuario_id
                GROUP BY pe.equipe_id, pe.equipe_nome
                {ordem}
            """,
        }

        resultado: dict[str, list[dict]] = {}
        for chave, sql in consultas.items():
            linhas = db.execute(text(sql), parametros).all()
            resultado[chave] = [
                {
                    "id": linha.id,
                    "nome": linha.nome,
                    "sessoes_ativas": int(linha.sessoes_ativas),
                    "demandas_distintas": int(linha.demandas_distintas),
                    "tempo_ativo_total_segundos": int(linha.tempo_total),
                }
                for linha in linhas
            ]
        return resultado

    def agora_trafego(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_ids: Sequence[str] | None = None,
        departamento_ids: Sequence[str] | None = None,
        demanda_query: str | None = None,
        avancados: FiltrosSessaoAvancados | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Mapping[str, object]:
        """D2-D3C3 — "Quem está trabalhando agora" (`TrafegoAgoraTable`): sessões ATIVAS
        paginadas no servidor, com usuário/departamento/Demanda JÁ resolvidos na mesma consulta —
        nunca a lista de 100 do cliente nem os diretórios globais (o de usuários cortado em 200).
        2 consultas (página + total), sempre, independente de quantas sessões existam.

        ## Universo e filtros (comparados, campo a campo, com `TrafegoView`/`filterSessoes`)
        - só `ativa` (a tela buscava `listSessoesTrabalho({status: "ativa"})`): encerrada e
          cancelada nunca aparecem;
        - SEM período e SEM `status` da tela — nunca afetaram esta tabela (mesma conclusão de D3C2);
        - `usuario_ids`/`departamento_ids`/`demanda_query`: os MESMOS de D3C1/D3C2
          (`_filtros_sessao`, regra única, sem terceira versão).

        ## Ordem
        A tabela ordenava por tempo decorrido DECRESCENTE (`elapsedSeconds`, "maior tempo em
        execução primeiro"). Tempo decorrido decrescente ≡ `inicio_em` CRESCENTE — chave que não
        depende do relógio, então a paginação por offset é estável (ordenar por `FLOOR(NOW() −
        inicio_em)` faria sessões de início sub-segundo mudarem de lado entre duas páginas).
        Desempate: `created_at DESC` (a ordem em que a API entregava ao cliente, preservada pelo
        sort estável) e depois `id`, para ser determinístico.

        ## Resolução de nomes (LEFT JOIN, mesma empresa)
        `usuario_nome`/`departamento_nome` são `None` só quando a sessão não tem o vínculo (FK
        `ON DELETE SET NULL` garante que, se `usuario_id` existe, a linha existe) — o cliente
        mostrava "Sem usuário"/"Sem departamento". Demanda inexistente → `demanda_numero`/
        `demanda_nome` `None` (o cliente caía no `demandaId`); arquivada continua resolvida.
        `decorrido_segundos`: mesmo cálculo de `elapsedSeconds` (`GREATEST(0, FLOOR(...))`),
        "as of" `NOW()` — o frontend o faz andar sem novo fetch.
        """
        _, clausulas_filtros, parametros_filtros = _filtros_sessao(usuario_ids, departamento_ids, demanda_query, avancados)
        clausulas = ["s.empresa_id = :empresa_id", "s.status = 'ativa'", *clausulas_filtros]
        parametros = {"empresa_id": empresa_id, **parametros_filtros}

        # A Demanda é SEMPRE unida aqui (nome na linha); `_filtros_sessao` referencia o mesmo alias
        # `d` na busca de demanda, com a mesma condição de junção — por isso ignoramos a junção
        # que ele devolve (evita juntar duas vezes).
        juncoes = """
            LEFT JOIN demandas d ON d.id = s.demanda_id AND d.empresa_id = s.empresa_id
            LEFT JOIN usuarios u ON u.id = s.usuario_id AND u.empresa_id = s.empresa_id
            LEFT JOIN departamentos dep ON dep.id = s.departamento_id AND dep.empresa_id = s.empresa_id
        """
        onde = " AND ".join(clausulas)

        total = db.execute(
            text(f"SELECT COUNT(*) FROM sessoes_trabalho s {juncoes} WHERE {onde}"), parametros
        ).scalar_one()

        linhas = db.execute(
            text(
                f"""
                SELECT
                    s.id AS sessao_id,
                    s.inicio_em,
                    GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (NOW() - s.inicio_em)))) AS decorrido,
                    s.demanda_id,
                    d.numero_operacional AS demanda_numero,
                    d.identificador AS demanda_identificador,
                    d.nome AS demanda_nome,
                    s.usuario_id,
                    u.nome AS usuario_nome,
                    s.departamento_id,
                    dep.nome AS departamento_nome
                FROM sessoes_trabalho s
                {juncoes}
                WHERE {onde}
                ORDER BY s.inicio_em ASC, s.created_at DESC, s.id ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            {**parametros, "limit": limit, "offset": offset},
        ).all()

        return {
            "items": [
                {
                    "sessao_id": linha.sessao_id,
                    "inicio_em": linha.inicio_em,
                    "decorrido_segundos": int(linha.decorrido),
                    "demanda_id": linha.demanda_id,
                    "demanda_numero": linha.demanda_numero,
                    "demanda_identificador": linha.demanda_identificador,
                    "demanda_nome": linha.demanda_nome,
                    "usuario_id": linha.usuario_id,
                    "usuario_nome": linha.usuario_nome,
                    "departamento_id": linha.departamento_id,
                    "departamento_nome": linha.departamento_nome,
                }
                for linha in linhas
            ],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }
