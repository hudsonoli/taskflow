# Acesso multiempresa por slug (Fase 2)

Cada empresa tem entrada própria, resolvida pelo **slug público** (`empresas.slug`, criado na Fase 1B):

| Rota | Função |
| --- | --- |
| `/e/<slug>/login` | login (local e Google) da empresa do slug |
| `/e/<slug>/esqueci-senha` | pedido de redefinição; o e-mail volta ao **mesmo** tenant |
| `/e/<slug>/redefinir-senha` | confirmação com o token do e-mail (o token precisa ser da empresa do slug) |
| `/e/<slug>` | redireciona para o login da empresa |
| `/login`, `/esqueci-senha`, `/redefinir-senha` | **legado**: usam `EMPRESA_CODIGO` (empresa padrão do servidor, hoje DEMO) |

Slug inexistente, reservado, malformado ou de empresa **inativa** mostram a mesma tela ("Empresa não encontrada ou
indisponível"), com identidade neutra; login, reset e Google são recusados com as mensagens genéricas de sempre.

## Regras de segurança

- **O slug nunca autoriza dados.** Ele só diz a qual empresa pertence uma tela *pública* (marca, login, reset). Depois do
  login a fonte de verdade é a sessão no backend (`current_user.empresa_id`); nenhuma rota autenticada lê slug, cookie visual
  ou header para decidir tenant. Navegar para `/e/outra/...` com uma sessão aberta não muda empresa, RBAC, escopo nem dados.
- Backend: login, Google, reset (pedido e confirmação) aceitam **exatamente um** de `empresaCodigo` / `empresaSlug`
  (`AuthService._resolver_empresa`). O link de reset por slug é `APP_PUBLIC_URL` + `/e/<slug>/redefinir-senha#token=…`
  (uma única `APP_PUBLIC_URL`; o slug vai no caminho). Token de A na URL de B → "link inválido", sem consumir o token.
- BFF: o slug vem do corpo (a chave pública da URL) e é validado; slug presente porém inválido **não** cai no legado.
  `EMPRESA_CODIGO` só existe como fallback do acesso legado. O navegador nunca escolhe `empresaCodigo`.
- Branding público: `GET /publico/empresas/{slug}/branding` e `/branding/logo` devolvem só logo, cores, tema e nome de
  exibição (nada de id, documento, usuários ou configuração). O logo sai com MIME canônico e `nosniff`.
- Cache de branding do SSR é **por tenant** (chave `slug:<slug>` / `legado:<codigo>`; TTL curto, teto de entradas, limpo
  quando a personalização muda). Sem Redis.
- `proxy.ts` traduz o caminho em headers internos (`x-tf-tenant-slug`, `x-tf-contexto`) e **apaga** os que vierem do navegador.
- Cookie visual `tf_tenant_slug` (HttpOnly, não sensível): reconciliado com a empresa da **sessão** (`/auth/me`), usado só
  para escolher a marca de quem está logado e para voltar ao login da empresa certa; removido no logout.
- O console `/plataforma` mantém a identidade da plataforma (marca neutra); "Empresa em foco" é só um rótulo.
- Logout tenant remove `tf_session`, `tf_tenant_slug`, `tf_platform` (a sessão de plataforma deriva da tenant) e o cookie de
  tema; "encerrar só plataforma" remove apenas `tf_platform`.

## Segundo tenant

Pode usar **login local** (e-mail + senha, reset por e-mail). Limitações conhecidas, fora desta fase:

- `GOOGLE_WORKSPACE_ALLOWED_DOMAIN` é configuração **global** (não há domínio por empresa).
- `google_sub` é **globalmente único**: a mesma conta Google não pode ser vinculada a duas empresas.
- O SMTP/e-mail transacional é por empresa (`ConfiguracaoEmail`); sem configuração, o reset não envia.

Testes: backend `tests/test_acesso_por_slug.py`; frontend `npm run test:multitenant`.
