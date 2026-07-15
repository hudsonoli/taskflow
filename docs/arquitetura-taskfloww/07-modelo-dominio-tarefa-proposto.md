# 07 — Modelo de Domínio da Tarefa (Proposto)

> Documento conceitual de modelagem de dados. Não é migration, não é DDL, não altera código nem schema atual.
> Base: [`06-diagnostico-entidade-tarefa-atual.md`](./06-diagnostico-entidade-tarefa-atual.md) e
> [`02-modelo-dados-futuro.md`](./02-modelo-dados-futuro.md) — este documento **estende** `02`, não o substitui.
> Entidades já detalhadas em `02` (`Checklist`, `ChecklistItem`, `Anexo`, `Comentario`, `Evento`,
> `EtapaSessaoTempo`, `SlaRegra`, `Tag`, `FiltroSalvo`, `Notificacao`) não são redetalhadas aqui — apenas
> referenciadas onde a Tarefa as usa. Este documento cobre exclusivamente o que é **novo ou diferente**
> em relação a `02`, motivado pelo modelo funcional oficial definido para a Tarefa.
> "Campos principais" é descrito em prosa, não em `CREATE TABLE`. Tipos são indicativos, a confirmar na implementação.
> **Revisão 2** (esta versão): incorpora as 12 decisões funcionais oficiais aprovadas após a auditoria de `06`
> (ver seção 0.1). A revisão anterior deste documento tratava nome de código, Squad-vs-Equipe, e dependência
> de autenticação para Pautas como pendências em aberto — todas essas pendências foram resolvidas nesta revisão.

---

## 0. O que muda em relação a `02-modelo-dados-futuro.md`

`02` já propunha `DemandaEtapa`, `Workflow`, `WorkflowEtapaTemplate`, `WorkflowRegraTransicao`, `Responsavel` (com `tipoResponsavel: usuario | departamento | equipe`). O modelo funcional oficial (ver `06`, seção 7, e as decisões da seção 0.1 abaixo) exige extensões que `02` **não cobria**:

| # | Extensão exigida | Por quê `02` não cobre |
|---|---|---|
| 1 | `Squad` como entidade própria, distinta de `Equipe` **e** de `Departamento` | `02` só previa `equipe` como valor de `Responsavel.tipoResponsavel`; o modelo oficial trata Squad como terceiro conceito organizacional, transversal a departamentos |
| 2 | Distinção entre **Responsável principal**, **Responsáveis**, **Participantes** e regra de **elegibilidade ampla** de atribuição | `02.Responsavel` não tinha papel diferenciado nem regra de quem pode ser atribuído |
| 3 | **Ciclo de revisão** com 6 resultados possíveis, dentro da mesma etapa | `02` não modela ciclos dentro de uma etapa — só transição entre etapas |
| 4 | **Nome de revisão configurável por empresa**, conceito técnico fixo | Não modelado em `02` |
| 5 | **Versionamento de Workflow** | `02.WorkflowEtapaTemplate` só resolvia via snapshot campo-a-campo, sem versionar o `Workflow` como um todo |
| 6 | **Pautas** (Minha, Departamento, Squad, Head, Geral) e **Minha Pauta de Hoje** (dashboard) | Não mencionado em `02` |
| 7 | **Departamento com `headUsuarioId` e gestores adicionais**; "Head" como papel de Usuário, não entidade | `02` tratava Departamento só como referência simples (`DepartamentoOption`) |
| 8 | **`Usuario.cargo`** (função/cargo, distinto de `perfil`/RBAC) | Não existia em `02` nem no tipo atual |
| 9 | **`WorkflowEtapaTemplate`/`TarefaEtapa` com 10 campos de regra de etapa** (tipo, responsáveis padrão, ações, prazo relativo, etapa final etc.) | `02` modelava só nome/ordem/prazo/aprovação booleana |
| 10 | **Permissão por escopo e temporária** | `02` não modelava permissão |
| 11 | **Autenticação real antecipada para a Fundação** (não só bloqueante futuro) | `02`/`03` tratavam autenticação como fora de escopo geral do projeto |

Este documento usa **`Tarefa`** como nome de código-alvo (decisão 1, seção 0.1) — a implementação atual (`Demanda`) é renomeada de forma progressiva, não por substituição global cega; a estratégia de renomeação está detalhada em `08`, Subtarefa 0.

---

## 0.1 Decisões oficiais incorporadas nesta revisão

| # | Decisão (resumo) | Onde está refletida neste documento |
|---|---|---|
| 1 | Nome oficial = `Tarefa` (produto, código novo, API, banco); renomeação progressiva, não substituição cega | Seção 0; estratégia detalhada em `08`, Subtarefa 0 |
| 2 | Departamento é entidade e cadastro próprio | Seção 3 (extensão sobre `02`) |
| 3 | Head não é entidade nem perfil — é Usuário com perfil Gestor + cargo "Head", responsável por 1+ Departamentos; Departamento tem `headUsuarioId` e gestores adicionais | Seção 3, seção 4 |
| 4 | Squad permanece entidade própria, transversal a departamentos; diferença clara entre Departamento/Equipe/Squad | Seção 5 |
| 5 | Atribuição de Tarefa/etapa: qualquer usuário ativo da empresa dentro do escopo de permissão; participar do Projeto não é pré-requisito; membros de Projeto/Departamento/Squad são só sugestão priorizada | Seção 6.1 |
| 6 | Projeto/Campanha tem prazo/período opcional; prazo operacional obrigatório fica na Tarefa/etapa; Projeto exibe Tarefas por status + histórico agregado | Seção 2, seção 8, seção 10 |
| 7 | Revisão com 6 resultados (aprovado, ajuste solicitado, refação parcial, refação completa, reprovado, cancelado) + origem, motivo, comentário, arquivos/versões, responsável, novo prazo, tratamento de checklist; nome configurável, conceito técnico fixo (`Revisao`) | Seção 7.5 |
| 8 | `WorkflowEtapaTemplate`/`TarefaEtapa`: tipo de etapa, responsáveis padrão, departamento/squad padrão, requisitos obrigatórios, ação ao aprovar/ajustar, etapa de retorno ao reprovar, permissão de avanço, prazo relativo, etapa final | Seção 7.3, seção 7.4 |
| 9 | Experiência por papel (Operador, Head/Gestor, Atendimento, Admin); Atendimento é cargo/experiência, não novo perfil-base | Seção 4, seção 12 |
| 10 | Dashboard: "Minha Pauta de Hoje" no lugar de Atividades Recentes; métricas gerais não indiscriminadas para operacional | Seção 9, seção 11 |
| 11 | Autenticação real e usuário atual entram cedo na Fundação, não só como bloqueante futuro | Seção 9 (pré-requisitos atualizados); detalhado em `08`, Fase A |
| 12 | Plano mantém entregas pequenas, critérios de aceite e dependências explícitas | Aplicado em `08` |

---

## 1. Entidades já cobertas por `02`, sem alteração de forma

`Empresa/Agência`, `Usuario` (com a extensão da seção 4), `Cliente`, `Fornecedor`, `GrupoDeClientes`, `Checklist`/`ChecklistItem`, `Anexo`, `Comentario`, `Evento`, `EtapaSessaoTempo`, `SlaRegra`, `Tag`/`EntidadeTag`, `FiltroSalvo`, `Notificacao`/`PreferenciaNotificacao` — mantidas como descritas em `02`, apenas trocando `entidadeTipo = demanda` por `entidadeTipo = tarefa` nos pontos de associação polimórfica. **`Departamento` deixa de estar nesta lista** — ganha extensão própria na seção 3, por decisão 3.

---

## 2. `Projeto`

Em relação a `02`/tipo atual (`types/projeto.ts`):

- **Prazo opcional (decisão 6)**: `dataInicio` e `dataFimPrevista` passam de obrigatórios para **nullable** — um Projeto/Campanha pode existir sem prazo definido ou só com uma ponta do período preenchida. O prazo **operacional obrigatório** continua exclusivamente em `Tarefa.dataFimPrevista` e em `TarefaEtapa` (ver seção 8) — essa distinção é uma regra de negócio explícita, não um detalhe incidental.
- **Resumo de Tarefas por status (decisão 6)**: o Projeto passa a expor uma projeção `TarefaStatusResumo` (não é tabela própria — é uma consulta agregada sobre `Tarefa`/`RevisaoCiclo`, mesmo princípio de Histórico/Timeline em `02`, seção 6.2-6.3) com 5 categorias: **ativas, pausadas, aguardando aprovação, concluídas, canceladas** — ver derivação exata na seção 8.
- **Rollup de histórico** (seção 10) passa a incluir eventos das Tarefas filhas.
- `ProjetoModeloCampanhaItem.tipoTarefaId` deixa de ser texto solto e passa a referenciar `TipoTarefa` real (hoje `/configuracoes/tipos-tarefa` é 100% hardcoded — ver `06`, seção 2).
- `ProjetoEquipeMembro` (`Projeto.equipe`) deixa de ter qualquer papel de restrição sobre quem pode ser atribuído a uma Tarefa do projeto — passa a ser puramente uma lista de sugestão (ver seção 6.1, decisão 5).

---

## 3. `Departamento` — extensão (decisões 2 e 3)

`02` tratava Departamento apenas como referência simples, herdando o que já existia informalmente em `DepartamentoOption` (`types/usuario.ts`). A decisão 2 confirma Departamento como **entidade e cadastro próprio** (já era o plano — Fase 3.14 do `PROJECT_STATUS.md`); a decisão 3 acrescenta uma responsabilidade nova, específica: liderança formal.

- **Campos principais adicionais**: `headUsuarioId (uuid, FK → Usuario, nullable)`.
- **Regra de "Head" (decisão 3, importante)**: **Head não é uma entidade nem um valor de `PerfilAcesso`.** É um `Usuario` com `perfil = Gestor` (ou superior) que ocupa `Departamento.headUsuarioId`. Um mesmo usuário pode ser `headUsuarioId` de **mais de um** Departamento simultaneamente — isso já é suportado naturalmente pela relação N:1 (vários `Departamento` podem apontar para o mesmo `Usuario`), sem necessidade de tabela adicional para esse caso.
- **Restrição**: `headUsuarioId`, quando preenchido, deve referenciar um `Usuario` com `perfil = Gestor` (ou perfil superior na hierarquia — `Admin`, `SuperAdmin`, `Diretoria`, conforme a lista de perfis vigente, ver seção 11) — validação de aplicação, não de banco.

### 3.1 `DepartamentoGestor` (nova)

- **Finalidade**: registrar **gestores adicionais** de um Departamento — usuários com responsabilidade de gestão sobre o departamento além do Head principal (decisão 3: "Departamento deve possuir `headUsuarioId` e gestores adicionais").
- **Campos principais**: `id (uuid)`, `departamentoId (uuid, FK)`, `usuarioId (uuid, FK)`, `atribuidoEm (timestamp)`, `atribuidoPor (uuid → Usuario)`.
- **Relacionamentos**: N:1 `Departamento`; N:1 `Usuario`.
- **Índices**: `UNIQUE (departamentoId, usuarioId)`.
- **Restrições**: um `usuarioId` que já é `Departamento.headUsuarioId` do mesmo departamento não deveria também aparecer em `DepartamentoGestor` para esse departamento (evita duplicidade de papel) — validação de aplicação.
- **Riscos de migração**: nenhum dado hoje — `DepartamentoOption` (`types/usuario.ts:49-53`) não tem nenhum campo de liderança.
- **Compatibilidade com o código atual**: nenhuma.

---

## 4. `Usuario` — extensão (decisões 3 e 9)

- **Campo novo**: `cargo (texto, nullable)` — função/cargo operacional do usuário (ex.: "Head de Criação", "Atendimento", "Redator", "Diretor de Arte"), **distinto de `perfil`** (RBAC — `PerfilAcesso`, seção 11).
- **Natureza do campo — importante**: `cargo` é **metadado descritivo e de roteamento de experiência de produto** (decisão 9 — usado para decidir o que a Home/Dashboard prioriza mostrar), **não é fonte de autorização**. A autoridade de "Head" vem estruturalmente de `Departamento.headUsuarioId`/`DepartamentoGestor` (seção 3), não do texto livre em `cargo` — um usuário pode ter `cargo = "Head"` sem estar em nenhum `headUsuarioId` (nesse caso não tem autoridade real, é só um rótulo desatualizado) e vice-versa (pode ser `headUsuarioId` de um Departamento com `cargo` preenchido com outro texto). A aplicação deve sempre checar a estrutura (`headUsuarioId`), nunca o texto de `cargo`, para decisões de permissão.
- **"Atendimento" (decisão 9)**: mesmo princípio — é um valor de `cargo`, combinável com qualquer `perfil` (tipicamente `Operador` ou `Gestor`), **não um novo valor de `PerfilAcesso`**. Determina a experiência de produto priorizada (seção 12), não uma regra de RBAC nova.
- **Riscos de migração**: nenhum dado hoje (`UsuarioDraft` não tem campo equivalente). Risco de **design**, o mesmo já observado para `squad: string` antes de virar entidade (`06`, conflito #1): texto livre sem catálogo permite grafias divergentes ("Head", "head de criação", "Head Criação"...). Diferente de Squad, este documento **não** propõe transformar `cargo` em entidade agora — mantém como texto simples por ser majoritariamente descritivo — mas registra a recomendação de, se a lista de cargos usados crescer e ganhar peso operacional (ex.: filtros por cargo), avaliar um catálogo `CargoOption` (mesmo padrão de `DepartamentoOption`) no futuro.

---

## 5. `Squad` (entidade própria — decisão 4)

- **Finalidade**: unidade de trabalho multidisciplinar, **transversal a Departamentos**, que pode ser titular de uma Tarefa. Decisão 4 confirma definitivamente que Squad **não** se funde com `Equipe` — permanece entidade irmã, com propósito distinto.
- **Diferença entre Departamento, Equipe e Squad (decisão 4, explícita)**:

| | `Departamento` | `Equipe` | `Squad` |
|---|---|---|---|
| **O que é** | Unidade organizacional formal da empresa (estrutura hierárquica) | Agrupamento formal de pessoas **dentro de um único** Departamento | Agrupamento de trabalho **transversal**, cruzando departamentos |
| **Cardinalidade com Departamento** | — (é a própria unidade) | 1 Equipe → exatamente 1 Departamento (`Equipe.departamentoId`, obrigatório, `types/equipe.ts:33`) | 0..N Departamentos representados entre seus membros — sem FK direta para Departamento |
| **Quem lidera** | `headUsuarioId` + `DepartamentoGestor` (seção 3) — papel estrutural, checável | `Equipe.responsavelId` (já existente) | Sem "head" formal — liderança é só `SquadMembro.papel = "líder"` (metadado, não autoridade estrutural) |
| **Exemplo** | "Criação", "Atendimento", "Mídia" | "Equipe de Redação" (dentro de Criação) | "Squad Cliente Clare" (1 redator de Criação + 1 mídia de Mídia + 1 atendimento) |
| **Uso em Tarefa** | `Responsavel.departamentoId` / `Tarefa.titularidade = departamento` | Hoje sem relação direta com Tarefa | `Responsavel.squadId` / `Tarefa.titularidade = squad` |

- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `nome (texto)`, `sigla (texto)`, `codigoInterno (texto)`, `descricao (texto, nullable)`, `ativa (booleano, default true)`, `createdAt`, `updatedAt`. **Sem `headUsuarioId`** — removido em relação à revisão anterior deste documento: "Head" é termo reservado exclusivamente a Departamento (decisão 3); Squad não tem papel de liderança estrutural equivalente, só o metadado `SquadMembro.papel`.
- **Relacionamentos**: 1:N `SquadMembro`; referenciada por `Responsavel.squadId` (seção 6) e por `Tarefa.titularidade = squad` (seção 8).
- **Índices**: `(empresaId, nome)`.
- **Restrições**: `nome` obrigatório.
- **Riscos de migração**: **nenhum dado a migrar** — o único vestígio hoje é o campo de texto livre `UsuarioDraft.squad` (`types/usuario.ts:63`), que precisa virar dado de seed (uma Squad por valor distinto encontrado) e não uma migração automática confiável.
- **Compatibilidade com o código atual**: nenhuma estrutural — `squad: string` solto em `Usuario` viola a regra de "sempre ID" desde a origem (`06`, conflito #1); é substituído por `SquadMembro`.

### 5.1 `SquadMembro`

- **Campos principais**: `id (uuid)`, `squadId (uuid, FK)`, `usuarioId (uuid, FK)`, `papel (texto, nullable — ex.: "líder", "membro")`, `entradaEm (timestamp)`, `saidaEm (timestamp, nullable)`.
- **Relacionamentos**: N:1 `Squad`; N:1 `Usuario`.
- **Índices**: `UNIQUE (squadId, usuarioId) WHERE saidaEm IS NULL`.
- **Riscos de migração**: nenhum dado a migrar (conceito novo).

---

## 6. `Responsavel` — estendido com papel, Squad e elegibilidade ampla

Reaproveita a base de `02`, seção 2.1, com três mudanças:

- `tipoResponsavel` ganha `squad` como quarto valor: `enum: usuario | departamento | equipe | squad`.
- `squadId (uuid, nullable)` adicionado aos campos, seguindo o padrão de "exatamente um preenchido conforme `tipoResponsavel`".
- `papel` vira **enum fechado**: `principal | apoio | participante`.
  - **Regra**: no escopo `entidadeTipo = tarefa`, deve existir **no máximo um** `Responsavel` com `papel = principal` por tarefa (`UNIQUE (entidadeId) WHERE entidadeTipo = 'tarefa' AND papel = 'principal'`).
  - `apoio` cobre o que hoje é só "responsável" no plural (`usuarioResponsavelIds`).
  - `participante` é o papel que acompanha a tarefa (recebe notificação, aparece na tarefa) sem ser cobrado pela entrega.

Isso substitui, em conjunto, tanto `Demanda.usuarioResponsavelIds`/`departamentoResponsavelIds` quanto a lacuna de "participante" e "responsável principal" apontada em `06`, conflito #2.

### 6.1 Regra de elegibilidade e sugestões priorizadas de atribuição (decisão 5)

- **Regra de domínio**: o conjunto elegível para ser `Responsavel` (qualquer papel) de uma `Tarefa`/`TarefaEtapa` é **todo `Usuario` ativo da empresa** (`acessoSistema = true` e `emAtividade = true`, campos já existentes em `UsuarioDraft`) cujo escopo de permissão (`PermissaoEscopo`, seção 11) autorize leitura/escrita sobre o Cliente/Projeto/Departamento/Squad daquela tarefa. **Participar de `Projeto.equipe` não é pré-requisito** — um usuário fora da equipe nominal do projeto pode ser atribuído normalmente, desde que dentro do escopo de permissão.
- **Regra de UI (não é regra de banco, é comportamento de picker)**: ao abrir o seletor de responsável/participante (hoje `MultiSelect`, `frontend/src/components/ui/MultiSelect.tsx`), a lista deve **priorizar visualmente** — não restringir — três grupos, nesta ordem de sugestão: (1) membros de `Projeto.equipe`, (2) membros do `Departamento` já vinculado à tarefa, (3) membros da `Squad` já vinculada à tarefa; abaixo desses grupos, o restante dos usuários elegíveis permanece disponível sem bloqueio.
- **Implicação para `Responsavel.papel = participante`**: como participante é, por definição, alguém que só acompanha, a regra de elegibilidade ampla é particularmente relevante aqui — é o caso de uso mais comum de "alguém de fora do projeto/departamento/squad precisa ser adicionado" (ex.: um gestor de outra área que quer acompanhar).
- **Riscos de migração**: nenhum dado a migrar. Risco de **design**: se a implementação inicial (antes de `PermissaoEscopo` existir de fato, ver `08`, Fase A/E) liberar "qualquer usuário ativo" sem nenhum filtro de escopo, isso é aceitável como estado transitório, mas deve ser tratado explicitamente como incompleto — não como comportamento final — até `PermissaoEscopo` estar aplicado.

---

## 7. Workflow — versionamento, etapa com regras completas e ciclo de revisão

### 7.1 `Workflow` (revisão de `02`, seção 3.1)

Sem alteração de campos. Ganha a responsabilidade de nunca ser editado in-place depois de ter ao menos uma `Tarefa` ativa vinculada — qualquer edição de etapas cria uma nova `WorkflowVersao` (seção 7.2).

### 7.2 `WorkflowVersao` (nova)

- **Finalidade**: resolver "alterar o modelo de workflow não pode modificar silenciosamente tarefas já iniciadas" — `02` (seção 3.2) mitigava isso só por snapshot campo-a-campo, sem registrar **qual versão** deu origem a cada tarefa.
- **Campos principais**: `id (uuid)`, `workflowId (uuid, FK)`, `numeroVersao (inteiro, sequencial por workflow)`, `vigente (booleano)`, `criadaEm (timestamp)`, `criadaPor (uuid → Usuario)`, `notaMudanca (texto, nullable)`.
- **Relacionamentos**: N:1 `Workflow`; 1:N `WorkflowEtapaTemplate` (etapa passa a pertencer a uma `WorkflowVersao`); referenciada por `Tarefa.workflowVersaoOrigemId`.
- **Índices**: `UNIQUE (workflowId, numeroVersao)`; `UNIQUE (workflowId) WHERE vigente = true`.
- **Restrições**: ao publicar uma nova versão vigente, a anterior vira `vigente = false` automaticamente (transacional); nenhuma `WorkflowVersao` referenciada por `Tarefa.workflowVersaoOrigemId` pode ser apagada (soft-delete apenas).
- **Riscos de migração**: nenhum dado hoje (`/configuracoes/workflows` é hardcoded, sem persistência). Risco de **design**: UI precisa deixar claro, visualmente, quando uma edição gera nova versão.
- **Compatibilidade com o código atual**: nenhuma.

### 7.3 `WorkflowEtapaTemplate` — extensão com 10 campos de regra (decisão 8)

`02` (seção 3.2) modelava só `nome, ordem, prazoHorasPadrao, exigeAprovacao`. A decisão 8 exige que tanto o template quanto a instância (`TarefaEtapa`, seção 7.4) suportem regra completa de etapa:

- `tipoEtapa (enum: execucao | revisao_interna | aprovacao_cliente | entrega | outro)` — natureza da etapa.
- `responsaveisPadrao` — não é um campo escalar; é uma tabela filha `WorkflowEtapaTemplateResponsavelPadrao (id, etapaTemplateId, tipoResponsavel: usuario|departamento|squad, usuarioId/departamentoId/squadId, papel: principal|apoio)`, mesma forma de `Responsavel` (seção 6), mas em nível de template — na instanciação, cada linha é copiada para um `Responsavel` real da nova `TarefaEtapa`.
- `departamentoPadraoId (uuid, nullable)`, `squadPadraoId (uuid, nullable)` — sugestão de **titularidade** padrão da etapa (distinto de `responsaveisPadrao`: estes definem indivíduos específicos, ex.: "sempre revisado por Fulano"; aqueles definem o departamento/squad "dono" padrão da etapa, alimentando `Tarefa.titularidade`/`TarefaEtapa` quando a etapa se torna a etapa atual).
- `requisitosObrigatorios`: `exigeChecklistCompleto (booleano, default false)` + `camposObrigatorios (jsonb, array de nomes de campo, nullable)` — o que precisa estar satisfeito antes de permitir avanço.
- `acaoAoAprovar (enum: avancar_proxima_etapa | concluir_tarefa)`.
- `acaoAoAjustar (enum: permanecer_na_etapa | retornar_etapa_anterior)` — o que acontece quando um `RevisaoCiclo` (seção 7.5) resulta em `ajuste_solicitado`/`refacao_parcial`/`refacao_completa`.
- `etapaRetornoReprovacaoId (uuid, FK → WorkflowEtapaTemplate, nullable)` — para qual etapa a tarefa retorna quando um `RevisaoCiclo` resulta em `reprovado`.
- `permissaoAvancoPerfil (enum de `PerfilAcesso`, nullable)` — perfil mínimo exigido para mover a tarefa para fora desta etapa, além do responsável natural da etapa (reaproveita o espírito de `WorkflowRegraTransicao.perfilAprovador` de `02`, seção 3.3, mas aplicado de forma geral a qualquer avanço, não só aprovação formal).
- `prazoRelativoHoras (inteiro)` — renomeação explícita de `prazoHorasPadrao` (`02`) para deixar claro que é relativo ao momento em que a tarefa entra na etapa, nunca uma data absoluta (a data absoluta só existe em `TarefaEtapa`/`Tarefa.prazoEtapaAtual`, calculada a partir deste valor).
- `etapaFinal (booleano, default false)` — se `true`, um `RevisaoCiclo` com `resultado = aprovado` nesta etapa conclui a Tarefa automaticamente (`Tarefa.status = concluida`).
- **Riscos de migração**: nenhum dado hoje. Risco de **complexidade de UI**: 10 campos por etapa é uma superfície grande para quem só quer montar um workflow simples — recomenda-se, na implementação, esconder os campos avançados (`requisitosObrigatorios`, `acaoAoAjustar`, `etapaRetornoReprovacaoId`, `permissaoAvancoPerfil`) atrás de uma seção "avançado" recolhida por padrão, com valores default sensatos (`acaoAoAprovar = avancar_proxima_etapa`, `acaoAoAjustar = permanecer_na_etapa`) para quem não configura nada.
- **Risco de redundância**: `departamentoPadraoId`/`squadPadraoId` (nível etapa) e `Tarefa.titularidade` (nível tarefa inteira) resolvem "quem é dono por padrão" em granularidades diferentes — a aplicação precisa de uma regra de precedência explícita (recomendação deste documento: a etapa sobrepõe a tarefa quando ambos estão preenchidos e divergem, já que a etapa é mais específica) definida antes da implementação, não descoberta durante.

### 7.4 `TarefaEtapa` (equivalente a `DemandaEtapa` de `02`, seção 3.4, renomeada)

Mesma forma de `02`, mais os 10 campos de 7.3 **snapshotados** no momento da instanciação (mesma filosofia de `02`: mudança futura no template não altera a etapa já instanciada), mais `workflowVersaoOrigemId (uuid, FK → WorkflowVersao, nullable)` — agora registrado no nível da **tarefa** (`Tarefa.workflowVersaoOrigemId`, seção 8), não da etapa individual, para permitir relatórios do tipo "quantas tarefas ainda rodam sob a versão 3 do Workflow X".

### 7.5 `RevisaoCiclo` — 6 resultados e registro completo (decisão 7)

- **Finalidade**: modelar que uma tarefa pode passar por **várias revisões dentro da mesma etapa**, sem mudança de etapa — "aprovação, ajuste, reprovação e refação não devem ser tratados apenas como colunas fixas" (`06`, conflito #3). **O nome exibido ao usuário é configurável por empresa (`NomenclaturaConfiguravel`, seção 7.6); o conceito técnico permanece `RevisaoCiclo`/`Revisao` em qualquer empresa** — decisão 7 é explícita nesse ponto, não é uma sugestão.
- **Campos principais**:
  - `id (uuid)`, `tarefaId (uuid, FK)`, `tarefaEtapaId (uuid, FK → TarefaEtapa)`, `numeroCiclo (inteiro, sequencial por etapa)`.
  - `origem (enum: interno | cliente)` — renomeado de `tipo` (revisão anterior deste documento) para casar com o vocabulário exato da decisão 7 ("registrar origem"). Distingue ajuste solicitado internamente vs. pelo cliente (métrica pedida em `docs/requirements/projetos-demandas-dashboard.md`, seção 6.1).
  - `resultado (enum: pendente | aprovado | ajuste_solicitado | refacao_parcial | refacao_completa | reprovado | cancelado)` — **6 resultados finais + `pendente`** como estado aberto (decisão 7 lista os 6; `pendente` é necessário para representar o ciclo enquanto ainda não foi decidido).
  - `motivo (texto, nullable)` — motivo da decisão (por que foi pedido ajuste, por que foi reprovado etc.), campo distinto de `comentario`.
  - `comentario (texto, nullable)` — observação livre associada ao ciclo.
  - `responsavelSolicitanteId (uuid → Usuario, nullable)` — quem abriu o ciclo (nulo se automatizado). Renomeado de `solicitadoPor` só por clareza de nome, mesma semântica.
  - `responsavelExecucaoId (uuid, FK → Usuario, nullable)` — **novo**: quem deve executar o resultado do ciclo (ex.: quem vai fazer a refação), podendo ser diferente de quem solicitou.
  - `novoPrazo (timestamp, nullable)` — **novo**: novo prazo definido como consequência do ciclo (ex.: prazo estendido após `ajuste_solicitado`).
  - `tratamentoChecklist (enum: manter | resetar_tudo | resetar_itens_afetados, nullable)` — **novo**: o que acontece com o `Checklist` da Tarefa (`02`, seção 5) quando o ciclo resulta em ajuste/refação.
  - `abertoEm (timestamp)`, `fechadoEm (timestamp, nullable)`.
- **Arquivos/versões (decisão 7, "registrar... arquivos/versões")**: nova tabela `RevisaoCicloAnexo (id, revisaoCicloId, anexoId, versao)`, associando `Anexo` (`02`, seção 9.1) a um ciclo específico com número de versão — permite saber exatamente qual versão de um arquivo foi avaliada em qual ciclo. **Dependência cruzada**: esta relação só é plenamente utilizável quando `Anexo` estiver implementado em Tarefa (`08`, Fase C) — o núcleo de `RevisaoCiclo` (resultado, motivo, comentário, prazos) pode e deve ser entregue antes, sem bloquear em Anexo.
- **Relação `resultado` → consequência estrutural**: `aprovado` (etapa não-final) segue `acaoAoAprovar`; `aprovado` (etapa final) conclui a tarefa; `ajuste_solicitado`/`refacao_parcial`/`refacao_completa` seguem `acaoAoAjustar` (permanece ou retorna a etapa anterior, conforme 7.3); `reprovado` segue `etapaRetornoReprovacaoId`; `cancelado` fecha o ciclo sem nenhuma transição de etapa (a tarefa permanece exatamente onde estava).
- **Relacionamentos**: N:1 `Tarefa`; N:1 `TarefaEtapa`; 1:N `RevisaoCicloAnexo`; gera `Evento` (`revisao.aberta`, `revisao.fechada`); pode alimentar `EtapaSessaoTempo` (`espera_cliente` quando `origem = cliente` e o ciclo está aberto).
- **Índices**: `INDEX (tarefaEtapaId, numeroCiclo)`; `INDEX (tarefaId, origem)` para relatório de refações internas vs. cliente.
- **Restrições**: `numeroCiclo` sequencial por `tarefaEtapaId`; `fechadoEm >= abertoEm`; exatamente um ciclo com `resultado = pendente` por `tarefaEtapaId` por vez (não pode haver dois ciclos abertos simultaneamente na mesma etapa).
- **Riscos de migração**: nenhum dado hoje (conceito totalmente novo). Risco de **design**: distinguir `refacao_parcial` de `refacao_completa` exige critério de negócio claro (ex.: percentual do escopo original refeito) — este documento não define esse critério, só o schema; validar com o negócio antes de fechar como regra automática vs. escolha manual do usuário no momento do registro.
- **Compatibilidade com o código atual**: nenhuma.

### 7.6 `NomenclaturaConfiguravel` (nova, pequena)

- **Finalidade**: "o nome exibido para revisão poderá ser configurável pela empresa" (decisão 7 reforça: **só o nome**, o conceito técnico é sempre `RevisaoCiclo`/`Revisao`).
- **Campos principais**: `id (uuid)`, `empresaId (uuid)`, `chave (enum: revisao | etapa | responsavel_principal | ... — extensível)`, `rotulo (texto)`.
- **Índices**: `UNIQUE (empresaId, chave)`.
- **Restrições**: se não houver registro para uma `chave`, a aplicação usa um rótulo padrão embutido.
- **Riscos de migração**: nenhum. Recomenda-se começar só por `chave = revisao`.
- **Compatibilidade com o código atual**: nenhuma — hoje todo rótulo é hardcoded em `Record<..., string>` dentro de `lib/demandas-mock.ts`.

---

## 8. `Tarefa` — tipo central revisado

- **Finalidade**: entidade central, renomeando `Demanda` (seção 0, decisão 1) e incorporando responsável principal/participantes via `Responsavel` (seção 6) em vez de arrays embutidos.
- **Campos principais** (delta em relação ao `Demanda` atual, `types/demanda.ts`):
  - Mantidos como estão, **e permanecem obrigatórios (decisão 6 — prazo operacional é obrigatório na Tarefa, ao contrário do Projeto)**: `id, empresaId, agenciaId, projetoId, clienteId, codigoInterno, nome, briefing, prioridade, dataCriacao, dataInicio, dataFimPrevista, createdAt, updatedAt`.
  - `usuarioResponsavelIds`/`departamentoResponsavelIds` **removidos** — migram para `Responsavel` (seção 6).
  - `workflowEtapas: DemandaWorkflowEtapa[]` **removido** — migra para `TarefaEtapa` (tabela própria, seção 7.4).
  - `status: DemandaStatus` **mantido** como campo armazenado (rascunho, planejada, em_execucao, pausada, bloqueada, concluida, cancelada — `aguardando_cliente` sai do enum armazenado, vira estado derivado, ver `TarefaStatusResumo` abaixo). Não é mais o campo que posiciona a tarefa no Kanban — esse papel é de `etapaAtualId` (corrige `06`, conflito #6).
  - `etapaAtualId` **mantido**, aponta para `TarefaEtapa.id`.
  - `workflowVersaoOrigemId (uuid, FK → WorkflowVersao)` **novo** (seção 7.2/7.4).
  - `titularidade (enum: individual | departamento | squad)` **novo** — resolve "tarefa individual, de departamento e de squad": determina qual `Responsavel.papel = principal` é esperado, sem impedir que outros papéis sejam de qualquer tipo. Pode ser pré-preenchida a partir de `departamentoPadraoId`/`squadPadraoId` da etapa (seção 7.3), com a etapa tendo precedência em caso de divergência.
  - `historico` **removido** — migra para consulta filtrada sobre `Evento` (`02`, seção 6.2).
- **`TarefaStatusResumo` (view derivada, não é campo armazenado nem tabela — decisão 6)**: usada no rollup de Projeto (seção 2) e em telas agregadas, com exatamente as 5 categorias da decisão 6:
  - `cancelada` ← `Tarefa.status = cancelada`.
  - `concluida` ← `Tarefa.status = concluida`.
  - `aguardando_aprovacao` ← existe `RevisaoCiclo` com `resultado = pendente` aberto na `TarefaEtapa = etapaAtualId` (qualquer `origem`, interno ou cliente — generalização em relação à revisão anterior deste documento, que só derivava esse estado de `origem = cliente`).
  - `pausada` ← `Tarefa.status IN (pausada, bloqueada)`.
  - `ativa` ← qualquer outro caso (`rascunho`, `planejada`, `em_execucao`, sem ciclo pendente).
- **Relacionamentos**: N:1 `Projeto`; N:1 `Cliente` (redundância com `Projeto.clienteId` — **decisão de migração pendente, não resolvida por nenhuma das 12 decisões**: este documento recomenda remover `Tarefa.clienteId` e resolver sempre via `Tarefa.projeto.clienteId`, mas isso continua sendo uma decisão a confirmar em `08`); 1:N `TarefaEtapa`; 1:N `Responsavel` (via `entidadeTipo=tarefa`); 1:N `RevisaoCiclo`; 1:N `Checklist`/`Comentario`/`Anexo`/`EntidadeTag`; N:1 `WorkflowVersao` (origem).
- **Riscos de migração**: **baixo a médio** — os 3 registros de `demandasMock` (`06`, seção 1.3) têm forma direta o suficiente para virar seed; o trabalho real é "explodir" os arrays de responsável em `Responsavel` e decidir `papel` de cada um (sem distinção "principal" hoje no mock).

---

## 9. Pautas (decisões 6/9/10, dependências de autenticação atualizadas pela decisão 11)

As pautas não são novas tabelas: são **consultas de domínio** com escopo diferente sobre `Tarefa` + `Responsavel` + `TarefaEtapa`.

| Pauta | Escopo da consulta | Pré-requisito de dado |
|---|---|---|
| **Minha Pauta** | Tarefas onde o usuário logado é `Responsavel` (qualquer papel) da `TarefaEtapa` = `etapaAtualId` da tarefa | `Responsavel` (seção 6) + usuário autenticado — **agora entregue cedo na Fundação (decisão 11, `08` Fase A), não mais tratado como bloqueio externo** |
| **Minha Pauta de Hoje** (decisão 10) | Recorte de **Minha Pauta** filtrado por prazo vencendo no dia corrente (`Tarefa.dataFimPrevista`/`TarefaEtapa.prazoRelativoHoras` resolvido para hoje), com colunas tarefa, cliente, projeto, etapa, status, prazo (data/hora) — usado no Dashboard, no lugar de "Atividades Recentes" | Minha Pauta funcionando |
| **Pauta do Departamento** | Tarefas onde `titularidade = departamento` e `Responsavel.departamentoId` = departamento do usuário, **ou** onde o departamento aparece como `apoio` na etapa atual | `Departamento` real (seção 3) |
| **Pauta da Squad** | Tarefas onde `titularidade = squad` e `Responsavel.squadId` = squad do usuário | `Squad`/`SquadMembro` (seção 5) |
| **Pauta do Head** | Tarefas de todos os Departamentos onde o usuário logado é `headUsuarioId` **ou** consta em `DepartamentoGestor` (seção 3) — substitui a formulação anterior deste documento, que apontava para `Squad.headUsuarioId` (campo removido, seção 5) | `Departamento.headUsuarioId`/`DepartamentoGestor` (seção 3) |
| **Pauta Geral** | Todas as tarefas visíveis ao perfil do usuário (Gestor/Admin com visão ampliada) | `PermissaoEscopo` (seção 11) funcionando |

**Regra transversal**, herdada de `docs/requirements/projetos-demandas-dashboard.md` (seção 3.6): nenhuma pauta mostra etapas futuras do fluxo antecipadamente — filtro implícito por `TarefaEtapa.id = Tarefa.etapaAtualId`.

**Regra de visibilidade de métricas (decisão 10)**: métricas gerais de clientes/projetos/SLA **não** devem aparecer indiscriminadamente para usuários operacionais — o Dashboard de um usuário `Operador` sem `cargo`/permissão ampliada mostra só **Minha Pauta de Hoje**, não os agregados que hoje aparecem hardcoded em `DashboardStats.tsx` (`tarefas: 128, projetos: 24, clientes: 86, sla: 97`) para qualquer perfil. Ver seção 12 para o desenho completo de experiência por papel.

---

## 10. Histórico agregado em Projeto e Cliente

Sem alteração conceitual em relação à revisão anterior deste documento:

- **Histórico agregado do Projeto** = `Evento` onde `entidadeTipo = tarefa` E `entidadeId IN (SELECT id FROM Tarefa WHERE projetoId = :projetoId)`, união com eventos do próprio Projeto.
- **Histórico agregado do Cliente** = o mesmo, subindo mais um nível via `Projeto.clienteId`.
- **Irmão conceitual (decisão 6)**: `TarefaStatusResumo` (seção 8) é a mesma ideia de agregação aplicada a **estado atual**, não a histórico — os dois juntos (histórico agregado + resumo de status) são o que a tela de Projeto precisa exibir por completo, conforme decisão 6.
- **Risco de performance**: mesmo já registrado — considerar índice composto em `Evento (entidadeTipo, entidadeId, dataHora)` e projeção assíncrona se o volume justificar.
- **Compatibilidade com o código atual**: nenhuma — `Projeto.historico` e `Cliente.historico` hoje são arrays mock independentes.

---

## 11. Permissões por escopo e temporárias

Sem alteração estrutural em relação à revisão anterior, com uma adição de uso (decisão 10):

### 11.1 `PermissaoEscopo`

Como antes (`02` não cobria; `06`, seção 6.5): `id, usuarioId, modulo, acao, escopoTipo (empresa|cliente|projeto|departamento|squad), escopoId`.

### 11.2 `PermissaoTemporaria`

Como antes: `id, usuarioId, permissaoEscopoId, perfilTemporario, validoDe, validoAte, concedidoPor, motivo, revogadoEm, revogadoPor`.

### 11.3 Uso em Dashboard/Pautas (decisão 10)

O Dashboard e as telas de Pauta consultam `PermissaoEscopo` (e o `cargo`/`perfil` do usuário, seção 4/12) antes de decidir quais métricas agregadas exibir — um usuário sem escopo ampliado não deve receber, nem por engano de UI, número agregado de outros clientes/projetos/departamentos.

---

## 12. Experiência por papel (nova — decisão 9)

Não é uma nova entidade de dado — é uma regra de produto sobre como Dashboard/Pautas/telas são priorizadas por combinação de `perfil` (RBAC, seção 11) e `cargo` (metadado descritivo, seção 4). **"Atendimento" não é um valor de `PerfilAcesso`** — é um valor de `cargo`, combinável com `Operador` ou `Gestor`.

| Papel/cargo | Experiência principal | Pautas/telas priorizadas |
|---|---|---|
| **Usuário/Operador** (perfil `Operador`, sem `cargo` especial) | Pauta de hoje e execução | Minha Pauta, Minha Pauta de Hoje (seção 9) |
| **Head/Gestor** (perfil `Gestor`, com `headUsuarioId`/`DepartamentoGestor` preenchido, ou `cargo = "Head"`) | Departamento, squads, carga e gargalos | Pauta do Departamento, Pauta da Squad, Pauta do Head, indicadores de carga (Central de Tráfego, `06`, seção 6.4) |
| **Atendimento** (`cargo = "Atendimento"`, `perfil` tipicamente `Operador` ou `Gestor`) | Clientes, projetos, aprovações, prazos e SLA | Pauta Geral filtrada por cliente/projeto, `RevisaoCiclo` com `resultado = pendente` (fila de aprovação), `SlaRegra` |
| **Admin** (perfil `Admin`/`SuperAdmin`) | Configuração, permissões e visão geral | Todas as pautas + telas de configuração + `PermissaoEscopo`/`PermissaoTemporaria` |

**Nota explícita (decisão 9)**: esta tabela descreve **experiência de produto** (o que a Home/Dashboard prioriza mostrar por padrão), não uma nova regra de RBAC — não cria nenhum valor novo em `PerfilAcesso`.

---

## 13. Mapa entidade → motor central (extensão da tabela de `02`, seção 13)

| Entidade nova/alterada | Motor principal |
|---|---|
| `Departamento` (extensão: `headUsuarioId`), `DepartamentoGestor` | Motor de Entidades |
| `Usuario.cargo` (campo, não entidade nova) | Motor de Entidades |
| `Squad`, `SquadMembro` | Motor de Entidades |
| `Responsavel` (com `squad`, `papel` fechado, elegibilidade ampla) | Motor de Entidades (associação) + Workflow + Kanban + Pautas |
| `WorkflowVersao` | Motor de Workflow |
| `WorkflowEtapaTemplateResponsavelPadrao` | Motor de Workflow |
| `TarefaEtapa` (com `workflowVersaoOrigemId` e campos de regra de 7.3) | Motor de Workflow |
| `RevisaoCiclo`, `RevisaoCicloAnexo` | Motor de Workflow (regra) + Motor de Eventos (auditoria) |
| `NomenclaturaConfiguravel` | Motor de Entidades (configuração por empresa) |
| Pautas (Minha/Hoje/Departamento/Squad/Head/Geral) | Superfície de consulta sobre Workflow + Entidades |
| Histórico agregado (Projeto/Cliente), `TarefaStatusResumo` | Motor de Eventos / consulta agregada |
| `PermissaoEscopo`, `PermissaoTemporaria` | Transversal — filtro de autorização usado por todos os motores |

---

## 14. Riscos transversais desta revisão

1. **Maior risco do modelo inteiro, herdado da revisão anterior**: este é o primeiro contato do backend com dado real de Tarefa — erro de modelagem aqui se propaga por todas as fases de `08`.
2. **`WorkflowVersao` aumenta a complexidade de UI** se a interface não deixar claro quando uma edição gera nova versão.
3. **`RevisaoCiclo` e `EtapaSessaoTempo` (de `02`) têm sobreposição conceitual parcial** — decidir se `RevisaoCiclo` dispara `EtapaSessaoTempo` automaticamente ou de forma independente antes de implementar.
4. **Autenticação antecipada é uma exceção deliberada** à regra geral de fase do projeto (`PROJECT_STATUS.md`: "Nesta fase ainda não existe autenticação") — decisão 11 aplica essa exceção **apenas à fatia Tarefa**; precisa ser comunicada explicitamente para não gerar confusão com outras frentes do repositório que continuam sem autenticação.
5. **`Usuario.cargo` como texto livre** (seção 4) tem o mesmo risco já visto com `squad: string` antes de virar entidade — sem catálogo, grafias podem divergir; mantido como texto por ora, com recomendação de catálogo futuro se o uso operacional crescer.
6. **10 campos novos em `WorkflowEtapaTemplate`/`TarefaEtapa`** (seção 7.3) é uma superfície de configuração grande — risco de sobrecarregar a UI de quem só quer um workflow simples; mitigação sugerida (seção avançada recolhida) já registrada.
7. **Redundância `departamentoPadraoId`/`squadPadraoId` (etapa) vs. `Tarefa.titularidade` (tarefa)** — precisa de regra de precedência explícita antes da implementação (recomendação: etapa sobrepõe tarefa).
8. **Redundância `Tarefa.clienteId`/`Tarefa.projeto.clienteId`** permanece sem decisão — nenhuma das 12 decisões a resolveu; segue como pendência explícita para `08`.
9. **Distinção `refacao_parcial` vs. `refacao_completa`** (seção 7.5) não tem critério de negócio definido neste documento — só o schema; precisa de validação com o negócio antes de virar regra automática.
