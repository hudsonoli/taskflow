# Padrão BFF do módulo Usuários

Este documento define o padrão oficial de integração entre o frontend e APIs
internas do TaskFloww. O módulo Usuários é a primeira aplicação desse padrão e
serve como referência para Clientes, Projetos, Fornecedores, Tarefas e Workflow.

## Arquitetura

```text
Browser
  → Route Handler do Next.js (/api/usuarios/*)
  → BackendApiClient
  → FastAPI (/usuarios/*)
  → PostgreSQL
```

O navegador conversa somente com caminhos relativos do BFF. A URL interna do
FastAPI, o JWT e o identificador da empresa permanecem no servidor.

## Responsabilidades

### Browser

- chama somente `/api/usuarios` e `/api/usuarios/[usuarioId]`;
- usa `credentials: "same-origin"` e `cache: "no-store"`;
- envia apenas filtros públicos documentados;
- consome o contrato de domínio em `camelCase`;
- não lê cookies HttpOnly, não envia Bearer e não conhece `empresaId`.

### Route Handler

- delimita o contrato HTTP público do BFF;
- valida os parâmetros recebidos do navegador;
- resolve a sessão autenticada;
- delega a consulta ao serviço do módulo;
- devolve respostas e erros normalizados com cache desabilitado.

### BackendApiClient

- concentra a comunicação HTTP server-side com o FastAPI;
- aplica a URL interna, o Bearer da sessão, timeout e `cache: "no-store"`;
- traduz indisponibilidade, timeout, status HTTP e resposta inválida;
- permanece genérico e reutilizável pelos módulos de domínio.

### FastAPI

- é a autoridade sobre autenticação, autorização e isolamento por empresa;
- aplica regras de negócio e consulta o PostgreSQL;
- nunca é acessado diretamente pelo navegador.

## Sessão e isolamento por empresa

O Route Handler lê o cookie HttpOnly usando a infraestrutura de autenticação
existente. O token é enviado pelo servidor ao endpoint `/auth/me`, que devolve a
identidade autenticada e o `empresaId`.

O serviço BFF acrescenta esse `empresaId` à chamada do FastAPI. O parâmetro não é
aceito do navegador e também é removido pelo mapper antes da resposta pública.
Isso impede que o cliente escolha outro tenant e reduz a exposição de
identificadores internos.

O JWT nunca vai ao browser porque permanece no cookie HttpOnly e é convertido em
Bearer somente na comunicação server-side entre Next.js e FastAPI.

## Contratos públicos

### `GET /api/usuarios`

Aceita os filtros implementados pelo backend:

- `status`;
- `perfilBase`;
- `search`;
- `limit`;
- `offset`.

Resposta:

```json
{
  "items": []
}
```

O envelope permite acrescentar metadados de paginação futuramente sem substituir
o campo `items`.

### `GET /api/usuarios/[usuarioId]`

Resposta:

```json
{
  "data": {
    "id": "identificador-do-usuario"
  }
}
```

O objeto completo segue o contrato TypeScript público do módulo. Ele não contém
`empresaId`.

## Erros

Erros do FastAPI e da infraestrutura são convertidos para um envelope seguro e
estável. O BFF preserva os status relevantes, como `401`, `403` e `404`, e
normaliza falhas de validação, timeout, indisponibilidade e payload inválido.
Detalhes internos, tokens, URLs e cabeçalhos sensíveis não são retornados.

## Cache

Identidade e dados de usuários usam `cache: "no-store"` em todas as camadas do
Next.js. As respostas do BFF também incluem `Cache-Control: no-store`. Dados
autenticados e dependentes de empresa não devem ser reutilizados entre sessões.

## Reutilização em novos módulos

Clientes, Projetos, Fornecedores, Tarefas e Workflow devem seguir a mesma
separação:

1. definir contratos distintos para API e domínio frontend;
2. criar mappers explícitos que validem o payload e removam campos internos;
3. validar no Route Handler somente filtros públicos;
4. resolver sessão e empresa no servidor;
5. usar o `BackendApiClient` para chamar o FastAPI;
6. devolver um envelope público preparado para evolução;
7. criar um cliente browser que use somente `/api/*`;
8. manter `cache: "no-store"` para dados autenticados;
9. testar isolamento por empresa e ausência de JWT, URL interna e Bearer no
   navegador.

Cada módulo mantém suas regras de domínio fora do cliente HTTP compartilhado. A
autorização efetiva e o isolamento por tenant continuam sendo responsabilidades
do FastAPI.
