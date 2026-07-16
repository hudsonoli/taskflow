# 10 — Modelo de Domínio da Organização

> Documento conceitual de modelagem. Não é DDL, não é migration e não altera código.
> Este documento define o alvo para Empresa, Agência, Usuário, Cargo/Função,
> Departamento, Equipe, Squad, Head, gestores, vínculos e permissões.

## 1. Decisões fechadas

1. **Empresa é a raiz de isolamento dos dados.**
   Todos os registros de negócio e organização devem possuir `empresa_id`.

2. **Agência não compete com Empresa.**
   Agência deve ser cadastro opcional subordinado à Empresa. Pode representar uma unidade operacional, filial, marca ou núcleo de atendimento da mesma empresa, mas nunca uma segunda raiz de isolamento.

3. **Usuário pode participar de múltiplos Departamentos.**
   O vínculo principal fica em `usuario_departamentos.principal = true`, com uma regra de unicidade para permitir apenas um vínculo principal ativo por usuário/empresa.

4. **Head não é entidade nem perfil.**
   Head é um usuário com perfil-base compatível com gestão, cargo/função apropriado e vínculo formal com Departamento.

5. **Head não deve ser representado apenas por `departamento.head_usuario_id`.**
   A autoridade de Head deve ser registrada em vínculo com vigência, histórico e prevenção de duplicidade.

6. **Cargo/Função é cadastro configurável por Empresa.**
   Não deve ser enum fixo nem texto livre no usuário.

7. **Cargo não concede permissão automaticamente.**
   Permissão vem de perfil-base, escopo, regras específicas e eventuais permissões temporárias.

8. **Departamento, Equipe e Squad são conceitos distintos.**
   Departamento é estrutura formal; Equipe é agrupamento operacional geralmente subordinado a um Departamento; Squad é agrupamento transversal e multidisciplinar.

9. **Equipe normalmente pertence a um Departamento, mas pode ter membros convidados de outros Departamentos.**
   A regra normal é vínculo operacional a um Departamento; exceções devem aparecer explicitamente no vínculo de membro.

10. **Todos os vínculos usam IDs, status e datas de vigência quando aplicável.**
    Não usar `squad` como string, departamento por nome ou cargo por texto livre no usuário.

11. **Usuários externos não entram automaticamente em `usuarios` nesta fase.**
    Na primeira fase, `usuarios` representa colaboradores internos ou prestadores vinculados operacionalmente à Empresa. Contatos de Clientes não se tornam automaticamente usuários autenticáveis; a autenticação de clientes/usuários externos será tratada em fase própria.

## 2. Empresa e Agência

### Empresa

**Responsabilidade:** raiz de tenant e isolamento lógico dos dados.

**Campos principais:**

- `id`
- `nome`
- `documento`
- `codigo_interno`
- `status`
- `created_at`
- `updated_at`
- `inativado_at`
- `inativado_por_usuario_id`
- `motivo_inativacao`

**Status:** `ativa`, `inativa`, `arquivada`.

**Relacionamentos:** possui usuários, cargos, departamentos, equipes, squads, clientes, projetos, tarefas, eventos e agências.

**Índices e constraints:**

- `UNIQUE (documento)` quando aplicável.
- `UNIQUE (codigo_interno)`.
- Índice por `status`.

**Soft delete:** Empresa não deve ser removida em operação normal. Inativação ou arquivamento devem registrar data, motivo e usuário responsável.

**Eventos:**

- `empresa.criada`
- `empresa.alterada`
- `empresa.inativada`
- `empresa.reativada`
- `empresa.arquivada`

**Permissões mínimas:** somente Admin pode criar/inativar/arquivar; Gestor pode consultar conforme escopo; Operador não gerencia empresa.

### Agência

**Responsabilidade:** cadastro opcional subordinado à Empresa para unidade operacional, filial, marca ou núcleo.

**Campos principais:**

- `id`
- `empresa_id`
- `nome`
- `documento`
- `tipo` (`unidade_operacional`, `filial`, `marca`, `outro`)
- `status`
- `created_at`
- `updated_at`
- `inativado_at`
- `inativado_por_usuario_id`
- `motivo_inativacao`

**Regra:** Agência pode segmentar operação e relatórios, mas o isolamento principal continua em `empresa_id`.

**Eventos:** `agencia.criada`, `agencia.alterada`, `agencia.inativada`.

## 3. Usuários

### usuarios

**Responsabilidade:** representar colaboradores internos ou prestadores vinculados operacionalmente à Empresa, com ou sem acesso ao sistema.

**Campos principais:**

- `id`
- `empresa_id`
- `codigo_interno`
- `nome`
- `email`
- `perfil_base`
- `acesso_sistema`
- `status`
- `created_at`
- `updated_at`
- `inativado_at`
- `inativado_por_usuario_id`
- `motivo_inativacao`

**Perfil-base:** `admin`, `gestor`, `operador`.

**Observação:** `Cliente`, `Financeiro`, `Atendimento`, `Head`, `Diretor de Arte`, `Redator` e `Analista de Mídia` não devem ser tratados como novos perfis-base obrigatórios nesta arquitetura. Eles são cargos, funções, experiências de uso ou escopos específicos.

**Usuários externos:** contatos comerciais de Clientes não devem ser promovidos automaticamente para `usuarios`. Uma pessoa de contato pode continuar existindo como contato do Cliente sem credencial, sessão ou permissão. Quando houver portal de cliente ou acesso externo, a identidade autenticável deve ser desenhada em fase própria para não misturar contato comercial com usuário operacional da Empresa.

**Status:** `ativo`, `inativo`, `bloqueado`, `arquivado`.

**Índices e constraints:**

- `UNIQUE (empresa_id, email)`.
- `UNIQUE (empresa_id, codigo_interno)`.
- Índices por `empresa_id`, `perfil_base`, `status`.

**Soft delete:** usuário deve ser inativado ou arquivado. A remoção física não é operação normal.

**Eventos:**

- `usuario.criado`
- `usuario.alterado`
- `usuario.inativado`
- `usuario.reativado`
- `usuario.bloqueado`
- `usuario.arquivado`

## 4. Cargo/Função

### cargos

**Responsabilidade:** catálogo configurável por Empresa para posição organizacional e experiência de uso.

**Exemplos:**

- Head de Mídia
- Redator
- Diretor de Arte
- Atendimento
- Analista de Mídia

**Campos principais:**

- `id`
- `empresa_id`
- `nome`
- `descricao`
- `familia` ou `categoria`
- `status`
- `created_at`
- `updated_at`
- `inativado_at`
- `inativado_por_usuario_id`
- `motivo_inativacao`

**Decisão:** Cargo deve ser tabela configurável, não enum e não campo simples em `usuarios`.

**Justificativa:** cargos variam por empresa, por nomenclatura interna e por evolução operacional. Um enum exigiria release para mudar a lista; texto livre geraria grafias divergentes e impediria filtros confiáveis.

**Constraints:**

- `UNIQUE (empresa_id, nome)` para cargos ativos.

### usuario_cargos

**Responsabilidade:** vínculo histórico entre usuário e cargo.

**Campos principais:**

- `id`
- `empresa_id`
- `usuario_id`
- `cargo_id`
- `principal`
- `status`
- `inicio_em`
- `fim_em`
- `atribuido_por_usuario_id`
- `removido_por_usuario_id`
- `motivo`
- `created_at`
- `updated_at`

**Regra:** permitir múltiplos cargos, mas apenas um cargo principal ativo por usuário/empresa.

**Status:** `ativo`, `inativo`.

**Índices e constraints:**

- `UNIQUE (usuario_id, cargo_id) WHERE status = 'ativo'`.
- `UNIQUE (empresa_id, usuario_id) WHERE principal = true AND status = 'ativo'`.
- `fim_em >= inicio_em` quando `fim_em` existir.

**Eventos:**

- `cargo.atribuido`
- `cargo.removido`
- `cargo_principal.alterado`

## 5. Departamentos

### departamentos

**Responsabilidade:** estrutura formal da Empresa.

**Campos principais:**

- `id`
- `empresa_id`
- `codigo_interno`
- `nome`
- `sigla`
- `descricao`
- `status`
- `created_at`
- `updated_at`
- `inativado_at`
- `inativado_por_usuario_id`
- `motivo_inativacao`

**Status:** `ativo`, `inativo`, `arquivado`.

**Índices e constraints:**

- `UNIQUE (empresa_id, nome)` para ativos.
- `UNIQUE (empresa_id, sigla)` para ativos.
- `UNIQUE (empresa_id, codigo_interno)`.

**Soft delete:** inativar ou arquivar, preservando histórico e vínculos encerrados.

**Eventos:** `departamento.criado`, `departamento.alterado`, `departamento.inativado`, `departamento.arquivado`.

### usuario_departamentos

**Responsabilidade:** vínculo de usuários com Departamentos, incluindo o Departamento principal.

**Campos principais:**

- `id`
- `empresa_id`
- `usuario_id`
- `departamento_id`
- `principal`
- `status`
- `inicio_em`
- `fim_em`
- `atribuido_por_usuario_id`
- `removido_por_usuario_id`
- `motivo`
- `created_at`
- `updated_at`

**Status:** `ativo`, `inativo`.

**Índices e constraints:**

- `UNIQUE (usuario_id, departamento_id) WHERE status = 'ativo'`.
- `UNIQUE (empresa_id, usuario_id) WHERE principal = true AND status = 'ativo'`.
- Índices por `departamento_id`, `usuario_id`, `status`.

**Eventos:**

- `usuario.departamento_vinculado`
- `usuario.departamento_removido`
- `usuario.departamento_principal_alterado`

### departamento_gestores

**Responsabilidade:** registrar Head principal e gestores adicionais com vigência.

**Campos principais:**

- `id`
- `empresa_id`
- `departamento_id`
- `usuario_id`
- `tipo` (`head_principal`, `gestor_adicional`)
- `status`
- `inicio_em`
- `fim_em`
- `atribuido_por_usuario_id`
- `removido_por_usuario_id`
- `motivo`
- `created_at`
- `updated_at`

**Regra de Head principal:**

- Um Departamento deve ter no máximo um Head principal ativo.
- Um usuário pode ser Head principal de mais de um Departamento.
- Head principal deve ter vínculo ativo com o Departamento, preferencialmente como vínculo principal ou vínculo formal ativo.

**Gestores adicionais:**

- Podem existir vários por Departamento.
- Não devem duplicar o mesmo usuário e tipo no mesmo período ativo.

**Índices e constraints:**

- `UNIQUE (departamento_id) WHERE tipo = 'head_principal' AND status = 'ativo'`.
- `UNIQUE (departamento_id, usuario_id, tipo) WHERE status = 'ativo'`.
- `fim_em >= inicio_em` quando `fim_em` existir.

**Eventos:**

- `departamento.head_definido`
- `departamento.head_substituido`
- `departamento.gestor_adicional_incluido`
- `departamento.gestor_adicional_removido`

## 6. Equipes

### equipes

**Responsabilidade:** agrupamento operacional normalmente associado a um Departamento.

**Campos principais:**

- `id`
- `empresa_id`
- `departamento_id`
- `codigo_interno`
- `nome`
- `sigla`
- `descricao`
- `responsavel_usuario_id`
- `status`
- `created_at`
- `updated_at`
- `inativado_at`
- `inativado_por_usuario_id`
- `motivo_inativacao`

**Regra:** Equipe tem um Departamento de referência. Membros convidados de outros Departamentos podem existir via `equipe_membros.tipo_vinculo`.

**Status:** `ativa`, `inativa`, `arquivada`.

**Constraints:**

- `UNIQUE (empresa_id, nome)` para ativas.
- `UNIQUE (empresa_id, sigla)` para ativas.

**Eventos:** `equipe.criada`, `equipe.alterada`, `equipe.inativada`, `equipe.arquivada`.

### equipe_membros

**Responsabilidade:** vínculo entre usuários e Equipes.

**Campos principais:**

- `id`
- `empresa_id`
- `equipe_id`
- `usuario_id`
- `papel`
- `tipo_vinculo` (`membro_departamento`, `convidado`)
- `status`
- `inicio_em`
- `fim_em`
- `incluido_por_usuario_id`
- `removido_por_usuario_id`
- `motivo`
- `created_at`
- `updated_at`

**Constraints:**

- `UNIQUE (equipe_id, usuario_id) WHERE status = 'ativo'`.
- `fim_em >= inicio_em` quando `fim_em` existir.

**Eventos:**

- `equipe.membro_incluido`
- `equipe.membro_removido`
- `equipe.membro_papel_alterado`

## 7. Squads

### squads

**Responsabilidade:** agrupamento transversal e multidisciplinar.

**Campos principais:**

- `id`
- `empresa_id`
- `codigo_interno`
- `nome`
- `sigla`
- `descricao`
- `status`
- `created_at`
- `updated_at`
- `inativado_at`
- `inativado_por_usuario_id`
- `motivo_inativacao`

**Regra:** Squad não pertence obrigatoriamente a um Departamento. Sua composição transversal vem dos membros.

**Status:** `ativa`, `inativa`, `arquivada`.

**Constraints:**

- `UNIQUE (empresa_id, nome)` para ativas.
- `UNIQUE (empresa_id, sigla)` para ativas.

**Eventos:** `squad.criada`, `squad.alterada`, `squad.inativada`, `squad.arquivada`.

### squad_membros

**Responsabilidade:** vínculo entre usuários e Squads.

**Campos principais:**

- `id`
- `empresa_id`
- `squad_id`
- `usuario_id`
- `papel`
- `status`
- `inicio_em`
- `fim_em`
- `incluido_por_usuario_id`
- `removido_por_usuario_id`
- `motivo`
- `created_at`
- `updated_at`

**Constraints:**

- `UNIQUE (squad_id, usuario_id) WHERE status = 'ativo'`.
- `fim_em >= inicio_em` quando `fim_em` existir.

**Eventos:**

- `squad.membro_incluido`
- `squad.membro_removido`
- `squad.membro_papel_alterado`

## 8. Permissões

### Conceitos

- Perfil-base: autorização ampla inicial (`admin`, `gestor`, `operador`).
- Cargo/Função: posição organizacional e experiência de uso.
- Escopo: limite de atuação por empresa, cliente, projeto, departamento, equipe ou squad.
- Permissão específica: ação sobre recurso.
- Permissão temporária: concessão com validade.

### Tabelas futuras mínimas

- `permissoes`
- `usuario_permissoes`
- `permissoes_temporarias`

**Eventos:**

- `permissao.concedida`
- `permissao.revogada`
- `permissao_temporaria.concedida`
- `permissao_temporaria.revogada`

## 9. Consultas suportadas

O modelo acima deve suportar:

- Minha Pauta: tarefas em que o usuário é responsável/participante.
- Pauta do Departamento: tarefas dos Departamentos ativos do usuário.
- Pauta da Squad: tarefas das Squads ativas do usuário.
- Pauta do Head: tarefas dos Departamentos em que o usuário é Head principal ou gestor adicional.
- Pauta Geral: visão permitida por perfil e escopo.
- Responsáveis disponíveis: usuários ativos da Empresa, filtráveis por Departamento, Equipe, Squad, cargo e escopo.
- Carga de trabalho: agregação por usuário, Departamento, Equipe e Squad.
- Dashboards por papel.

## 10. Experiência por papel

| Papel/experiência | Foco |
|---|---|
| Usuário/Operador | própria pauta, tarefas e etapas, pouca exposição a métricas globais |
| Head/Gestor | Departamento, Equipes, Squads, carga, gargalos e redistribuição |
| Atendimento | Clientes, Projetos, prazos, aprovações e SLA |
| Admin | estrutura, cadastros, permissões e auditoria |

Atendimento deve ser cargo/função ou experiência de interface, não perfil-base obrigatório.

## 11. Decisões pendentes

1. Se Agência será usada apenas como unidade operacional genérica ou se terá subtipos obrigatórios de filial/marca.
2. Como será a fase própria de autenticação de clientes/usuários externos, sem misturar contato comercial com identidade autenticável.
3. Como mapear os perfis atuais do frontend (`Owner`, `SuperAdmin`, `Admin`, `Diretoria`, `Gerente`, `Gestor`, `Financeiro`, `Operador`, `Cliente`) para os perfis-base alvo.
4. O escopo exato da primeira versão de permissões por recurso e permissões temporárias após a autenticação mínima.
5. Se `usuario_cargos` já nascerá com múltiplos cargos na primeira migration ou se a UI inicial limitará a edição a um cargo principal, mantendo o schema preparado.
