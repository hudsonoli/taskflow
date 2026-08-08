"""Popula os usuários iniciais no banco (5 demo + planilha importada).

Usuário é entidade real desde a Fase 1; o mock do frontend (`lib/usuarios-mock.ts`) foi
removido no fechamento da Fase 2A. Este seed carrega o elenco original, que veio de lá.

Cada usuário recebe a senha padrão de BOOTSTRAP_DEFAULT_PASSWORD e fica marcado para
trocá-la no primeiro acesso (senha_deve_ser_alterada=true). A conta de sistema NÃO é
criada aqui — ver app/cli/seed_bootstrap.py.

perfil_base real só aceita admin/gestor/operador (3 valores) — o mock usava 7. Mapeamento
aplicado (decisão registrada no plano da Fase 1): superadmin|diretoria -> admin,
financeiro -> gestor, cliente -> operador, gestor/operador ficam iguais.

Fonte de dados: `app/cli/data/usuarios_seed.json` — **a única fonte oficial**. O backend
nunca lê nada de dentro de frontend/, e a cópia que existia lá foi removida junto com o
mock. Mais os 5 usuários demo replicados abaixo.

Uso: python -m app.cli.seed_usuarios
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.usuario import Usuario
from app.models.usuario_credencial import UsuarioCredencial
from app.repositories.usuario_credencial_repository import UsuarioCredencialRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.empresa import EmpresaCreate
from app.services.empresa_service import EmpresaService

DATA_FILE = Path(__file__).parent / "data" / "usuarios_seed.json"


def _normalizar_nome_departamento(nome: str) -> str:
    """Mesma regra da migration D2: sem acento, minúsculo, sem espaços nas pontas."""
    import unicodedata

    return unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().strip().lower()

PERFIL_MOCK_PARA_BASE = {
    "superadmin": "admin",
    "diretoria": "admin",
    "admin": "admin",
    "financeiro": "gestor",
    "gestor": "gestor",
    "operador": "operador",
    "cliente": "operador",
}

# Os 5 usuários demo que vinham hardcoded no mock removido — mesmos nomes/e-mails/perfis,
# pra manter o elenco de ~38 pessoas que o sistema já usava.
USUARIOS_DEMO = [
    {
        "codigo_interno": "usuario-1",
        "nome": "Hudson Cunha",
        "email": "hudson@taskfloww.local",
        "departamento": "Diretoria",
        "perfil": "superadmin",
        "cor_identificacao": "blue",
    },
    {
        "codigo_interno": "usuario-2",
        "nome": "Ana Costa",
        "email": "ana.costa@taskfloww.local",
        "departamento": "Atendimento",
        "perfil": "gestor",
        "valor_recebido_mensal_centavos": 800000,
        "horas_trabalho_aproximadas": 160,
        "cor_identificacao": "green",
    },
    {
        "codigo_interno": "usuario-3",
        "nome": "Carlos Lima",
        "email": "carlos.lima@taskfloww.local",
        "departamento": "Criação",
        "perfil": "operador",
        "lider_departamento": True,
        "cor_identificacao": "orange",
    },
    {
        "codigo_interno": "usuario-4",
        "nome": "João Silva",
        "email": "joao.silva@taskfloww.local",
        "departamento": "Mídia",
        "perfil": "operador",
        "cor_identificacao": "purple",
    },
    {
        "codigo_interno": "usuario-5",
        "nome": "Maria Souza",
        "email": "maria.souza@taskfloww.local",
        "departamento": "Conteúdo",
        "perfil": "operador",
        "cor_identificacao": "pink",
    },
]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _carregar_usuarios_importados() -> list[dict]:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    nomes_demo = {item["nome"].strip().lower() for item in USUARIOS_DEMO}
    # Mesma regra de dedup do mock: planilha importada não sobrescreve os 5 demo.
    return [item for item in raw if item["nome"].strip().lower() not in nomes_demo]


def seed_usuarios(output=print) -> None:
    settings = get_settings()
    factory = get_session_factory()
    empresa_service = EmpresaService()
    usuario_repository = UsuarioRepository()
    credencial_repository = UsuarioCredencialRepository()

    # Não há fallback no código (ver app/core/config.py): sem a variável definida, o seed
    # para aqui em vez de inventar uma senha silenciosamente.
    if not settings.bootstrap_default_password:
        raise RuntimeError(
            "BOOTSTRAP_DEFAULT_PASSWORD não configurada. Defina a variável de ambiente "
            "antes de executar o seed."
        )

    with factory() as db:
        empresa = empresa_service.repository.get_by_codigo_interno(db, settings.empresa_codigo)
        if empresa is None:
            empresa = empresa_service.create_empresa(
                db,
                EmpresaCreate(nome=settings.empresa_nome, codigoInterno=settings.empresa_codigo),
            )
            output(f"Empresa criada: {empresa.id} ({empresa.codigo_interno})")

        # D3-A: o seed nunca mais grava o NOME do departamento. A planilha traz nome
        # livre; aqui ele é resolvido para o `id` real de Departamento (mesma empresa).
        # Nome que não existir no cadastro vira vínculo nulo — melhor sem departamento do
        # que com relacionamento inventado.
        from app.repositories.departamento_repository import DepartamentoRepository

        departamento_repository = DepartamentoRepository()
        departamentos_por_nome = {
            _normalizar_nome_departamento(d.nome): d.id
            for d in departamento_repository.list_diretorio(db, empresa_id=empresa.id)
        }

        def resolver_departamento(nome: str | None) -> str | None:
            if not nome or not nome.strip():
                return None
            return departamentos_por_nome.get(_normalizar_nome_departamento(nome))

        criados = 0
        pulados = 0

        for item in USUARIOS_DEMO:
            criado = _criar_usuario(
                db,
                empresa_id=empresa.id,
                codigo_interno=item["codigo_interno"],
                nome=item["nome"],
                email=item["email"],
                perfil_mock=item["perfil"],
                ativo=True,
                departamento_id=resolver_departamento(item.get("departamento")),
                cor_identificacao=item.get("cor_identificacao"),
                lider_departamento=item.get("lider_departamento", False),
                valor_recebido_mensal_centavos=item.get("valor_recebido_mensal_centavos"),
                horas_trabalho_aproximadas=item.get("horas_trabalho_aproximadas"),
                usuario_repository=usuario_repository,
                credencial_repository=credencial_repository,
                senha_padrao=settings.bootstrap_default_password,
            )
            criados += 1 if criado else 0
            pulados += 0 if criado else 1

        for item in _carregar_usuarios_importados():
            criado = _criar_usuario(
                db,
                empresa_id=empresa.id,
                codigo_interno=item["id"],
                nome=item["nome"],
                email=item["email"],
                perfil_mock=item.get("perfil", "operador"),
                ativo=item.get("ativo", True),
                departamento_id=resolver_departamento(item.get("departamento")),
                cor_identificacao=item.get("corIdentificacao"),
                telefone=item.get("telefone") or None,
                cpf=item.get("cpf") or None,
                data_nascimento=_parse_date(item.get("dataNascimento")),
                observacoes=item.get("observacoes") or None,
                usuario_repository=usuario_repository,
                credencial_repository=credencial_repository,
                senha_padrao=settings.bootstrap_default_password,
            )
            criados += 1 if criado else 0
            pulados += 0 if criado else 1

        db.commit()
        output(f"Usuários criados: {criados} | já existiam (pulados): {pulados}")


def _criar_usuario(
    db,
    *,
    empresa_id: str,
    codigo_interno: str,
    nome: str,
    email: str,
    perfil_mock: str,
    ativo: bool,
    usuario_repository: UsuarioRepository,
    credencial_repository: UsuarioCredencialRepository,
    senha_padrao: str,
    departamento_id: str | None = None,
    cor_identificacao: str | None = None,
    lider_departamento: bool = False,
    valor_recebido_mensal_centavos: int | None = None,
    horas_trabalho_aproximadas: float | None = None,
    telefone: str | None = None,
    cpf: str | None = None,
    data_nascimento: date | None = None,
    observacoes: str | None = None,
) -> bool:
    email_normalizado = email.strip().lower()
    if usuario_repository.get_by_email(db, empresa_id=empresa_id, email=email_normalizado) is not None:
        return False

    now = datetime.now(timezone.utc)
    usuario = Usuario(
        id=str(uuid4()),
        empresa_id=empresa_id,
        codigo_interno=codigo_interno,
        nome=nome,
        email=email_normalizado,
        perfil_base=PERFIL_MOCK_PARA_BASE.get(perfil_mock, "operador"),
        acesso_sistema=True,
        status="ativo" if ativo else "inativo",
        departamento_id=departamento_id,
        cor_identificacao=cor_identificacao,
        lider_departamento=lider_departamento,
        valor_recebido_mensal_centavos=valor_recebido_mensal_centavos,
        horas_trabalho_aproximadas=horas_trabalho_aproximadas,
        telefone=telefone,
        cpf=cpf,
        data_nascimento=data_nascimento,
        observacoes=observacoes,
        is_system_account=False,
        created_at=now,
        updated_at=now,
    )
    usuario_repository.create(db, usuario)

    credencial = UsuarioCredencial(
        id=str(uuid4()),
        usuario_id=usuario.id,
        senha_hash=hash_password(senha_padrao),
        senha_definida_em=now,
        senha_alterada_em=None,
        tentativas_falhas=0,
        bloqueado_ate=None,
        senha_deve_ser_alterada=True,
        created_at=now,
        updated_at=now,
    )
    credencial_repository.create(db, credencial)
    return True


if __name__ == "__main__":
    seed_usuarios()
