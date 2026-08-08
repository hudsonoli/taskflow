"""Cria a conta de sistema (bootstrap/recuperação) e a Empresa padrão, se ainda não existirem.

Lê tudo de variáveis de ambiente — nunca hardcoda nome/e-mail/senha de pessoa alguma:
  BOOTSTRAP_OWNER_NAME, BOOTSTRAP_OWNER_EMAIL, BOOTSTRAP_OWNER_PASSWORD (obrigatórias)
  EMPRESA_CODIGO, EMPRESA_NOME (com default em app.core.config)

Idempotente: se a conta já existe (por e-mail), não faz nada.

Uso: python -m app.cli.seed_bootstrap
"""

from datetime import datetime, timezone
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

BOOTSTRAP_CODIGO_INTERNO = "BOOTSTRAP"


def seed_bootstrap(output=print) -> None:
    settings = get_settings()

    faltando = [
        nome
        for nome, valor in (
            ("BOOTSTRAP_OWNER_NAME", settings.bootstrap_owner_name),
            ("BOOTSTRAP_OWNER_EMAIL", settings.bootstrap_owner_email),
            ("BOOTSTRAP_OWNER_PASSWORD", settings.bootstrap_owner_password),
        )
        if not valor
    ]
    if faltando:
        raise RuntimeError(
            "Variáveis de ambiente obrigatórias ausentes para a conta de sistema: " + ", ".join(faltando)
        )

    factory = get_session_factory()
    empresa_service = EmpresaService()
    usuario_repository = UsuarioRepository()
    credencial_repository = UsuarioCredencialRepository()

    with factory() as db:
        empresa = empresa_service.repository.get_by_codigo_interno(db, settings.empresa_codigo)
        if empresa is None:
            empresa = empresa_service.create_empresa(
                db,
                EmpresaCreate(nome=settings.empresa_nome, codigoInterno=settings.empresa_codigo),
            )
            output(f"Empresa criada: {empresa.id} ({empresa.codigo_interno})")
        else:
            output(f"Empresa já existia: {empresa.id} ({empresa.codigo_interno})")

        email_normalizado = settings.bootstrap_owner_email.strip().lower()
        existente = usuario_repository.get_by_email(db, empresa_id=empresa.id, email=email_normalizado)
        if existente is not None:
            output(f"Conta de sistema já existia: {existente.id} ({existente.email}) — nada a fazer.")
            return

        now = datetime.now(timezone.utc)
        usuario = Usuario(
            id=str(uuid4()),
            empresa_id=empresa.id,
            codigo_interno=BOOTSTRAP_CODIGO_INTERNO,
            nome=settings.bootstrap_owner_name,
            email=email_normalizado,
            perfil_base="admin",
            acesso_sistema=True,
            status="ativo",
            is_system_account=True,
            created_at=now,
            updated_at=now,
        )
        usuario_repository.create(db, usuario)

        credencial = UsuarioCredencial(
            id=str(uuid4()),
            usuario_id=usuario.id,
            senha_hash=hash_password(settings.bootstrap_owner_password),
            senha_definida_em=now,
            senha_alterada_em=None,
            tentativas_falhas=0,
            bloqueado_ate=None,
            senha_deve_ser_alterada=False,
            created_at=now,
            updated_at=now,
        )
        credencial_repository.create(db, credencial)
        db.commit()
        output(f"Conta de sistema criada: {usuario.id} ({usuario.email}) — is_system_account=True, perfil_base=admin")


if __name__ == "__main__":
    seed_bootstrap()
