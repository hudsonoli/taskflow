import argparse
from collections.abc import Callable
from getpass import getpass

from sqlalchemy.orm import sessionmaker

from app.db.session import get_session_factory
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioCreate
from app.services.auth_service import AuthInvalidCredentialsError, AuthPasswordValidationError, AuthService
from app.services.usuario_service import UsuarioConflictError, UsuarioInvalidEmpresaError, UsuarioService

# perfil_base ainda não suporta "owner" no schema/JWT/autorização (ver
# ck_usuarios_perfil_base, ALLOWED_PERFIS_BASE em core/security.py e
# require_admin em dependencies/authorization.py — só admin/gestor/operador
# são aceitos hoje). "admin" é o nível mais alto disponível atualmente;
# "Owner" fica reservado para uma etapa própria de RBAC (já registrado em
# docs/setup/autenticacao.md). Este script cria o primeiro administrador da
# empresa usando "admin" como equivalente prático — por isso "bootstrap_admin",
# não "criar_owner".
BOOTSTRAP_PERFIL_BASE = "admin"

EMPRESA_STATUS_ATIVA = "ativa"


class BootstrapAlreadyExistsError(ValueError):
    pass


class BootstrapEmpresaError(ValueError):
    pass


class BootstrapInputError(ValueError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Cria o primeiro administrador (papel mais alto disponível hoje; "
            "ver BOOTSTRAP_PERFIL_BASE) de uma empresa. Idempotente: recusa-se "
            "a rodar se a empresa já tiver um usuário com esse perfil. "
            "empresa-codigo, nome e email são solicitados interativamente "
            "quando omitidos; passe todos os parâmetros para uso não "
            "interativo (automação)."
        )
    )
    parser.add_argument(
        "--empresa-codigo",
        default=None,
        help="Código interno da empresa (deve já existir e estar ativa). Solicitado interativamente se omitido.",
    )
    parser.add_argument(
        "--codigo-interno",
        required=True,
        help="Código interno do novo usuário (único na empresa).",
    )
    parser.add_argument(
        "--nome",
        default=None,
        help="Nome completo do usuário. Solicitado interativamente se omitido.",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="E-mail do usuário (único na empresa). Solicitado interativamente se omitido.",
    )
    return parser


def _resolve_value(value: str | None, label: str, reader: Callable[[str], str]) -> str:
    resolved = value.strip() if value else reader(f"{label}: ").strip()
    if not resolved:
        raise BootstrapInputError(f"{label} é obrigatório.")
    return resolved


def main(
    argv: list[str] | None = None,
    *,
    session_factory: sessionmaker | None = None,
    value_reader: Callable[[str], str] = input,
    password_reader: Callable[[str], str] = getpass,
    output: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    factory = session_factory or get_session_factory()

    empresa_repository = EmpresaRepository()
    usuario_repository = UsuarioRepository()
    usuario_service = UsuarioService(repository=usuario_repository, empresa_repository=empresa_repository)
    auth_service = AuthService(usuario_repository=usuario_repository, empresa_repository=empresa_repository)

    try:
        empresa_codigo = _resolve_value(args.empresa_codigo, "Código da empresa", value_reader)
    except BootstrapInputError as exc:
        output(f"Erro: {exc}")
        return 1

    # Valida empresa e idempotência antes de pedir nome/e-mail — evita
    # desperdiçar entrada interativa quando a empresa já está incorreta.
    try:
        with factory() as db:
            empresa = empresa_repository.get_by_codigo_interno(db, empresa_codigo.upper())
            if empresa is None:
                raise BootstrapEmpresaError(f"Empresa '{empresa_codigo}' não encontrada.")
            if empresa.status != EMPRESA_STATUS_ATIVA:
                raise BootstrapEmpresaError(f"Empresa '{empresa_codigo}' não está ativa (status={empresa.status}).")

            existentes = usuario_repository.list(db, empresa_id=empresa.id, perfil_base=BOOTSTRAP_PERFIL_BASE, limit=1)
            if existentes:
                raise BootstrapAlreadyExistsError(
                    f"Empresa '{empresa_codigo}' já possui usuário com perfil "
                    f"'{BOOTSTRAP_PERFIL_BASE}' ({existentes[0].email}). Use a API "
                    "autenticada (POST /usuarios) ou o CLI definir_senha_usuario "
                    "para gerenciar usuários adicionais — este comando é só para "
                    "o bootstrap inicial."
                )
    except (BootstrapEmpresaError, BootstrapAlreadyExistsError) as exc:
        output(f"Erro: {exc}")
        return 1

    try:
        nome = _resolve_value(args.nome, "Nome completo", value_reader)
        email = _resolve_value(args.email, "E-mail", value_reader)
    except BootstrapInputError as exc:
        output(f"Erro: {exc}")
        return 1

    senha = password_reader("Senha: ")
    confirmacao = password_reader("Confirme a senha: ")
    if senha != confirmacao:
        output("Erro: confirmação de senha não confere.")
        return 1

    try:
        with factory() as db:
            usuario_create = UsuarioCreate(
                empresaId=empresa.id,
                codigoInterno=args.codigo_interno.strip(),
                nome=nome,
                email=email,
                perfilBase=BOOTSTRAP_PERFIL_BASE,
                acessoSistema=True,
            )
            usuario = usuario_service.create_usuario(db, usuario_create, actor_usuario_id=None)
    except (UsuarioConflictError, UsuarioInvalidEmpresaError) as exc:
        output(f"Erro ao criar usuário: {exc}")
        return 1

    # LIMITAÇÃO CONHECIDA (não transacional): o usuário é criado antes da
    # credencial, em duas transações separadas (cada service commita por
    # conta própria). Se a definição de senha falhar aqui, não há rollback
    # automático — UsuarioRepository não expõe exclusão (Usuario nunca é
    # hard-deletado neste domínio, só inativado). O estado resultante é
    # seguro (usuário sem UsuarioCredencial não consegue autenticar —
    # AuthService.login trata credencial ausente como credenciais
    # inválidas) e recuperável via definir_senha_usuario, sem precisar
    # recriar o usuário. Melhoria arquitetural futura: quando AuthService e
    # UsuarioRepository forem refatorados, unificar criação de usuário e
    # credencial em uma única transação atômica, com rollback completo em
    # caso de falha — não implementado agora, por decisão explícita.
    try:
        with factory() as db:
            auth_service.definir_senha_usuario(
                db,
                empresa_codigo=empresa_codigo,
                email=email,
                senha=senha,
                actor_usuario_id=usuario.id,
            )
    except (AuthInvalidCredentialsError, AuthPasswordValidationError) as exc:
        output(
            f"Usuário '{usuario.email}' foi criado, mas a senha não pôde ser "
            f"definida ({exc}). Execute definir_senha_usuario para concluir."
        )
        return 1

    output(f"Usuário '{usuario.email}' (perfil {BOOTSTRAP_PERFIL_BASE}) criado com sucesso na empresa '{empresa_codigo}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
