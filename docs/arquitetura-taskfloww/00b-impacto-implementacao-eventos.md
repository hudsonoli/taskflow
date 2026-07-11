# 00b — Impacto Técnico da Implementação do Motor de Eventos

> Documento de análise. Nenhuma funcionalidade foi implementada, nenhum código foi alterado, nenhum documento existente foi modificado e nenhuma migration foi criada.
> Base lida obrigatoriamente: `00a-inventario-tecnico.md`, `03-roadmap-implementacao.md` e código real do repositório em `frontend/src`, `backend/` e `docs/arquitetura-taskfloww`.
> Data da análise: 2026-07-11.

---

## Premissas da análise

O Motor de Eventos deve ser tratado como uma camada transversal e imutável para registrar mudanças relevantes de estado, alimentar histórico, auditoria, notificações, timeline, relatórios e futura Central de Tráfego. O estado atual do projeto ainda é predominantemente frontend/mock: o backend real possui apenas `backend/main.py` com rotas de healthcheck, não existem models, schemas, routers, migrations, autenticação, RBAC real, services ou testes automatizados versionados.

O código já contém efeitos parecidos com eventos, mas sem motor central: históricos mock em múltiplas entidades, histórico de transições de workflow, tipos conceituais de sessão de trabalho e telas que renderizam histórico por módulo. A implementação futura deve consolidar esses pontos em um contrato único, evitando criar mais um histórico paralelo.

---

## 1. Arquivos que precisarão ser alterados

| Arquivo | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `backend/main.py` | Deixar de concentrar toda a API e registrar routers reais, incluindo eventos e histórico. | Médio/alto: muda a composição da aplicação FastAPI, sem alterar a finalidade das rotas de healthcheck. | Média | Definição da estrutura `backend/app`, routers, conexão de banco e padrão de dependency. |
| `backend/app/models/evento.py` *(novo futuro)* | Criar a entidade persistida `Evento` como fonte única de histórico/auditoria. | Alto: passa a sustentar histórico, timeline, auditoria e consumidores futuros. | Alta | SQLAlchemy, migrations, enums de tipo de entidade/evento, autenticação futura para `usuarioId`. |
| `backend/app/schemas/evento.py` *(novo futuro)* | Definir contratos Pydantic de criação, leitura e filtros de eventos. | Alto: contratos serão consumidos pelo frontend e por testes de API. | Média | Modelo `Evento`, decisões sobre payload `jsonb`, nomes de campos e enums. |
| `backend/app/routers/eventos.py` *(novo futuro)* | Expor consulta de eventos e histórico por entidade. | Alto: substitui históricos mock e será usado por Demandas, Projetos e cadastros. | Média | Service de eventos, paginação, filtros multiempresa e autenticação futura. |
| `backend/app/services/eventos.py` *(novo futuro)* | Centralizar emissão, consulta e projeção de histórico. | Alto: evita duplicação da gravação de evento por router. | Alta | Models, unidade transacional, política de imutabilidade e idempotência. |
| `backend/app/core/database.py` *(novo futuro)* | Separar criação de engine/session do arquivo principal. | Médio: pré-requisito para qualquer gravação real de eventos. | Média | Estrutura backend aprovada e configuração via ambiente. |
| `frontend/src/types/evento.ts` *(novo futuro)* | Criar tipo TypeScript único para evento/histórico/timeline. | Alto: remove necessidade de múltiplos tipos `Historico*` incompatíveis. | Média | Contrato Pydantic equivalente e taxonomia de eventos. |
| `frontend/src/types/demanda.ts` | Trocar histórico específico por evento genérico ou projeção de evento. | Alto: afeta Demandas, Workflow, Kanban futuro e relatórios. | Alta | `EventoDominio`, `WorkflowTransicaoHistorico`, API de histórico. |
| `frontend/src/types/workflow.ts` | Associar transições de workflow ao evento de domínio correspondente. | Alto: cada avanço, retorno, bloqueio e desbloqueio deve gerar evento. | Alta | Taxonomia de eventos de workflow e regra de etapa atual única. |
| `frontend/src/types/projeto.ts` | Substituir `ProjetoHistoricoEvento` por histórico baseado em `Evento`. | Médio/alto: afeta resumo, modelo de campanha, equipe, arquivos e auditoria futura. | Média | `EventoDominio` e API de histórico por entidade. |
| `frontend/src/types/usuario.ts`, `cliente.ts`, `equipe.ts`, `fornecedor.ts`, `grupo-cliente.ts` | Unificar tipos `HistoricoUsuario`, `HistoricoCliente`, `HistoricoEquipe`, `HistoricoFornecedor` e `HistoricoGrupoCliente`. | Médio/alto: padroniza histórico de cadastros. | Média | Tipo `EventoDominio`, decisão de compatibilidade temporária com mocks. |
| `frontend/src/lib/eventos-mock.ts` *(novo futuro)* | Simular eventos centralizados enquanto o backend real não existir. | Médio: reduz duplicação dos mocks de histórico. | Média | Taxonomia de eventos e helpers de entidades. |
| `frontend/src/lib/demandas-mock.ts` | Adaptar `historico` e `workflowHistorico` para consumir eventos mock centralizados. | Alto: ponto mais sensível do fluxo operacional. | Média/alta | `eventos-mock.ts`, `workflows-mock.ts` e tipos de evento. |
| `frontend/src/lib/workflows-mock.ts` | Fazer transições gerarem eventos conceituais em vez de apenas histórico local. | Alto: base futura do Kanban, Central de Tráfego e relatórios de tempo. | Alta | `EventoDominio`, regras de transição e API futura de workflow. |
| `frontend/src/lib/projetos-mock.ts` | Adaptar histórico de projeto ao contrato único de eventos. | Médio | Média | `eventos-mock.ts` e tipos de projeto. |
| `frontend/src/lib/usuario-mock.ts`, `cliente-mock.ts`, `equipe-mock.ts`, `fornecedor-mock.ts`, `grupo-cliente-mock.ts` | Remover ou compatibilizar históricos locais duplicados. | Médio | Média | Migração progressiva para API ou mock centralizado. |
| `frontend/src/components/*/*FormSections.tsx` com seções de histórico | Renderizar projeção de eventos em vez de arrays específicos por entidade. | Médio/alto: afeta muitas telas, mas a mudança deve ser visualmente contida. | Média | Componente reutilizável de timeline/histórico. |
| `frontend/src/components/workflows/*` | Transformar transições locais em emissões de evento e leitura de histórico. | Alto | Alta | API de workflow/transição, service de eventos, status de etapa. |
| `frontend/src/components/demandas/*` | Demandas é a entidade mais dependente de eventos para workflow, prazo, status e auditoria. | Alto | Alta | Workflow, eventos, histórico, visibilidade futura e Central de Tráfego. |
| `frontend/src/components/projetos/*` | Projetos deve registrar alterações de resumo, equipe, modelo de campanha e arquivos. | Médio/alto | Média | Eventos por entidade e histórico unificado. |
| `frontend/src/components/kanban/*` | O Kanban futuro deve acionar transições de workflow que geram eventos, não eventos próprios paralelos. | Alto | Alta | Demanda real, workflow real, endpoint de transição. |
| `frontend/src/components/dashboard/*` e `frontend/src/app/relatorios/page.tsx` | Eventos serão fonte de métricas, timeline e tempo por status no futuro. | Médio/alto | Alta | Agregações backend, sessões de tempo e dados persistidos. |

---

## 2. Componentes React afetados

| Arquivo | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `frontend/src/components/demandas/DemandasView.tsx` | Hoje cria histórico local em `createHistoricoDemanda` e mantém demandas em `useState`. | Alto: deverá chamar service/API que registra evento ao criar/editar/transicionar demanda. | Alta | API de Demandas, API de Eventos, autenticação futura para usuário real. |
| `frontend/src/components/demandas/DemandaDetailsDrawer.tsx` | Contém abas de Dados, Briefing, Workflow, Responsáveis e Histórico. | Alto: Histórico e Workflow passarão a depender da timeline/eventos. | Média/alta | `DemandaFormSections`, `WorkflowEditor`, endpoint de histórico. |
| `frontend/src/components/demandas/DemandaFormSections.tsx` | Renderiza `HistoricoDemandaSection` e delega workflow para `WorkflowEditor`. | Alto: seção de histórico deve virar projeção de eventos; workflow deve emitir transição auditável. | Alta | Componente de timeline reutilizável e tipos de evento. |
| `frontend/src/components/workflows/WorkflowEditor.tsx` | Hoje aplica template e transiciona etapa em estado local. | Alto: deve se tornar consumidor do endpoint de transição e produtor indireto de eventos. | Alta | Workflow persistido, service de eventos, confirmação de troca de template. |
| `frontend/src/components/workflows/WorkflowTransitionControls.tsx` | Botões de próxima etapa, etapa anterior, bloquear e desbloquear. | Alto: cada ação deve registrar evento atômico e manter uma única etapa atual. | Alta | API transacional de workflow. |
| `frontend/src/components/workflows/WorkflowHistory.tsx` | Lista `WorkflowTransicaoHistorico`. | Alto: deve convergir para `Evento` filtrado por demanda/workflow. | Média | `EventoDominio` e projeção de histórico. |
| `frontend/src/components/projetos/ProjetosView.tsx` | Hoje cria histórico local em `createHistoricoProjeto`. | Médio/alto: criação/edição de projeto deve emitir evento. | Média | API de Projetos e Eventos. |
| `frontend/src/components/projetos/ProjetoDetailsDrawer.tsx` | Aba Histórico e abas que alteram dados relevantes do projeto. | Médio/alto | Média | Histórico unificado e events para resumo/modelo/equipe/arquivos. |
| `frontend/src/components/projetos/ProjetoFormSections.tsx` | Renderiza `HistoricoProjetoSection` com dados mock. | Médio/alto: deve usar componente genérico de histórico/timeline. | Média | `EventoDominio` e endpoint de histórico por entidade. |
| `frontend/src/components/clientes/ClienteFormSections.tsx` | Possui `HistoricoSection` mock estático. | Médio: deve deixar de usar mock local. | Média | Componente genérico de histórico e API de eventos. |
| `frontend/src/components/usuarios/UsuarioFormSections.tsx` | Possui `HistoricoSection` mock estático. | Médio | Média | Eventos de criação/edição de usuário e autenticação futura. |
| `frontend/src/components/equipes/EquipeFormSections.tsx` | Possui `HistoricoSection` mock estático. | Médio | Média | Eventos de equipe/departamento. |
| `frontend/src/components/fornecedores/FornecedorFormSections.tsx` | Renderiza histórico de fornecedor. | Médio | Média | Eventos de fornecedor e histórico unificado. |
| `frontend/src/components/kanban/KanbanBoard.tsx` | Futuramente mover card será transição de workflow. | Alto | Alta | Demandas reais, workflow real, eventos e Kanban conectado. |
| `frontend/src/components/kanban/KanbanCard.tsx` | Exibirá dados derivados da etapa/status/eventos, sem virar fonte de evento própria. | Médio | Média | Tipo `Demanda` real e status de etapa. |
| `frontend/src/components/dashboard/DashboardActivities.tsx` | Atividades recentes devem vir de eventos, não de dado estático. | Médio | Média | Endpoint de eventos recentes. |
| `frontend/src/components/dashboard/DashboardChart.tsx` e `DashboardStats.tsx` | Métricas futuras dependerão de eventos e sessões de tempo. | Médio/alto | Alta | Agregações backend e Central de Tráfego. |
| `frontend/src/components/conta/NotificacoesView.tsx` | Preferências de notificação são consumidoras futuras dos eventos. | Médio | Média | Persistência de preferências e motor de notificação. |

---

## 3. Tipos TypeScript que precisarão mudar

| Arquivo | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `frontend/src/types/evento.ts` *(novo futuro)* | Definir `EventoDominio`, `EventoTipo`, `EntidadeTipo`, `AtorEvento`, `EventoPayload`, `EventoFiltro` e metadados de auditoria. | Alto: contrato transversal usado por todos os módulos. | Alta | Modelo backend, taxonomia de eventos e política de payload. |
| `frontend/src/types/demanda.ts` | `DemandaHistoricoEvento` e `workflowHistorico` sobrepõem o conceito de evento. | Alto: deve convergir para `EventoDominio[]` ou histórico carregado sob demanda. | Alta | `workflow.ts`, API de histórico e timeline. |
| `frontend/src/types/workflow.ts` | `WorkflowTransicaoHistorico` deve referenciar ou ser substituído por evento de transição. | Alto: transição é um evento de domínio central. | Alta | Taxonomia `workflow.etapa.*`, status de etapa e endpoint transacional. |
| `frontend/src/types/projeto.ts` | `ProjetoHistoricoEvento` duplica o formato de auditoria. | Médio/alto | Média | `EventoDominio`, eventos de projeto e histórico por entidade. |
| `frontend/src/types/usuario.ts` | `HistoricoUsuario` deve deixar de ser tipo próprio. | Médio | Média | Eventos de cadastro e autenticação futura. |
| `frontend/src/types/cliente.ts` | `HistoricoCliente` usa `ipOrigem`, diferente de outros tipos. | Médio: precisa normalizar nomes de campos (`ip` vs. `ipOrigem`). | Média | Contrato único de evento. |
| `frontend/src/types/equipe.ts` | `HistoricoEquipe` duplica contrato. | Médio | Média | Eventos de equipe/departamento. |
| `frontend/src/types/fornecedor.ts` | `HistoricoFornecedor` duplica contrato. | Médio | Média | Eventos de fornecedor. |
| `frontend/src/types/grupo-cliente.ts` | `HistoricoGrupoCliente` também deve convergir para evento. | Médio | Média | Eventos de grupo de cliente. |
| `frontend/src/types/agenda.ts` | Contatos podem precisar de `ultimaInteracao` derivada de eventos. | Baixo/médio | Baixa/média | Decisão se Agenda consumirá eventos ou manterá metadado próprio. |

Tipos novos recomendados para o contrato futuro:

| Tipo | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `EventoDominio` | Representar registro imutável de domínio. | Alto | Alta | Backend e banco. |
| `EventoTipo` | Padronizar valores como `entidade.criada`, `entidade.atualizada`, `workflow.etapa.avancada`, `workflow.etapa.bloqueada`, `cliente.retorno.registrado`. | Alto | Média/alta | Taxonomia aprovada. |
| `EntidadeTipo` | Limitar entidades suportadas: `demanda`, `projeto`, `cliente`, `usuario`, `equipe`, `fornecedor`, `grupo_cliente`, `workflow`, etc. | Alto | Média | Modelo de dados. |
| `EventoPayload` | Carregar `valorAnterior`, `valorNovo`, `observacao`, `metadados` de forma tipada quando possível. | Alto | Alta | Política de privacidade e tamanho de payload. |
| `EventoAuditoria` | Normalizar `usuarioId`, `dataHora`, `ip`, `dispositivo`, `correlationId`, `causationId`. | Alto | Alta | Autenticação, request context e logs. |

---

## 4. Mocks que precisarão ser adaptados

| Arquivo | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `frontend/src/lib/eventos-mock.ts` *(novo futuro)* | Centralizar geração e consulta de eventos mock. | Alto: permite migrar UI gradualmente sem backend real. | Média | `types/evento.ts` e helpers de data/ID. |
| `frontend/src/lib/demandas-mock.ts` | Hoje cria histórico de demanda e mantém `workflowHistorico` separado. | Alto: Demandas deve usar eventos mock para criação, edição, mudança de status e workflow. | Alta | `eventos-mock.ts`, `workflows-mock.ts`. |
| `frontend/src/lib/workflows-mock.ts` | Hoje cria `WorkflowTransicaoHistorico` próprio. | Alto: transições devem gerar eventos compatíveis com o motor. | Alta | Taxonomia de workflow e consistência de etapa atual. |
| `frontend/src/lib/projetos-mock.ts` | Hoje usa `ProjetoHistoricoEvento`. | Médio/alto: projeto deve registrar eventos de resumo, modelo, equipe e arquivos. | Média | `eventos-mock.ts`. |
| `frontend/src/lib/usuario-mock.ts` | Deve gerar histórico de usuário via evento. | Médio | Média | Eventos de cadastro e usuário autenticado futuro. |
| `frontend/src/lib/cliente-mock.ts` | Deve normalizar histórico de cliente e contatos. | Médio | Média | Eventos de cliente e relação com Agenda. |
| `frontend/src/lib/equipe-mock.ts` | Deve registrar mudanças de equipe/departamento via evento. | Médio | Média | Entidade Departamento futura. |
| `frontend/src/lib/fornecedor-mock.ts` | Tem histórico com ids `evento-fornecedor-*`, mas sem motor central. | Médio | Média | Eventos de fornecedor. |
| `frontend/src/lib/grupo-cliente-mock.ts` | Histórico vazio deve seguir contrato comum quando houver eventos. | Baixo/médio | Baixa/média | Eventos de grupo de cliente. |
| `frontend/src/lib/conta-mock.ts` | `currentUser` fixo limita auditoria real. | Médio: enquanto não houver auth, eventos mock usarão ator fixo. | Média | Autenticação futura. |

---

## 5. Rotas backend que precisarão existir

| Arquivo | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `backend/app/routers/eventos.py` | Consultar eventos por filtros gerais. | Alto | Média/alta | Modelo `Evento`, paginação e autenticação. |
| `backend/app/routers/historico.py` ou rota em `eventos.py` | Expor histórico como projeção filtrada por entidade. | Alto: substitui abas de histórico mock. | Média | Índice por entidade e ordenação por data. |
| `backend/app/routers/demandas.py` | Criar/editar demanda e emitir eventos. | Alto | Alta | Entidade Demanda, service de eventos e transação. |
| `backend/app/routers/projetos.py` | Criar/editar projeto e emitir eventos. | Alto | Alta | Entidade Projeto e service de eventos. |
| `backend/app/routers/workflows.py` | Aplicar template e transicionar etapa emitindo eventos. | Alto: base do Kanban e da Central de Tráfego. | Alta | Workflow persistido, DemandaEtapa e Eventos. |
| `backend/app/routers/usuarios.py`, `clientes.py`, `equipes.py`, `fornecedores.py`, `grupos_clientes.py` | CRUDs devem emitir eventos de criação/alteração/exclusão/inativação. | Médio/alto | Média/alta | Models, schemas, service de eventos. |
| `backend/app/routers/notificacoes.py` *(futuro consumidor)* | Eventos poderão gerar notificações. | Médio | Alta | Preferências de notificação e fila/worker. |
| `backend/app/routers/timeline.py` *(futuro)* | Agregar Evento + Comentário + Anexo + Sessão de tempo. | Médio/alto | Alta | Fases posteriores de cartão completo e Central de Tráfego. |

Rotas mínimas esperadas para o Motor de Eventos:

| Rota | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `GET /eventos` | Consulta administrativa ou interna com filtros. | Alto | Média | Paginação, filtros por empresa/agência, auth. |
| `GET /eventos/{id}` | Inspeção de evento único. | Médio | Baixa/média | Modelo persistido. |
| `GET /historico?entidadeTipo=&entidadeId=` | Alimentar abas de histórico. | Alto | Média | Índice composto e contrato `EventoDominio`. |
| `GET /demandas/{id}/eventos` | Histórico específico da demanda. | Alto | Média | Demanda persistida. |
| `GET /projetos/{id}/eventos` | Histórico específico do projeto. | Médio/alto | Média | Projeto persistido. |
| `POST /demandas/{id}/workflow/transicoes` | Aplicar transição e registrar evento dentro da mesma transação. | Alto | Alta | Workflow real e service de eventos. |
| `POST /eventos` *(restrito ou interno)* | Emissão direta somente para serviços internos, se adotada. | Alto risco se público. | Alta | RBAC, idempotência e validação rigorosa. |

A escrita de eventos não deve ser uma rota pública genérica para qualquer cliente frontend gravar qualquer payload. O ideal é que CRUDs e transições emitam eventos no backend dentro da mesma unidade transacional da regra de negócio.

---

## 6. Migrations necessárias

| Arquivo | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `backend/migrations/*_create_eventos.py` *(novo futuro)* | Criar tabela principal de eventos. | Alto: base de auditoria e histórico. | Alta | Alembic ou ferramenta escolhida, Postgres e models. |
| `backend/migrations/*_create_evento_consumidores.py` *(opcional futuro)* | Controlar consumidores/processamento assíncrono de eventos. | Médio/alto | Alta | Decisão sobre fila, Redis/outbox e notificações. |
| `backend/migrations/*_create_evento_outbox.py` *(opcional futuro)* | Implementar padrão outbox para evitar perda entre transação e processamento externo. | Alto em produção. | Alta | Worker, Redis e política de retry. |
| `backend/migrations/*_create_workflow_transicoes.py` *(se separado de Evento)* | Registrar transições normalizadas quando necessário para consulta rápida. | Médio/alto | Média/alta | Decisão: evento puro vs tabela derivada. |
| `backend/migrations/*_add_audit_columns.py` *(por entidade, se aprovado)* | Adicionar `createdBy`, `updatedBy` ou metadados mínimos, se não ficarem só em Evento. | Médio | Média | Decisão de auditoria mínima por linha vs evento. |

Estrutura recomendada da tabela `eventos`:

| Campo/índice | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `id uuid primary key` | Identidade imutável do evento. | Alto | Baixa | UUID no backend. |
| `empresa_id uuid not null`, `agencia_id uuid null` | Isolamento multiempresa/agência. | Alto | Média | Entidades reais e auth futura. |
| `tipo varchar/enum not null` | Taxonomia do evento. | Alto | Média | Lista inicial de eventos. |
| `entidade_tipo varchar/enum not null`, `entidade_id uuid not null` | Projeção de histórico por entidade. | Alto | Média | Enum controlado de entidades. |
| `usuario_id uuid null` | Ator humano ou sistema. | Alto | Média | Autenticação futura. |
| `data_hora timestamptz not null` | Ordenação cronológica. | Alto | Baixa | Relógio backend. |
| `ip varchar null`, `dispositivo varchar null` | Auditoria requerida. | Médio/alto | Média | Request context. |
| `valor_anterior jsonb null`, `valor_novo jsonb null`, `metadados jsonb null` | Diferenças e payloads específicos por evento. | Alto | Alta | Política de privacidade e tamanho. |
| `correlation_id uuid null`, `causation_id uuid null` | Rastrear cadeia de eventos e idempotência. | Médio/alto | Alta | Service de eventos. |
| `INDEX (empresa_id, entidade_tipo, entidade_id, data_hora desc)` | Histórico por entidade. | Alto | Média | Volume esperado. |
| `INDEX (empresa_id, tipo, data_hora desc)` | Relatórios e auditoria por tipo. | Médio/alto | Média | Consultas de gestão. |
| `INDEX (correlation_id)` | Diagnóstico de fluxo. | Médio | Baixa/média | Correlation id definido. |

---

## 7. Testes que precisarão ser criados

| Arquivo | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `backend/tests/test_eventos_service.py` *(novo futuro)* | Validar emissão, imutabilidade, payload e metadados. | Alto | Alta | Service de eventos e banco de teste. |
| `backend/tests/test_eventos_api.py` *(novo futuro)* | Validar filtros, paginação e histórico por entidade. | Alto | Alta | Routers, schemas e auth/test client. |
| `backend/tests/test_demandas_eventos.py` *(novo futuro)* | Garantir que criar/editar/transicionar demanda gera evento correto. | Alto | Alta | Demanda real e workflow real. |
| `backend/tests/test_workflow_transicoes_eventos.py` *(novo futuro)* | Validar avanço, retorno, bloqueio e desbloqueio com evento e uma única etapa atual. | Alto | Alta | Workflow persistido. |
| `backend/tests/test_multiempresa_eventos.py` *(novo futuro)* | Impedir vazamento de eventos entre empresas/agências. | Alto | Alta | Auth/tenant context ou filtro obrigatório. |
| `backend/tests/test_eventos_migrations.py` *(novo futuro)* | Validar criação de tabela, índices e constraints. | Médio/alto | Média | Alembic e banco de teste. |
| `frontend/src/**/*.test.tsx` ou configuração equivalente *(novo futuro)* | Não há stack de teste frontend hoje; será necessário decidir Vitest/Testing Library ou alternativa. | Médio/alto | Alta | Dependências novas e padrão de teste aprovado. |
| `frontend/src/types/evento.test.ts` *(novo futuro, se houver testes TS)* | Validar helpers de normalização/derivação de eventos. | Médio | Média | Test runner frontend. |
| `frontend/src/components/workflows/WorkflowEditor.test.tsx` *(novo futuro)* | Garantir que controles disparam callbacks corretos sem duplicar eventos. | Alto | Alta | Test runner, mocks e componentes. |
| `frontend/src/components/*/Historico*.test.tsx` ou componente genérico de Timeline | Validar renderização de histórico unificado. | Médio | Média | Componente reutilizável. |

Observação: atualmente não há Jest, Vitest, Testing Library, Playwright ou Pytest versionados. A implementação do Motor de Eventos deve incluir uma decisão explícita de infraestrutura de testes antes de confiar em eventos para auditoria e relatórios.

---

## 8. Riscos durante a implementação

| Arquivo/área | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| Histórico duplicado em `frontend/src/types/*` | Existem múltiplos tipos `Historico*` com formatos parecidos, mas não idênticos. | Alto: risco de manter histórico duplo ou divergente. | Alta | Migração progressiva para `EventoDominio`. |
| `frontend/src/types/workflow.ts` e `frontend/src/types/demanda.ts` | Há `WorkflowTransicaoHistorico`, `DemandaHistoricoEvento` e tipos conceituais de sessão. | Alto: risco de três fontes de verdade para auditoria/tempo. | Alta | Decisão de modelo único. |
| `frontend/src/components/workflows/WorkflowEditor.tsx` | Transições locais podem parecer auditadas, mas não são persistidas nem transacionais. | Alto | Alta | Backend de workflow e eventos. |
| `backend/main.py` | Backend sem arquitetura modular; crescer diretamente nele geraria acoplamento. | Alto | Média/alta | Estrutura backend aprovada. |
| Ausência de auth/RBAC | Eventos exigem `usuarioId`, IP e dispositivo confiáveis, mas usuário atual é mock. | Alto | Alta | Autenticação futura e request context. |
| Ausência de migrations | Criar evento sem estratégia de migration pode gerar schema instável. | Alto | Alta | Alembic ou ferramenta definida. |
| Ausência de testes | Eventos viram fonte de auditoria; falhas silenciosas são críticas. | Alto | Alta | Infra de testes. |
| Payload `jsonb` com PII | Usuários já modelam dados sensíveis; eventos podem copiar valores sensíveis em `valorAnterior`/`valorNovo`. | Alto | Alta | Política de mascaramento e minimização de dados. |
| Processamento síncrono de notificações | Redis hoje só faz healthcheck; notificações síncronas podem travar ações do usuário. | Médio/alto | Alta | Fila/outbox/worker. |
| Ordem/idempotência de eventos | Transições duplicadas ou eventos fora de ordem quebram relatórios de tempo. | Alto | Alta | Correlation id, constraints e transações. |
| Multiempresa | Sem filtro obrigatório, histórico pode vazar entre empresas. | Alto | Alta | Auth, tenant context, índices e testes. |

---

## 9. O que pode quebrar

| Arquivo/área | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|
| `frontend/src/components/demandas/DemandasView.tsx` | Mudança de histórico local para evento/API altera criação e edição. | Alto: pode quebrar cadastro e edição de demanda. | Alta | API, tratamento de loading/erro e fallback mock. |
| `frontend/src/components/demandas/DemandaFormSections.tsx` | Aba Histórico e Workflow dependem dos tipos atuais. | Alto | Alta | Novo tipo de evento e adaptação de props. |
| `frontend/src/components/workflows/WorkflowEditor.tsx` | Transições deixam de ser apenas estado local. | Alto: pode quebrar fluxo de etapa atual, bloqueio e histórico. | Alta | Endpoint transacional e contrato de workflow. |
| `frontend/src/components/projetos/ProjetosView.tsx` | Criação/edição hoje injeta histórico local. | Médio/alto | Média | Eventos de projeto e API. |
| `frontend/src/components/projetos/ProjetoFormSections.tsx` | Aba Histórico usa formato específico de projeto. | Médio | Média | Histórico genérico. |
| `frontend/src/components/clientes/ClienteFormSections.tsx` | Usa `ipOrigem`, diferente de `ip`. | Médio: pode quebrar renderização se o contrato não normalizar. | Média | `EventoDominio` e mapeamento legado. |
| `frontend/src/components/usuarios/UsuarioFormSections.tsx` e `EquipeFormSections.tsx` | Históricos mock estáticos podem ficar incompatíveis com timeline. | Médio | Média | Componente genérico. |
| `frontend/src/components/kanban/*` | O Kanban futuro dependerá de transições que emitem eventos. | Alto | Alta | Workflow real e eventos. |
| `frontend/src/components/dashboard/*` | Atividades e métricas hardcoded podem ser substituídas por dados reais incompletos. | Médio/alto | Alta | Agregações e dados suficientes. |
| `frontend/src/app/relatorios/page.tsx` | Relatórios reais dependem de eventos confiáveis. | Alto futuro | Alta | Motor de Eventos e Central de Tráfego. |
| Build TypeScript | Remover tipos `Historico*` sem migração em todos os consumidores quebra build. | Alto | Média/alta | Migração coordenada por módulo. |
| Auditoria | Eventos duplicados ou ausentes quebram confiança operacional. | Alto | Alta | Testes e transações. |

---

## 10. Ordem recomendada de implementação

| Ordem | Arquivo/área | Motivo | Impacto | Complexidade | Dependências |
|---|---|---|---|---|---|
| 1 | Documento técnico de taxonomia de eventos *(novo futuro)* | Definir nomes de eventos, entidades, payloads, política de PII e imutabilidade antes de código. | Alto | Média | Aprovação de produto/arquitetura. |
| 2 | `frontend/src/types/evento.ts` | Criar contrato TypeScript inicial para alinhar frontend/mock. | Médio/alto | Média | Taxonomia aprovada. |
| 3 | `frontend/src/lib/eventos-mock.ts` | Centralizar eventos mock sem tocar ainda no backend. | Médio/alto | Média | Tipo `EventoDominio`. |
| 4 | Adaptar um único módulo piloto: recomendação `Demandas` | Demandas concentra workflow, status, prioridade, prazo e histórico. | Alto | Alta | Eventos mock e workflow. |
| 5 | Adaptar `WorkflowEditor` e `workflows-mock.ts` | Transição de etapa é o caso mais crítico de evento. | Alto | Alta | Contrato de evento e regra de etapa atual. |
| 6 | Criar componente genérico de histórico/timeline | Reduz duplicação visual antes de migrar todos os módulos. | Médio/alto | Média | Evento mock e contrato de renderização. |
| 7 | Migrar Projetos e cadastros para histórico genérico | Remove tipos `Historico*` gradualmente. | Médio/alto | Média/alta | Componente genérico validado. |
| 8 | Estruturar backend modular (`backend/app/*`) | Preparar API real sem crescer `main.py`. | Alto | Alta | Decisão de organização backend. |
| 9 | Criar migrations e model `Evento` | Persistir fonte única de auditoria. | Alto | Alta | Alembic/ferramenta definida, Postgres. |
| 10 | Criar service backend de eventos | Centralizar emissão e consulta. | Alto | Alta | Model, schemas, transação. |
| 11 | Criar endpoints de histórico/eventos | Alimentar UI com dados reais. | Alto | Média/alta | Service e paginação. |
| 12 | Integrar CRUDs e transições reais ao service de eventos | Garantir que evento nasce junto com regra de negócio. | Alto | Alta | Entidades reais de Fase 1. |
| 13 | Criar testes backend e frontend mínimos | Travar regressões de auditoria e histórico. | Alto | Alta | Infra de testes. |
| 14 | Preparar consumidores futuros: notificações, timeline, relatórios e Central de Tráfego | Eventos passam a alimentar outras projeções sem duplicar regra. | Alto futuro | Alta | Eventos confiáveis e dados persistidos. |

A ordem evita começar por telas ou relatórios. Primeiro é preciso padronizar o contrato, depois consolidar o mock, então persistir no backend e só depois conectar consumidores como Kanban, Dashboard, Relatórios e Central de Tráfego.

---

## Conclusão

A implementação do Motor de Eventos terá impacto transversal alto. O maior risco técnico não é criar a tabela de eventos, mas substituir com segurança os históricos paralelos já existentes e garantir que transições de Workflow, alterações de Demandas e mudanças de Projetos passem por uma fonte única, imutável e auditável.

A implementação futura deve evitar uma rota pública genérica para o frontend gravar eventos arbitrários. Eventos de domínio devem nascer no backend, dentro da mesma transação da ação real que os causou. Enquanto o backend não existir, um `eventos-mock.ts` pode servir como etapa intermediária para reduzir duplicação no frontend sem fingir persistência real.

Nenhuma funcionalidade foi implementada nesta análise.

---

## Nota de consolidação arquitetural

A ordem de implementação **frontend-first** proposta na seção 10 deste documento (taxonomia → `types/evento.ts` → `lib/eventos-mock.ts` → adaptar Demandas → adaptar `WorkflowEditor` → componente genérico de timeline → migrar Projetos/cadastros → só então estruturar backend/migrations/service) **foi substituída** pela ordem **backend-first** definida em `04-fase-1a-eventos-historico.md` (seção 24: decisões de nomenclatura/mascaramento → modelagem mínima das entidades + tabela `eventos` na mesma migration → estrutura backend modular → serviço central de eventos já com transação e mascaramento → entidade piloto real via API → demais entidades → só então avaliar integração do Workflow).

O motivo da substituição está registrado em `04-fase-1a-eventos-historico.md`, seção "Divergências entre `00a-inventario-tecnico.md` e `00b-impacto-implementacao-eventos.md`", item 1: um `eventos-mock.ts` em `useState` não pode garantir a imutabilidade nem a atomicidade transacional que são a razão de existir do Motor de Eventos — e tratar esse mock como etapa de persistência intermediária contraria a exigência de não tratar os mocks atuais como persistência.

Este documento (`00b`) **continua válido como análise de impacto**: os levantamentos de arquivos afetados, componentes React impactados, tipos TypeScript a mudar, mocks a adaptar, rotas backend a criar, migrations, testes e riscos (seções 1 a 9) permanecem uma referência útil de superfície de mudança. A única parte substituída é a **sequência** de implementação (seção 10) — a partir de agora, `04-fase-1a-eventos-historico.md` é a referência arquitetural e executiva principal da Fase 1A, e qualquer conflito de ordem entre os dois documentos deve ser resolvido a favor do `04`.
