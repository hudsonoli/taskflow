# 09 — Diagnóstico da Estrutura Organizacional

> Documento de diagnóstico. Não é implementação, não é migration e não altera schema.
> Base principal: `PROJECT_STATUS.md`, `docs/database-model.md`, `docs/skills/database-rules.md`,
> `06-diagnostico-entidade-tarefa-atual.md`, `07-modelo-dominio-tarefa-proposto.md`,
> `08-plano-migracao-entidade-tarefa.md` e arquivos reais do repositório.

## 0. Fontes e lacunas de documentação

Os documentos abaixo foram solicitados para leitura, mas não existem na branch atual:

- `docs/arquitetura-taskfloww/00a-inventario-tecnico.md`
- `docs/arquitetura-taskfloww/00b-impacto-implementacao-eventos.md`
- `docs/arquitetura-taskfloww/04-fase-1a-eventos-historico.md`

Eles não foram recriados e nenhum conteúdo foi inferido a partir deles.

## 1. Estado atual por conceito

| Conceito | Estado atual | Evidências |
|---|---|---|
| Empresa | Existe como `empresaId`/`empresa_id`, mas não como cadastro persistido próprio | `frontend/src/lib/usuario-mock.ts`, `frontend/src/types/usuario.ts`, `backend/app/models/evento.py`, `backend/app/models/sessao_trabalho.py` |
| Agência | Existe como cadastro visual mockado e como `agenciaId` em Projeto/Demanda/Eventos/Sessões | `frontend/src/app/configuracoes/agencias/page.tsx`, `frontend/src/lib/projetos-mock.ts`, migrations de eventos e sessões |
| Departamento | Lista fixa/mock, tipo simples e referências por ID; não existe entidade persistida | `frontend/src/types/usuario.ts`, `frontend/src/lib/usuario-mock.ts`, `frontend/src/lib/equipe-mock.ts` |
| Equipe | Tipo TypeScript, mock e UI de cadastro; não existe backend | `frontend/src/types/equipe.ts`, `frontend/src/components/equipes/*` |
| Squad | Apenas texto livre no usuário; não existe tipo, cadastro, ID ou backend | `UsuarioDraft.squad` em `frontend/src/types/usuario.ts` |
| Usuário | Tipo TypeScript, mock em componente e Entity Drawer; sem tabela/API | `frontend/src/components/usuarios/UsuariosView.tsx`, `frontend/src/types/usuario.ts` |
| Cargo/Função | Existe só no usuário logado mockado (`currentUser.cargo`) e em contatos; não existe no cadastro de usuário | `frontend/src/lib/conta-mock.ts`, `frontend/src/types/usuario.ts` |
| Head | Ausente como estrutura; não existe relação com Departamento | Confirmado em `06`, e ausente nos arquivos atuais |
| Gestores | Parcialmente representados por `perfil = Gestor`; não há vínculo de gestão de departamento | `frontend/src/lib/access-control.ts`, `UsuarioDraft.perfil` |
| Permissões | Estrutura visual no usuário e gates front-only; sem backend/autorização real | `frontend/src/types/usuario.ts`, `frontend/src/lib/access-control.ts`, `frontend/src/app/configuracoes/permissoes/page.tsx` |

## 2. Classificação por tipo de existência

### Implementação real

- Backend real existe para fundação, Event Store e sessões de trabalho:
  - `backend/app/models/evento.py`
  - `backend/app/models/sessao_trabalho.py`
  - `backend/app/api/routes/eventos.py`
  - `backend/app/api/routes/sessoes_trabalho.py`
  - `backend/alembic/versions/20260711_1a2_cria_tabela_eventos.py`
  - `backend/alembic/versions/20260712_1a5_cria_sessoes_trabalho.py`
- Não há implementação real de `empresas`, `usuarios`, `departamentos`, `equipes`, `squads`, `cargos` ou permissões persistidas.

### Mock

- Usuários: `frontend/src/components/usuarios/UsuariosView.tsx`
- Departamentos: `frontend/src/lib/usuario-mock.ts`
- Equipes: `frontend/src/components/equipes/EquipesView.tsx`, `frontend/src/lib/equipe-mock.ts`
- Agências: `frontend/src/app/configuracoes/agencias/page.tsx`
- Projeto/Demanda/Tráfego usam universos mock próprios:
  - `frontend/src/lib/projetos-mock.ts`
  - `frontend/src/lib/demandas-mock.ts`
  - `frontend/src/lib/trafego-mock.ts`

### Tipo TypeScript

- `UsuarioDraft`, `DepartamentoOption`, `PermissaoItem`: `frontend/src/types/usuario.ts`
- `EquipeDraft`, `EquipeMembro`: `frontend/src/types/equipe.ts`
- `Projeto`, `ProjetoEquipeMembro`: `frontend/src/types/projeto.ts`
- `Demanda`: `frontend/src/types/demanda.ts`
- `TrafegoAgoraItem`, `TrafegoCargaItem`: `frontend/src/types/trafego.ts`

### Texto livre

- `UsuarioDraft.squad: string`
- `EquipeMembro.papel: string`
- `ProjetoEquipeMembro.funcao: string`
- `currentUser.cargo: string`
- Contatos de Cliente/Fornecedor usam `cargo` como texto, mas não representam o cargo organizacional de usuários internos.

### Componente visual

- Usuários: `/configuracoes/usuarios`
- Equipes: `/configuracoes/equipes`
- Agências: `/configuracoes/agencias`
- Permissões: `/configuracoes/permissoes`, ainda com empty state
- Sidebar/Header já expõem navegação de Configurações, mas não há tela de Departamentos ou Squads.

### Ausência completa

- Cadastro real de Empresa.
- Cadastro real de Departamento.
- Cadastro real de Cargo/Função.
- Cadastro real de Squad.
- Relações N:N de usuário com departamento, equipe, squad e cargo.
- Head principal com vigência.
- Gestores adicionais de Departamento.
- Permissões por escopo e permissões temporárias.
- Autenticação real.

## 3. Conflitos atuais

1. **Squad como string em Usuário**
   - `UsuarioDraft.squad` não é ID, não referencia entidade, não possui status e não tem vigência.
   - Viola a regra de não usar texto livre quando existir entidade relacionada.

2. **Departamento como lista fixa/mock**
   - `DepartamentoOption` tem só `id`, `nome`, `ativo`.
   - Não há `empresaId`, `codigoInterno`, `sigla`, responsável, Head, gestores, histórico ou backend.

3. **IDs divergentes de Departamento**
   - Usuários/equipes/projetos usam IDs como `dep-atendimento`.
   - Tráfego usa IDs como `departamento-atendimento`.
   - Isso impede consultas confiáveis de carga, pauta e responsabilidade por departamento.

4. **Equipe e Squad ainda podem ser confundidos**
   - Equipe existe como agrupamento operacional com `departamentoId`.
   - Squad não existe como entidade e aparece apenas como campo de texto em usuário.

5. **Agência versus Empresa**
   - `empresaId` aparece como raiz de dados em vários tipos e no backend.
   - `agenciaId` aparece em Projeto, Demanda, Evento e Sessão, e há tela de Agências.
   - Falta decisão implementada que impeça Agência de competir com Empresa como raiz de isolamento.

6. **Perfil versus Cargo**
   - `PerfilAcesso` é usado para gates visuais.
   - `currentUser.cargo` é texto livre de experiência de UI.
   - `UsuarioDraft` ainda não tem cargo/função configurável.
   - Head e Atendimento não devem virar perfis-base obrigatórios.

7. **Permissões apenas no frontend**
   - `UsuarioDraft.permissoes` é decorativo.
   - `hasAdministrativeAccess` e `hasDashboardAccess` só controlam renderização.
   - Não há sessão, token, escopo, autorização no backend ou tabela persistida.

8. **Backend sem entidades organizacionais**
   - O backend atual está preparado com SQLAlchemy/Alembic e Event Store, mas só possui `eventos` e `sessoes_trabalho`.
   - A próxima etapa precisa iniciar por persistência real, não por novos mocks.

## 4. Impacto funcional

### Cadastro de Usuários e Entity Drawer

- Deve substituir `departamentoId` único por vínculos em `usuario_departamentos`, preservando um vínculo principal.
- Deve remover `squad` texto livre e exibir Squads por vínculos.
- Deve substituir cargo textual por `usuario_cargos`.
- Deve manter permissões visuais apenas até existir API real.

### Permissões

- Perfis-base devem ser reduzidos ao papel de autorização ampla.
- Cargo/Função não concede permissão automaticamente.
- Permissões futuras precisam combinar perfil, recurso, nível de acesso, escopo, permissão específica e validade temporária.

### Sidebar e dashboards por papel

- O acesso visual atual por `currentUser.perfil` é temporário.
- Dashboard deve variar por papel/escopo real:
  - Operador: própria pauta.
  - Head/Gestor: departamento, equipes, squads, carga e gargalos.
  - Atendimento: clientes, projetos, prazos, aprovações e SLA.
  - Admin: estrutura, cadastros, permissões e auditoria.

### Workflow, Projeto, Tarefa e Pauta

- Projeto e Tarefa já referenciam usuários/departamentos por arrays de IDs mock.
- A arquitetura organizacional precisa suportar:
  - Minha Pauta.
  - Pauta do Departamento.
  - Pauta da Squad.
  - Pauta do Head.
  - Pauta Geral.
  - responsáveis disponíveis.
  - carga de trabalho.

### Histórico/Event Store

- O Event Store existente é o destino natural dos eventos organizacionais.
- A implementação deve emitir eventos de criação, alteração, inativação e mudança de vínculos.

## 5. Conclusão do diagnóstico

O repositório já possui uma base visual rica para Usuários, Equipes, Agências e permissões, mas os dados organizacionais ainda estão em mocks e tipos TypeScript. A fundação backend existe, porém ainda não contém as entidades organizacionais. A implementação deve começar por Empresa, Usuário persistido e catálogos/vínculos organizacionais no backend, preservando o frontend atual até haver APIs reais para substituir os mocks com segurança.
