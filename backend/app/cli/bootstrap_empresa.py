import argparse
from collections.abc import Callable

from sqlalchemy.orm import sessionmaker

from app.db.session import get_session_factory
from app.domain.validators import validar_cnpj
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.empresa import EmpresaCreate
from app.services.empresa_service import EmpresaConflictError, EmpresaService

# Nome fantasia ("nome") e razão social ("razao_social") são campos
# distintos desde a migration 20260721_1a19 — antes dela, Empresa só tinha
# "nome" (ver histórico na Fase 9B). razao_social é opcional no schema
# (EmpresaCreate/EmpresaUpdate), porque empresas já existentes como
# EMP-TESTCLIENT não têm uma; este bootstrap exige preenchimento porque é
# o cadastro oficial da empresa piloto, não porque o schema obriga.


class BootstrapEmpresaExistsError(ValueError):
    pass


class BootstrapInputError(ValueError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Cria a primeira empresa (tenant) do sistema. Idempotente: "
            "recusa-se a rodar se já existir qualquer empresa cadastrada — "
            "este comando é só para o bootstrap inicial de um banco vazio, "
            "não para cadastro contínuo de empresas adicionais. nome, razão "
            "social e cnpj são solicitados interativamente quando omitidos; "
            "passe todos os parâmetros para uso não interativo (automação)."
        )
    )
    parser.add_argument(
        "--nome",
        default=None,
        help="Nome da empresa. Solicitado interativamente se omitido.",
    )
    parser.add_argument(
        "--razao-social",
        default=None,
        help="Razão social da empresa. Solicitada interativamente se omitida.",
    )
    parser.add_argument(
        "--cnpj",
        default=None,
        help="CNPJ da empresa (com ou sem pontuação). Solicitado interativamente se omitido.",
    )
    parser.add_argument(
        "--codigo-interno",
        required=True,
        help="Código interno da empresa (único no sistema).",
    )
    return parser


def _resolve_value(value: str | None, label: str, reader: Callable[[str], str]) -> str:
    resolved = value.strip() if value else reader(f"{label}: ").strip()
    if not resolved:
        # "obrigatório(a)": label é genérico (usado para "Nome da empresa",
        # "Razão social", "CNPJ" — gêneros gramaticais diferentes), evita
        # concordância incorreta como "Razão social é obrigatório".
        raise BootstrapInputError(f"{label} é obrigatório(a).")
    return resolved


def main(
    argv: list[str] | None = None,
    *,
    session_factory: sessionmaker | None = None,
    value_reader: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    factory = session_factory or get_session_factory()

    empresa_repository = EmpresaRepository()
    empresa_service = EmpresaService(repository=empresa_repository)

    # Verificação de idempotência do bootstrap: recusa se QUALQUER empresa já
    # existir, não só se código/CNPJ colidirem — este comando é para nascer o
    # banco com a empresa piloto, não para cadastro contínuo (isso já existe,
    # embora desativado por ora, em POST /empresas). Duplicidade por código
    # interno/CNPJ específico continua garantida por
    # EmpresaService.create_empresa (EmpresaConflictError), tratada abaixo —
    # essa checagem aqui é apenas a primeira e mais ampla linha de defesa.
    try:
        with factory() as db:
            existentes = empresa_repository.list(db, limit=1)
            if existentes:
                raise BootstrapEmpresaExistsError(
                    f"Já existe ao menos uma empresa cadastrada "
                    f"('{existentes[0].codigo_interno}'). Este comando é só "
                    "para o bootstrap inicial de um banco vazio."
                )
    except BootstrapEmpresaExistsError as exc:
        output(f"Erro: {exc}")
        return 1

    try:
        nome = _resolve_value(args.nome, "Nome da empresa", value_reader)
        razao_social = _resolve_value(args.razao_social, "Razão social", value_reader)
        cnpj = _resolve_value(args.cnpj, "CNPJ", value_reader)
    except BootstrapInputError as exc:
        output(f"Erro: {exc}")
        return 1

    if not validar_cnpj(cnpj):
        output(f"Erro: CNPJ '{cnpj}' inválido.")
        return 1

    try:
        with factory() as db:
            empresa_create = EmpresaCreate(
                nome=nome,
                razaoSocial=razao_social,
                documento=cnpj,
                codigoInterno=args.codigo_interno.strip(),
            )
            empresa = empresa_service.create_empresa(db, empresa_create, actor_usuario_id=None)
    except EmpresaConflictError as exc:
        output(f"Erro ao criar empresa: {exc}")
        return 1

    output(f"Empresa '{empresa.nome}' (código {empresa.codigo_interno}) criada com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
