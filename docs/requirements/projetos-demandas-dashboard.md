# Requisitos - Projetos, Demandas, Kanban, Workflow, Dashboard, Relatórios e Agenda

## 1. Visão geral

Projetos e Demandas serão o núcleo operacional do TaskFloww.

Esses módulos deverão concentrar a operação diária da agência, conectando clientes, projetos, campanhas, workflows, etapas de execução, prazos, produtividade, relatórios e visibilidade gerencial.

Esta documentação registra requisitos funcionais e premissas futuras. Não representa implementação imediata de frontend, backend, banco de dados, Docker, rotas ou integrações reais.

## 2. Projetos

### 2.1 Resumo do projeto

- Cada projeto deverá possuir uma aba "Resumo".
- O resumo será preenchido pela equipe.
- Esse conteúdo deverá aparecer em um box separado nos detalhes das demandas vinculadas.
- A estrutura deve ser preparada para controle de permissão e histórico de alterações.

### 2.2 Integração com Publi

- Prever possibilidade futura de vincular o PIT do projeto criado no Publi.
- A integração deverá permitir consultar dados vinculados ao PIT.
- Prever consulta de CNPJ.
- Prever consulta das OCs vinculadas ao PIT.
- Não implementar integração neste momento.
- Tratar como integração externa futura.

### 2.3 Backlog do projeto

- Cada projeto poderá possuir um backlog de demandas padrão.
- O backlog deverá permitir campanhas recorrentes.
- Cada item do backlog poderá conter:
  - nome da demanda;
  - tipo de tarefa;
  - briefing base;
  - prioridade padrão;
  - workflow sugerido;
  - responsável ou setor sugerido.
- Ao iniciar uma campanha ou projeto recorrente, essas demandas poderão ser geradas a partir do backlog.

## 3. Demandas

### 3.1 Editor de briefing

- Permitir cor de fonte.
- Permitir grifo ou destaque de texto.
- Não criar editor excessivamente complexo.
- Não incluir recursos desnecessários de texto ou layout do iClips.

### 3.2 Prioridade

Valores previstos:

- Baixa
- Média
- Alta

Regras visuais do Kanban:

- Alta: contorno azul-marinho.
- Média: contorno azul-céu.
- Baixa: contorno azul-bebê.

As cores devem ser configuráveis futuramente.

### 3.3 Workflow personalizado

- O sistema poderá possuir templates de workflow.
- Cada demanda poderá ajustar seu workflow individualmente.
- Permitir:
  - incluir etapa;
  - remover etapa;
  - reordenar etapa;
  - ajustar responsável;
  - ajustar prazo.
- Mudanças devem ser auditáveis futuramente.

### 3.4 Prazo de retorno do cliente

- Criar futuramente uma ação "Enviado ao cliente".
- Ao acionar essa ação, iniciar um contador independente de prazo de retorno.
- Várias demandas poderão ter contadores ativos simultaneamente.
- Registrar:
  - data/hora do envio;
  - usuário responsável;
  - prazo esperado;
  - data/hora do retorno;
  - tempo total de espera;
  - aprovado ou solicitado ajuste.
- Esse tempo será usado em relatórios.

### 3.5 Card do Kanban

Exibir apenas:

- nome da demanda;
- projeto vinculado;
- prioridade;
- prazo da etapa atual.

Para o colaborador, o prazo exibido deve ser o prazo do workflow em que ele está atuando.

Evitar excesso de informações no card.

### 3.6 Visibilidade das demandas

- O colaborador deverá visualizar na pauta principal somente demandas que já estejam atribuídas à sua etapa atual.
- Demandas futuras do fluxo não devem aparecer antecipadamente.
- Gestores poderão possuir visão ampliada conforme permissão.
- Itens sem permissão devem ser ocultados, não apenas desabilitados.

## 4. Kanban

- Kanban por projeto.
- Kanban por equipe.
- Kanban por colaborador.
- Possibilidade futura de filtros por:
  - cliente;
  - projeto;
  - responsável;
  - prioridade;
  - atraso;
  - etapa.
- Cards enxutos.
- Workflow representado pelas colunas ou etapas configuradas.

## 5. Dashboard de gestão

### 5.1 Status por cliente e projeto

- Gráfico de pizza.
- Mostrar a porcentagem de demandas abertas por projeto dentro de um cliente.
- Permitir identificar campanhas que mais demandam o time.

### 5.2 Volume por projeto e colaborador

- Gráfico de barras empilhadas.
- Mostrar volume de demandas por projeto.
- Segmentar por colaborador.

### 5.3 Volume histórico

- Gráfico de linhas.
- Mostrar volume de demandas em fluxo.
- Janela máxima sugerida de 12 semanas.
- Permitir seleção de período futuramente.

## 6. Relatórios

### 6.1 Análise de projeto

Exibir:

- quantidade de demandas abertas;
- tempo médio entre criação e entrada no atendimento;
- tempo médio de retorno do cliente;
- volume por prioridade baixa, média e alta;
- alterações internas;
- alterações solicitadas pelo cliente;
- refações;
- colaboradores participantes;
- quantidade de demandas trabalhadas por colaborador.

### 6.2 Análise de peças por projeto

Formato de planilha ou tabela.

Exibir:

- nome da demanda;
- redator;
- diretor de arte;
- tempo em pauta;
- tempo entre briefing e aprovação;
- ajustes internos;
- ajustes do cliente;
- refações.

### 6.3 Performance de colaborador

Exibir:

- demandas entregues no período;
- demandas no prazo;
- demandas em atraso;
- gráfico de participação por etapa do workflow;
- criação;
- ajuste;
- finalização;
- outras etapas configuráveis.

## 7. Agenda

A Agenda será um hub híbrido.

Contatos automáticos:

- Clientes
- Fornecedores
- Usuários

Regras para contatos automáticos:

- exibidos automaticamente na Agenda;
- editados em seus módulos de origem;
- Agenda deverá oferecer ação "Abrir cadastro".

Contatos manuais:

- Parceiros
- Freelancers
- Leads
- Transportadoras
- Outros

Regras para contatos manuais:

- criados e editados diretamente na Agenda.

Modelagem futura sugerida:

- origemTipo
- origemId
- empresaId
- agenciaId
- manual
- favorito
- ultimaInteracao

Evitar duplicidade entre contatos automáticos e manuais.

## 8. Permissões e visibilidade

- Itens sem permissão devem ser ocultados.
- Não mostrar mensagens como "Somente SuperAdmin" em menus comuns.
- Criação e gestão de Agências será exclusiva de SuperAdmin.
- Gestores poderão ter acesso ampliado a projetos, demandas e relatórios.
- Colaboradores verão somente o que estiver em sua etapa atual, salvo permissão adicional.

## 9. Auditoria futura

Prever registro de:

- usuário responsável;
- data e hora;
- IP;
- dispositivo;
- valor anterior;
- valor novo;
- mudança de workflow;
- mudança de prioridade;
- envio e retorno do cliente.

## 10. Fora do escopo desta fase

- integração real com Publi;
- sincronização PIT/OC;
- banco definitivo;
- relatórios reais;
- autenticação;
- RBAC real;
- gráficos com dados reais;
- notificações reais.
