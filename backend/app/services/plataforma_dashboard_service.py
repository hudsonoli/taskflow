"""Dashboard da Administração da Plataforma: composição das métricas agregadas, resumo global e "Precisa de atenção".

Sem tracking novo e sem migration: usa só dados existentes (usuarios, eventos `auth.login_sucesso`, projetos, demandas).
Quatro consultas agregadas (ver `PlataformaDashboardRepository`); o resto é aritmética em memória.

Definições
- Usuário **cadastrado**: humano (não é conta de sistema) não arquivado — inclui inativos/bloqueados.
- Usuário **utilizável** (o "Usuários" da Dashboard): humano ativo com acesso ao sistema. Adoção (já acessaram, nunca
  acessaram, ativos) e Gestores contam SOMENTE utilizáveis; `nunca acessaram = utilizáveis − já acessaram`.
- **Já acessou**: há ao menos um login bem-sucedido (`auth.login_sucesso`, e-mail/senha ou Google).
- **Ativo 7d / 30d**: último login dentro da janela. NÃO é presença em tempo real ("online").
- **Último acesso**: último login de qualquer humano da empresa. Só o login é rastreado; por isso não se chama "atividade".
- Resumo global: usuários e adoção das empresas ATIVAS (empresa inativa não autentica); a tabela mostra todas as empresas.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.repositories.plataforma_dashboard_repository import PlataformaDashboardRepository, UsuariosAgregados
from app.schemas.plataforma_dashboard import (
    DashboardAtencaoRead,
    DashboardEmpresaRead,
    DashboardResumoRead,
    PlataformaDashboardRead,
)

JANELA_7D = timedelta(days=7)
JANELA_30D = timedelta(days=30)
# Empresa recém-criada não é "sem acesso": dá-se um prazo antes de avisar.
CARENCIA_EMPRESA_NOVA = timedelta(days=7)


class PlataformaDashboardService:
    def __init__(self, repository: PlataformaDashboardRepository | None = None) -> None:
        self.repository = repository or PlataformaDashboardRepository()

    def montar(self, db: Session, *, agora: datetime | None = None) -> PlataformaDashboardRead:
        agora = agora or datetime.now(timezone.utc)
        empresas = self.repository.listar_empresas(db)
        usuarios = self.repository.usuarios_por_empresa(db, limite_7d=agora - JANELA_7D, limite_30d=agora - JANELA_30D)
        projetos = self.repository.projetos_por_empresa(db)
        demandas = self.repository.demandas_por_empresa(db)

        linhas: list[DashboardEmpresaRead] = []
        for empresa in empresas:
            u = usuarios.get(empresa.id, UsuariosAgregados())
            linhas.append(
                DashboardEmpresaRead(
                    id=empresa.id,
                    nome=empresa.nome,
                    nomeFantasia=empresa.nome_fantasia,
                    slug=empresa.slug,
                    status=empresa.status,
                    createdAt=empresa.created_at,
                    usuarios=u.usuarios,
                    cadastrados=u.cadastrados,
                    jaAcessaram=u.ja_acessaram,
                    nuncaAcessaram=u.usuarios - u.ja_acessaram,
                    ativos7d=u.ativos_7d,
                    ativos30d=u.ativos_30d,
                    gestores=u.gestores,
                    ultimoAcesso=u.ultimo_acesso,
                    projetos=projetos.get(empresa.id, 0),
                    demandas=demandas.get(empresa.id, 0),
                )
            )

        ativas = [linha for linha in linhas if linha.status == "ativa"]
        resumo = DashboardResumoRead(
            empresasTotal=len(linhas),
            empresasAtivas=len(ativas),
            usuarios=sum(linha.usuarios for linha in ativas),
            cadastrados=sum(linha.cadastrados for linha in ativas),
            jaAcessaram=sum(linha.ja_acessaram for linha in ativas),
            nuncaAcessaram=sum(linha.nunca_acessaram for linha in ativas),
            ativos7d=sum(linha.ativos_7d for linha in ativas),
            ativos30d=sum(linha.ativos_30d for linha in ativas),
            gestores=sum(linha.gestores for linha in ativas),
        )
        return PlataformaDashboardRead(geradoEm=agora, resumo=resumo, empresas=linhas, atencoes=self._atencoes(ativas, agora))

    @staticmethod
    def _atencoes(ativas: list[DashboardEmpresaRead], agora: datetime) -> list[DashboardAtencaoRead]:
        """Só regras objetivas, sobre empresas ATIVAS: sem Gestor; usuários que nunca acessaram; sem nenhum acesso nos
        últimos 30 dias (com ao menos um usuário e depois da carência de empresa nova)."""
        resultado: list[DashboardAtencaoRead] = []
        for linha in ativas:
            if linha.gestores == 0:
                resultado.append(
                    DashboardAtencaoRead(
                        tipo="sem_gestor", severidade="aviso", empresaId=linha.id, empresaNome=linha.nome,
                        mensagem="Empresa ativa sem Gestor.",
                    )
                )
            if linha.nunca_acessaram > 0:
                resultado.append(
                    DashboardAtencaoRead(
                        tipo="nunca_acessaram", severidade="info", empresaId=linha.id, empresaNome=linha.nome,
                        quantidade=linha.nunca_acessaram,
                        mensagem=f"{linha.nunca_acessaram} {'usuário nunca acessou' if linha.nunca_acessaram == 1 else 'usuários nunca acessaram'}.",
                    )
                )
            criada_ha = agora - linha.created_at if linha.created_at.tzinfo else agora.replace(tzinfo=None) - linha.created_at
            if linha.usuarios > 0 and linha.ativos_30d == 0 and criada_ha > CARENCIA_EMPRESA_NOVA:
                resultado.append(
                    DashboardAtencaoRead(
                        tipo="sem_acesso_30d", severidade="aviso", empresaId=linha.id, empresaNome=linha.nome,
                        mensagem="Nenhum acesso nos últimos 30 dias.",
                    )
                )
        ordem = {"aviso": 0, "info": 1}
        return sorted(resultado, key=lambda a: (ordem[a.severidade], a.empresa_nome.lower(), a.tipo))
