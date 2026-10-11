# Acesso multiempresa por slug (Fase 2 + URL canônica da Fase 9D + Gestão/TaskFlow da Fase 10A)

## Nome do produto e identidade (Fase 10A)

- O produto se chama **TaskFlow** (nunca "TaskFloww"). Dentro de `/e/<slug>/...` a identidade PRINCIPAL é a da empresa contratante (nome + logo vindos do servidor
  pelo slug); o produto é secundário. **Título da aba:** tenant `<Empresa> | TaskFlow`; Gestão `Gestão | TaskFlow`; telas neutras `TaskFlow`. Sem logo, o cabeçalho
  mostra o nome da empresa (nunca inventa logo). Na Gestão a marca efetiva é sempre a do produto (não herda o último tenant).
- A renomeação é **só de nome visível**: contêineres, volumes, network, diretórios (`/docker/taskflow`), pacote técnico, tabelas, event types e ids de migration
  seguem como estão (P3 de nomenclatura técnica).
- Slugs reservados (validação da aplicação): `plataforma, gestao, api, e, aprovacao, login, logout, admin, suporte`. O CHECK do banco (migration 0041) ficou com a
  lista antiga — é só a rede de segurança; alinhá-lo é um P3 para uma futura migration.

## URL canônica (Fase 9D)

**Toda interface de uma empresa vive em `/e/<slug>/...`** (BOX = `/e/boxcom/...`). O slug na URL é a **única** fonte do contexto de empresa no
navegador: não há empresa padrão, `EMPRESA_CODIGO` nem cookie decidindo a empresa.

| Endereço | Resultado |
| --- | --- |
| `/` | 404 neutro (nunca abre a BOX, nunca redireciona, sem seletor de empresas) |
| `/login`, `/esqueci-senha`, `/redefinir-senha`, `/tarefas`, `/meu-dia`, `/projetos`, `/pauta`, `/arquivos`, `/relatorios`, `/trafego`, `/configuracoes/**`, `/aprovacao`… | 404 neutro (não existem mais) |
| `/e/<slug>/login` | login da empresa; depois do login a navegação segue em `/e/<slug>/...` |
| `/e/<slug>/<modulo>` | módulo da empresa (`meu-dia`, `tarefas`, `projetos`, `pauta`, `arquivos`, `relatorios`, `trafego`, `meu-departamento`, `minhas-demandas`, `notificacoes`, `minha-conta`, `configuracoes/**`) |
| `/e/<slug>` | entra na home da empresa (o `AppShell` leva ao login se não houver sessão da própria empresa); slug inválido = 404 |
| `/gestao/**` | Gestão da plataforma (Fase 10A), **fora** dos tenants: sem slug, sem empresa implícita, identidade do produto TaskFlow |
| `/plataforma/**` | **404** — a interface antiga deixou de existir (sem redirect; URL canônica única) |
| `/api/**` | BFF e APIs: a empresa vem da sessão/token, não da URL |

Catálogo público mínimo (sem sessão) no `AppShell`: `/e/<slug>/login`, `/e/<slug>/esqueci-senha`, `/e/<slug>/redefinir-senha` e
`/e/<slug>/aprovacao` (Portal Externo). Nenhum outro `/e/<slug>/...` é público; `/e/<slug>/trocar-senha-inicial` é tela nua mas exige sessão.

- **Helpers:** `caminhoDoTenant(slug, caminho)` (`lib/tenant.ts`) e o hook `useTenantPath()` montam todo link/`router.push`/`redirect` interno; sem slug
  válido devolvem `/` (404 neutro). Os menus (`TopNav`, Configurações) guardam caminhos relativos do módulo e aplicam `tp()` na renderização.
- **Sessão × slug:** se a sessão é de outra empresa que a da URL, o `AppShell` mostra "Esta sessão é de outra empresa" (sem carregar nada da empresa da URL,
  sem nomear nenhuma) com "Ir para a minha empresa" e "Sair". A URL **nunca** troca a empresa da sessão. O backend continua tenant-safe por `current_user.empresa_id`.
- **Logout** volta a `/e/<slug>/login` (slug da URL/sessão). **Reset de senha:** o e-mail **sempre** leva `APP_PUBLIC_URL/e/<slug>/redefinir-senha#token=…`
  (o slug não substitui a validação do token).
- **Google:** o login usa o botão Google Identity na própria tela `/e/<slug>/login` (id_token no navegador, sem redirect OAuth); o BFF exige o slug.
- **`EMPRESA_CODIGO`** saiu do frontend (login, Google, reset, branding, logo, layout). Permanece no backend/CLI apenas para o acesso legado por `empresaCodigo`
  da API e seeds — o navegador não o usa. O cookie visual `tf_tenant_slug` foi aposentado (o logout ainda o apaga para limpar navegadores antigos).

## Entrada por slug (Fase 2)

Cada empresa tem entrada própria, resolvida pelo **slug público** (`empresas.slug`, criado na Fase 1B):

| Rota | Função |
| --- | --- |
| `/e/<slug>/login` | login (local e Google) da empresa do slug |
| `/e/<slug>/esqueci-senha` | pedido de redefinição; o e-mail volta ao **mesmo** tenant |
| `/e/<slug>/redefinir-senha` | confirmação com o token do e-mail (o token precisa ser da empresa do slug) |
| `/e/<slug>` | entra na home da empresa (veja acima) |

Slug inexistente, reservado, malformado ou de empresa **inativa** mostram a mesma tela ("Empresa não encontrada ou
indisponível"), com identidade neutra; login, reset e Google são recusados com as mensagens genéricas de sempre.

## Regras de segurança

- **O slug nunca autoriza dados.** Ele só diz a qual empresa pertence uma tela *pública* (marca, login, reset). Depois do
  login a fonte de verdade é a sessão no backend (`current_user.empresa_id`); nenhuma rota autenticada lê slug, cookie visual
  ou header para decidir tenant. Navegar para `/e/outra/...` com uma sessão aberta não muda empresa, RBAC, escopo nem dados.
- Backend: login, Google, reset (pedido e confirmação) aceitam **exatamente um** de `empresaCodigo` / `empresaSlug`
  (`AuthService._resolver_empresa`). O link de reset por slug é `APP_PUBLIC_URL` + `/e/<slug>/redefinir-senha#token=…`
  (uma única `APP_PUBLIC_URL`; o slug vai no caminho). Token de A na URL de B → "link inválido", sem consumir o token.
- BFF: o slug vem do corpo (a chave pública da URL) e é **obrigatório**; sem slug (ou inválido) a resposta é a genérica de sempre, sem empresa padrão.
  O navegador nunca escolhe `empresaCodigo`.
- Branding público: `GET /publico/empresas/{slug}/branding` e `/branding/logo` devolvem só logo, cores, tema e nome de
  exibição (nada de id, documento, usuários ou configuração). O logo sai com MIME canônico e `nosniff`.
- Cache de branding do SSR é **por tenant** (chave `slug:<slug>`; TTL curto, teto de entradas, limpo
  quando a personalização muda). Sem Redis.
- `proxy.ts` traduz o caminho em headers internos (`x-tf-tenant-slug`, `x-tf-contexto`) e **apaga** os que vierem do navegador.
- Não há cookie visual de tenant: a marca vem do slug da rota; fora de `/e/<slug>` a identidade é a neutra do TaskFloww.
- A Gestão (`/gestao`) mantém a identidade do produto TaskFlow (marca neutra, nunca a de uma empresa); "Empresa em foco" é só um rótulo e não cria sessão tenant.
- Logout tenant remove `tf_session`, `tf_platform` (a sessão de plataforma deriva da tenant) e o cookie de
  tema; "encerrar só plataforma" remove apenas `tf_platform`.

## Segundo tenant

Pode usar **login local** (e-mail + senha, reset por e-mail). Limitações conhecidas, fora desta fase:

- `GOOGLE_WORKSPACE_ALLOWED_DOMAIN` é configuração **global** (não há domínio por empresa).
- `google_sub` é **globalmente único**: a mesma conta Google não pode ser vinculada a duas empresas.
- O SMTP/e-mail transacional é por empresa (`ConfiguracaoEmail`); sem configuração, o reset não envia.

Testes: backend `tests/test_acesso_por_slug.py`; frontend `npm run test:multitenant`.
