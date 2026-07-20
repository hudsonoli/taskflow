# 16 — Plano Técnico TF-ORG-002.2 — Departamentos

> Plano técnico de implementação. Não é arquitetura, não é DDL, não é
> migration, não altera código e não altera os Documentos 13, 14 ou 15.
> Todas as decisões de domínio e de sequenciamento já foram tomadas
> anteriormente; este documento apenas as converte em uma sequência técnica
> executável.

## 1. Objetivo

Este documento detalha o roteiro técnico da etapa **TF-ORG-002.2 —
Departamentos**, definida pelo Documento 14 (seção 5) como a segunda etapa
da sequência oficial de implementação do épico TF-ORG-002.

Relação com os documentos anteriores:

- **Documento 13** (`13-dominio-organizacional-oficial.md`) define a
  semântica oficial de Departamento (seções 6.2, 7.2, 8.1, 8.6, 8.7 e 9.9).
  Este plano não reinterpreta nem estende essa semântica — apenas a aplica.
- **Documento 14** (`14-plano-implementacao-organizacao.md`) define, para
  TF-ORG-002.2: objetivo "Consolidar Departamentos como estrutura
  organizacional da Empresa e preparar seu uso consistente pelas etapas
  seguintes"; dependências "TF-ORG-002.1, Empresa, Usuários, Equipes, RBAC e
  histórico organizacional"; resultado esperado "Departamentos alinhados ao
  documento 13, com isolamento preservado e aptos à consolidação de
  Equipes."
- **Documento 15** (`15-diagnostico-convergencia-organizacional.md`)
  inventariou o estado atual de Departamentos (seções 3, 4, 8.1–8.4) e já
  atribuiu a esta etapa três questões em aberto (seção 10, bloco
  "TF-ORG-002.2"): a necessidade de `sigla`, a responsabilidade pela tela de
  frontend, e a unicidade de nome/código não particionada por status. Este
  plano resolve essas três questões com base estrita no texto do Documento
  13 e na estrutura do Documento 14 (seção 3).

### 1.1 Nota de revisão

Esta é a segunda revisão deste documento. A primeira versão cobria apenas a
dependência de `usuario_departamentos` (participação, Head, Gestor) na
validação de inativação de Departamento. Uma auditoria adicional realizada
pelo Codex, durante a validação prévia de TF-ORG-002.2A, identificou que
`SessaoTrabalho` também referencia `departamento_id` e pode permanecer com
`status = 'ativa'` respondendo diretamente por uma Demanda (sem
`usuario_id`), sem que `DepartamentoService.inativar_departamento()`
verificasse essa dependência. O Documento 15 não catalogou explicitamente
essa relação — e não é alterado por este achado — mas a dependência se
enquadra diretamente na cláusula final da seção 9.9 do Documento 13:
"objetos operacionais que dependam dele". Esta revisão incorpora essa
dependência ao escopo técnico, sem alterar nenhuma decisão de domínio já
tomada nos Documentos 13, 14 ou 15.

## 2. Estado Atual

Resumo apenas dos pontos relevantes para esta etapa (detalhamento completo
no Documento 15, seções 3.1–3.2, 4 e 8).

**Backend:** `Departamento` já existe como entidade persistida real, com
`id`, `empresa_id`, `codigo_interno`, `nome`, `descricao`, `status`
(`ativa`/`inativa`/`arquivada`), timestamps e campos de inativação. Model,
schema, repository, service e rotas (`/departamentos`) estão completos para
criar, listar, obter, atualizar, inativar e reativar. `create_departamento`
valida Empresa ativa e unicidade de `codigo_interno`/`nome` por Empresa.
`inativar_departamento` e `reativar_departamento` validam apenas a
transição de `status` do próprio Departamento — **não verificam
dependências ativas** (vínculos de Usuário, Head, Gestor organizacional,
nem sessões de trabalho ativas) antes de bloquear a operação.

**SessaoTrabalho:** `backend/app/models/sessao_trabalho.py` possui uma
coluna `departamento_id` (`String(128)`, indexada, **sem `ForeignKey`**
para `departamentos.id`) e `status` (`ativa`/`encerrada`/`cancelada`). Uma
sessão pode responder por uma Demanda diretamente pelo Departamento, sem
`usuario_id` — há inclusive um índice único parcial
(`uq_sessoes_trabalho_ativa_demanda_departamento`) que impede duas sessões
ativas do mesmo Departamento para a mesma Demanda quando `usuario_id` é
nulo. `SessaoTrabalhoRepository.list()` já aceita `departamento_id` e
`status` como filtros, e a rota `GET /sessoes-trabalho` já expõe
`departamentoId` como query param. `DepartamentoService` não consulta essa
tabela em nenhum ponto hoje.

**Banco:** migration `20260715_1a11_cria_tabela_departamentos.py` já cria a
tabela com os três estados de `status`, `UNIQUE(empresa_id, codigo_interno)`
e `UNIQUE(empresa_id, nome)` (sem particionamento por status), FK para
`empresas` e para `usuarios.id` (`inativado_por_usuario_id`). Não há coluna
`sigla` nem `departamento_pai_id`.

**API:** contrato estável, aliases camelCase, protegido por
`require_admin` (escrita) e `require_admin_or_gestor` (leitura), isolamento
por Empresa via `ensure_same_empresa`/`ensure_resource_empresa`. Rota de
exclusão física não existe (`test_delete_route_does_not_exist` confirma).

**Frontend:** não existe nenhuma tela, componente, tipo ou mock real de
Departamento como entidade própria — apenas listas fixas em
`usuario-mock.ts`/`trafego-mock.ts` com IDs divergentes entre si e sem
relação com o backend real.

**Testes:** `test_departamentos.py` (425 linhas) cobre autenticação,
autorização por perfil, isolamento por Empresa, normalização de campos,
conflitos de duplicidade, transições de status inválidas, e rollback em
falha de publicação de evento. **Não existe** nenhum teste que crie um
vínculo ativo de Usuário, nem uma `SessaoTrabalho` ativa, associados ao
Departamento antes de tentar inativá-lo — confirmado por leitura completa
do arquivo.

## 3. Objetivo da Implementação

Ao final da TF-ORG-002.2, o módulo de Departamentos deve:

- Continuar com a mesma estrutura de dados, o mesmo contrato de API e o
  mesmo comportamento de criação, listagem, obtenção, atualização e
  reativação já existentes hoje — nenhum desses pontos diverge do Documento
  13.
- Passar a impedir a inativação de um Departamento quando existir, para
  ele, ao menos um vínculo ativo em `usuario_departamentos` (participação
  como `membro`, responsabilidade de `gestor` ou de `head`), conforme exige
  o Documento 13, seção 9.9 ("Um Departamento não deve ser inativado
  silenciosamente quando possuir... vínculos ativos de Usuários; Head
  ativo; Gestores organizacionais ativos").
- Passar a impedir, também, a inativação de um Departamento quando existir
  ao menos uma `SessaoTrabalho` com `departamento_id` igual ao do
  Departamento e `status = 'ativa'` — enquadrado na mesma seção 9.9 do
  Documento 13, na cláusula "objetos operacionais que dependam dele".
- Deixar explicitamente registrado — em código e em documentação de status,
  nunca por omissão — que a parte da seção 9.9 referente a "Equipes
  ativas" **não é tecnicamente verificável nesta etapa**, porque a entidade
  `Equipe` ainda não possui `departamento_id` (Documento 15, seção 8.3).
  Essa checagem específica é dependência declarada de TF-ORG-002.3. Com a
  adição da checagem de `SessaoTrabalho`, "Equipes ativas" passa a ser a
  **única** lacuna remanescente da seção 9.9 nesta etapa.
- Permanecer "apto à consolidação de Equipes", exatamente como descreve o
  resultado esperado do Documento 14 — ou seja, pronto para que
  TF-ORG-002.3 adicione a relação Equipe→Departamento sem precisar alterar
  nada em Departamento além de completar a validação de dependências.

Nenhuma tela de frontend, nenhum novo campo (`sigla`, hierarquia) e nenhum
novo endpoint (arquivamento via API) fazem parte deste objetivo — ver seção
4.2.

## 4. Escopo

### 4.1 Dentro do escopo

- Validação de dependências ativas em `inativar_departamento`
  (`backend/app/services/departamento_service.py`), cobrindo vínculos
  ativos de Usuário com o Departamento (qualquer `papel`: `membro`,
  `gestor`, `head`).
- Validação de sessões de trabalho ativas (`SessaoTrabalho.status = 'ativa'`
  com `departamento_id` igual ao do Departamento) na mesma operação de
  inativação.
- Reaproveitamento da exceção `DepartamentoConflictError` já existente e do
  tratamento HTTP 409 já existente em
  `backend/app/api/routes/departamentos.py` — sem alterar assinatura de
  rota, schema de entrada/saída ou código de status para os cenários já
  cobertos.
- Registro explícito, em comentário curto no próprio service, de que a
  checagem de "Equipes ativas" está pendente e depende de
  `departamento_id` em `Equipe` (TF-ORG-002.3).
- Testes automatizados novos cobrindo o bloqueio e a ausência de bloqueio,
  para vínculos de Usuário e para sessões de trabalho.
- Execução da suíte completa do backend para confirmar ausência de
  regressão.
- Atualização de `PROJECT_STATUS.md` ao final, registrando conclusão e a
  pendência explícita sobre Equipes.

### 4.2 Fora do escopo

- **Campo `sigla` em Departamento:** o Documento 13 não exige `sigla` para
  Departamento (só é citada para Equipe/Squad como atributo de
  apresentação em exemplos gerais, e apenas o Documento 10 — histórico,
  não normativo — previa esse campo). Resolução desta etapa: **não
  adicionar**. Se `sigla` vier a ser necessária, deve ser decidida por
  revisão formal do domínio, não introduzida silenciosamente aqui.
- **Unicidade de nome/código particionada por status:** o Documento 13,
  seção 7.2, exige apenas que "nome e código devem ser únicos no escopo
  definido pela Empresa" — sem qualificar "apenas entre ativos". A
  constraint atual (`UNIQUE(empresa_id, nome)` sem partição) já satisfaz
  literalmente essa regra. Resolução desta etapa: **manter como está**;
  não é uma divergência a corrigir.
- **Endpoint de arquivamento (`/departamentos/{id}/arquivar`):** hoje o
  estado `arquivada` existe no schema mas não é alcançável via API para
  nenhuma entidade de catálogo do sistema (Departamento, Cargo, Equipe,
  Agência ou Empresa se comportam da mesma forma). Alterar esse padrão
  apenas para Departamento criaria inconsistência entre entidades e exigiria
  uma decisão de arquitetura compartilhada, não tomada pelo Documento 13.
  Fora do escopo desta etapa.
- **Hierarquia/organograma (`departamento_pai_id`):** o Documento 13, seção
  7.2, é explícito: "um Departamento não contém outro Departamento até que
  hierarquia e organograma sejam formalmente decididos" — e a seção 14.3
  lista organograma como ponto pendente de decisão. Fora do escopo.
- **`departamento_id` em Equipe:** pertence a TF-ORG-002.3 (Documento 14).
- **Head e Gestor organizacional como responsabilidade própria** (tabela
  dedicada, histórico e eventos de domínio específicos, hoje representados
  apenas como valor de `papel` em `usuario_departamentos`): pertence a
  TF-ORG-002.5 — Vínculos (Documento 14; Documento 15, seção 10, bloco
  "TF-ORG-002.5").
- **Consolidação do vocabulário de `status` entre `usuario_departamentos`,
  `usuario_cargos` e `usuario_equipes`:** pertence a TF-ORG-002.5
  (Documento 15, seção 10).
- **Contexto organizacional agregado por Usuário:** pertence a
  TF-ORG-002.6.
- **Qualquer alteração de frontend** (tipos, mocks, componentes, telas,
  drawers, formulários, hooks, BFF): pertence a TF-ORG-002.8 — Integração
  Frontend. O resultado esperado de TF-ORG-002.2 no Documento 14 não
  menciona interface; a integração de interfaces é objetivo explícito de
  outra etapa.
- **Migration nova:** não é necessária — o schema atual de `departamentos`
  já atende integralmente aos campos e estados exigidos pelo Documento 13
  para esta etapa.
- **Novo método de repository:** não é necessário — `
  UsuarioDepartamentoRepository.list_by_departamento(...)` e
  `SessaoTrabalhoRepository.list(...)`, ambos já existentes, são
  suficientes para as consultas de dependências ativas (ver seção 5,
  TF-ORG-002.2A e TF-ORG-002.2B).
- **Adicionar `ForeignKey` de `sessoes_trabalho.departamento_id` para
  `departamentos.id`:** a coluna hoje é um `String(128)` solto, sem
  constraint de integridade referencial. Corrigir isso exigiria migration e
  validação de dados existentes, o que está fora do objetivo desta etapa
  (que é apenas impedir inativação silenciosa, não corrigir integridade
  referencial). Fica registrado como dívida técnica observada, não como
  tarefa desta etapa.
- **Permissões por escopo/recurso:** fora do escopo do TF-ORG-002 inteiro
  (Documento 14, seção 2, "Fora do escopo").

## 5. Sequência Técnica

### TF-ORG-002.2A — Validação de dependências ativas no service

**Objetivo:** alterar `DepartamentoService.inativar_departamento` para
consultar vínculos ativos do Departamento em `usuario_departamentos` antes
de efetivar a inativação, e bloquear a operação (levantando
`DepartamentoConflictError`) quando houver ao menos um vínculo com
`status = 'ativo'`, independentemente do `papel` (`membro`, `gestor` ou
`head`).

**Arquivos envolvidos:**
- `backend/app/services/departamento_service.py` — adicionar dependência
  opcional `usuario_departamento_repository: UsuarioDepartamentoRepository
  | None` ao construtor (mesmo padrão já usado para `empresa_repository`);
  adicionar verificação no início de `inativar_departamento`, antes da
  alteração de `status`.
- `backend/app/repositories/usuario_departamento_repository.py` — leitura
  apenas; nenhuma alteração esperada (`list_by_departamento` já aceita
  `status="ativo"`).

**Dependências:** nenhuma além do que já existe no repositório.

**Critério de conclusão:** chamar `inativar_departamento` para um
Departamento com um vínculo `usuario_departamentos` ativo (qualquer papel)
levanta `DepartamentoConflictError`, sem alterar `status`, `inativado_at`
nem publicar `DEPARTAMENTO_INATIVADO`; chamar para um Departamento sem
vínculos ativos mantém o comportamento atual (sucesso).

### TF-ORG-002.2B — Validação de sessões de trabalho ativas vinculadas ao Departamento

**Objetivo:** alterar `DepartamentoService.inativar_departamento` para
também consultar `SessaoTrabalho` e bloquear a inativação (levantando
`DepartamentoConflictError`) quando existir ao menos uma sessão com
`departamento_id` igual ao do Departamento e `status = 'ativa'` —
enquadrado na cláusula "objetos operacionais que dependam dele" da seção
9.9 do Documento 13 (achado da auditoria do Codex, ver seção 1.1).

**Arquivos envolvidos:**
- `backend/app/services/departamento_service.py` — adicionar dependência
  opcional `sessao_trabalho_repository: SessaoTrabalhoRepository | None` ao
  construtor (mesmo padrão já usado para `empresa_repository` e
  `usuario_departamento_repository`); estender a verificação adicionada em
  TF-ORG-002.2A para incluir esta consulta.
- `backend/app/repositories/sessao_trabalho_repository.py` — leitura
  apenas; nenhuma alteração esperada (`list` já aceita `departamento_id` e
  `status` como filtros; usar `limit=1` é suficiente, já que apenas a
  existência de alguma sessão ativa importa).

**Dependências:** TF-ORG-002.2A (mesma operação de inativação; a checagem
de sessões deve ocorrer no mesmo método, antes de qualquer alteração de
estado do Departamento).

**Critério de conclusão:** chamar `inativar_departamento` para um
Departamento com uma `SessaoTrabalho` ativa vinculada por
`departamento_id` levanta `DepartamentoConflictError`, sem alterar
`status`, `inativado_at` nem publicar `DEPARTAMENTO_INATIVADO`; chamar para
um Departamento sem sessões ativas (e sem vínculos ativos, conforme
TF-ORG-002.2A) mantém o comportamento atual (sucesso).

### TF-ORG-002.2C — Confirmação do mapeamento HTTP do novo erro

**Objetivo:** confirmar que `handle_departamento_error` em
`backend/app/api/routes/departamentos.py` já mapeia
`DepartamentoConflictError` para HTTP 409 (mapeamento já existente hoje
para outros cenários de conflito) e que nenhuma alteração de assinatura de
rota é necessária para os novos cenários (vínculo ativo de Usuário ou
sessão de trabalho ativa).

**Arquivos envolvidos:**
- `backend/app/api/routes/departamentos.py` — leitura/confirmação; alteração
  de código só é esperada se a mensagem de erro precisar de um texto mais
  específico do que a exceção genérica já produz (decisão de detalhe, não
  de contrato).

**Dependências:** TF-ORG-002.2A, TF-ORG-002.2B.

**Critério de conclusão:** `POST /departamentos/{id}/inativar` contra um
Departamento com vínculo ativo de Usuário ou com sessão de trabalho ativa
retorna HTTP 409 com corpo `{"detail": "..."}`, sem exigir mudança de
schema de request ou response.

### TF-ORG-002.2D — Registro explícito da limitação sobre Equipes ativas

**Objetivo:** deixar visível, no próprio código da validação adicionada em
TF-ORG-002.2A/TF-ORG-002.2B, que a checagem de "Equipes ativas" exigida
pela seção 9.9 do Documento 13 não está incluída nesta etapa por
impossibilidade técnica atual (ausência de `departamento_id` em `Equipe`),
e não por omissão — e que, com a checagem de `SessaoTrabalho` incluída
nesta revisão, "Equipes ativas" passa a ser a única lacuna remanescente da
seção 9.9. Um comentário curto no método de validação, apontando para
TF-ORG-002.3, é suficiente — sem criar nem alterar arquivo de
documentação.

**Arquivos envolvidos:**
- `backend/app/services/departamento_service.py` — apenas o comentário
  descrito.

**Dependências:** TF-ORG-002.2A, TF-ORG-002.2B.

**Critério de conclusão:** a lacuna é identificável por leitura direta do
código, sem exigir consulta a este ou a outros documentos para ser
compreendida.

### TF-ORG-002.2E — Testes de service e de API

**Objetivo:** cobrir o novo comportamento com testes automatizados,
seguindo o padrão já usado em `test_departamentos.py` e reaproveitando os
helpers de criação de vínculo já existentes em
`test_usuario_departamentos.py` e de sessão em `test_sessoes_trabalho.py`
(ou helpers equivalentes, se já existirem em `conftest.py`).

**Arquivos envolvidos:**
- `backend/tests/test_departamentos.py` — novos casos de teste.

**Casos mínimos a cobrir:**
1. Inativar Departamento com vínculo ativo de papel `membro` → HTTP 409 /
   `DepartamentoConflictError`, sem alteração de estado.
2. Inativar Departamento com Head ativo (`papel = 'head'`) → mesmo
   resultado.
3. Inativar Departamento com Gestor organizacional ativo
   (`papel = 'gestor'`) → mesmo resultado.
4. Inativar Departamento cujo único vínculo já está encerrado
   (`status = 'inativo'`) → sucesso (não deve haver bloqueio por vínculo
   histórico/encerrado).
5. Inativar Departamento com `SessaoTrabalho` ativa (`status = 'ativa'`,
   `departamento_id` do Departamento, sem `usuario_id`) → HTTP 409 /
   `DepartamentoConflictError`, sem alteração de estado.
6. Inativar Departamento cuja única `SessaoTrabalho` vinculada já está
   `encerrada` ou `cancelada` → sucesso (não deve haver bloqueio por sessão
   histórica).
7. Inativar Departamento sem nenhum vínculo e sem nenhuma sessão ativa →
   sucesso (regressão do comportamento atual, já coberta indiretamente
   pelos testes existentes, mas deve ser reconfirmada após a alteração).

**Dependências:** TF-ORG-002.2A, TF-ORG-002.2B, TF-ORG-002.2C.

**Critério de conclusão:** os sete casos acima presentes e passando em
`pytest backend/tests/test_departamentos.py`.

### TF-ORG-002.2F — Regressão da suíte completa do backend

**Objetivo:** garantir que a alteração não afeta nenhum comportamento fora
do escopo — em especial `test_usuario_departamentos.py`,
`test_usuario_cargos.py`, `test_usuario_equipes.py`, `test_equipes.py`,
`test_cargos.py`, `test_agencias.py`, `test_sessoes_trabalho.py`,
`test_auth*.py`.

**Arquivos envolvidos:** nenhum (execução de teste apenas).

**Dependências:** TF-ORG-002.2A a TF-ORG-002.2E.

**Critério de conclusão:** `pytest` completo do diretório
`backend/tests/` passa sem falhas nem novas emissões de warning
relacionadas à mudança.

### TF-ORG-002.2G — Atualização de status documental

**Objetivo:** registrar a conclusão da etapa em `PROJECT_STATUS.md`,
incluindo explicitamente a pendência sobre "Equipes ativas" como item
aberto vinculado a TF-ORG-002.3, e a checagem de sessões de trabalho ativas
como item concluído. Não alterar os Documentos 13, 14 ou 15.

**Arquivos envolvidos:**
- `PROJECT_STATUS.md`.

**Dependências:** TF-ORG-002.2A a TF-ORG-002.2F concluídas e homologadas
(Documento 14, seção 11 — fluxo oficial de execução).

**Critério de conclusão:** `PROJECT_STATUS.md` reflete a conclusão de
TF-ORG-002.2 e a pendência remanescente, sem reescrever histórico de
etapas anteriores.

## 6. Ordem Recomendada

```text
TF-ORG-002.2A  Validação de vínculos ativos de Usuário (service)
        ↓
TF-ORG-002.2B  Validação de sessões de trabalho ativas (service)
        ↓
TF-ORG-002.2C  Confirmação do mapeamento HTTP (rota)
        ↓
TF-ORG-002.2D  Registro explícito da limitação sobre Equipes (comentário)
        ↓
TF-ORG-002.2E  Testes de service e API
        ↓
TF-ORG-002.2F  Regressão da suíte completa
        ↓
TF-ORG-002.2G  Atualização de status documental
```

Etapas não aplicáveis e por quê:

- **Migration:** não necessária — o schema já atende ao Documento 13 para
  esta etapa (seção 4.2).
- **Repository (novo método):** não necessário — o método de consulta já
  existe (seção 4.2).
- **Novos Schemas/DTOs:** não necessário — nenhum contrato de entrada ou
  saída muda.
- **Frontend (componentes, Drawer, formulários, tipos, hooks, BFF):** fora
  do escopo desta etapa; pertence a TF-ORG-002.8 (seção 4.2).

## 7. Riscos

- **Quebra de testes existentes:** mitigado — confirmado por leitura
  completa de `test_departamentos.py` que nenhum teste atual cria vínculo
  ativo nem sessão de trabalho ativa antes de inativar um Departamento
  (os `departamento_id` usados em `test_sessoes_trabalho.py` são strings
  soltas, não IDs de Departamentos criados nos testes de Departamento); a
  mudança não deve quebrar nenhum teste hoje verde.
- **Bloqueio de fluxos operacionais legítimos:** risco baixo — não existe
  hoje nenhum consumidor real (frontend ou outro serviço) que inative
  Departamentos com vínculos ou sessões ativas, pois não há tela de
  Departamento em uso (Documento 15, seção 5.5).
- **Falsa sensação de conformidade total com a seção 9.9 do Documento
  13:** mesmo após esta revisão, a validação cobre vínculos/Head/Gestor e
  sessões de trabalho, mas ainda não cobre Equipes. Mitigação:
  TF-ORG-002.2D torna essa lacuna explícita no código; TF-ORG-002.2G a
  torna explícita na documentação de status.
- **Integridade referencial fraca em `sessoes_trabalho.departamento_id`:**
  como a coluna não é `ForeignKey`, a consulta desta etapa depende de o
  valor gravado coincidir exatamente com `departamentos.id`; nenhuma
  garantia de banco impede um `departamento_id` inválido ou órfão em
  `sessoes_trabalho`. Isso não é corrigido nesta etapa (seção 4.2) e deve
  ser tratado como dívida técnica conhecida, não como bloqueio à
  implementação da validação (que opera por igualdade de string,
  independentemente da ausência de FK).
- **Regressão de RBAC:** risco muito baixo — nenhuma alteração em
  `require_admin`, `require_admin_or_gestor`, `ensure_same_empresa` ou
  `ensure_resource_empresa`; a nova checagem ocorre inteiramente dentro do
  service, após a autorização já ter sido validada pela rota.
- **Integração futura com TF-ORG-002.3:** quando `departamento_id` for
  adicionado a `Equipe`, a validação de dependências ativas desta etapa
  precisará ser complementada para incluir Equipes ativas. Se
  TF-ORG-002.3 não tratar esse complemento como critério de aceite
  explícito, um Departamento com Equipes ativas poderá ser inativado sem
  bloqueio — risco a ser formalmente registrado na abertura de
  TF-ORG-002.3, não mitigável dentro desta etapa.
- **Outras dependências operacionais ainda não catalogadas:** a auditoria
  do Codex que originou esta revisão (seção 1.1) demonstra que o
  inventário de "objetos operacionais que dependam" de um Departamento
  (Documento 13, seção 9.9) pode não estar completo mesmo após esta etapa.
  Novas dependências equivalentes a `SessaoTrabalho.departamento_id`,
  encontradas em auditorias futuras, devem ser tratadas como revisão deste
  mesmo plano ou como nova etapa, nunca corrigidas silenciosamente durante
  a implementação.
- **Dados existentes:** não há dado de produção a migrar; a mudança é
  apenas de comportamento de validação, não de schema.

## 8. Estratégia de Compatibilidade

- **Contrato de API:** inalterado. Mesma rota
  (`POST /departamentos/{id}/inativar`), mesmo schema de entrada
  (`DepartamentoInativar`) e de saída (`DepartamentoResponse`). O único
  efeito observável novo é um HTTP 409 adicional em um cenário que hoje
  retornaria 200 apenas na ausência de qualquer verificação de dependência
  — cenário esse que, por não haver consumidor real hoje, não quebra
  nenhum fluxo em produção ou em teste.
- **Usuários e vínculos:** nenhuma alteração em `usuarios`,
  `usuario_departamentos`, `usuario_cargos` ou `usuario_equipes`, nem em
  seus services, repositories ou rotas. A nova consulta feita por
  `DepartamentoService` é somente leitura.
- **Sessões de trabalho e Central de Tráfego:** nenhuma alteração em
  `SessaoTrabalho`, `SessaoTrabalhoService`, `SessaoTrabalhoRepository` ou
  nas rotas `/sessoes-trabalho`. A consulta feita por `DepartamentoService`
  em TF-ORG-002.2B é somente leitura e não altera o ciclo de vida de
  nenhuma sessão. Este é o único módulo, além de Usuários/Vínculos, com
  dependência operacional real identificada em relação à inativação de
  Departamento — diferente do restante da seção 7 do Documento 15, que não
  havia catalogado essa relação (ver seção 1.1).
- **Equipes:** como `Equipe` não referencia `Departamento` hoje, esta etapa
  não tem nenhum efeito sobre o módulo de Equipes — nem sobre o backend
  (`/equipes`) nem sobre o frontend mock (`EquipesView.tsx`).
- **Projetos, Clientes, Workflow, Kanban, Agenda, Dashboard:** nenhuma
  dependência direta desses módulos em relação ao comportamento de
  inativação de Departamento foi identificada no Documento 15 (seção 7);
  nenhum impacto esperado.
- **Frontend:** como não existe hoje nenhuma tela, tipo ou mock real de
  Departamento consumindo a API real (Documento 15, seção 5.5), não há
  superfície de frontend a preservar ou quebrar nesta etapa.
- **Rollback funcional:** caso a validação precise ser revertida, basta
  remover as chamadas de verificação adicionadas em TF-ORG-002.2A e
  TF-ORG-002.2B — não há dado persistido, migration ou contrato público que
  precise ser desfeito.

## 9. Critérios de Aceite

- [ ] Inativação de Departamento com vínculo ativo (qualquer `papel`) é
      bloqueada com HTTP 409, sem alterar o estado do Departamento.
- [ ] Inativação de Departamento com sessão de trabalho ativa
      (`SessaoTrabalho.status = 'ativa'` com `departamento_id`
      correspondente) é bloqueada com HTTP 409, sem alterar o estado do
      Departamento.
- [ ] Inativação de Departamento sem vínculos ativos e sem sessões ativas
      continua funcionando exatamente como hoje.
- [ ] A limitação sobre "Equipes ativas" está registrada de forma
      explícita no código (TF-ORG-002.2D) e na documentação de status
      (TF-ORG-002.2G) — não implementada silenciosamente como resolvida.
- [ ] Nenhuma migration foi criada; a ausência de `ForeignKey` em
      `sessoes_trabalho.departamento_id` não foi corrigida nesta etapa
      (fora de escopo, seção 4.2).
- [ ] Nenhum contrato público de API foi alterado (mesma rota, mesmo
      schema de entrada/saída).
- [ ] Nenhum arquivo de frontend foi alterado.
- [ ] Os Documentos 13, 14 e 15 permanecem inalterados.
- [ ] Isolamento por Empresa preservado (nenhuma alteração em
      `ensure_same_empresa`/`ensure_resource_empresa`).
- [ ] RBAC sem regressão (`require_admin` continua sendo exigido para
      inativar; `require_admin_or_gestor` continua sendo exigido para
      leitura).
- [ ] Testes novos (seção 5, TF-ORG-002.2E) presentes e passando, incluindo
      os casos de sessão de trabalho ativa.
- [ ] Suíte completa do backend (`pytest backend/tests/`) sem regressões.
- [ ] `PROJECT_STATUS.md` atualizado refletindo a conclusão, a checagem de
      sessões de trabalho e a pendência remanescente sobre Equipes.
- [ ] Rollback funcional avaliado (seção 8).
- [ ] Etapa revisada e homologada pelo fluxo oficial (Documento 14, seção
      11: Hudson → ChatGPT → Claude → Codex → ChatGPT → Hudson).

## 10. Entregáveis

**Arquivos alterados:**

- `backend/app/services/departamento_service.py`
- `backend/tests/test_departamentos.py`
- `PROJECT_STATUS.md`

**Arquivos explicitamente não alterados por esta etapa:**

- Nenhum model (`backend/app/models/*.py`), incluindo
  `sessao_trabalho.py` (a ausência de `ForeignKey` em `departamento_id`
  não é corrigida nesta etapa).
- Nenhum schema Pydantic (`backend/app/schemas/*.py`).
- Nenhum repository além do uso, já existente, de
  `UsuarioDepartamentoRepository.list_by_departamento` e de
  `SessaoTrabalhoRepository.list`.
- Nenhuma migration (`backend/alembic/versions/`).
- Nenhuma rota (`backend/app/api/routes/*.py`) além de eventual ajuste de
  mensagem de erro que não altera assinatura nem contrato.
- Nenhum arquivo de frontend (`frontend/src/**`).
- Documentos 13, 14 e 15 (`docs/arquitetura-taskfloww/13-*.md`,
  `14-*.md`, `15-*.md`).

Este documento não autoriza, por si só, a execução das tarefas listadas na
seção 5. A execução depende da aprovação explícita do fluxo oficial descrito
no Documento 14, seção 11.
