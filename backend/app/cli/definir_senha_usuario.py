import argparse
from collections.abc import Callable
from getpass import getpass

from sqlalchemy.orm import sessionmaker

from app.db.session import get_session_factory
from app.services.auth_service import AuthInvalidCredentialsError, AuthPasswordValidationError, AuthService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Define ou substitui a senha de um usuário existente.")
    parser.add_argument("--empresa-codigo", required=True)
    parser.add_argument("--email", required=True)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    session_factory: sessionmaker | None = None,
    password_reader: Callable[[str], str] = getpass,
    output: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    senha = password_reader("Senha: ")
    confirmacao = password_reader("Confirme a senha: ")

    if senha != confirmacao:
        output("Erro: confirmação de senha não confere.")
        return 1

    factory = session_factory or get_session_factory()
    service = AuthService()
    try:
        with factory() as db:
            service.definir_senha_usuario(
                db,
                empresa_codigo=args.empresa_codigo,
                email=args.email,
                senha=senha,
            )
    except (AuthInvalidCredentialsError, AuthPasswordValidationError) as exc:
        output(f"Erro: {exc}")
        return 1

    output("Senha definida com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
