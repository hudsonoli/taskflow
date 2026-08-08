"""Popula os fornecedores iniciais no banco.

Fornecedor é entidade real desde a Fase 2C. O mock do frontend que servia de base foi
removido; a fonte única passou a ser `app/cli/data/fornecedores_seed.json`, aqui no backend.

## codigoInterno

Preserva o valor que o mock já usava (`fornecedor-1`, `fornecedor-imp-001`). Diferente de
Cliente, **nenhum domínio referencia fornecedor** — não existe `fornecedorId` em Demanda,
Projeto ou SLA. Ele existe por um motivo só: ser a chave estável de idempotência deste seed,
já que o UUID muda a cada ambiente. O `codigoReferencia` (F26000001) é emitido pela
infraestrutura central, nunca derivado do mock.

## Idempotência ANTES de consumir sequência

Para cada item, busca por (empresa, codigoInterno) e, se já existir, ignora sem chamar
`gerar_proxima_referencia` — rodar duas vezes não duplica, não altera código de referência e
não avança o contador.

## Duplicidade não interrompe o seed

Nome e documento repetidos são cadastros legítimos em entidade externa (ver
docs/padrao-entidades-externas.md) e não têm UNIQUE. O seed não consulta duplicidade: ela é
um aviso de interface, não uma regra de importação.

Uso: python -m app.cli.seed_fornecedores
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.repositories.fornecedor_repository import FornecedorRepository
from app.schemas.fornecedor import FornecedorCreate
from app.services.empresa_service import EmpresaService
from app.services.fornecedor_service import FornecedorService

DATA_FILE = Path(__file__).parent / "data" / "fornecedores_seed.json"


def seed_fornecedores(output=print) -> None:
    settings = get_settings()
    factory = get_session_factory()

    empresa_service = EmpresaService()
    fornecedor_service = FornecedorService()
    fornecedor_repository = FornecedorRepository()

    with factory() as db:
        empresa = empresa_service.repository.get_by_codigo_interno(db, settings.empresa_codigo)
        if empresa is None:
            raise RuntimeError(
                f"Empresa '{settings.empresa_codigo}' não encontrada. "
                "Rode `python -m app.cli.seed_bootstrap` antes."
            )

        itens = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        criados = 0
        ignorados = 0

        for item in itens:
            codigo_interno = item["codigoInterno"]

            # Checagem ANTES de gerar referência: rodar de novo não queima números.
            if fornecedor_repository.get_by_codigo_interno(
                db, empresa_id=empresa.id, codigo_interno=codigo_interno
            ):
                ignorados += 1
                continue

            data = FornecedorCreate.model_validate(
                {campo: valor for campo, valor in item.items() if campo != "codigoInterno"}
            )

            criado = fornecedor_service.create_fornecedor_com_codigo_legado(
                db, data, empresa_id=empresa.id, codigo_interno=codigo_interno
            )
            criados += 1
            output(f"Fornecedor criado: {criado.codigo_referencia} — {criado.nome}")

        output("")
        output(f"Fornecedores criados: {criados}")
        output(f"Fornecedores já existentes (ignorados): {ignorados}")


if __name__ == "__main__":
    seed_fornecedores()
