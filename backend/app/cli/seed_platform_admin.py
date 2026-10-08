"""Concede (ou reativa) a autoridade de Administrador da Plataforma a um usuário JÁ existente.

É o ÚNICO ponto em que um e-mail localiza a autoridade: o e-mail só serve para achar o usuário aqui; a autorização em
runtime consulta `administradores_plataforma` e nunca compara e-mail. Nada é hardcoded — o e-mail vem de argumento ou
de variável de ambiente:

    python -m app.cli.seed_platform_admin --email <email> [--empresa-codigo <codigo>]
    PLATFORM_ADMIN_EMAIL=<email> python -m app.cli.seed_platform_admin

Idempotente: criar, reativar e "já ativa" são resultados normais (rodar duas vezes não muda nada na segunda). Exige
usuário existente, `ativo` e com acesso ao sistema. NÃO altera a linha do usuário (perfil, conta de sistema, empresa,
credenciais) e não imprime segredo algum — só o resultado.

Com `--revogar` a autoridade é desativada (registrada, nunca apagada).
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable

from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.plataforma_service import PlataformaService

ENV_EMAIL = "PLATFORM_ADMIN_EMAIL"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Concede/reativa (ou --revogar) o Administrador da Plataforma.")
    parser.add_argument("--email", default=None, help=f"E-mail do usuário existente (ou variável {ENV_EMAIL}).")
    parser.add_argument(
        "--empresa-codigo",
        default=None,
        help="Código interno da empresa do usuário (padrão: EMPRESA_CODIGO do ambiente).",
    )
    parser.add_argument("--revogar", action="store_true", help="Desativa a autoridade em vez de concedê-la.")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    session_factory: sessionmaker | None = None,
    output: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    email = (args.email or os.getenv(ENV_EMAIL) or "").strip().lower()
    if not email:
        output(f"Erro: informe --email ou a variável {ENV_EMAIL}.")
        return 1
    empresa_codigo = (args.empresa_codigo or get_settings().empresa_codigo).strip().upper()

    factory = session_factory or get_session_factory()
    with factory() as db:
        empresa = EmpresaRepository().get_by_codigo_interno(db, empresa_codigo)
        if empresa is None:
            output("Erro: empresa não encontrada.")
            return 1
        usuario = UsuarioRepository().get_by_email(db, empresa_id=empresa.id, email=email)
        if usuario is None:
            output("Erro: usuário não encontrado nessa empresa.")
            return 1

        service = PlataformaService()
        if args.revogar:
            administrador = service.administrador_ativo_de(db, usuario)
            if administrador is None:
                output("Nada a revogar: o usuário não é administrador ativo da plataforma.")
                return 0
            service.revogar_autoridade(db, administrador)
            output("Autoridade de plataforma revogada.")
            return 0

        if usuario.status != "ativo" or not usuario.acesso_sistema:
            output("Erro: o usuário precisa estar ativo e com acesso ao sistema.")
            return 1
        linha, resultado = service.conceder_autoridade(db, usuario)
        rotulo = {"criada": "concedida", "reativada": "reativada", "ja_ativa": "já estava ativa"}[resultado]
        output(f"Autoridade de plataforma {rotulo} (administrador {linha.id}).")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
