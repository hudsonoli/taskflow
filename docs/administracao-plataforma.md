# Administração da Plataforma (Fase 1B)

A **Administração da Plataforma** é a camada que cria e mantém as empresas que existem no TaskFloww. É uma autoridade
**separada do RBAC tenant**: quem a exerce não ganha perfil novo dentro de nenhuma empresa, e nenhum perfil tenant
(`admin`, `gestor`, `operador`) dá acesso a ela.

> **SEGUNDO_TENANT_GO_LIVE_BLOQUEADO** — criar uma empresa e o primeiro Gestor dela já funciona por esta API/UI, mas o
> **login do produto ainda resolve a empresa por `EMPRESA_CODIGO`** (uma única empresa por instalação). Login, reset de
> senha e branding das telas públicas por slug (`/e/<slug>/login`) são da **Fase 2**. Enquanto isso, **não** operar um
> segundo cliente real: os testes e a validação em DEV usam empresas sintéticas e **não** fazem login web nelas.

## Modelo

| Onde | O quê |
| --- | --- |
| `empresas.slug` | `NOT NULL`, único, 3–40, `[a-z0-9-]`, sem hífen nas pontas, fora de `plataforma, api, login, logout, admin, suporte`. CHECKs no banco (`ck_empresas_slug_formato`, `ck_empresas_slug_reservado`) + validação amigável em `app/core/empresa_slug.py`. Backfill da migration: `DEMO` → `demo`. |
| `empresas.nome_fantasia` | opcional |
| `administradores_plataforma` | uma linha por usuário (`UNIQUE usuario_id`), `ativo`, `criado_em`, `criado_por_usuario_id`, `revogado_em`, `revogado_por_usuario_id`. `CHECK (ativo OR revogado_em IS NOT NULL)`. A autoridade é **registrada e revogada, nunca apagada**. |

Migration `0041_plataforma_empresas` (`c5b2e8a91d47`, depois de `9a3d4e6f1b28`): aditiva e reversível; **não** cria
administrador e **não** altera `usuarios`, `codigo_interno`, personalização nem arquivos de logo.

## Quem é Administrador da Plataforma

Só o CLI idempotente concede (e revoga) a autoridade — **nenhum e-mail é hardcoded** e **nenhuma decisão em runtime usa
e-mail, `perfil_base` ou `is_system_account`**:

```bash
python -m app.cli.seed_platform_admin --email <email> [--empresa-codigo <codigo>]
PLATFORM_ADMIN_EMAIL=<email> python -m app.cli.seed_platform_admin
python -m app.cli.seed_platform_admin --email <email> --revogar
```

O e-mail só localiza o usuário **no bootstrap**. O CLI exige usuário existente, ativo e com acesso ao sistema, não altera
a linha dele e não imprime segredo.

## Sessão e isolamento de tokens

1. O usuário entra normalmente (sessão tenant, cookie `tf_session`).
2. `GET /plataforma/acesso` (sessão tenant) diz à UI se a entrada do menu deve existir.
3. `POST /plataforma/sessao` (sessão tenant) troca por um token `tipo="plataforma"` (claims `sub`, `adm`, `iat`, `exp`,
   `tipo`; TTL `PLATFORM_TOKEN_EXPIRE_MINUTES`, padrão 30). O BFF o guarda no cookie **`tf_platform`**: HttpOnly, Secure em
   produção, SameSite estrito, `Path=/api/plataforma`. O navegador nunca lê o token.
4. `require_platform_admin` aceita **só** esse token e **rechecka a linha ativa no banco a cada requisição** — revogar a
   autoridade (ou inativar o usuário) vale na requisição seguinte, mesmo com token dentro do prazo.

Isolamento nos dois sentidos: `get_current_user`/`decode_access_token` continuam exigindo `tipo="access"` (token de
plataforma não entra em rota tenant) e `decode_platform_token` exige `tipo="plataforma"` (token tenant não entra em
`/plataforma`). Sair do sistema apaga os dois cookies.

## API (`/plataforma/*`)

`GET /acesso`, `POST /sessao` (sessão tenant) · `GET /me` · `GET|POST /empresas` · `GET|PATCH /empresas/{id}` ·
`POST /empresas/{id}/inativar|reativar` · `GET|PATCH|DELETE /empresas/{id}/personalizacao` ·
`GET|POST|DELETE /empresas/{id}/personalizacao/logo` · `GET /empresas/{id}/usuarios` · `POST /empresas/{id}/gestores`.

- **Não há DELETE de empresa** (empresa nunca é apagada); só inativar/reativar. A empresa que hospeda um Administrador da
  Plataforma ativo **não pode ser inativada**.
- Só a Plataforma altera `codigoInterno` e `slug`. O tenant (`/empresas`) é somente leitura da própria empresa (`PATCH`,
  `POST`, inativar e reativar respondem 403).
- Branding reaproveita `ConfiguracaoPersonalizacaoService` (mesmos validadores: PNG/GIF por bytes, 320×132, ≤ 2 MB,
  cores `#RRGGBB`, tema). Storage por empresa: `uploads/personalizacao/<empresa_id>/`.
- `POST /empresas/{id}/gestores`: perfil **sempre** `gestor` (nunca `admin`; o corpo é `{nome, email}` e rejeita campos
  extras), senha temporária gerada no servidor, `deve_alterar_senha=true`. A senha existe **apenas** na resposta da
  criação — nunca em log, evento (`Evento.payload`), listagem ou consulta posterior.

## Auditoria e privacidade

Toda ação de plataforma reaproveita os eventos existentes (`empresa.criada|alterada|inativada|reativada`) e dois novos
(`empresa.personalizacao_alterada`, `empresa.gestor_criado`), com `usuario_id` do ator. Não há colunas
`ator_plataforma_admin_id`/`sessao_suporte_id`. Como o ator é conta de sistema, o tenant **não vê** esses eventos
(filtro da Fase 1A). Arquivos (`GET /arquivos`, anexos de demanda) e comentários também mascaram a conta de sistema como
**"Sistema"** na leitura (por `is_system_account`, nunca por nome/e-mail).

## Fora de escopo (não existe nesta fase)

Suporte/impersonação, `tf_support`, `/e/<slug>/login`, remoção de `EMPRESA_CODIGO`, mudanças em login/reset/Google,
remoção de `admin` do CHECK de perfis, renomear `operador`.

## Frontend

`/plataforma` (início), `/plataforma/empresas` (lista + "Nova empresa") e `/plataforma/empresas/[id]` (abas Dados,
Personalização, Usuários; "Criar primeiro Gestor" com modal de senha única). A entrada fica no **menu do perfil** e só
aparece se `GET /plataforma/acesso` confirmar. "Suporte" é apenas um marcador "Em breve". O chip "🏢 Empresa em foco" é um
rótulo de contexto: não troca sessão nem empresa.

Testes: backend `tests/test_plataforma.py`, `tests/test_migration_0041_plataforma.py`,
`tests/test_privacidade_arquivos_comentarios.py`; frontend `npm run test:plataforma`.
