from sqlalchemy import select

from app.cli.bootstrap_admin import main
from app.core.security import verify_password
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from conftest import make_empresa, persist


def outputs():
    lines: list[str] = []
    return lines, lines.append


def scripted_reader(values):
    values = list(values)

    def read(prompt):
        return values.pop(0)

    return read


def test_bootstrap_creates_first_admin_with_hashed_password(session_factory):
    persist(session_factory, make_empresa(codigo_interno="BOX"))
    lines, output = outputs()

    exit_code = main(
        [
            "--empresa-codigo", "BOX",
            "--codigo-interno", "OWNER-001",
            "--nome", "Hudson Cunha",
            "--email", "hudson@empresa.com",
        ],
        session_factory=session_factory,
        password_reader=scripted_reader(["SenhaForte123", "SenhaForte123"]),
        output=output,
    )

    assert exit_code == 0
    assert lines == ["Usuário 'hudson@empresa.com' (perfil admin) criado com sucesso na empresa 'BOX'."]

    with session_factory() as db:
        usuario = db.scalars(select(Usuario).where(Usuario.email == "hudson@empresa.com")).one()
        assert usuario.perfil_base == "admin"
        assert usuario.status == "ativo"
        assert usuario.acesso_sistema is True
        credencial = db.scalars(
            select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == usuario.id)
        ).one()
        assert verify_password("SenhaForte123", credencial.senha_hash)


def test_bootstrap_refuses_when_admin_already_exists(session_factory):
    persist(session_factory, make_empresa(codigo_interno="BOX"))
    main(
        [
            "--empresa-codigo", "BOX",
            "--codigo-interno", "OWNER-001",
            "--nome", "Primeiro Admin",
            "--email", "primeiro@empresa.com",
        ],
        session_factory=session_factory,
        password_reader=scripted_reader(["SenhaForte123", "SenhaForte123"]),
        output=lambda _line: None,
    )

    lines, output = outputs()
    exit_code = main(
        [
            "--empresa-codigo", "BOX",
            "--codigo-interno", "OWNER-002",
            "--nome", "Segundo Admin",
            "--email", "segundo@empresa.com",
        ],
        session_factory=session_factory,
        password_reader=scripted_reader(["SenhaForte123", "SenhaForte123"]),
        output=output,
    )

    assert exit_code == 1
    assert len(lines) == 1
    assert "já possui usuário com perfil 'admin'" in lines[0]
    with session_factory() as db:
        assert db.query(Usuario).count() == 1


def test_bootstrap_rejects_unknown_empresa(session_factory):
    lines, output = outputs()

    exit_code = main(
        [
            "--empresa-codigo", "NAO-EXISTE",
            "--codigo-interno", "OWNER-001",
            "--nome", "Hudson Cunha",
            "--email", "hudson@empresa.com",
        ],
        session_factory=session_factory,
        password_reader=scripted_reader(["SenhaForte123", "SenhaForte123"]),
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: Empresa 'NAO-EXISTE' não encontrada."]
    with session_factory() as db:
        assert db.query(Usuario).count() == 0


def test_bootstrap_rejects_inactive_empresa(session_factory):
    persist(session_factory, make_empresa(codigo_interno="BOX", status="inativa"))
    lines, output = outputs()

    exit_code = main(
        [
            "--empresa-codigo", "BOX",
            "--codigo-interno", "OWNER-001",
            "--nome", "Hudson Cunha",
            "--email", "hudson@empresa.com",
        ],
        session_factory=session_factory,
        password_reader=scripted_reader(["SenhaForte123", "SenhaForte123"]),
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: Empresa 'BOX' não está ativa (status=inativa)."]
    with session_factory() as db:
        assert db.query(Usuario).count() == 0


def test_bootstrap_prompts_interactively_when_arguments_omitted(session_factory):
    persist(session_factory, make_empresa(codigo_interno="BOX"))
    lines, output = outputs()

    exit_code = main(
        ["--codigo-interno", "OWNER-001"],
        session_factory=session_factory,
        value_reader=scripted_reader(["BOX", "Hudson Cunha", "hudson@empresa.com"]),
        password_reader=scripted_reader(["SenhaForte123", "SenhaForte123"]),
        output=output,
    )

    assert exit_code == 0
    with session_factory() as db:
        usuario = db.scalars(select(Usuario).where(Usuario.email == "hudson@empresa.com")).one()
        assert usuario.nome == "Hudson Cunha"


def test_bootstrap_rejects_blank_interactive_field(session_factory):
    lines, output = outputs()

    exit_code = main(
        ["--codigo-interno", "OWNER-001"],
        session_factory=session_factory,
        value_reader=scripted_reader(["   "]),
        password_reader=scripted_reader(["SenhaForte123", "SenhaForte123"]),
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: Código da empresa é obrigatório."]
    with session_factory() as db:
        assert db.query(Usuario).count() == 0


def test_bootstrap_rejects_confirmation_mismatch(session_factory):
    persist(session_factory, make_empresa(codigo_interno="BOX"))
    lines, output = outputs()

    exit_code = main(
        [
            "--empresa-codigo", "BOX",
            "--codigo-interno", "OWNER-001",
            "--nome", "Hudson Cunha",
            "--email", "hudson@empresa.com",
        ],
        session_factory=session_factory,
        password_reader=scripted_reader(["SenhaForte123", "OutraSenha123"]),
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: confirmação de senha não confere."]
    with session_factory() as db:
        assert db.query(Usuario).count() == 0


def test_bootstrap_creates_user_but_reports_password_policy_failure(session_factory):
    # Sem validação de política duplicada no script: a política (mínimo de 8
    # caracteres) vive só em AuthService.definir_senha_usuario, chamada após
    # o usuário já existir. Não há rollback automático (UsuarioRepository não
    # expõe exclusão — Usuario nunca é hard-deletado neste domínio), então o
    # usuário permanece criado, mas sem UsuarioCredencial: não consegue
    # autenticar e é recuperável via definir_senha_usuario.
    persist(session_factory, make_empresa(codigo_interno="BOX"))
    lines, output = outputs()

    exit_code = main(
        [
            "--empresa-codigo", "BOX",
            "--codigo-interno", "OWNER-001",
            "--nome", "Hudson Cunha",
            "--email", "hudson@empresa.com",
        ],
        session_factory=session_factory,
        password_reader=scripted_reader(["curta", "curta"]),
        output=output,
    )

    assert exit_code == 1
    assert len(lines) == 1
    assert "não pôde ser definida" in lines[0]
    assert "pelo menos 8 caracteres" in lines[0]

    with session_factory() as db:
        usuario = db.scalars(select(Usuario).where(Usuario.email == "hudson@empresa.com")).one()
        assert (
            db.scalars(
                select(UsuarioCredencial).where(UsuarioCredencial.usuario_id == usuario.id)
            ).first()
            is None
        )


def test_bootstrap_never_prints_password_or_hash(session_factory):
    persist(session_factory, make_empresa(codigo_interno="BOX"))
    lines, output = outputs()

    exit_code = main(
        [
            "--empresa-codigo", "BOX",
            "--codigo-interno", "OWNER-001",
            "--nome", "Hudson Cunha",
            "--email", "hudson@empresa.com",
        ],
        session_factory=session_factory,
        password_reader=scripted_reader(["SenhaSecreta123", "SenhaSecreta123"]),
        output=output,
    )

    assert exit_code == 0
    joined = " ".join(lines)
    assert "SenhaSecreta123" not in joined
    assert "argon2" not in joined.lower()
