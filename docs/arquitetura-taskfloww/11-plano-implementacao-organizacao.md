# 11 — Plano de Implementação da Organização

> Plano incremental. Não é implementação, não cria migrations e não altera código.
> A sequência começa por backend e persistência real. Novas telas mockadas não devem ser a primeira entrega.

## 1. Ordem recomendada

A ordem sugerida originalmente foi ajustada: Empresa, Usuário persistido e autenticação mínima precisam vir antes das operações organizacionais auditáveis que dependem de usuário atual. Migrations podem existir antes da autenticação, mas endpoints de alteração e eventos auditáveis devem preferencialmente nascer protegidos e associados a um usuário autenticado.

1. TF-ORG-002 — Empresa
2. TF-ORG-003 — Usuário persistido e compatibilidade com usuário atual
3. TF-AUTH-001 — Autenticação mínima
4. TF-ORG-002A — Agência subordinada
5. TF-ORG-004 — Cargo/Função configurável
6. TF-ORG-005 — Departamento persistido
7. TF-ORG-006 — Vínculos de usuário com Departamento, Head e gestores
8. TF-ORG-007 — Equipe persistida
9. TF-ORG-008 — Squad persistida
10. TF-ORG-009 — Vínculos de usuários, cargos, equipes e squads no frontend
11. TF-ORG-010 — API de consultas organizacionais
12. TF-ORG-011 — Substituição controlada de mocks no frontend
13. TF-ORG-012 — Permissões por escopo e permissões temporárias

## 2. Subtarefas

### TF-ORG-002 — Empresa

**Objetivo:** criar somente Empresa como raiz obrigatória de isolamento dos dados.

**Arquivos afetados:** `backend/app/models/`, `backend/app/schemas/`, `backend/app/repositories/`, `backend/app/services/`, `backend/app/api/routes/`, `backend/alembic/versions/`, `backend/tests/`.

**Cria tabela:** sim, `empresas`.

**Cria migration:** sim.

**Cria endpoint:** sim, CRUD administrativo mínimo.

**Substitui mock:** não nesta etapa.

**Altera Entity Drawer:** não.

**Depende de autenticação:** não para migration. Endpoints de alteração e eventos auditáveis devem preferencialmente aguardar TF-AUTH-001; bootstrap técnico, se inevitável para criar a primeira Empresa, deve ser exceção controlada, documentada e não reutilizada como fluxo normal.

**Models:** `Empresa`.

**Schemas:** create/read/update com aliases camelCase.

**Repositories:** CRUD e filtros por status.

**Services:** validação de unicidade, inativação e emissão de eventos.

**Frontend:** nenhum, salvo consumo futuro.

**Testes:** unitários de service, integração de migration e endpoints.

**Riscos:** criar Empresa sem identidade auditável; limitar bootstrap técnico ao mínimo necessário.

**Critérios de aceite:** migration sobe; CRUD básico passa; eventos de criação/alteração/inativação são gravados em `eventos` quando houver usuário autenticado ou bootstrap controlado; nenhuma tela mock nova é criada.

### TF-ORG-003 — Usuário persistido

**Objetivo:** criar `usuarios` persistido com `empresa_id`, perfil-base e status.

**Arquivos afetados:** backend nos mesmos módulos; testes backend; futuramente `frontend/src/lib/conta-mock.ts`.

**Cria tabela:** sim, `usuarios`.

**Cria migration:** sim.

**Cria endpoint:** sim, CRUD mínimo e listagem por empresa/status.

**Substitui mock:** não completamente; pode criar ponte de leitura depois.

**Altera Entity Drawer:** não nesta etapa.

**Depende de autenticação:** parcial. O cadastro pode existir antes do login real; operações finais exigirão usuário atual.

**Models:** `Usuario`.

**Schemas:** `UsuarioCreate`, `UsuarioUpdate`, `UsuarioRead`.

**Repositories:** busca por email, listagem, status.

**Services:** unicidade por empresa, inativação, bloqueio, emissão de eventos.

**Endpoints:** `/usuarios`.

**Frontend:** sem alteração inicial.

**Testes:** criação, email duplicado na mesma empresa, inativação, filtros.

**Riscos:** divergência entre perfis atuais do frontend e perfil-base alvo.

**Critérios de aceite:** usuário persistido com `empresa_id`; sem `cargo` texto livre; sem relações organizacionais ainda.

### TF-AUTH-001 — Autenticação mínima

**Objetivo:** criar identidade mínima para proteger operações organizacionais e associar eventos ao usuário atual.

**Arquivos afetados:** `backend/app/core/`, `backend/app/models/`, `backend/app/schemas/`, `backend/app/repositories/`, `backend/app/services/`, `backend/app/api/routes/`, `backend/alembic/versions/`, `backend/tests/`.

**Cria tabela:** sim, credenciais/sessões ou estrutura equivalente para autenticação.

**Cria migration:** sim, se credenciais/sessões forem persistidas em tabela separada.

**Cria endpoint:** sim, login, logout quando aplicável, refresh quando aplicável e `/me`.

**Substitui mock:** não ainda; habilita a substituição posterior de `frontend/src/lib/conta-mock.ts`.

**Altera Entity Drawer:** não.

**Depende de autenticação:** é a própria fundação de autenticação; depende de TF-ORG-002 e TF-ORG-003.

**Models:** credencial por e-mail e senha, sessão ou token persistido conforme decisão técnica.

**Schemas:** login request, token/session response, `MeRead`.

**Repositories:** busca de usuário por e-mail, credencial ativa, sessão/token quando persistido.

**Services:** hash seguro de senha, verificação de senha, criação/revogação de sessão ou token, resolução de usuário atual e empresa atual.

**Endpoints:** `/auth/login`, `/auth/logout` quando aplicável, `/me`.

**Frontend:** nenhum obrigatório nesta subtarefa; integração de UI de login pode ser etapa posterior se necessário.

**Testes:** senha inválida, usuário inativo, login válido, `/me`, proteção inicial de endpoint e identidade em evento.

**Riscos:** implementar endpoints organizacionais sem usuário atual; a partir desta subtarefa, alterações auditáveis devem receber usuário autenticado.

**Critérios de aceite:** e-mail/senha com hash seguro; login funcional; sessão ou token funcional; `/me` retorna usuário ativo e empresa atual; endpoints protegidos rejeitam acesso anônimo; eventos gerados por operações protegidas recebem `usuario_id`.

### TF-ORG-002A — Agência subordinada

**Objetivo:** criar Agência como cadastro opcional subordinado à Empresa, sem competir com a raiz de isolamento.

**Arquivos afetados:** backend models/schemas/repositories/services/routes/tests; migration.

**Cria tabela:** sim, `agencias`.

**Cria migration:** sim.

**Cria endpoint:** sim, CRUD administrativo mínimo.

**Substitui mock:** não nesta etapa.

**Altera Entity Drawer:** não.

**Depende de autenticação:** sim para endpoints de alteração e eventos auditáveis; depende de TF-ORG-002 e TF-AUTH-001.

**Models:** `Agencia`.

**Schemas:** create/read/update com `empresaId`.

**Repositories:** CRUD por `empresa_id`, filtros por status.

**Services:** validação de subordinação à Empresa, inativação e eventos.

**Endpoints:** `/agencias`.

**Frontend:** nenhum, salvo consumo futuro.

**Testes:** criação vinculada a Empresa, inativação, filtros e eventos.

**Riscos:** Agência virar segunda raiz de dados; mitigar mantendo `empresa_id` obrigatório em todos os registros.

**Critérios de aceite:** Agência opcional pertence a uma Empresa; não existe dado isolado apenas por `agencia_id`; eventos auditáveis usam usuário autenticado.

### TF-ORG-004 — Cargo/Função configurável

**Objetivo:** criar catálogo de cargos e vínculo histórico usuário-cargo.

**Arquivos afetados:** backend models/schemas/repositories/services/routes/tests; migration.

**Cria tabela:** sim, `cargos` e `usuario_cargos`.

**Cria migration:** sim.

**Cria endpoint:** sim, CRUD de cargos e atribuição/remoção de cargo.

**Substitui mock:** não imediatamente.

**Altera Entity Drawer:** depois, em TF-ORG-009/011.

**Depende de autenticação:** sim para atribuição, remoção e eventos auditáveis; depende de TF-AUTH-001.

**Models:** `Cargo`, `UsuarioCargo`.

**Schemas:** cargo create/update/read; vínculo create/update/read.

**Repositories:** cargos por empresa; vínculos ativos por usuário.

**Services:** cargo principal único, vigência, eventos.

**Endpoints:** `/cargos`, `/usuarios/{id}/cargos`.

**Frontend:** nenhum na subtarefa inicial.

**Testes:** múltiplos cargos, cargo principal único, encerramento de vigência.

**Riscos:** UI tentar tratar cargo como permissão.

**Critérios de aceite:** cargo configurável por empresa; nenhum cargo concede acesso automaticamente.

### TF-ORG-005 — Departamento persistido

**Objetivo:** criar Departamento como entidade formal da Empresa.

**Arquivos afetados:** backend; migration; testes.

**Cria tabela:** sim, `departamentos`.

**Cria migration:** sim.

**Cria endpoint:** sim.

**Substitui mock:** não ainda.

**Altera Entity Drawer:** não.

**Depende de autenticação:** sim para endpoints de alteração e eventos auditáveis; a migration pode existir antes, mas a operação normal depende de TF-AUTH-001.

**Models:** `Departamento`.

**Schemas:** create/update/read.

**Repositories:** listagem por empresa/status, unicidade por nome/sigla.

**Services:** inativação, reativação, eventos.

**Endpoints:** `/departamentos`.

**Frontend:** sem tela nova mock; frontend consome depois.

**Testes:** CRUD, unicidade, status, event store.

**Riscos:** IDs mock divergentes. Migração de consumo deve escolher uma fonte única.

**Critérios de aceite:** Departamento real existe; nenhuma referência nova por nome livre.

### TF-ORG-006 — Vínculos de Departamento, Head e gestores

**Objetivo:** criar vínculos de usuários com Departamentos, Head principal e gestores adicionais com vigência.

**Arquivos afetados:** backend; migration; testes; depois frontend de Usuários/Departamentos.

**Cria tabela:** sim, `usuario_departamentos` e `departamento_gestores`.

**Cria migration:** sim.

**Cria endpoint:** sim, endpoints de vínculo e liderança.

**Substitui mock:** parcialmente em consultas, não ainda em telas.

**Altera Entity Drawer:** depois.

**Depende de autenticação:** sim. Vínculos, Head e gestores dependem de usuário atual para `atribuido_por_usuario_id`, encerramento de vigência e eventos auditáveis.

**Models:** `UsuarioDepartamento`, `DepartamentoGestor`.

**Schemas:** vínculo create/read/update; gestor create/read/update.

**Repositories:** vínculos ativos, principal por usuário, gestores por departamento.

**Services:** vínculo principal único, Head único ativo por Departamento, prevenção de duplicidade, encerramento de vigência.

**Endpoints:** `/usuarios/{id}/departamentos`, `/departamentos/{id}/gestores`.

**Frontend:** nenhum na primeira entrega.

**Testes:** múltiplos Departamentos por usuário, um principal ativo, Head substituído, gestor adicional removido.

**Riscos:** modelar Head só como campo em `departamentos`; isso não atende vigência/histórico.

**Critérios de aceite:** Head e gestores existem como vínculos auditáveis e com eventos.

### TF-ORG-007 — Equipe persistida

**Objetivo:** criar Equipe real e seus membros.

**Arquivos afetados:** backend; migration; testes; depois `frontend/src/components/equipes/*`.

**Cria tabela:** sim, `equipes` e `equipe_membros`.

**Cria migration:** sim.

**Cria endpoint:** sim.

**Substitui mock:** depois.

**Altera Entity Drawer:** não, Equipes usa modal próprio hoje.

**Depende de autenticação:** sim para endpoints de alteração, membros e eventos auditáveis.

**Models:** `Equipe`, `EquipeMembro`.

**Schemas:** equipe e membro.

**Repositories:** equipes por departamento, membros ativos.

**Services:** membro único ativo, convidados de outros Departamentos, eventos.

**Endpoints:** `/equipes`, `/equipes/{id}/membros`.

**Frontend:** sem alteração inicial.

**Testes:** equipe vinculada a departamento, membro convidado, remoção com vigência.

**Riscos:** confundir Equipe com Squad ou restringir indevidamente membros a um único Departamento.

**Critérios de aceite:** Equipe pertence a um Departamento, mas permite convidado explícito.

### TF-ORG-008 — Squad persistida

**Objetivo:** criar Squad real e seus membros transversais.

**Arquivos afetados:** backend; migration; testes; depois frontend.

**Cria tabela:** sim, `squads` e `squad_membros`.

**Cria migration:** sim.

**Cria endpoint:** sim.

**Substitui mock:** remove uso futuro de `UsuarioDraft.squad`.

**Altera Entity Drawer:** depois.

**Depende de autenticação:** sim para endpoints de alteração, membros e eventos auditáveis.

**Models:** `Squad`, `SquadMembro`.

**Schemas:** squad e membro.

**Repositories:** squads por empresa, membros ativos.

**Services:** membro único ativo, vigência, eventos.

**Endpoints:** `/squads`, `/squads/{id}/membros`.

**Frontend:** sem alteração inicial.

**Testes:** composição transversal, membro único ativo, encerramento de vínculo.

**Riscos:** criar `head_usuario_id` em Squad; não é desejado.

**Critérios de aceite:** Squad não usa texto livre e não depende de Departamento direto.

### TF-ORG-009 — Vínculos no frontend de Usuários

**Objetivo:** adaptar o cadastro de Usuários para consumir vínculos reais sem duplicar estado.

**Arquivos afetados:** `frontend/src/components/usuarios/*`, `frontend/src/types/usuario.ts`, libs de API a criar, testes frontend.

**Cria tabela:** não.

**Cria migration:** não.

**Cria endpoint:** não, consome endpoints anteriores.

**Substitui mock:** parcialmente.

**Altera Entity Drawer:** sim.

**Depende de autenticação:** sim para salvar alterações reais; leitura inicial pode ser técnica enquanto a tela migra, mas operação normal depende de `/me` e usuário atual.

**Models/Schemas/Repositories/Services:** não se aplica no frontend.

**Frontend:** remover `squad` string; trocar `departamentoId` único por vínculos; exibir cargo principal e múltiplos cargos; preservar UX do Entity Drawer.

**Testes:** typecheck, lint, build e testes de interação do Drawer.

**Riscos:** quebrar foco/estado do Entity Drawer; duplicar draft entre frontend e backend.

**Critérios de aceite:** usuário edita vínculos por IDs; campo `squad` texto não é mais usado; cursor/foco preservado.

### TF-ORG-010 — API de consultas organizacionais

**Objetivo:** oferecer endpoints de leitura para seleção de responsáveis, composição organizacional e futuras pautas.

**Arquivos afetados:** backend routes/services/repositories/schemas/tests.

**Cria tabela:** não.

**Cria migration:** não.

**Cria endpoint:** sim.

**Substitui mock:** habilita substituição posterior.

**Altera Entity Drawer:** não diretamente.

**Depende de autenticação:** sim para escopo final e para evitar exposição indevida de usuários fora do contexto permitido.

**Endpoints candidatos:**

- `/organizacao/responsaveis-disponiveis`
- `/organizacao/usuarios/{id}/contexto`
- `/organizacao/departamentos/{id}/estrutura`
- `/organizacao/carga-base`

**Services:** agregações de vínculos ativos.

**Testes:** filtros por departamento, equipe, squad, cargo e status.

**Riscos:** expor usuários fora do escopo quando auth/permissões ainda não existirem.

**Critérios de aceite:** consultas retornam IDs e metadados suficientes para Minha Pauta, Pauta de Departamento, Pauta da Squad e Pauta do Head.

### TF-ORG-011 — Substituir mocks no frontend

**Objetivo:** trocar gradualmente mocks por APIs reais.

**Arquivos afetados:** `frontend/src/lib/usuario-mock.ts`, `frontend/src/lib/equipe-mock.ts`, componentes de Usuários, Equipes, Configurações, Projeto, Demanda/Tarefa e Tráfego conforme cada consumo.

**Cria tabela:** não.

**Cria migration:** não.

**Cria endpoint:** não.

**Substitui mock:** sim.

**Altera Entity Drawer:** sim, onde consumir dados reais.

**Depende de autenticação:** sim para experiência final por usuário atual.

**Frontend:** criar camada de API; preservar contratos visuais; remover universos mock divergentes.

**Testes:** lint, build, fluxos principais e regressão de hidratação/foco.

**Riscos:** substituir todos os mocks de uma vez. Deve ser feito por tela/fluxo.

**Critérios de aceite:** uma fonte real para Departamentos, Usuários, Equipes, Squads e Cargos; nenhum novo relacionamento por nome livre.

### TF-ORG-012 — Permissões por escopo e temporárias

**Objetivo:** implementar autorização além de gates visuais.

**Arquivos afetados:** backend auth/core, models/schemas/repositories/services/routes/tests; frontend `access-control` e telas de permissões.

**Cria tabela:** sim, permissões e permissões temporárias.

**Cria migration:** sim.

**Cria endpoint:** sim.

**Substitui mock:** sim, substitui matriz decorativa gradualmente.

**Altera Entity Drawer:** sim, para permissões reais do usuário.

**Depende de autenticação:** sim.

**Models:** `Permissao`, `UsuarioPermissao`, `PermissaoTemporaria`.

**Schemas:** concessão, revogação, leitura por escopo.

**Repositories:** permissões ativas e temporárias válidas.

**Services:** avaliação de acesso, concessão/revogação, eventos.

**Endpoints:** `/permissoes`, `/usuarios/{id}/permissoes`, `/permissoes-temporarias`.

**Frontend:** `/configuracoes/permissoes`, gates de Sidebar/Dashboard/Entity Drawer.

**Testes:** autorização de endpoint, expiração, revogação, escopos.

**Riscos:** frontend achar que ocultar campo é segurança. Backend precisa validar.

**Critérios de aceite:** permissões são aplicadas no backend; permissões temporárias geram eventos e expiram.

## 3. Dependências gerais

- Event Store já existe e deve ser usado para eventos organizacionais.
- TF-AUTH-001 deve vir antes das operações organizacionais auditáveis que criam, alteram, inativam ou encerram vínculos.
- Empresa deve vir antes de qualquer entidade de negócio persistida.
- Usuário persistido deve vir antes de autenticação mínima, Head, gestores, membros e permissões.
- Agência depende de Empresa e deve continuar subordinada a ela.
- Departamento deve vir antes de Equipe e Pauta do Departamento.
- Squad deve vir antes de Pauta da Squad.

## 4. Critérios globais de aceite

- Nenhuma nova tela mock deve substituir a criação das entidades reais.
- Todo relacionamento novo deve usar ID.
- Todo vínculo com vigência deve registrar `inicio_em`, `fim_em`, `status` e usuário responsável em operação normal autenticada.
- Nenhuma operação normal deve apagar registros organizacionais permanentemente.
- Eventos organizacionais relevantes devem ser gravados em `eventos`.
- Frontend, backend e banco devem convergir para uma única fonte de Departamentos, Usuários, Equipes, Squads e Cargos.
