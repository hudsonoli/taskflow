# 15 — Diagnóstico de Convergência Organizacional

> Documento de diagnóstico técnico. Não é DDL, não é migration, não altera
> schema, não altera contratos, não altera comportamento e não corrige nada.
> Tarefa: **TF-ORG-002.1 — Convergência do modelo existente**.

## 1. Objetivo

Este documento mapeia, de forma exclusivamente diagnóstica, o estado atual da
implementação do domínio organizacional do TaskFloww V2, para preparar a
execução segura das etapas TF-ORG-002.2 a TF-ORG-002.9.

Relação com os documentos anteriores:

- **Documento 13** (`13-dominio-organizacional-oficial.md`) é a referência
  conceitual oficial e congelada do domínio organizacional. Este diagnóstico
  não a substitui, não a reinterpreta e não propõe mudanças a ela.
- **Documento 14** (`14-plano-implementacao-organizacao.md`) organiza a
  execução incremental do TF-ORG-002. Este documento entrega o "Resultado
  esperado" descrito para a etapa **TF-ORG-002.1 — Convergência do modelo
  existente**: "Implementação e divergências conhecidas, com a convergência
  organizada e sem decisões implícitas."
- **TF-ORG-002.1** é a primeira etapa da sequência oficial definida no
  Documento 14 (seção 5) e é pré-requisito declarado de TF-ORG-002.2 a
  TF-ORG-002.9.

Este documento não decide nada. Ele registra fatos observáveis no
repositório na branch `feature/cadastros-clientes`, na data em que foi
produzido, para servir de inventário técnico oficial de apoio à
implementação futura pelo Codex.

## 2. Estado Atual

O TaskFloww V2 já possui, no backend, uma implementação real e persistida
para grande parte das entidades organizacionais descritas no Documento 13:
Empresa, Usuário, Departamento, Cargo, Equipe, Agência, além dos vínculos
`usuario_departamentos`, `usuario_cargos` e `usuario_equipes`. Essa
implementação é mais avançada do que os diagnósticos anteriores (Documentos
09, 10 e 11) registravam — aqueles documentos descreviam essas entidades como
inexistentes ou apenas mockadas, o que já era apontado como desatualizado
pelo próprio Documento 13 (seção 13.1).

No frontend, o cadastro de Usuários passou por uma migração parcial: existe
hoje um fluxo "remoto" (`UsuariosView.tsx` + hooks `useUsuarioCreate`,
`useUsuarioDetail`, `useUsuariosList`, `useUsuarioUpdate`, camada de API em
`lib/api/usuarios*.ts`, BFF em `app/api/usuarios/*`) que consome o backend
real, e um conjunto de arquivos legados (`useUsuarioDraft.ts`,
`UsuarioFormSections.tsx`, `UsuarioEditFormBody.tsx`, `usuario-mock.ts`) que
não é mais importado pela tela principal, mas continua presente no
repositório com tipos e mocks próprios.

O módulo de Equipes (`EquipesView.tsx`) permanece inteiramente baseado em
mock local (`equipe-mock.ts`), sem qualquer integração com os endpoints reais
de `/equipes` já existentes no backend. Não existe, no frontend, nenhuma tela
para Departamentos nem para Cargos, apesar de ambos possuírem CRUD completo
no backend.

Squad não existe em nenhuma camada como entidade — apenas como campo de
texto legado (`UsuarioDraft.squad`) na ilha de código não utilizada pela tela
atual de Usuários.

## 3. Backend

### 3.1 Entidades e models (`backend/app/models/`)

| Entidade | Arquivo | Tabela |
|---|---|---|
| Empresa | `empresa.py` | `empresas` |
| Usuário | `usuario.py` | `usuarios` |
| UsuarioCredencial | `usuario_credencial.py` | `usuario_credenciais` |
| Departamento | `departamento.py` | `departamentos` |
| Cargo | `cargo.py` | `cargos` |
| Equipe | `equipe.py` | `equipes` |
| Agência | `agencia.py` | `agencias` |
| UsuarioDepartamento | `usuario_departamento.py` | `usuario_departamentos` |
| UsuarioCargo | `usuario_cargo.py` | `usuario_cargos` |
| UsuarioEquipe | `usuario_equipe.py` | `usuario_equipes` |
| Cliente | `cliente.py` | `clientes` (fora do domínio organizacional, listado por dependência) |
| Evento | `evento.py` | `eventos` (Event Store) |
| SessaoTrabalho | `sessao_trabalho.py` | `sessoes_trabalho` |

Não existem models para: Squad, `squad_membros`, `departamento_gestores`
(Head/Gestor como entidade própria), Permissão, `usuario_permissoes`,
`permissoes_temporarias`, organograma (Departamento pai) ou gestor direto.

### 3.2 Campos por entidade organizacional

**Empresa** (`empresas`): `id`, `nome`, `documento`, `codigo_interno`,
`status` (`ativa`/`inativa`/`arquivada`), `created_at`, `updated_at`,
`inativado_at`, `inativado_por_usuario_id`, `motivo_inativacao`.

**Usuário** (`usuarios`): `id`, `empresa_id`, `codigo_interno`, `nome`,
`email`, `perfil_base` (`admin`/`gestor`/`operador`), `acesso_sistema`,
`status` (`ativo`/`inativo`/`bloqueado`/`arquivado`), `created_at`,
`updated_at`, `inativado_at`, `inativado_por_usuario_id`,
`motivo_inativacao`. Não possui `cargo`, `departamento_id`, `squad` nem
qualquer campo pessoal/administrativo (telefone, CPF, endereço, salário,
dados bancários).

**Departamento** (`departamentos`): `id`, `empresa_id`, `codigo_interno`,
`nome`, `descricao`, `status` (`ativa`/`inativa`/`arquivada`), `created_at`,
`updated_at`, `inativado_at`, `motivo_inativacao`,
`inativado_por_usuario_id`. Não possui `sigla` (prevista no Documento 10) nem
`departamento_pai_id`.

**Cargo** (`cargos`): mesmos campos-padrão de Departamento
(`codigo_interno`, `nome`, `descricao`, `status`
`ativa`/`inativa`/`arquivada`, timestamps e campos de inativação). Não
possui `familia`/`categoria` (prevista no Documento 10).

**Equipe** (`equipes`): `id`, `empresa_id`, `codigo_interno`, `nome`,
`descricao`, `status` (`ativa`/`inativa`/`arquivada`), timestamps e campos de
inativação. **Não possui `departamento_id`** nem `sigla` nem
`responsavel_usuario_id`.

**Agência** (`agencias`): `id`, `empresa_id`, `codigo_interno`, `nome`,
`sigla`, `descricao`, `status`, timestamps, campos de inativação. Não possui
campo `tipo` (unidade_operacional/filial/marca) previsto no Documento 10.

**UsuarioDepartamento** (`usuario_departamentos`): `id`, `empresa_id`,
`usuario_id`, `departamento_id`, `papel` (`membro`/`gestor`/`head`),
`principal`, `status` (`ativo`/`inativo`), `inicio_em`, `fim_em`,
`motivo_encerramento`, `criado_por_usuario_id`, `encerrado_por_usuario_id`,
timestamps.

**UsuarioCargo** (`usuario_cargos`): mesma estrutura de vínculo, sem campo
`papel` (Cargo não tem papel), `status` `ativo`/`inativo`.

**UsuarioEquipe** (`usuario_equipes`): mesma estrutura de vínculo, `papel`
(`membro`/`lider`/`coordenador`), **`status`** usa valores
**`ativo`/`encerrado`** (diferente dos outros dois vínculos). Não possui
campo equivalente a `tipo_vinculo` (`membro_departamento`/`convidado`)
previsto no Documento 10 e exigido conceitualmente pelo Documento 13 (seção
8.4 e 9.12).

### 3.3 Schemas (`backend/app/schemas/`)

Existe um schema Pydantic por entidade e por vínculo, todos com aliases
camelCase (`empresaId`, `codigoInterno`, `perfilBase` etc.):
`empresa.py`, `usuario.py`, `departamento.py`, `cargo.py`, `equipe.py`,
`agencia.py`, `usuario_departamento.py`, `usuario_cargo.py`,
`usuario_equipe.py`, além de `auth.py`, `cliente.py`, `evento.py`,
`sessao_trabalho.py`.

### 3.4 Services (`backend/app/services/`)

Um service por entidade/vínculo, todos seguindo o mesmo padrão (create,
list, get, update parcial, inativar, reativar, `to_response`/`to_read`,
exceções específicas `*NotFoundError`, `*ConflictError`,
`*InvalidDataError`/`*InvalidEmpresaError`, `*InvalidTransitionError`):
`empresa_service.py`, `usuario_service.py`, `departamento_service.py`,
`cargo_service.py`, `equipe_service.py`, `agencia_service.py`,
`usuario_departamento_service.py`, `usuario_cargo_service.py`,
`usuario_equipe_service.py`. Também presentes: `auth_service.py`,
`cliente_service.py`, `evento_service.py`, `domain_event_publisher.py`,
`trafego_event_handler.py`, `sessao_trabalho_service.py`.

`usuario_departamento_service.py` contém lógica de unicidade de Head ativo
por Departamento (`_ensure_head_available`), mas trata Head como um valor do
campo `papel`, não como responsabilidade própria com histórico dedicado
— consistente com a divergência já registrada no Documento 13 (13.2).

### 3.5 Repositories (`backend/app/repositories/`)

Um repository por entidade/vínculo, todos com filtros por `empresa_id`,
status, busca textual (quando aplicável) e paginação (`limit`/`offset`):
`empresa_repository.py`, `usuario_repository.py`,
`departamento_repository.py`, `cargo_repository.py`, `equipe_repository.py`,
`agencia_repository.py`, `usuario_departamento_repository.py`,
`usuario_cargo_repository.py`, `usuario_equipe_repository.py`, além de
`usuario_credencial_repository.py`, `cliente_repository.py`,
`evento_repository.py`, `sessao_trabalho_repository.py`.

### 3.6 Endpoints (`backend/app/api/routes/`)

| Recurso | Prefixo | Métodos |
|---|---|---|
| Empresas | `/empresas` | GET (lista/detalhe), PATCH; POST e ciclo de vida (`inativar`/`reativar`) retornam 403 nesta etapa |
| Usuários | `/usuarios` | POST, GET, GET/{id}, PATCH, POST `/inativar`, `/reativar`, `/bloquear`, `/desbloquear` |
| Departamentos | `/departamentos` | POST, GET, GET/{id}, PATCH, POST `/inativar`, `/reativar` |
| Cargos | `/cargos` | POST, GET, GET/{id}, PATCH, POST `/inativar`, `/reativar` |
| Equipes | `/equipes` | POST, GET, GET/{id}, PATCH, POST `/inativar`, `/reativar` |
| Agências | `/agencias` | POST, GET, GET/{id}, PATCH, POST `/inativar`, `/reativar` |
| Vínculo Usuário-Departamento | `/vinculos/departamentos` | POST, GET, GET/{id}, PATCH (`papel`, `principal`), POST `/encerrar` |
| Vínculo Usuário-Cargo | `/vinculos/cargos` | POST, GET, GET/{id}, PATCH (`principal`), POST `/encerrar` |
| Vínculo Usuário-Equipe | `/vinculos/equipes` | POST, GET, GET/{id}, PATCH (`papel`, `principal`), POST `/encerrar` |
| Auth | `/auth` | login, `/me`, alterar senha (ver `auth.py`) |
| Eventos | `/eventos` | leitura do Event Store |

Não existem endpoints de: Squad, `departamento_gestores` (Head/Gestor como
recurso próprio), Permissões, consultas organizacionais agregadas
(`/organizacao/*` previstas no Documento 11) ou organograma.

Os vínculos usam rotas genéricas (`/vinculos/departamentos`,
`/vinculos/cargos`, `/vinculos/equipes`), exatamente como registrado no
Documento 13 (13.9), e não rotas aninhadas por Usuário ou por Departamento.

### 3.7 Autorização e dependências (`backend/app/dependencies/`)

`authorization.py` define `require_profiles`, `require_admin` (perfil
`admin`), `require_admin_or_gestor` (`admin` ou `gestor`),
`ensure_same_empresa` e `ensure_resource_empresa` (isolamento por tenant via
`current_user.empresa_id`). `auth.py` resolve o usuário atual a partir de
Bearer token via `AuthService`.

Todos os endpoints de escrita organizacional (`POST`, `PATCH`,
`/inativar`, `/reativar`, vínculos) exigem `require_admin`. Todos os `GET`
exigem `require_admin_or_gestor`. Não existe autorização por escopo
organizacional (Departamento, Equipe) nem permissão granular — apenas os
três perfis-base (`admin`, `gestor`, `operador`), confirmando a separação
entre organização e RBAC descrita no Documento 13 (seção 11), mas também
confirmando que RBAC ainda é apenas perfil-base, sem o modelo de permissões
por recurso previsto no Documento 10 (seção 8) e no Documento 11
(TF-ORG-012).

### 3.8 CLI

`backend/app/cli/definir_senha_usuario.py` é o único utilitário de linha de
comando encontrado; usado para definir senha de usuário fora do fluxo HTTP
(bootstrap). Não há CLI de bootstrap de Empresa.

## 4. Banco de Dados

### 4.1 Migrations relevantes (`backend/alembic/versions/`)

| Migration | Cria |
|---|---|
| `20260711_1a2_cria_tabela_eventos.py` | `eventos` |
| `20260712_1a5_cria_sessoes_trabalho.py` | `sessoes_trabalho` |
| `20260715_1a6_cria_tabela_empresas.py` | `empresas` |
| `20260715_1a7_cria_tabela_usuarios.py` | `usuarios` |
| `20260715_1a8_cria_tabela_agencias.py` | `agencias` |
| `20260715_1a9_cria_usuario_credenciais.py` | `usuario_credenciais` |
| `20260715_1a10_cria_tabela_cargos.py` | `cargos` |
| `20260715_1a11_cria_tabela_departamentos.py` | `departamentos` |
| `20260715_1a12_cria_usuario_departamentos.py` | `usuario_departamentos` |
| `20260716_1a13_cria_usuario_cargos.py` | `usuario_cargos` |
| `20260716_1a14_cria_tabela_equipes.py` | `equipes` |
| `20260716_1a15_cria_usuario_equipes.py` | `usuario_equipes` |
| `20260716_1a16_cria_tabela_clientes.py` | `clientes` |

Não existe migration para: `squads`, `squad_membros`,
`departamento_gestores`, `permissoes`, `usuario_permissoes`,
`permissoes_temporarias`, nem para adicionar `departamento_id` a `equipes`.

### 4.2 Constraints e índices relevantes

- `usuario_departamentos`: índice único parcial para vínculo ativo por
  usuário/departamento; índice único parcial para **Head ativo por
  Departamento** (`papel = 'head' AND status = 'ativo'`); índice único
  parcial para **principal ativo por usuário**; `CheckConstraint` de
  `papel IN ('membro', 'gestor', 'head')`.
- `usuario_equipes`: mesma estrutura, com índice único parcial para
  **Líder ativo por Equipe** (`papel = 'lider' AND status = 'ativo'`);
  `CheckConstraint` de `papel IN ('membro', 'lider', 'coordenador')` — o
  valor `coordenador` não é mencionado no Documento 13 nem no Documento 10.
- `usuario_cargos`: índice único parcial para vínculo ativo e para
  principal ativo por usuário; sem `papel`.
- Todas as tabelas de catálogo (`departamentos`, `cargos`, `equipes`,
  `agencias`) têm `UNIQUE(empresa_id, codigo_interno)` e
  `UNIQUE(empresa_id, nome)` — sem particionar por status, ou seja, um nome
  usado por um registro arquivado bloqueia reuso do mesmo nome mesmo
  inativo.
- `empresas` tem `UNIQUE(codigo_interno)` e `UNIQUE(documento)` globais
  (não há mais de uma Empresa em uso hoje; ver seção 6).

### 4.3 Divergências identificadas com a arquitetura (Documento 13)

- A tabela `equipes` não possui `departamento_id` — diverge diretamente da
  seção 8.2 e da divergência 13.3 do Documento 13.
- `usuario_departamentos.papel` aceita `head` e `gestor` como valores de um
  mesmo campo de papel de participação, não como responsabilidade
  independente com tabela e ciclo de vida próprios (Documento 13, seções
  6.8–6.9, 8.6–8.7, divergência 13.2).
- `usuario_equipes` não possui campo equivalente a `tipo_vinculo` para
  distinguir membro do Departamento de referência de convidado externo
  (Documento 13, seção 8.4 e divergência 13.4).
- Vocabulário de `status` não é uniforme entre tabelas de vínculo:
  `usuario_departamentos` e `usuario_cargos` usam `ativo`/`inativo`;
  `usuario_equipes` usa `ativo`/`encerrado` (divergência 13.8, confirmada).
- Vocabulário de `status` também não é uniforme entre entidades de
  catálogo: `empresas`, `departamentos`, `cargos`, `equipes` e `agencias`
  usam `ativa`/`inativa`/`arquivada` (feminino), enquanto `usuarios` usa
  `ativo`/`inativo`/`bloqueado`/`arquivado` (masculino, com estado adicional
  `bloqueado`). Essa divergência de vocabulário não está registrada
  explicitamente no Documento 13.
- Não existe tabela para Squad em nenhuma forma — confirma divergência 13.5.
- Não existe tabela dedicada a Head/Gestor com vigência própria
  (`departamento_gestores`, prevista no Documento 10) — confirma
  divergência 13.2.

## 5. Frontend

### 5.1 Tipos (`frontend/src/types/`)

- `usuario.ts` — tipos **legados**: `UsuarioDraft` (com `departamentoId`
  singular, `squad: string`, `perfil: PerfilAcesso`, `permissoes`,
  `enderecos`, `informacoes`, `administrativo`, `historico`),
  `DepartamentoOption`, `PermissaoItem`, `UsuarioEndereco`,
  `UsuarioInformacoes`, `UsuarioSalario`, `UsuarioDadosBancarios`,
  `UsuarioAdministrativo`, `HistoricoUsuario`.
- `usuario-domain.ts` — tipo **remoto/real**: `Usuario` (`id`,
  `codigoInterno`, `nome`, `email`, `perfilBase`, `perfilLabel`,
  `acessoSistema`, `status`, `statusLabel`, timestamps, campos de
  inativação), `UsuarioListResult`, `UsuarioDetailResult`,
  `UsuarioClientResult`.
- `usuario-api.ts` — contrato HTTP com o backend: `UsuarioApiResponse`,
  `UsuarioListFilters`, `UsuarioEditableValues`, `UsuarioCreatePayload`,
  `UsuarioUpdatePayload`, `UsuarioErrorCode`, `UsuarioErrorResponse`.
- `equipe.ts` — apenas o tipo legado/mock: `EquipeDraft` (com
  `departamentoId`, `responsavelId`, `membros: EquipeMembro[]` com `papel:
  string` livre), `EquipeMembro`, `EquipeAcesso`, `HistoricoEquipe`. Não
  existe um `equipe-domain.ts`/`equipe-api.ts` equivalente ao par criado
  para Usuário.
- `auth.ts` — `AuthPerfilBase` e `AuthUsuarioStatus`, que são a fonte real
  de `admin`/`gestor`/`operador` e `ativo`/`inativo`/`bloqueado`/`arquivado`
  usados por `usuario-api.ts`/`usuario-domain.ts`.
- Não existem arquivos de tipos para Departamento, Cargo, Agência ou Squad
  como entidades de domínio no frontend.

### 5.2 Mocks (`frontend/src/lib/`)

- `usuario-mock.ts` — expõe `departamentos: DepartamentoOption[]` (IDs como
  `dep-atendimento`, `dep-trafego` etc.), `perfis: PerfilAcesso[]`
  (`Owner`, `Diretoria`, `Gestor`, `Financeiro`, `Operador`, `Cliente`),
  `paginasPrincipais`, catálogo de permissões (`permissoesBase`) — inclui
  entradas para "Departamentos" e "Squad" como itens de permissão
  decorativa, não como entidades reais.
- `equipe-mock.ts` — reexporta `departamentos` de `usuario-mock.ts` e
  define `responsaveisDisponiveis`, `clientesDisponiveis`,
  `equipesDisponiveis` (IDs como `equipe-1`, `equipe-2`), todos com
  universos de ID próprios, desconectados dos IDs reais do backend.
- `conta-mock.ts` — `currentUser` mockado com `cargo: string` e
  `departamento: string` livres (texto), usado no menu do usuário logado
  (`UserMenu.tsx`, `PerfilView.tsx`).
- `access-control.ts` — define `PerfilAcesso` (`Owner`, `SuperAdmin`,
  `Admin`, `Diretoria`, `Gerente`, `Gestor`, `Financeiro`, `Operador`,
  `Cliente`) e os gates `hasAdministrativeAccess`/`hasDashboardAccess`,
  usados apenas para decidir renderização — nenhuma verificação equivalente
  existe no backend para esses nove valores (que não coincidem com o
  `perfil_base` real: `admin`/`gestor`/`operador`).
- `trafego-mock.ts`, `projetos-mock.ts`, `demandas-mock.ts`,
  `agenda-mock.ts`, `dashboard-mock.ts` também referenciam departamento,
  cargo ou responsável com universos de ID próprios (ver seção 7).

### 5.3 Componentes — Usuários (`frontend/src/components/usuarios/`)

Duas trilhas coexistem no mesmo diretório:

**Trilha remota (em uso por `UsuariosView.tsx`):** `useUsuarioCreate.ts`,
`useUsuarioDetail.ts`, `useUsuariosList.ts`, `useUsuarioUpdate.ts`,
`UsuarioCreateForm.tsx`, `UsuarioEditDrawer.tsx`, `usuario-update.ts`.
Consome `Usuario`/`usuario-domain.ts` e a camada `lib/api/usuarios*.ts`.
Campos editáveis: `codigoInterno`, `nome`, `email`, `perfilBase`,
`acessoSistema` — apenas os campos existentes no backend.

**Trilha legada (não referenciada por `UsuariosView.tsx`):**
`useUsuarioDraft.ts`, `UsuarioFormSections.tsx`, `UsuarioEditFormBody.tsx`.
Consomem `UsuarioDraft`/`types/usuario.ts` e `usuario-mock.ts`
(`departamentos`, `perfis`). `useUsuarioDraft` ainda é importado por
`UsuarioEditFormBody.tsx` e por `tests/usuarios/usuarios-view.test.ts`, mas
nenhum dos componentes ativos da tela principal (`UsuariosView.tsx`) importa
essa trilha.

### 5.4 Componentes — Equipes (`frontend/src/components/equipes/`)

`EquipesView.tsx`, `EquipeFormSections.tsx`, `NovaEquipeModal.tsx`,
`NovaEquipeButton.tsx` — toda a implementação consome exclusivamente
`equipe-mock.ts` e `EquipeDraft`. Não há hook, cliente de API, BFF ou
qualquer chamada HTTP para os endpoints reais de `/equipes` já existentes no
backend. `resolveDepartamentoNome` resolve o nome do Departamento por busca
em array mock local usando `departamentoId`, campo que não existe na
entidade real `Equipe`.

### 5.5 Rotas (`frontend/src/app/`)

| Rota | Origem dos dados |
|---|---|
| `/configuracoes/usuarios` | `UsuariosView` — trilha remota (backend real) |
| `/configuracoes/equipes` | `EquipesView` — mock local |
| `/configuracoes/agencias` | mock local (não inventariado em profundidade nesta etapa; fora do foco de Usuário/Departamento/Equipe/Cargo) |
| `/configuracoes/permissoes` | tela com empty state, decorativa |
| — | **não existe rota para Departamentos** |
| — | **não existe rota para Cargos** |
| — | **não existe rota para Squad** |

`app/api/usuarios/route.ts` e `app/api/usuarios/[usuarioId]/route.ts`
formam o BFF real de Usuários (validação de payload, filtros, proxy
autenticado para o backend). Não existe BFF equivalente para Departamentos,
Cargos ou Equipes.

### 5.6 Estado e providers

Não foi localizado um provider ou contexto React dedicado a "contexto
organizacional" (Departamento/Equipe/Cargo do usuário atual). O único
estado "atual" existente é `conta-mock.ts` (`currentUser`), consumido por
componentes de layout/conta, com `cargo` e `departamento` como texto livre.

## 6. Contratos

### 6.1 Formato geral

Todos os endpoints REST usam JSON com aliases camelCase (Pydantic
`populate_by_name`/aliases), paginação via `limit`/`offset`, filtro
obrigatório `empresaId` em listagens, e um schema `*Response`/`*Read` de
saída por entidade. PATCH usa `dict[str, Any]` com uma allowlist de campos
(`PATCH_ALLOWED_FIELDS`) validada manualmente antes do parse Pydantic.

### 6.2 Empresa — situação particular

`POST /empresas` e `POST /empresas/{id}/inativar` e `/reativar` retornam
`403` fixo ("indisponível nesta etapa"). `GET /empresas` sempre retorna a
Empresa do usuário autenticado (`current_user.empresa_id`), nunca uma lista
real de múltiplas Empresas. Isso indica que o sistema opera hoje com uma
única Empresa efetiva, com o ciclo de vida de criação/inativação de Empresa
deliberadamente bloqueado nesta fase.

### 6.3 DTOs de vínculo

`UsuarioDepartamentoCreate`/`Update`/`Response`, `UsuarioCargoCreate`/...,
`UsuarioEquipeCreate`/... — cada schema expõe enums de `papel` e `status`
próprios (`UsuarioDepartamentoPapel`, `UsuarioDepartamentoStatus`,
`UsuarioEquipePapel`, `UsuarioEquipeStatus`), refletindo exatamente os
valores de `CheckConstraint` do banco descritos na seção 4.2.

### 6.4 Contrato remoto de Usuário consumido pelo frontend

`UsuarioApiResponse` (backend → BFF) e `Usuario`
(`usuario-domain.ts`, BFF → UI) só carregam os campos que também existem no
model `Usuario` do backend. Não há, em nenhum contrato remoto, campo de
Departamento, Equipe, Cargo, Squad ou responsabilidade organizacional —
confirma a divergência 13.6 do Documento 13: o contexto organizacional do
Usuário não é exposto pela API real nem pelo BFF hoje.

### 6.5 Contrato legado de Usuário (não exposto por API)

`UsuarioDraft` não corresponde a nenhum contrato HTTP real — é preenchido e
mantido inteiramente em estado local do componente
(`useUsuarioDraft.ts`), sem persistência. Os campos `departamentoId`
(singular), `squad`, `permissoes`, `enderecos`, `informacoes`,
`administrativo`, `historico` não têm equivalente no backend.

## 7. Dependências

Módulos que referenciam conceitos organizacionais (Departamento, Equipe,
Cargo, responsável) por meio de universos de ID próprios em mock, sem
consumir os IDs reais do backend:

| Módulo | Arquivo(s) | Uso |
|---|---|---|
| Tráfego / Central de Tráfego | `trafego-mock.ts`, `TrafegoCargaDepartamentos.tsx`, `TrafegoFilters.tsx`, `TrafegoAgoraTable.tsx`, `TrafegoResumoCards.tsx`, `TrafegoView.tsx` | carga e filtros por Departamento com IDs próprios (Documento 13, divergência 13.10, confirmada — usa padrão `departamento-atendimento`, diferente de `dep-atendimento` usado em Usuários/Equipes) |
| Projetos | `projetos-mock.ts`, `ProjetoFormSections.tsx`, `ProjetoDetailsDrawer.tsx`, `ProjetosTable.tsx`, `ProjetosView.tsx`, `NovoProjetoModal.tsx` | referências a Departamento/responsável em mock próprio |
| Demandas | `demandas-mock.ts`, `DemandaFormSections.tsx`, `DemandasKanban.tsx`, `DemandasView.tsx`, `NovaDemandaModal.tsx` | idem |
| Agenda | `agenda-mock.ts`, `AgendaList.tsx`, `AgendaView.tsx` | referências a cargo/departamento em mock |
| Conta / Perfil | `conta-mock.ts`, `PerfilView.tsx`, `UserMenu.tsx` | `cargo`/`departamento` como texto livre do usuário logado mockado |
| Fornecedores | `fornecedor-mock.ts`, `FornecedoresView.tsx`, `FornecedorFormSections.tsx` | campo `cargo` de contato, não organizacional |
| Clientes | `ClienteFormSections.tsx` | campo `cargo` de contato comercial, não organizacional (consistente com Documento 13, seção 6.12: contato de Cliente não é Usuário) |

Nenhum desses módulos consome hoje os endpoints reais de
`/departamentos`, `/equipes`, `/cargos` ou `/vinculos/*`. Workflow, Kanban e
Dashboard não apresentaram, na busca realizada, referências diretas a
Departamento/Equipe/Cargo além do que já está listado acima via Projetos e
Demandas. RBAC/autorização real (backend) depende apenas de `perfil_base`
(`admin`/`gestor`/`operador`); o gate visual do frontend
(`access-control.ts`) depende de um vocabulário de nove perfis totalmente
diferente, sem correspondência com o backend (ver seção 8.5).

## 8. Divergências

### 8.1 Implementado corretamente (em relação ao Documento 13)

- Empresa como raiz de isolamento (`empresa_id` obrigatório e validado via
  `ensure_same_empresa`/`ensure_resource_empresa` em todas as rotas
  organizacionais).
- Relações N:N reais de Usuário com Departamento, Equipe e Cargo, cada uma
  com tabela de vínculo própria, `principal`, `status`, `inicio_em`,
  `fim_em`, `motivo_encerramento`, `criado_por_usuario_id`,
  `encerrado_por_usuario_id` — cobre a seção 8.3–8.5 do Documento 13.
  Testes cobrem múltiplos vínculos por usuário, unicidade de principal
  ativo, e encerramento com vigência (`test_usuario_departamentos.py`,
  `test_usuario_cargos.py`, `test_usuario_equipes.py`).
  atenção: `usuario_equipes` não distingue convidado (ver 8.3).
- Unicidade de Head ativo por Departamento e de Líder ativo por Equipe via
  índice único parcial no banco (seção 8.6 e 8.8 do Documento 13).
- Cargo não concede permissão nem é usado como perfil em nenhum ponto do
  backend (seção 6.5, 8.5 do Documento 13).
- RBAC (perfil-base) e organização são camadas separadas no backend: nenhum
  endpoint deriva autorização de `papel` do vínculo (seção 4.2 e 11 do
  Documento 13).
- IDs estáveis (UUID/string 36) em todos os relacionamentos reais do
  backend — nenhuma FK por nome (seção 4.4 do Documento 13).

### 8.2 Parcialmente implementado

- Head e Gestor organizacional existem apenas como valor do campo `papel`
  em `usuario_departamentos`, com unicidade garantida por índice parcial,
  mas sem tabela própria, sem histórico dedicado (fora do histórico
  genérico do vínculo departamental) e sem eventos de domínio específicos
  (`departamento.head_definido`/`head_substituido` não existem em
  `event_types.py`; o que existe é o evento genérico
  `usuario_departamento.alterado`). Diverge da seção 6.8, 8.6, 9.6 e 12.1 do
  Documento 13, que trata Head como responsabilidade com semântica própria.
- Líder de Equipe está na mesma situação: existe como valor de `papel` em
  `usuario_equipes`, com unicidade garantida, mas sem histórico ou eventos
  dedicados a "líder atribuído"/"líder substituído" (seção 6.10, 8.8, 9.7 do
  Documento 13).
- Vínculos organizacionais existem e preservam histórico no backend, mas o
  frontend só consome vínculos de Usuário-com-Departamento/Equipe/Cargo de
  forma nenhuma — não há tela nem componente que liste, crie ou encerre
  esses vínculos hoje. A capacidade de domínio existe; a integração de
  camadas (TF-ORG-002.6/002.7/002.8) ainda não começou.
- Migração de Usuário no frontend: a trilha remota cobre identidade básica
  (nome, email, perfil-base, código interno, acesso ao sistema), mas não
  cobre nenhum dado organizacional, pessoal ou administrativo — a trilha
  legada que cobria esses campos ficou desconectada da tela principal, sem
  ter sido formalmente descontinuada (arquivos, tipos e teste ainda
  existem).

### 8.3 Não implementado

- Squad: nenhuma entidade, tabela, schema, repository, service, rota ou
  tipo de frontend real. Existe apenas `UsuarioDraft.squad: string`, em
  código não referenciado pela tela ativa de Usuários (seção 6.4, 7.6,
  13.5 do Documento 13).
- `departamento_id` em Equipe: não existe na tabela `equipes`, no model, no
  schema nem no service. O único lugar onde essa relação aparece é no mock
  de frontend (`EquipeDraft.departamentoId`), desconectado da entidade real
  (seção 8.2, 13.3 do Documento 13).
- Distinção de convidado em vínculo de Equipe (`tipo_vinculo`): não existe
  em nenhuma camada (seção 8.4, 9.12, 13.4 do Documento 13).
- Permissões por escopo/recurso e permissões temporárias: não existem
  tabelas, endpoints nem lógica real — apenas o gate visual decorativo do
  frontend (`access-control.ts`, tela `/configuracoes/permissoes` com empty
  state) (seção 11.3, 12.5 do Documento 13).
- Contexto organizacional consolidado por Usuário (visão única combinando
  Departamento principal, Equipe principal, Cargo principal,
  responsabilidades): não existe endpoint, service nem tipo de frontend
  para isso — cada consumidor precisaria reconstruir essa visão sozinho
  hoje, o que o Documento 13 (seção 12.3) explicitamente não permite como
  solução definitiva.
- Telas de Departamento e Cargo no frontend: não existem, apesar do backend
  já suportar CRUD completo para ambos.
- Integração real de Equipes no frontend: `EquipesView.tsx` não faz nenhuma
  chamada aos endpoints `/equipes` já existentes.
- Organograma, gestor direto, aprovações, férias/ausências, substituições:
  fora do escopo do Documento 13 e do TF-ORG-002 (Documento 14, seção 2);
  não implementados, como esperado.

### 8.4 Conflita com a arquitetura

- `usuario_equipes.status` usa vocabulário `ativo`/`encerrado`, enquanto
  `usuario_departamentos.status` e `usuario_cargos.status` usam
  `ativo`/`inativo` — viola a expectativa de vocabulário único de status
  antes de novos contratos públicos (Documento 13, seção 13.8).
- `usuario_equipes.papel` aceita `coordenador`, um terceiro valor não
  descrito nem no Documento 13 nem no Documento 10 (que só previam
  `membro`/`líder` como papéis de Equipe); não há definição de domínio para
  o que "coordenador" representa nem se é responsabilidade, papel
  operacional ou cargo disfarçado.
- O vocabulário de `PerfilAcesso` do frontend (`Owner`, `SuperAdmin`,
  `Admin`, `Diretoria`, `Gerente`, `Gestor`, `Financeiro`, `Operador`,
  `Cliente`, em `access-control.ts` e usado por `UsuarioDraft.perfil`) não
  corresponde a `perfil_base` real do backend (`admin`/`gestor`/`operador`).
  Isso é uma instância concreta do que o Documento 13 (seção 13.11) já
  descrevia de forma geral como "Perfil, Cargo e responsabilidade ainda
  aparecem misturados" — aqui, dois vocabulários de perfil inteiramente
  diferentes coexistem, um decorativo (frontend legado) e um real
  (backend), sem qualquer mapeamento formal entre eles.
- IDs de Departamento divergem entre módulos mock: `dep-atendimento`
  (Usuários/Equipes, `usuario-mock.ts`) versus
  `departamento-atendimento` (Tráfego, `trafego-mock.ts`) — nenhum dos dois
  corresponde a um `id` real de `departamentos` no backend. Confirma e
  detalha a divergência 13.10 do Documento 13.
- `UsuarioDraft.squad`, `UsuarioDraft.departamentoId` (singular) e
  `UsuarioDraft.perfil` continuam presentes no repositório mesmo não sendo
  mais usados pela tela ativa — o Documento 13 (seção 13.7) já registrava
  isso como divergência de cardinalidade; o fato de o código legado não ter
  sido removido nem formalmente descontinuado mantém viva a possibilidade
  de reintrodução acidental desses padrões.

## 9. Dívida Técnica

Itens de dívida técnica identificados, estritamente relacionados ao domínio
organizacional (sem sugestão de correção):

- **Ilha de código legado em Usuários:** `useUsuarioDraft.ts`,
  `UsuarioFormSections.tsx` e `UsuarioEditFormBody.tsx` não são mais
  importados por `UsuariosView.tsx`, mas continuam no repositório,
  referenciados entre si e por um teste (`tests/usuarios/usuarios-view.test.ts`),
  criando um caminho de código morto ou semi-morto que ainda compila e
  ainda é testado, mas não é mais alcançável pela navegação real do
  usuário.
- **Duplicação de tipos de Usuário:** três arquivos de tipos coexistem
  (`usuario.ts` legado, `usuario-domain.ts` real, `usuario-api.ts`
  contrato), sem nenhum deles ser formalmente marcado como obsoleto.
- **Mocks com universos de ID divergentes:** `usuario-mock.ts`,
  `equipe-mock.ts` e `trafego-mock.ts` definem, cada um, seu próprio
  conjunto de IDs de Departamento e Equipe, sem nenhuma fonte única.
- **Equipes sem qualquer integração real:** todo o módulo de Equipes no
  frontend opera 100% sobre mock, mesmo com o backend de `/equipes` maduro
  e testado (448 linhas de teste em `test_equipes.py`).
- **Ausência de telas para entidades já persistidas:** Departamento e
  Cargo têm CRUD completo, testado e protegido por RBAC no backend, mas
  zero superfície de UI — o "Checklist obrigatório" descrito no
  `CLAUDE.md` raiz (rota, view, componentes, tipos, mocks, menu) nunca foi
  percorrido para essas duas entidades do lado frontend.
- **Vocabulário de perfil duplicado e não sincronizado:** `PerfilAcesso`
  (frontend, 9 valores decorativos) e `perfil_base` (backend, 3 valores
  reais) não têm nenhum mapeamento formal nem teste de compatibilidade
  entre si.
- **Vocabulário de status não uniforme entre tabelas de vínculo e entre
  entidades de catálogo** (detalhado na seção 4.3 e 8.4).
- **Papel `coordenador` sem definição de domínio** em `usuario_equipes`
  (seção 8.4).
- **Head/Gestor/Líder sem eventos de domínio dedicados:** o Event Store
  (`event_types.py`) só registra eventos genéricos de vínculo
  (`usuario_departamento.*`, `usuario_equipe.*`), não eventos semânticos
  como "Head atribuído" ou "Head substituído" previstos na seção 9.3 do
  Documento 13.
- **Ciclo de vida de Empresa bloqueado por código fixo (403):** não é uma
  falha, mas é uma dívida de rastreabilidade — a razão do bloqueio
  ("indisponível nesta etapa") está apenas em string de erro HTTP, não em
  documentação ou flag versionada.
- **Contatos com campo `cargo` textual fora do domínio organizacional**
  (`ClienteFormSections.tsx`, `FornecedorFormSections.tsx`,
  `conta-mock.ts`): não violam o Documento 13 por si (contato comercial não
  é Usuário), mas o nome do campo é idêntico ao conceito organizacional de
  Cargo, o que é uma fonte de confusão terminológica já antecipada pela
  seção 13.11 do Documento 13.

## 10. Plano de Convergência

Distribuição das divergências e dívidas registradas nas seções 8 e 9 entre
as etapas já definidas pelo Documento 14 (seção 5). Nenhuma etapa nova é
criada; nenhuma etapa existente é alterada.

### TF-ORG-002.2 — Departamentos

- Confirmar se `sigla` (prevista no Documento 10, ausente no model atual)
  deve ser incluída no escopo desta etapa.
- Avaliar a ausência de tela de frontend para Departamento (seção 8.3) como
  parte do resultado esperado desta etapa ou de TF-ORG-002.8.
- Unicidade de nome/código não particionada por status (registros
  arquivados bloqueiam reuso) — avaliar se está dentro do escopo desta
  etapa ou é aceitável como está.

### TF-ORG-002.3 — Equipes

- Ausência de `departamento_id` em `equipes` (seção 8.3, divergência
  central da etapa, já antecipada pelo Documento 13 seção 13.3).
- Ausência de `tipo_vinculo`/distinção de convidado em `usuario_equipes`
  (seção 8.3).
- Papel `coordenador` sem definição de domínio (seção 8.4) — decidir se é
  tratado nesta etapa ou levado a revisão do Documento 13.
- `EquipeDraft.departamentoId` no mock de frontend, hoje desconectado da
  entidade real — avaliar convergência ou remoção controlada junto com
  TF-ORG-002.9.
- Vocabulário de status `ativo`/`encerrado` divergente de
  `ativo`/`inativo` usado pelos demais vínculos (seção 8.4) — decidir se a
  consolidação de vocabulário (Documento 13, 13.8) é tratada aqui ou em
  TF-ORG-002.5.
- `EquipesView.tsx` sem qualquer integração com `/equipes` — resultado
  esperado desta etapa é "compatibilidade operacional preservada"; a
  integração real do frontend, no entanto, pertence a TF-ORG-002.8.

### TF-ORG-002.4 — Cargos

- Ausência de tela de frontend para Cargo (seção 8.3).
- Ausência de `familia`/`categoria` (prevista no Documento 10, ausente no
  model atual) — confirmar se está no escopo.
- Campo `cargo` textual em Cliente/Fornecedor/`conta-mock.ts` não é Cargo
  organizacional, mas gera confusão terminológica (seção 9) — registrar
  como fora de escopo desta etapa, já que não pertence ao domínio de
  Usuário interno.

### TF-ORG-002.5 — Vínculos

- Head e Gestor organizacional como valor de `papel` em vez de
  responsabilidade própria com histórico e eventos dedicados (seção 8.2,
  divergência central desta etapa, já antecipada pela seção 13.2 do
  Documento 13).
- Líder de Equipe na mesma situação (seção 8.2).
- Consolidação do vocabulário de `status` entre `usuario_departamentos`,
  `usuario_cargos` e `usuario_equipes` (seção 4.3, 8.4).
- Ausência de eventos de domínio dedicados a Head/Gestor/Líder no Event
  Store (seção 9).

### TF-ORG-002.6 — Contexto organizacional

- Ausência de uma visão consolidada por Usuário combinando Departamento
  principal, Equipe principal, Cargo principal e responsabilidades (seção
  8.3) — resultado esperado central desta etapa.
- Definição de como resolver a ausência de campo `sigla`/`familia` e outros
  campos previstos no Documento 10 mas ausentes hoje, caso afetem o
  contrato de contexto organizacional.

### TF-ORG-002.7 — Integração Backend

- Nenhuma rota de consulta organizacional agregada existe hoje
  (`/organizacao/*` do Documento 11) — avaliar se pertence a esta etapa.
- Garantir que o contexto organizacional (de TF-ORG-002.6) seja exposto de
  forma consistente antes de qualquer consumo por frontend.

### TF-ORG-002.8 — Integração Frontend

- Reconectar (ou substituir) a trilha de Usuário para expor dados
  organizacionais reais, hoje ausentes da trilha remota (seção 8.2).
- Construir a primeira integração real de Equipes com `/equipes` (seção
  8.3) — atualmente 100% mock.
- Construir as primeiras telas de Departamento e Cargo (seção 8.3).
- Resolver o vocabulário de `PerfilAcesso` (9 valores decorativos) frente a
  `perfil_base` real (3 valores) antes de qualquer novo uso desse gate em
  telas organizacionais (seção 8.4).
- Substituir os universos de ID divergentes de mock (`usuario-mock.ts`,
  `equipe-mock.ts`, `trafego-mock.ts`) por uma fonte real única, começando
  pelos módulos que esta etapa efetivamente tocar.

### TF-ORG-002.9 — Legados

- Remoção controlada de `useUsuarioDraft.ts`, `UsuarioFormSections.tsx`,
  `UsuarioEditFormBody.tsx` e do teste associado, após confirmação de que
  nenhum consumidor ativo depende deles (seção 9, "ilha de código legado").
- Remoção controlada de `UsuarioDraft`, `DepartamentoOption`,
  `PermissaoItem` e tipos relacionados em `types/usuario.ts`, quando não
  houver mais consumidor.
- Remoção controlada de `EquipeDraft.departamentoId` e do universo de mock
  de Equipes, após a integração real de TF-ORG-002.8.
- Avaliação do campo `cargo`/`departamento` texto livre em
  `conta-mock.ts` (usuário logado mockado) frente ao contexto organizacional
  real disponibilizado por TF-ORG-002.6/002.7.
- Atualização de status desta documentação e do `PROJECT_STATUS.md` para
  refletir a convergência concluída.

## 11. Fontes analisadas

### Documentação

- `docs/arquitetura-taskfloww/13-dominio-organizacional-oficial.md`
- `docs/arquitetura-taskfloww/14-plano-implementacao-organizacao.md`
- `docs/arquitetura-taskfloww/09-diagnostico-estrutura-organizacional.md`
- `docs/arquitetura-taskfloww/10-modelo-dominio-organizacao.md`
- `docs/arquitetura-taskfloww/11-plano-implementacao-organizacao.md`
- `CLAUDE.md` (raiz), `docs/CLAUDE.md`, `frontend/AGENTS.md`

### Backend

- `backend/app/models/` (todos os arquivos)
- `backend/app/schemas/` (arquivos organizacionais)
- `backend/app/services/` (arquivos organizacionais)
- `backend/app/repositories/` (arquivos organizacionais)
- `backend/app/api/routes/usuarios.py`, `departamentos.py`, `cargos.py`,
  `equipes.py`, `agencias.py`, `empresas.py`, `usuario_departamentos.py`,
  `usuario_cargos.py`, `usuario_equipes.py`
- `backend/app/dependencies/authorization.py`, `auth.py`
- `backend/app/domain/event_types.py`
- `backend/app/cli/`
- `backend/alembic/versions/` (todas as migrations)
- `backend/tests/` (listagem completa; leitura de estrutura, não de
  conteúdo integral)

### Frontend

- `frontend/src/types/usuario.ts`, `usuario-domain.ts`, `usuario-api.ts`,
  `equipe.ts`, `auth.ts`
- `frontend/src/lib/usuario-mock.ts`, `equipe-mock.ts`, `conta-mock.ts`,
  `access-control.ts`, `trafego-mock.ts`, `projetos-mock.ts`,
  `demandas-mock.ts`
- `frontend/src/lib/api/usuarios.ts`, `usuarios-client.ts`, `backend.ts`,
  `errors.ts`
- `frontend/src/lib/domain/`, `frontend/src/lib/auth/`
- `frontend/src/components/usuarios/` (todos os arquivos)
- `frontend/src/components/equipes/` (todos os arquivos)
- `frontend/src/app/` (estrutura de rotas completa)
- `frontend/src/app/api/usuarios/` (BFF)
- `frontend/tests/usuarios/`, `frontend/tests/auth/` (listagem)

## 12. Encerramento

Este documento não autoriza nenhuma implementação. Seu único propósito é
registrar, de forma verificável, o estado atual do repositório em relação
ao domínio organizacional oficial (Documento 13), organizado segundo a
sequência do plano oficial (Documento 14), para uso do Codex nas próximas
subtarefas do TF-ORG-002.
