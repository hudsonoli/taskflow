"""Popula as equipes iniciais no banco.

Equipe é entidade real desde a Fase 2A — o mock do frontend (`lib/equipes-mock.ts`) foi
removido no fechamento daquela fase. Este seed carrega o elenco original, que veio de lá.

`codigoInterno` preserva o `id` do mock (`equipe-1`). Departamento, líder e membros são
resolvidos a partir dos respectivos `codigoInterno` legados (`dep-criacao`, `usuario-3`) —
o JSON de seed nunca carrega UUID, porque os IDs técnicos mudam a cada ambiente.

**Idempotência antes de consumir sequência**: busca por (empresa, codigoInterno) e, se já
existir, ignora sem chamar `gerar_proxima_referencia`.

## Depende de seed_departamentos e seed_usuarios

Toda referência não resolvida **aborta** (`ReferenciaDeEquipeNaoResolvidaError`), antes de
gravar qualquer coisa. Até então o seed pulava a equipe inválida, imprimia "invalida" no
fim e saía com sucesso — e membro não resolvido era simplesmente filtrado da lista, criando
a equipe com menos gente do que o dado de origem manda. Mesma classe de falha silenciosa
que existia em `seed_usuarios`: banco válido, conteúdo errado.

Uso: `python -m app.cli.seed_all` (recomendado, garante a ordem) ou
`python -m app.cli.seed_equipes` isoladamente, com departamentos e usuários já semeados.
Ver docs/reconstrucao-banco.md.
"""

import json
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.usuario import Usuario
from app.services.departamento_service import DepartamentoService
from app.services.empresa_service import EmpresaService
from app.services.equipe_service import EquipeService

DATA_FILE = Path(__file__).parent / "data" / "equipes_seed.json"


class ReferenciaDeEquipeNaoResolvidaError(RuntimeError):
    """Departamento, líder ou membro citado pelo seed não existe no cadastro.

    Levantado **antes de gravar qualquer coisa**, com a lista completa — não no primeiro
    problema, para não obrigar a rodar de novo a cada correção.

    Nunca criar a referência automaticamente nem seguir sem ela: uma equipe com dois
    membros em vez de quatro é pior que nenhuma equipe, porque parece certa.
    """


def seed_equipes(output=print) -> None:
    settings = get_settings()
    factory = get_session_factory()
    empresa_service = EmpresaService()
    departamento_service = DepartamentoService()
    equipe_service = EquipeService()

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

        def resolver_usuario(codigo_interno: str) -> str | None:
            statement = select(Usuario).where(
                Usuario.empresa_id == empresa.id, Usuario.codigo_interno == codigo_interno
            )
            usuario = db.scalars(statement).first()
            return usuario.id if usuario else None

        # --- checagem prévia de TODAS as referências, antes de qualquer escrita -------
        nao_resolvidas: list[str] = []
        for item in itens:
            codigo_interno = item.get("codigoInterno") or "<sem codigoInterno>"
            # Já existente é ignorado adiante; não faz sentido cobrar referências dele.
            if item.get("codigoInterno") and equipe_service.repository.get_by_codigo_interno(
                db, empresa_id=empresa.id, codigo_interno=item["codigoInterno"]
            ):
                continue

            codigo_departamento = item.get("departamentoCodigoInterno")
            if codigo_departamento and departamento_service.repository.get_by_codigo_interno(
                db, empresa_id=empresa.id, codigo_interno=codigo_departamento
            ) is None:
                nao_resolvidas.append(
                    f"{codigo_interno}: departamento '{codigo_departamento}' não encontrado"
                )

            codigo_lider = item.get("liderCodigoInterno")
            if codigo_lider and resolver_usuario(codigo_lider) is None:
                nao_resolvidas.append(f"{codigo_interno}: líder '{codigo_lider}' não encontrado")

            for codigo_membro in item.get("membrosCodigoInterno", []):
                if resolver_usuario(codigo_membro) is None:
                    nao_resolvidas.append(
                        f"{codigo_interno}: membro '{codigo_membro}' não encontrado"
                    )

        if nao_resolvidas:
            raise ReferenciaDeEquipeNaoResolvidaError(
                f"Não é possível semear equipes: {len(nao_resolvidas)} referência(s) não "
                "resolvem.\n  " + "\n  ".join(nao_resolvidas)
                + "\n\nRode `python -m app.cli.seed_departamentos` e "
                "`python -m app.cli.seed_usuarios` antes — ou use o orquestrador oficial "
                "`python -m app.cli.seed_all`, que garante a ordem. "
                "Ver docs/reconstrucao-banco.md."
            )

        for item in itens:
            codigo_interno = item.get("codigoInterno")
            nome = item.get("nome")
            cor = item.get("corIdentificacao")
            if not codigo_interno or not nome or not cor:
                invalidos.append(str(item))
                continue

            # Idempotência ANTES de emitir código.
            existente = equipe_service.repository.get_by_codigo_interno(
                db, empresa_id=empresa.id, codigo_interno=codigo_interno
            )
            if existente is not None:
                ignorados.append(f"{codigo_interno} ({existente.codigo_referencia})")
                continue

            departamento_id = None
            codigo_departamento = item.get("departamentoCodigoInterno")
            if codigo_departamento:
                departamento = departamento_service.repository.get_by_codigo_interno(
                    db, empresa_id=empresa.id, codigo_interno=codigo_departamento
                )
                if departamento is None:
                    invalidos.append(f"{codigo_interno}: departamento '{codigo_departamento}' não encontrado")
                    continue
                departamento_id = departamento.id

            lider_id = resolver_usuario(item["liderCodigoInterno"]) if item.get("liderCodigoInterno") else None
            membro_ids = [
                resolvido
                for codigo in item.get("membrosCodigoInterno", [])
                if (resolvido := resolver_usuario(codigo)) is not None
            ]

            try:
                criada = equipe_service.create_equipe_com_codigo_legado(
                    db,
                    nome=nome,
                    cor_identificacao=cor,
                    descricao=item.get("descricao"),
                    empresa_id=empresa.id,
                    codigo_interno=codigo_interno,
                    departamento_id=departamento_id,
                    lider_usuario_id=lider_id,
                    membro_ids=membro_ids,
                )
                criados.append(f"{codigo_interno} -> {criada.codigo_referencia} ({len(membro_ids)} membro(s))")
            except Exception as exc:
                conflitos.append(f"{codigo_interno}: {exc}")

    output(
        f"Equipes — criadas: {len(criados)} | ignoradas: {len(ignorados)} | "
        f"inválidas: {len(invalidos)} | conflitos: {len(conflitos)}"
    )
    for linha in criados:
        output(f"  criada    {linha}")
    for linha in ignorados:
        output(f"  ignorada  {linha}")
    for linha in invalidos:
        output(f"  invalida  {linha}")
    for linha in conflitos:
        output(f"  conflito  {linha}")


if __name__ == "__main__":
    seed_equipes()
