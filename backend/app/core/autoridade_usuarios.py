"""Autoridade tenant sobre Usuários — quem pode atribuir/administrar qual `perfil_base` (Fase 1A).

## Por que existe

Até a Fase 1A só `admin` administrava usuários, e a API aceitava qualquer `perfil_base` de quem
chamava. Com o modelo Plataforma → Gestor → Usuário, o **Gestor** passa a ser a autoridade máxima da
empresa, mas só sobre **Usuários** (`perfil_base="operador"`). Gestor administrar outro Gestor (ou o
admin legado) seria uma escalada lateral — e um gestor mal-intencionado poderia se perpetuar e
remover os pares. Estas regras vivem no BACKEND (service e rotas de permissões); a UI só espelha.

## O modelo

- `admin` é LEGADO: continua válido internamente (CHECK do banco, bootstrap, conta de sistema), mas a
  API normal NUNCA atribui `admin` — criar ou promover alguém a admin é recusado já no schema (422).
- Admin legado, como ator, administra Gestor e Usuário (é o que permite tocar a DEMO até existir
  administrador da plataforma). Nunca promove ninguém a admin.
- Gestor administra SOMENTE Usuário (`operador`).
- Qualquer outro perfil que receba `usuarios.*` por override (um Usuário com concessão) é tratado como
  o Gestor: só administra Usuário, e nunca atribui um perfil acima do dele. Uma concessão não é
  hierarquia.
- Mexer em si mesmo: suspender, bloquear, excluir e trocar o próprio perfil são recusados para todo
  ator — ninguém se remove administrativamente por um caminho indireto.

Funções puras (sem banco), para ficarem testáveis e reaproveitáveis nas rotas.
"""

from __future__ import annotations

from app.core.permissoes import PERFIL_ADMIN, PERFIL_GESTOR, PERFIL_OPERADOR

# O que a API normal pode ATRIBUIR a alguém (criar/promover). Nunca `admin`.
PERFIS_ATRIBUIVEIS_POR_ADMIN: frozenset[str] = frozenset({PERFIL_GESTOR, PERFIL_OPERADOR})
PERFIS_ATRIBUIVEIS_POR_DEMAIS: frozenset[str] = frozenset({PERFIL_OPERADOR})

# Sobre quem o ator pode operar (editar, suspender, bloquear, excluir, restaurar, permissões).
PERFIS_ALVO_DO_ADMIN: frozenset[str] = frozenset({PERFIL_ADMIN, PERFIL_GESTOR, PERFIL_OPERADOR})
PERFIS_ALVO_DOS_DEMAIS: frozenset[str] = frozenset({PERFIL_OPERADOR})

MENSAGEM_ALVO_NAO_PERMITIDO = "Seu perfil só administra Usuários."
MENSAGEM_PERFIL_NAO_PERMITIDO = "Seu perfil só pode atribuir o perfil Usuário."
MENSAGEM_AUTO_ADMINISTRACAO = "Você não pode alterar a própria situação ou o próprio perfil."


class AutoridadeUsuarioError(ValueError):
    """O ator não tem autoridade sobre este alvo/perfil (vira 403 nas rotas)."""


def perfis_atribuiveis_por(perfil_ator: str) -> frozenset[str]:
    return PERFIS_ATRIBUIVEIS_POR_ADMIN if perfil_ator == PERFIL_ADMIN else PERFIS_ATRIBUIVEIS_POR_DEMAIS


def perfis_alvo_de(perfil_ator: str) -> frozenset[str]:
    return PERFIS_ALVO_DO_ADMIN if perfil_ator == PERFIL_ADMIN else PERFIS_ALVO_DOS_DEMAIS


def ensure_pode_atribuir_perfil(perfil_ator: str, perfil_novo: str) -> None:
    """Criar ou trocar o perfil de alguém para `perfil_novo`."""
    if perfil_novo not in perfis_atribuiveis_por(perfil_ator):
        raise AutoridadeUsuarioError(MENSAGEM_PERFIL_NAO_PERMITIDO)


def ensure_pode_administrar_alvo(perfil_ator: str, perfil_alvo: str) -> None:
    """Operar sobre um usuário existente cujo perfil atual é `perfil_alvo`."""
    if perfil_alvo not in perfis_alvo_de(perfil_ator):
        raise AutoridadeUsuarioError(MENSAGEM_ALVO_NAO_PERMITIDO)


def ensure_nao_e_auto_administracao(ator_id: str, alvo_id: str) -> None:
    if ator_id == alvo_id:
        raise AutoridadeUsuarioError(MENSAGEM_AUTO_ADMINISTRACAO)
