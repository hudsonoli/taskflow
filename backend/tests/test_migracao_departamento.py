"""Migração de Departamento em Usuário — invariantes pós-contract (D3-B).

## Por que este arquivo mudou

Até a D3-A ele reproduzia a lógica de backfill da migration D2 (`0008`) contra as DUAS
colunas que coexistiam: `departamento_id` (texto com o nome) e `departamento_uuid` (FK).

A D3-B removeu a coluna textual e renomeou a de UUID para `departamento_id`. As asserções
antigas passariam a rodar contra colunas que não existem mais — não é possível "manter" o
teste do backfill: ele testava um estado transitório que acabou. A migration `0008`
continua no repositório como história e roda em qualquer banco novo pelo `upgrade head`.

O que substitui aquela cobertura são as invariantes que **sobrevivem** ao contract e que
protegem o dado de verdade daqui pra frente: a FK, o `ON DELETE SET NULL`, o escopo por
empresa e a guarda de cross-tenant que a migration `0009` executa antes de qualquer DROP.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario

# Guarda de cross-tenant idêntica à da migration 0009 (D3-B).
SQL_GUARDA_CROSS_TENANT = text(
    """
    SELECT count(*) FROM usuarios u
    JOIN departamentos d ON d.id = u.departamento_id
    WHERE d.empresa_id <> u.empresa_id
    """
)

SQL_GUARDA_ORFAOS = text(
    """
    SELECT count(*) FROM usuarios u
    WHERE u.departamento_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM departamentos d WHERE d.id = u.departamento_id)
    """
)


def _departamento(db: Session, empresa: Empresa, nome: str | None = None) -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=nome or f"Depto {sufixo}",
        nome_normalizado=f"depto-{sufixo}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _usuario(db: Session, empresa: Empresa, departamento_id: str | None = None) -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"u-{sufixo}",
        nome=f"Usuário {sufixo}",
        email=f"u-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status="ativo",
        departamento_id=departamento_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


# --------------------------------------------------------------------------------------

def test_base_vazia_nao_viola_guardas(db_session: Session) -> None:
    """As guardas da 0009 são estruturais: em banco sem vínculos, zero violações."""
    db_session.execute(text("UPDATE usuarios SET departamento_id = NULL"))
    assert db_session.execute(SQL_GUARDA_ORFAOS).scalar_one() == 0
    assert db_session.execute(SQL_GUARDA_CROSS_TENANT).scalar_one() == 0


def test_fk_impede_uuid_orfao(db_session: Session, empresa: Empresa) -> None:
    """Depois do contract, órfão é impossível por construção — a FK recusa."""
    usuario = _usuario(db_session, empresa)
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE usuarios SET departamento_id = :d WHERE id = :i"),
            {"d": str(uuid.uuid4()), "i": usuario.id},
        )
        db_session.flush()


def test_guarda_detecta_cross_tenant(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    """A FK garante existência, não tenant. É a guarda que pega vínculo entre empresas.

    O vínculo é forjado por SQL cru de propósito: pela API o serviço já recusa (422), então
    só assim dá pra provar que a guarda enxergaria uma inconsistência vinda de fora.
    """
    alheio = _departamento(db_session, outra_empresa)
    usuario = _usuario(db_session, empresa)

    assert db_session.execute(SQL_GUARDA_CROSS_TENANT).scalar_one() == 0

    db_session.execute(
        text("UPDATE usuarios SET departamento_id = :d WHERE id = :i"),
        {"d": alheio.id, "i": usuario.id},
    )
    db_session.flush()

    assert db_session.execute(SQL_GUARDA_CROSS_TENANT).scalar_one() == 1


def test_on_delete_set_null_preserva_usuario(db_session: Session, empresa: Empresa) -> None:
    """Apagar um Departamento nunca pode apagar Usuário — só desfaz o vínculo.

    (Na prática Departamento é arquivado, nunca apagado — mas a garantia é do schema.)
    """
    departamento = _departamento(db_session, empresa)
    usuario = _usuario(db_session, empresa, departamento.id)

    db_session.execute(text("DELETE FROM departamentos WHERE id = :d"), {"d": departamento.id})
    db_session.flush()
    db_session.expire_all()

    sobreviveu, vinculo = db_session.execute(
        text("SELECT count(*), max(departamento_id) FROM usuarios WHERE id = :i"), {"i": usuario.id}
    ).one()
    assert sobreviveu == 1, "usuário não pode ser removido junto com o departamento"
    assert vinculo is None, "o vínculo tem de virar NULL"


def test_null_permanece_null(db_session: Session, empresa: Empresa) -> None:
    usuario = _usuario(db_session, empresa, None)
    atual = db_session.execute(
        text("SELECT departamento_id FROM usuarios WHERE id = :i"), {"i": usuario.id}
    ).scalar_one()
    assert atual is None


def test_contagem_por_departamento(db_session: Session, empresa: Empresa) -> None:
    """A distribuição por departamento continua consultável pela coluna única."""
    primeiro = _departamento(db_session, empresa)
    segundo = _departamento(db_session, empresa)
    for _ in range(3):
        _usuario(db_session, empresa, primeiro.id)
    for _ in range(2):
        _usuario(db_session, empresa, segundo.id)

    for departamento_id, esperado in ((primeiro.id, 3), (segundo.id, 2)):
        atual = db_session.execute(
            text("SELECT count(*) FROM usuarios WHERE departamento_id = :d"), {"d": departamento_id}
        ).scalar_one()
        assert atual == esperado
