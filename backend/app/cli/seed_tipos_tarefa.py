"""Popula os Tipos de Tarefa iniciais no banco.

Tipo de Tarefa é entidade real desde a Fase 2G.2 — o mock do frontend
(`tiposTarefaProjetoDisponiveis` em `lib/projeto-modelo-campanha-mock.ts`) é removido no
fechamento daquela fase. Este seed carrega o elenco original, que veio de lá.

Diferente de Departamento/GrupoCliente, Tipo de Tarefa não tem `codigo_interno` nem
`codigo_referencia` (não é documento pesquisável, sem importação legada prevista — ver
docstring de app/models/tipo_tarefa.py) e nenhum outro domínio ainda referencia os ids
antigos do mock (`tipo-post` etc.) por string: o consumidor (Modelo de Campanha de Projeto)
passa a usar o UUID real vindo do diretório. Por isso a idempotência aqui é por
`nome_normalizado`, não por código legado.

Fonte de dados: cópia estática em app/cli/data/tipos_tarefa_seed.json (o backend nunca lê
nada de dentro de frontend/).

Deliberadamente NÃO registrado em `seed_all.py`: aquele orquestrador tem contrato travado por
teste (`test_seed_all.py::test_ordem_oficial_e_a_declarada` e as contagens finais exatas em
`test_seed_all_reconstroi_a_base_inteira`), e Tipo de Tarefa não tem nenhuma dependência real
de outro seed nem é dependência de nenhum — encaixá-lo ali exigiria reabrir esse contrato sem
necessidade. Roda isolado, na Empresa que já existir.

Uso: python -m app.cli.seed_tipos_tarefa
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.schemas.tipo_tarefa import TipoTarefaCreate
from app.services.empresa_service import EmpresaService
from app.services.tipo_tarefa_service import TipoTarefaService

DATA_FILE = Path(__file__).parent / "data" / "tipos_tarefa_seed.json"


def _normalizar_nome(nome: str) -> str:
    # Mesma regra de TipoTarefaService._normalizar_nome — duplicada aqui de propósito, como
    # em todo par service/seed deste projeto (ex.: DepartamentoService).
    return nome.strip().lower()


def seed_tipos_tarefa(output=print) -> None:
    settings = get_settings()
    factory = get_session_factory()
    empresa_service = EmpresaService()
    tipo_tarefa_service = TipoTarefaService()

    itens = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    criados: list[str] = []
    ignorados: list[str] = []

    with factory() as db:
        empresa = empresa_service.repository.get_by_codigo_interno(db, settings.empresa_codigo)
        if empresa is None:
            raise RuntimeError(
                f"Empresa '{settings.empresa_codigo}' não encontrada — rode app.cli.seed_bootstrap primeiro"
            )

        for ordem, item in enumerate(itens):
            nome = item["nome"]
            nome_normalizado = _normalizar_nome(nome)

            # Idempotência ANTES de criar — mesmo espírito de seed_departamentos, ainda que
            # aqui não exista sequência a proteger (Tipo de Tarefa não emite código próprio).
            existente = tipo_tarefa_service.repository.get_by_nome_normalizado(
                db, empresa_id=empresa.id, nome_normalizado=nome_normalizado
            )
            if existente is not None:
                ignorados.append(nome)
                continue

            criado = tipo_tarefa_service.create_tipo_tarefa(
                db,
                TipoTarefaCreate(nome=nome, ordem=ordem),
                empresa_id=empresa.id,
                actor_usuario_id=None,
            )
            criados.append(criado.nome)

    output(f"Tipos de Tarefa — criados: {len(criados)} | já existiam (ignorados): {len(ignorados)}")
    for nome in criados:
        output(f"  criado    {nome}")
    for nome in ignorados:
        output(f"  ignorado  {nome}")


if __name__ == "__main__":
    seed_tipos_tarefa()
