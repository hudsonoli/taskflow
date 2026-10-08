"""Consultas AGREGADAS da Dashboard da plataforma — poucas queries, nenhuma por empresa (sem N+1).

Quatro consultas no total, qualquer que seja o número de empresas:
  1. empresas;
  2. usuários agregados por empresa (cadastrados, utilizáveis, Gestores, já acessaram, ativos 7d/30d, último acesso) com UM
     LEFT JOIN no último login de cada usuário (`auth.login_sucesso` agrupado por `usuario_id`, via `ix_eventos_tipo`);
  3. projetos por empresa; 4. demandas por empresa (ambos por `ix_*_empresa_id`).

Definições (fonte única): "humano" = não é conta de sistema e não está arquivado; "utilizável" = humano ativo com acesso ao
sistema. Login = evento `auth.login_sucesso` (e-mail/senha ou Google); não existe outro rastreio de atividade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.projeto import Projeto
from app.models.usuario import Usuario

TIPO_LOGIN = "auth.login_sucesso"


@dataclass(frozen=True)
class UsuariosAgregados:
    cadastrados: int = 0
    usuarios: int = 0
    gestores: int = 0
    ja_acessaram: int = 0
    ativos_7d: int = 0
    ativos_30d: int = 0
    ultimo_acesso: datetime | None = None


class PlataformaDashboardRepository:
    def listar_empresas(self, db: Session) -> list[Empresa]:
        return list(db.scalars(select(Empresa).order_by(Empresa.nome, Empresa.id)).all())

    def usuarios_por_empresa(self, db: Session, *, limite_7d: datetime, limite_30d: datetime) -> dict[str, UsuariosAgregados]:
        ultimo_login = (
            select(Evento.usuario_id.label("usuario_id"), func.max(Evento.occurred_at).label("ultimo"))
            .where(Evento.tipo == TIPO_LOGIN, Evento.usuario_id.is_not(None))
            .group_by(Evento.usuario_id)
            .subquery()
        )
        utilizavel = and_(Usuario.status == "ativo", Usuario.acesso_sistema.is_(True))
        consulta = (
            select(
                Usuario.empresa_id,
                func.count(Usuario.id).label("cadastrados"),
                func.count(Usuario.id).filter(utilizavel).label("usuarios"),
                func.count(Usuario.id).filter(and_(utilizavel, Usuario.perfil_base == "gestor")).label("gestores"),
                func.count(Usuario.id).filter(and_(utilizavel, ultimo_login.c.ultimo.is_not(None))).label("ja_acessaram"),
                func.count(Usuario.id).filter(and_(utilizavel, ultimo_login.c.ultimo >= limite_7d)).label("ativos_7d"),
                func.count(Usuario.id).filter(and_(utilizavel, ultimo_login.c.ultimo >= limite_30d)).label("ativos_30d"),
                func.max(ultimo_login.c.ultimo).label("ultimo_acesso"),
            )
            .select_from(Usuario)
            .outerjoin(ultimo_login, ultimo_login.c.usuario_id == Usuario.id)
            .where(Usuario.is_system_account.is_(False), Usuario.status != "arquivado")
            .group_by(Usuario.empresa_id)
        )
        return {
            linha.empresa_id: UsuariosAgregados(
                cadastrados=linha.cadastrados,
                usuarios=linha.usuarios,
                gestores=linha.gestores,
                ja_acessaram=linha.ja_acessaram,
                ativos_7d=linha.ativos_7d,
                ativos_30d=linha.ativos_30d,
                ultimo_acesso=linha.ultimo_acesso,
            )
            for linha in db.execute(consulta)
        }

    def projetos_por_empresa(self, db: Session) -> dict[str, int]:
        consulta = select(Projeto.empresa_id, func.count(Projeto.id)).where(Projeto.status != "arquivado").group_by(Projeto.empresa_id)
        return {empresa_id: total for empresa_id, total in db.execute(consulta)}

    def demandas_por_empresa(self, db: Session) -> dict[str, int]:
        consulta = select(Demanda.empresa_id, func.count(Demanda.id)).where(Demanda.status != "arquivada").group_by(Demanda.empresa_id)
        return {empresa_id: total for empresa_id, total in db.execute(consulta)}
