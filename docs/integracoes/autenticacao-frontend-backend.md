# Autenticação frontend-backend

## Escopo

Esta fundação implementa sessão autenticada no frontend por BFF same-origin. Ela não cria tela de login, não protege páginas, não substitui `conta-mock` e não implementa refresh token, login Google ou cadastro livre.

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

Foram adicionados tipos, cinco helpers server-only, quatro Route Handlers, testes nativos em `frontend/tests/auth/` e este documento. Os Compose receberam somente as variáveis pertencentes a cada serviço.

## Próximos passos

1. Criar a tela visual de login consumindo exclusivamente `/api/auth/login`.
2. Adicionar `src/proxy.ts` e validação server-side para rotas protegidas.
3. Migrar Shell, Header, Sidebar, Perfil e permissões visuais de `conta-mock` para `/api/auth/me`.
4. Avaliar revogação server-side e refresh token em etapa própria.
5. Implementar vínculo Google pré-autorizado em etapa futura.
