"""Migra os grupos de cliente hoje mockados no frontend
(frontend/src/lib/grupos-cliente-mock.ts, derivados dos nomes de tag únicos em
frontend/src/lib/clientes-import.json) pro banco real.

`codigoInterno` de cada grupo é o mesmo `id` que o mock já usava (ex.
"grupo-grupo-bretas") — de propósito, pra que `Cliente.tagIds` (que continua mock nesta
entrega) siga resolvendo esses grupos sem precisar de nenhuma mudança em
clientes-mock.ts/clientes-import.json (ver GrupoClienteService.create_grupo_cliente_com_codigo_legado).

Fonte de dados: cópia estática em app/cli/data/grupos_cliente_seed.json (o backend nunca lê
nada de dentro de frontend/).

Uso: python -m app.cli.seed_grupos_cliente
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.empresa_service import EmpresaService
from app.services.grupo_cliente_service import GrupoClienteService

DATA_FILE = Path(__file__).parent / "data" / "grupos_cliente_seed.json"


def seed_grupos_cliente(output=print) -> None:
    settings = get_settings()
    factory = get_session_factory()
    empresa_service = EmpresaService()
    grupo_cliente_service = GrupoClienteService()

    itens = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    with factory() as db:
        empresa = empresa_service.repository.get_by_codigo_interno(db, settings.empresa_codigo)
        if empresa is None:
            raise RuntimeError(
                f"Empresa '{settings.empresa_codigo}' não encontrada — rode app.cli.seed_usuarios primeiro"
            )

        criados = 0
        pulados = 0
        for item in itens:
            ja_existia = (
                grupo_cliente_service.repository.get_by_codigo_interno(
                    db, empresa_id=empresa.id, codigo_interno=item["codigoInterno"]
                )
                is not None
            )
            grupo_cliente_service.create_grupo_cliente_com_codigo_legado(
                db,
                nome=item["nome"],
                cor_identificacao=item["corIdentificacao"],
                empresa_id=empresa.id,
                codigo_interno=item["codigoInterno"],
                actor_usuario_id=None,
            )
            criados += 0 if ja_existia else 1
            pulados += 1 if ja_existia else 0

        output(f"Grupos de cliente criados: {criados} | já existiam (pulados): {pulados}")


if __name__ == "__main__":
    seed_grupos_cliente()
