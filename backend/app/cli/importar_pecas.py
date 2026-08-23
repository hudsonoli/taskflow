"""Importa o catálogo real de Peças pro banco (Fase 2G.4).

Peça é entidade real desde esta fase — o mock do frontend (`pecas-mock.ts`) é removido no
fechamento. Este import carrega o catálogo original, que veio de uma planilha externa.

Fonte de dados: cópia estática em app/cli/data/pecas_seed.json (419 itens; o backend nunca lê
nada de dentro de frontend/) — mesmo arquivo que era `frontend/src/lib/pecas-import.json`.
Contém só os itens reais importados, NÃO os 9 exemplos de demonstração que existiam em
`pecasDemo` (fabricados só pra UI mock ter categoria preenchida, sem identidade legada real —
decisão da Fase 2G.4).

## Identidade idempotente

Cada item tem um `id` original estável (`peca-imp-001` .. `peca-imp-431`, sequencial, 419
únicos) — vira `codigo_legado` na tabela `pecas`, com `UNIQUE(empresa_id, codigo_legado)`.
A idempotência é por **empresa + código legado, nunca por nome**: o catálogo tem nomes que se
repetem legitimamente (variação histórica de nomenclatura) e nome nunca poderia distinguir com
segurança "já importei este" de "outro item com nome parecido".

## Remapeamento de tempo (regra já consolidada pelo mock, replicada aqui)

O campo `tempoEstimadoMinutos` da planilha original **na verdade contém a média de execução**,
apesar do nome — não uma estimativa (é assim que `pecas-mock.ts::migrarPecaImportada` já
tratava). Aqui:

    raw.tempoEstimadoMinutos → tempo_medio_minutos
    tempo_estimado_minutos  → sempre NULL (fica livre pra preenchimento manual futuro)

`sindicato_ativo` é derivado: `true` quando qualquer um dos 3 valores de sindicato da planilha
é > 0. Valores monetários são copiados como vieram — já em centavos inteiros, sem conversão.

## Categoria

O catálogo importado não traz nenhuma categoria (`"categoria": ""` em 100% dos itens) — cada
Peça importada nasce com `categoria_id = NULL`, pra classificação manual posterior via a API
real. Nenhuma categoria é inventada/semeada a partir daqui.

Uso: python -m app.cli.importar_pecas
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.empresa_service import EmpresaService
from app.services.peca_service import PecaService

DATA_FILE = Path(__file__).parent / "data" / "pecas_seed.json"


def _tem_valor_sindicato(item: dict) -> bool:
    return (
        (item.get("valorSindicatoCriacaoCentavos") or 0) > 0
        or (item.get("valorSindicatoAdaptacaoCentavos") or 0) > 0
        or (item.get("valorSindicatoFinalizacaoCentavos") or 0) > 0
    )


def importar_pecas(output=print) -> None:
    settings = get_settings()
    factory = get_session_factory()
    empresa_service = EmpresaService()
    peca_service = PecaService()

    itens = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    criadas: list[str] = []
    ignoradas: list[str] = []

    with factory() as db:
        empresa = empresa_service.repository.get_by_codigo_interno(db, settings.empresa_codigo)
        if empresa is None:
            raise RuntimeError(
                f"Empresa '{settings.empresa_codigo}' não encontrada — rode app.cli.seed_bootstrap primeiro"
            )

        for item in itens:
            codigo_legado = item["id"]

            # Idempotência ANTES de criar — mesmo espírito de seed_tipos_tarefa/seed_departamentos.
            existente = peca_service.get_by_codigo_legado(
                db, empresa_id=empresa.id, codigo_legado=codigo_legado
            )
            if existente is not None:
                ignoradas.append(f"{codigo_legado} — {item['nome']}")
                continue

            criada = peca_service.criar_peca_importada(
                db,
                empresa_id=empresa.id,
                codigo_legado=codigo_legado,
                nome=item["nome"],
                # Remapeamento de tempo — ver docstring do módulo.
                tempo_estimado_minutos=None,
                tempo_medio_minutos=item.get("tempoEstimadoMinutos"),
                valor_tabela_centavos=item.get("valorTabelaCentavos"),
                sindicato_ativo=_tem_valor_sindicato(item),
                valor_sindicato_criacao_centavos=item.get("valorSindicatoCriacaoCentavos"),
                valor_sindicato_adaptacao_centavos=item.get("valorSindicatoAdaptacaoCentavos"),
                valor_sindicato_finalizacao_centavos=item.get("valorSindicatoFinalizacaoCentavos"),
                briefing_padrao=item.get("briefingPadrao") or "",
            )
            criadas.append(f"{codigo_legado} — {criada.nome}")

    output(f"Peças — criadas: {len(criadas)} | já existiam (ignoradas): {len(ignoradas)}")


if __name__ == "__main__":
    importar_pecas()
