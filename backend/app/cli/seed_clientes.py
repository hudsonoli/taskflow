"""Popula os clientes iniciais no banco.

Cliente é entidade real desde a Fase 2B. Os mocks do frontend que serviam de base foram
removidos; a fonte única passou a ser `app/cli/data/clientes_seed.json`, aqui no backend.

## codigoInterno

Preserva o valor que o mock já usava (`#1001`, `#2001`) — de propósito, porque Projeto e
Demanda continuam mock nesta fase e referenciam clientes por ele. O `codigoReferencia`
(C26000001) é emitido pela infraestrutura central, nunca derivado do mock.

## Resolução de referências — nunca por UUID, nunca por nome

O JSON de seed não carrega UUID: os IDs técnicos mudam a cada ambiente, e o objetivo é que
`alembic upgrade head` + seeds reconstruam um banco vazio inteiro. Então:

- Grupo de Cliente é resolvido por `codigoInterno` (`grupo-grupo-bretas`);
- responsável comercial é resolvido pelo `codigoInterno` do usuário (`usuario-4`).

Referência que não resolve **aborta o seed** — nunca cria vínculo silenciosamente errado.

## Idempotência ANTES de consumir sequência

Para cada item, busca por (empresa, codigoInterno) e, se já existir, ignora sem chamar
`gerar_proxima_referencia` — rodar duas vezes não duplica, não altera código de referência
e não avança o contador.

Uso: python -m app.cli.seed_clientes
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.grupo_cliente_repository import GrupoClienteRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.cliente import ClienteCreate
from app.services.cliente_service import ClienteService
from app.services.empresa_service import EmpresaService

DATA_FILE = Path(__file__).parent / "data" / "clientes_seed.json"


def seed_clientes(output=print) -> None:
    settings = get_settings()
    factory = get_session_factory()

    empresa_service = EmpresaService()
    cliente_service = ClienteService()
    cliente_repository = ClienteRepository()
    grupo_repository = GrupoClienteRepository()
    usuario_repository = UsuarioRepository()

    registros = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    with factory() as db:
        empresa = empresa_service.repository.get_by_codigo_interno(db, settings.empresa_codigo)
        if empresa is None:
            raise RuntimeError(
                f"Empresa '{settings.empresa_codigo}' não encontrada. "
                "Rode os seeds de empresa/usuários antes deste."
            )

        # Índices por codigoInterno, montados uma vez. Grupos arquivados entram no índice de
        # propósito: o vínculo histórico é legítimo, quem recusa vínculo novo é o service.
        grupos_por_codigo = {
            grupo.codigo_interno: grupo.id
            for grupo in grupo_repository.list_diretorio(db, empresa_id=empresa.id)
        }
        usuarios_por_codigo = {
            usuario.codigo_interno: usuario.id
            for usuario in usuario_repository.list_diretorio(db, empresa_id=empresa.id, limit=1000)
        }

        criados = 0
        ignorados = 0

        for item in registros:
            codigo_interno = item["codigoInterno"]

            # Idempotência ANTES da sequência: se já existe, não queima número.
            if cliente_repository.get_by_codigo_interno(
                db, empresa_id=empresa.id, codigo_interno=codigo_interno
            ):
                ignorados += 1
                continue

            grupo_ids = []
            for codigo_grupo in item.get("gruposCliente") or []:
                grupo_id = grupos_por_codigo.get(codigo_grupo)
                if grupo_id is None:
                    raise RuntimeError(
                        f"Cliente '{codigo_interno}': grupo '{codigo_grupo}' não encontrado. "
                        "Rode o seed de grupos de cliente antes deste."
                    )
                grupo_ids.append(grupo_id)

            responsavel_id = None
            codigo_responsavel = item.get("responsavelComercialCodigoInterno")
            if codigo_responsavel:
                responsavel_id = usuarios_por_codigo.get(codigo_responsavel)
                if responsavel_id is None:
                    raise RuntimeError(
                        f"Cliente '{codigo_interno}': responsável comercial "
                        f"'{codigo_responsavel}' não encontrado. Rode o seed de usuários antes deste."
                    )

            data = ClienteCreate.model_validate(
                {
                    "nome": item["nome"],
                    "tipoDocumento": item["tipoDocumento"],
                    "corIdentificacao": item.get("corIdentificacao") or "blue",
                    "razaoSocial": item.get("razaoSocial"),
                    "documento": item.get("documento"),
                    "email": item.get("email"),
                    "whatsapp": item.get("whatsapp"),
                    "cep": item.get("cep"),
                    "bairro": item.get("bairro"),
                    "enderecoCompleto": item.get("enderecoCompleto"),
                    "cidade": item.get("cidade"),
                    "uf": item.get("uf"),
                    "segmento": item.get("segmento"),
                    "origem": item.get("origem"),
                    "responsavelComercialId": responsavel_id,
                    "clienteReferencial": bool(item.get("clienteReferencial")),
                    "avisarConclusaoPorEmail": bool(item.get("avisarConclusaoPorEmail")),
                    "feeMensalCentavos": item.get("feeMensalCentavos"),
                    "horasContratadasMes": item.get("horasContratadasMes"),
                    "observacoes": item.get("observacoes"),
                    "contatos": item.get("contatos") or [],
                    "grupoClienteIds": grupo_ids,
                }
            )

            cliente = cliente_service.create_cliente_com_codigo_legado(
                db, data, empresa_id=empresa.id, codigo_interno=codigo_interno
            )

            # O JSON traz status que a criação não aceita (suspenso/inativo): a criação é
            # sempre "ativo" e o estado real é aplicado logo depois, pelo caminho normal de
            # alteração — sem escrita direta no model.
            status_desejado = item.get("status") or "ativo"
            if status_desejado != cliente.status:
                from app.schemas.cliente import ClienteUpdate

                cliente_service.update_cliente(
                    db, cliente.id, ClienteUpdate.model_validate({"status": status_desejado})
                )

            criados += 1

        output(f"Clientes criados: {criados}")
        output(f"Clientes já existentes (ignorados): {ignorados}")


if __name__ == "__main__":  # pragma: no cover
    seed_clientes()
