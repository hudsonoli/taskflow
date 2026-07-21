from sqlalchemy import select

from app.cli.bootstrap_empresa import main
from app.models.empresa import Empresa
from conftest import make_empresa, persist


def outputs():
    lines: list[str] = []
    return lines, lines.append


def scripted_reader(values):
    values = list(values)

    def read(prompt):
        return values.pop(0)

    return read


VALID_CNPJ = "15.519.472/0001-22"
VALID_CNPJ_DIGITS = "15519472000122"
VALID_RAZAO_SOCIAL = "Box Comunicação LTDA"


def test_bootstrap_creates_first_empresa(session_factory):
    lines, output = outputs()

    exit_code = main(
        [
            "--nome", "BOX COMUNICAÇÃO",
            "--razao-social", VALID_RAZAO_SOCIAL,
            "--cnpj", VALID_CNPJ,
            "--codigo-interno", "BOX",
        ],
        session_factory=session_factory,
        output=output,
    )

    assert exit_code == 0
    assert lines == ["Empresa 'BOX COMUNICAÇÃO' (código BOX) criada com sucesso."]

    with session_factory() as db:
        empresa = db.scalars(select(Empresa).where(Empresa.codigo_interno == "BOX")).one()
        assert empresa.nome == "BOX COMUNICAÇÃO"
        assert empresa.razao_social == VALID_RAZAO_SOCIAL
        # EmpresaService normaliza documento para apenas dígitos (ver
        # EmpresaService._normalize_documento) — o CNPJ é passado formatado,
        # mas persistido só com dígitos.
        assert empresa.documento == VALID_CNPJ_DIGITS
        assert empresa.status == "ativa"


def test_bootstrap_refuses_when_any_empresa_already_exists(session_factory):
    # A checagem é global (qualquer empresa), não só por código/CNPJ
    # coincidente — este comando é só para o bootstrap inicial de um banco
    # vazio. Isso também impede, transitivamente, duplicidade por código
    # interno/CNPJ: se já existe qualquer empresa, uma segunda tentativa
    # (mesmo com código/CNPJ diferentes) é recusada antes de chegar em
    # EmpresaService.create_empresa. A proteção específica por
    # código/CNPJ igual continua garantida por
    # EmpresaService.create_empresa (EmpresaConflictError), já coberta em
    # test_empresas.py — não duplicada aqui.
    persist(session_factory, make_empresa(codigo_interno="OUTRA", documento="00000000000100"))
    lines, output = outputs()

    exit_code = main(
        [
            "--nome", "BOX COMUNICAÇÃO",
            "--razao-social", VALID_RAZAO_SOCIAL,
            "--cnpj", VALID_CNPJ,
            "--codigo-interno", "BOX",
        ],
        session_factory=session_factory,
        output=output,
    )

    assert exit_code == 1
    assert len(lines) == 1
    assert "Já existe ao menos uma empresa cadastrada" in lines[0]
    with session_factory() as db:
        assert db.query(Empresa).count() == 1


def test_bootstrap_prompts_interactively_when_arguments_omitted(session_factory):
    lines, output = outputs()

    exit_code = main(
        ["--codigo-interno", "BOX"],
        session_factory=session_factory,
        value_reader=scripted_reader(["BOX COMUNICAÇÃO", VALID_RAZAO_SOCIAL, VALID_CNPJ]),
        output=output,
    )

    assert exit_code == 0
    with session_factory() as db:
        empresa = db.scalars(select(Empresa).where(Empresa.codigo_interno == "BOX")).one()
        assert empresa.nome == "BOX COMUNICAÇÃO"
        assert empresa.razao_social == VALID_RAZAO_SOCIAL
        assert empresa.documento == VALID_CNPJ_DIGITS


def test_bootstrap_rejects_blank_interactive_field(session_factory):
    lines, output = outputs()

    exit_code = main(
        ["--codigo-interno", "BOX"],
        session_factory=session_factory,
        value_reader=scripted_reader(["   "]),
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: Nome da empresa é obrigatório(a)."]
    with session_factory() as db:
        assert db.query(Empresa).count() == 0


def test_bootstrap_rejects_blank_razao_social(session_factory):
    lines, output = outputs()

    exit_code = main(
        ["--nome", "BOX COMUNICAÇÃO", "--codigo-interno", "BOX"],
        session_factory=session_factory,
        value_reader=scripted_reader(["   "]),
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: Razão social é obrigatório(a)."]
    with session_factory() as db:
        assert db.query(Empresa).count() == 0


def test_bootstrap_rejects_invalid_cnpj(session_factory):
    lines, output = outputs()

    exit_code = main(
        [
            "--nome", "BOX COMUNICAÇÃO",
            "--razao-social", VALID_RAZAO_SOCIAL,
            "--cnpj", "11.111.111/1111-11",
            "--codigo-interno", "BOX",
        ],
        session_factory=session_factory,
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: CNPJ '11.111.111/1111-11' inválido."]
    with session_factory() as db:
        assert db.query(Empresa).count() == 0


def test_bootstrap_rejects_malformed_cnpj(session_factory):
    lines, output = outputs()

    exit_code = main(
        [
            "--nome", "BOX COMUNICAÇÃO",
            "--razao-social", VALID_RAZAO_SOCIAL,
            "--cnpj", "123",
            "--codigo-interno", "BOX",
        ],
        session_factory=session_factory,
        output=output,
    )

    assert exit_code == 1
    assert lines == ["Erro: CNPJ '123' inválido."]
    with session_factory() as db:
        assert db.query(Empresa).count() == 0
