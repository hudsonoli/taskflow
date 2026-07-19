# Preparação da autenticação

## Arquitetura

A autenticação usa o frontend Next.js como BFF. O navegador nunca acessa o
FastAPI diretamente:

```text
Navegador → Next.js/BFF → FastAPI → PostgreSQL
                         ↘ Redis
```

O navegador envia somente e-mail e senha para `/api/auth/login`. O BFF adiciona
o código da empresa, recebe o JWT do FastAPI e o mantém exclusivamente em cookie
HttpOnly. A identidade é revalidada pelo FastAPI por meio de `/api/auth/me`.

## Separação das variáveis

### Frontend e BFF

| Variável | Função |
| --- | --- |
| `TASKFLOWW_API_INTERNAL_URL` | Endereço do FastAPI dentro da rede Docker. |
| `TASKFLOWW_AUTH_ALLOWED_ORIGINS` | Origens explícitas aceitas nas operações de autenticação. |
| `TASKFLOWW_SESSION_MAX_AGE_SECONDS` | Duração do cookie de sessão. |
| `AUTH_DEFAULT_EMPRESA_CODIGO` | Empresa adicionada pelo BFF ao login. |

O frontend não recebe `AUTH_SECRET_KEY`, credenciais de banco ou a URL pública
do FastAPI.

### Backend

| Variável | Função |
| --- | --- |
| `DATABASE_URL` | Conexão com PostgreSQL. |
| `REDIS_URL` | Conexão com Redis. |
| `AUTH_SECRET_KEY` | Assinatura e validação de JWTs. |
| `AUTH_ALGORITHM` | Algoritmo JWT, atualmente `HS256`. |
| `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token de acesso. |
| `AUTH_MAX_FAILED_ATTEMPTS` | Limite de falhas antes do bloqueio temporário. |
| `AUTH_LOCKOUT_MINUTES` | Duração do bloqueio temporário. |

Valores reais ficam no `.env`, ignorado pelo Git e com permissão `600`. Nunca
use prefixo `NEXT_PUBLIC_` para configurações de autenticação ou segredos.

## Ambiente NOC

O NOC de desenvolvimento usa:

- frontend publicado na porta `3010`;
- API publicada na porta `8010`;
- empresa padrão `EMP-TESTCLIENT` — Empresa TestClient 2;
- origens `http://localhost:3010` e `http://10.153.110.10:3010`;
- sessão de 1800 segundos.

As origens devem ser separadas por vírgulas, sem curingas, caminhos ou barra
final. Caso surja domínio interno ou HTTPS, configure a origem exata.

Valide o ambiente sem imprimir valores:

```bash
docker compose config --quiet
docker compose ps
```

## Recriar somente autenticação

Alterações de variáveis do BFF ou JWT exigem recriar somente API e frontend:

```bash
docker compose up -d --force-recreate --no-deps \
  taskfloww_api taskfloww_front
```

Não execute `down`, não remova volumes e não recrie PostgreSQL ou Redis para uma
mudança de autenticação.

## Empresa padrão

O formulário atual não permite selecionar empresa. O BFF envia
`AUTH_DEFAULT_EMPRESA_CODIGO` ao FastAPI. Antes de mudar essa configuração,
confirme que a empresa existe, está ativa e possui usuários habilitados.

Seleção dinâmica por formulário, domínio ou subdomínio está fora do fluxo atual.

## Administrador inicial

O administrador inicial do NOC possui:

- código interno `ADMIN-INITIAL`;
- nome Administrador;
- e-mail `admin@taskflow.local`;
- perfil `admin`;
- status `ativo`;
- acesso ao sistema habilitado;
- empresa `EMP-TESTCLIENT`.

A criação deve ser transacional e idempotente: consultar e-mail e código dentro
da empresa, interromper diante de conflito e nunca sobrescrever silenciosamente
cadastro ou senha existentes. A credencial deve usar a função oficial de hashing.

`admin` é atualmente o perfil de maior privilégio. O perfil Owner/Dono ainda não
existe no schema, JWT ou frontend e deverá ser introduzido em uma etapa própria
de RBAC.

## Redefinir ou alterar senha

Para redefinir a senha de um usuário existente, use o CLI interativo oficial:

```bash
docker compose exec taskfloww_api \
  python -m app.cli.definir_senha_usuario \
  --empresa-codigo EMP-TESTCLIENT \
  --email usuario@exemplo.local
```

O usuário também pode usar a interface existente de alteração de senha depois
do login. Ainda não há troca obrigatória no primeiro acesso; uma senha temporária
deve ser alterada manualmente assim que o acesso for confirmado.

## Validar login, identidade e logout

1. Acesse uma rota privada sem sessão e confirme o redirecionamento para
   `/login?returnTo=...`.
2. Envie uma credencial inválida e confirme erro normalizado sem cookie.
3. Entre com a credencial válida e confirme retorno à rota original.
4. Consulte `/api/auth/me` e confirme somente os campos de identidade.
5. Atualize a página e confirme persistência da sessão.
6. Execute logout e confirme expiração do cookie.
7. Consulte `/api/auth/me` novamente e confirme estado não autenticado.

Nunca registre JWT, valor integral do cookie, senha, hash ou segredo durante as
validações.

## Novas empresas e usuários

Novas empresas precisam de código interno único e status `ativa`. Para usá-las
no login atual, atualize `AUTH_DEFAULT_EMPRESA_CODIGO` e recrie o frontend.

Novos usuários precisam de empresa, código e e-mail únicos dentro da empresa,
perfil suportado (`admin`, `gestor` ou `operador`), status `ativo`, acesso ao
sistema e credencial definida pela rotina oficial.

## Desenvolvimento e produção

Em desenvolvimento, o cookie é `taskfloww_session`. Em produção, o cookie é
`__Host-taskfloww_session`, com `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/` e
sem `Domain`.

Produção deve usar somente origem HTTPS explícita, segredo JWT exclusivo e
configuração própria de banco e Redis. Não reutilize segredo ou origens HTTP do
NOC em produção.
