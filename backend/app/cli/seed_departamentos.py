"""Popula os departamentos iniciais no banco.

Departamento é entidade real desde a Fase 2A — o mock do frontend
(`lib/departamentos-mock.ts`) foi removido no fechamento daquela fase. Este seed carrega o
elenco original, que veio de lá.

`codigoInterno` preserva o `id` que o mock usava (`dep-criacao`) — de propósito, porque
Projeto, Demanda e SLA continuam mock nesta fase e referenciam esses valores. O
`codigoReferencia` (D26000001) é emitido pela infraestrutura central, nunca derivado do
mock.

**Idempotência antes de consumir sequência**: para cada item, busca por
(empresa, codigoInterno) e, se já existir, ignora sem chamar `gerar_proxima_referencia` —
rodar duas vezes não duplica, não altera código e não avança o contador.

Uso: python -m app.cli.seed_departamentos
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.departamento_service import DepartamentoService
from app.services.empresa_service import EmpresaService

DATA_FILE = Path(__file__).parent / "data" / "departamentos_seed.json"


def seed_departamentos(output=print) -> None:
    settings = get_settings()
    factory = get_session_factory()
    empresa_service = EmpresaService()
    departamento_service = DepartamentoService()

    itens = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    criados: list[str] = []
    ignorados: list[str] = []
    invalidos: list[str] = []
    conflitos: list[str] = []

    with factory() as db:
        empresa = empresa_service.repository.get_by_codigo_interno(db, settings.empresa_codigo)
        if empresa is None:
            raise RuntimeError(
                f"Empresa '{settings.empresa_codigo}' não encontrada — rode app.cli.seed_usuarios primeiro"
            )

        for item in itens:
            codigo_interno = item.get("codigoInterno")
            nome = item.get("nome")
            cor = item.get("corIdentificacao")
            if not codigo_interno or not nome or not cor:
                invalidos.append(str(item))
                continue

            # Idempotência ANTES de qualquer emissão de código.
            existente = departamento_service.repository.get_by_codigo_interno(
                db, empresa_id=empresa.id, codigo_interno=codigo_interno
            )
            if existente is not None:
                ignorados.append(f"{codigo_interno} ({existente.codigo_referencia})")
                continue

            try:
                criado = departamento_service.create_departamento_com_codigo_legado(
                    db,
                    nome=nome,
                    cor_identificacao=cor,
                    descricao=item.get("descricao"),
                    empresa_id=empresa.id,
                    codigo_interno=codigo_interno,
                )
                criados.append(f"{codigo_interno} -> {criado.codigo_referencia}")
            except Exception as exc:  # nome já usado por outro codigoInterno, por exemplo
                conflitos.append(f"{codigo_interno}: {exc}")

    output(f"Departamentos — criados: {len(criados)} | ignorados: {len(ignorados)} | "
           f"inválidos: {len(invalidos)} | conflitos: {len(conflitos)}")
    for linha in criados:
        output(f"  criado    {linha}")
    for linha in ignorados:
        output(f"  ignorado  {linha}")
    for linha in invalidos:
        output(f"  invalido  {linha}")
    for linha in conflitos:
        output(f"  conflito  {linha}")


if __name__ == "__main__":
    seed_departamentos()
