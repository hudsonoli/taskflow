# Personalização visual global

Configurações → **Personalizar** (Admin/Gestor). Logo, cores e tema padrão valem para **toda a empresa**. Só o *tema* pode ser sobrescrito por cada usuário (ver abaixo); logo e cores nunca.

## O que é configurável

| Item | Regra |
|---|---|
| Logo | PNG ou GIF, **exatamente 320×132 px**, até 2 MB. GIF animado é guardado byte a byte (sem recodificar). |
| Cor principal / secundária | `#RRGGBB`. Padrão: `#6366f1` / `#7c3aed` (o visual original do TaskFloww). |
| Tema padrão da empresa | `claro` (padrão) ou `escuro`. É o tema de quem não escolheu nada e o das telas públicas. |

Fundo, superfícies, texto, bordas e estados (sucesso/aviso/erro/info) **não** são configuráveis: são tokens fixos por tema com contraste garantido.

## Backend

- Tabela `configuracoes_personalizacao` (1 linha por empresa, criada na primeira alteração; migration `0038`).
- `GET|PATCH|DELETE /configuracoes/personalizacao`, `POST|DELETE /configuracoes/personalizacao/logo` — `require_admin_or_gestor`, empresa sempre vinda do token.
- `GET /personalizacao/publica?empresaCodigo=` e `/publica/logo` — sem autenticação (login precisa do branding); só devolve cores, tema e versão do logo; código desconhecido → padrões.
- Logo validado **pelos bytes** (assinatura, IHDR/CRC/IEND no PNG; cabeçalho/dimensões/trailer no GIF); extensão e `Content-Type` declarados precisam concordar. Arquivo em `uploads/personalizacao/<empresa-id>/<uuid>.<ext>` (volume `taskfloww_uploads`), nunca no banco; servido com `Content-Type` canônico, `nosniff` e versão na URL (`?v=`) para cache imutável.

## Frontend

- `app/layout.tsx` (async + `connection()`) busca o branding **uma vez** no servidor (`lib/server/branding.ts`: timeout 1,5 s, cache de 30 s em `globalThis`, invalidado pelo proxy BFF após mutações) e grava `data-theme` + variáveis CSS no `<html>` → sem flash de tema. Falha do backend → padrões; nunca bloqueia o login.
- `lib/branding-tokens.ts` (puro): escala 50–950 da cor da empresa em OKLCH (a cor escolhida ocupa exatamente o passo 500/600), texto automático branco/quase-preto por WCAG, degradê só quando um texto serve às duas pontas (senão cor sólida).
- `globals.css`: variante `dark:` por atributo (`[data-theme="escuro"]`); `indigo-*`/`violet-*` do Tailwind apontam para `--brand-*`/`--accent-*` (sem variáveis = valores originais do Tailwind); tokens semânticos (`bg-surface`, `text-fg`, `border-field-line`, …); classe `.field` para todos os controles de formulário.
- `BrandLogo` é o único componente que desenha o logo (reserva 320:132; `<img>` para preservar GIF animado; falha → marca padrão).
- Teste de contraste: `npm run test:contraste` (lê os tokens reais do CSS; claro e escuro; 10 marcas de amostra).

## Convenções para telas novas

Use os tokens (`bg-surface`, `text-fg`, `text-fg-muted`, `border-line`, `.field`, `bg-brand-gradient`) em vez de `zinc-*`/`white`. Texto colorido com a marca: `text-indigo-600 dark:text-indigo-400` (garantidos ≥ 4,5:1 pela escala). Nunca `text-white` sobre `bg-indigo-500` (use `text-primary-fg`) nem sobre o degradê (a classe `bg-brand-gradient` já define a cor do texto).

## Tema individual por usuário

Cada usuário autenticado escolhe no menu do avatar: **Claro**, **Escuro**, **Sistema** ou **Usar padrão da empresa**.

- Persistência: `usuarios.tema_preferencia` (nullable; `claro | escuro | sistema`; migration `0039`). `NULL` = herdar `configuracoes_personalizacao.tema` — estado de todo usuário existente.
- API: `PATCH /usuarios/me/preferencias` `{ "tema": "claro" | "escuro" | "sistema" | null }`. A identidade vem só do token; sem RBAC (qualquer autenticado altera o próprio). `/auth/me` devolve `temaPreferencia`.
- Precedência (`lib/tema.ts → resolveEffectiveTheme`): sem usuário / página pública / `NULL` → empresa; `claro|escuro` → o escolhido; `sistema` → `prefers-color-scheme` (acompanha o SO em tempo de execução via `matchMedia`).
- Login, esqueci/redefinir senha e troca de senha inicial usam sempre o tema da empresa.
- Anti-flash: cookie-espelho `taskflow_tema` (HttpOnly, só `claro|escuro|sistema`, ausente = empresa), gravado/reconciliado por `/api/auth/login`, `/api/auth/google`, `/api/auth/session`, `/api/auth/tema` e apagado no logout. O layout só o honra se existir a sessão (`tf_session`). Para `sistema` o servidor emite um script inline mínimo que só lê `prefers-color-scheme`. A verdade é sempre o banco.
- Troca otimista: aplica na hora; se o PATCH falhar, restaura o tema anterior e avisa no menu.
- Teste: `npm run test:tema`.
