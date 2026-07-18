# Autenticação frontend-backend

## Escopo

Esta fundação implementa sessão autenticada no frontend por BFF same-origin e uma camada compartilhada de identidade no React. Ela não cria tela de login, não protege páginas, não redireciona usuários, não substitui integralmente `conta-mock` e não implementa refresh token, login Google ou cadastro livre.

## Fluxo

```text
Navegador
  -> POST /api/auth/login (Next Route Handler)
  -> POST /auth/login (FastAPI pela rede Docker)
  <- accessToken somente no servidor Next
  -> GET /auth/me com Bearer server-side
  <- identidade validada pelo FastAPI
  <- cookie HttpOnly + AuthCurrentUser, sem JWT no response
```

As chamadas subsequentes usam o cookie apenas no Next. O BFF lê o JWT, adiciona `Authorization: Bearer` e chama um endpoint FastAPI previamente permitido. Não existe proxy genérico.

## Endpoints BFF

| Método | Endpoint | Comportamento |
| --- | --- | --- |
| POST | `/api/auth/login` | Valida Origin e JSON, autentica, confirma identidade em `/auth/me` e cria o cookie. |
| GET | `/api/auth/me` | Retorna somente a identidade atual; limpa o cookie se o backend responder 401. |
| POST | `/api/auth/logout` | Valida Origin e remove o cookie local. |
| POST | `/api/auth/alterar-senha` | Valida Origin e JSON, encaminha somente o payload permitido com Bearer server-side. |

O cliente backend possui allowlist fechada para `/auth/login`, `/auth/me` e `/auth/alterar-senha`. Há timeout explícito de cinco segundos. Falhas de rede, timeout, JSON inválido e status upstream são convertidos para erros tipados, sem stack trace, URL interna, senha ou token.

## Tipos

Os tipos em `frontend/src/types/auth.ts` refletem os aliases JSON reais:

- `AuthLoginRequest`: `empresaCodigo`, `email`, `senha`;
- `AuthLoginBackendResponse`: `accessToken`, `tokenType`;
- `AuthCurrentUser`: `usuarioId`, `empresaId`, `nome`, `perfilBase`, `acessoSistema`, `status`;
- `AuthChangePasswordRequest`: `senhaAtual`, `novaSenha`, `confirmacaoSenha`;
- `AuthErrorResponse`: envelope seguro `error.code` e `error.message`.

Não existe tipo de refresh token.

## Identidade compartilhada no navegador

O `AuthProvider`, instalado no layout raiz, executa uma única busca inicial em `GET /api/auth/me`; chamadas concorrentes dessa carga inicial são deduplicadas. Operações posteriores recebem uma sequência lógica, e somente o resultado da operação mais recente pode atualizar o estado. O estado é uma união discriminada com `loading`, `authenticated`, `unauthenticated` e `error`; não existem booleanos independentes para representar a sessão.

O hook `useAuth()` expõe somente `status`, `user`, `refresh()` e `logout()`. O Context contém `AuthCurrentUser`, nunca o JWT. Não há proteção de páginas, `RequireAuth`, redirecionamento ou tratamento de rotas nesta etapa.

O cliente browser em `src/lib/auth/client.ts` usa exclusivamente `GET /api/auth/me` e `POST /api/auth/logout`, sempre com `credentials: "same-origin"` e `cache: "no-store"`. Ele não envia `Authorization`, não conhece a URL interna do FastAPI e não depende de Cloudflare, Nginx Proxy Manager ou headers encaminhados.

O adaptador temporário converte `AuthCurrentUser` apenas em `id`, `nome`, `perfilBase` e `perfilLabel`. UserMenu e Dashboard usam a identidade real quando disponível e preservam o mock como fallback enquanto não existe login nem proteção. Avatar, departamento, e-mail, preferências, notificações, último acesso e IP continuam mockados até a etapa de migração de perfil.

Na alteração de senha, um 401 dispara `refresh()` para que o Provider confirme o estado `unauthenticated`. Um 204 não recarrega a identidade.

## Helper de cookie

`src/lib/auth/cookie.ts` centraliza o nome esperado por ambiente e é consumido pela política server-side de sessão. Ele não lê o cookie no navegador e poderá ser reutilizado pela futura camada Proxy e seus testes.

## Cookie

| Ambiente | Nome | Secure | Demais flags |
| --- | --- | --- | --- |
| Desenvolvimento HTTP | `taskfloww_session` | não | HttpOnly, SameSite=Lax, Path=/ |
| Produção HTTPS | `__Host-taskfloww_session` | sim | HttpOnly, SameSite=Lax, Path=/, sem Domain |

Criação e remoção usam a mesma política e o mesmo nome por ambiente. A remoção usa `Max-Age=0`. O `Max-Age` de criação vem de `TASKFLOWW_SESSION_MAX_AGE_SECONDS` e deve permanecer coerente com `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` do backend. O frontend não decodifica nem valida a assinatura do JWT; `/auth/me` é a fonte de verdade.

## Variáveis de ambiente

### Backend somente

- `AUTH_SECRET_KEY`: obrigatória, forte e exclusiva por implantação;
- `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES`: duração do JWT, padrão operacional de 30 minutos.

### Frontend somente

- `TASKFLOWW_API_INTERNAL_URL`: URL do FastAPI na rede Docker, sem prefixo `NEXT_PUBLIC_`;
- `TASKFLOWW_AUTH_ALLOWED_ORIGINS`: lista separada por vírgula de origins exatos;
- `TASKFLOWW_SESSION_MAX_AGE_SECONDS`: duração do cookie em segundos.

`AUTH_SECRET_KEY` nunca é entregue ao Next. O Next não assina, emite ou valida JWT. O `.env.example` contém apenas placeholders e referências de implantação.

## Origin e CSRF

Todas as mutações exigem o header `Origin`. Requests sem Origin são rejeitados com 403. A origem precisa:

1. estar na allowlist configurada;
2. corresponder à URL efetiva, ao `Host`, ou ao par `X-Forwarded-Host`/`X-Forwarded-Proto`;
3. no caso de headers encaminhados, reconstruir uma origem já presente na allowlist.

Headers encaminhados múltiplos ou malformados não são aceitos. A premissa de produção é que o Nginx Proxy Manager preserve `Host`, `X-Forwarded-Host` e `X-Forwarded-Proto`, e que a allowlist contenha exclusivamente a origem pública HTTPS. SameSite=Lax reduz exposição, mas não substitui essa validação de Origin.

## Expiração, 401 e logout

O backend não oferece refresh token. Quando o FastAPI devolve 401 em `/auth/me` ou na alteração de senha, o BFF remove o cookie. O logout atual remove apenas o cookie: não há revogação server-side, portanto um JWT previamente extraído permanece válido até expirar.

## Erros

O BFF padroniza erros para 400, 401, 403, 415, 422, 429, 500, 502 e 504. Respostas do FastAPI não são repassadas diretamente. Credenciais inválidas recebem mensagem genérica; problemas internos não revelam a URL Docker nem detalhes de exceção.

## Fronteira server-only

`backend.ts`, `config.ts`, `session.ts`, `origin.ts` e `errors.ts` importam o marcador oficial `server-only`. O build do Next impede que esses módulos sejam importados por Client Components. O JWT não é armazenado em React, `localStorage` ou `sessionStorage`.

## Interceptação futura

O projeto usa Next.js 16.2.10. Nessa versão, `middleware.ts` foi renomeado e depreciado; a convenção correta para a fase de proteção de páginas é `frontend/src/proxy.ts`. Esse arquivo não faz parte desta etapa e não deve ser a única camada de validação da sessão.

## Google futuro

A mesma fronteira BFF/cookie poderá receber um callback OAuth server-side. A evolução deve exigir vínculo ou autorização prévia pelo Gestor, validar `state`, `nonce` e PKCE, e nunca criar usuário livremente. A elegibilidade de usuário e empresa continuará sendo validada pelo backend antes de emitir a sessão.

## Arquivos desta etapa

A fundação contém tipos e helpers server-only, quatro Route Handlers e testes nativos em `frontend/tests/auth/`. A etapa de identidade compartilhada acrescenta tipos de sessão, cliente browser, Context, Provider, hook, adaptador e helper de cookie, sem alterar backend ou infraestrutura.

## Próximos passos

1. Criar a tela visual de login consumindo exclusivamente `/api/auth/login`.
2. Adicionar `src/proxy.ts` em etapa separada para a barreira rápida de páginas.
3. Migrar Sidebar, Perfil e permissões visuais restantes de `conta-mock`.
4. Avaliar revogação server-side e refresh token em etapa própria.
5. Implementar vínculo Google pré-autorizado em etapa futura.
