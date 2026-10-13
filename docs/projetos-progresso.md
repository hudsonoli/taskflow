# Projetos — visão Progresso

Aba **Progresso** dentro de `/projetos` (ao lado de "Projetos"). Leitura operacional agrupada por projeto: cada projeto é expansível e lista suas tarefas em linhas. **Somente leitura** — status, responsáveis e prazo continuam sendo editados nas telas de sempre; clicar numa linha abre o painel de detalhes que já existe (`DemandaDetailsDrawer`).

## Regras

- **Percentual do projeto** = tarefas `concluida` ÷ tarefas consideradas. Consideradas = todas as tarefas do projeto que o usuário enxerga, **exceto `cancelada` e `arquivada`**. Não usa horas, prazo, sessões, `updated_at` nem etapas. Projeto sem tarefas mostra "—" / "Sem tarefas" (nunca 0%).
- **Fluxo da tarefa** = "etapas concluídas / total" (● concluída, ◉ atual, ○ pendente). É outra coisa que o percentual do projeto e **não** é "% de trabalho" (etapas têm esforços diferentes). Sem workflow: "Sem workflow", sem percentual inventado.
- **Etapa atual** = `etapaAtualId` entregue pelo servidor (menor `ordem` não concluída). A tela nunca recalcula a etapa atual.
- **Responsáveis** = usuários da etapa atual; sem usuário, o(s) departamento(s); sem nada, "Sem responsável". Tarefa sem workflow usa os responsáveis da própria tarefa. Workflow todo concluído: "—".
- **Atrasada** = `classificarTarefa(demanda).atrasada` (`lib/escopo-operacional.ts`) — a regra oficial. Prazo não entra em nenhum cálculo de progresso.
- **Agora** (sessão ativa): o avatar do responsável da etapa atual com sessão ativa **nessa tarefa** recebe a marca "Agora". Quem trabalha na tarefa sem ser responsável aparece em "Também trabalhando agora" (sem afirmar que é responsável).
- **Ordem das tarefas**: bloqueadas, atrasadas, em execução, aguardando cliente, pausadas, planejadas/rascunho, concluídas (depois prazo e número). **Projetos**: com trabalho em aberto primeiro, mais bloqueadas+atrasadas, nome. Canceladas não são exibidas.
- **Filtros** (V1, sobre o que já foi carregado): Busca, Cliente, Responsável, Departamento, Status. Filtros mexem só nas linhas; o resumo do projeto sempre considera todas as tarefas.

## Fontes de dados (nenhum endpoint novo)

| Dado | Endpoint | Observação |
| --- | --- | --- |
| Projetos | `GET /projetos` | 1 requisição (limit 200), sem arquivados |
| Tarefas | `GET /demandas?projetoId=<csv>&limit=200` | em lote (até 40 projetos por requisição, paginado de 200 em 200); etapas, etapa atual, responsáveis e prazo já vêm no payload; RBAC/escopo do servidor |
| Quem trabalha agora | `GET /sessoes-trabalho/trafego/agora` | pessoas — só admin/gestor (Central de Tráfego); se 403, cai para `GET /sessoes-trabalho/pauta/em-execucao` (só QUAIS tarefas têm alguém trabalhando → "Em execução agora"); se também falhar, nada é mostrado |
| Nomes/avatares | `GET /usuarios/diretorio/por-ids` | UMA chamada em lote para todos os usuários das linhas |

Custo típico: 4 requisições de dados, independente da quantidade de linhas. Sem N+1.

## Limites conhecidos

- Teto de 1000 tarefas carregadas: acima disso a tela mostra um aviso de que os totais podem estar incompletos (nunca um total falso em silêncio).
- "Sem projeto" **não** é suportado: não existe filtro "sem projeto" na API de tarefas. Exigiria endpoint/filtro novo.
- A aba não é refletida na URL (estado local).

## Futuros (não implementados)

- Matriz/pipeline (tarefa × etapa).
- Progresso por esforço (depende da fase 11B.2B).
- Ações rápidas na linha.
