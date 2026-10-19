# Backlog de produto — decisões do benchmark funcional (iClips × Runrun.it × TaskFlow)

Registro de **decisões de produto** que afetam o roadmap. Só documentação: nenhum código, migration ou deploy
decorre deste arquivo. O estudo completo fica fora do repositório (`research/`, contém dados reais de clientes dos
produtos observados); aqui entram apenas os requisitos, escritos com termos do TaskFlow. Os termos de uso dos
produtos estudados restringem engenharia reversa e uso concorrente: nada foi copiado (texto, layout, ícones, marca).

## 1. Fase 11B.2B — arquitetura aprovada permanece

| Fase | Escopo | Estado |
| --- | --- | --- |
| 11B.2B-A | Janela planejada por etapa + fator alocável da empresa | **Em produção** (main `d2b3455`, Alembic `e8a4c2d71f96`) |
| 11B.2B-B | Motor e endpoint de Carga (`GET /trafego/operacional/carga`) | Próximo passo |
| 11B.2B-C | UI de Carga | Depois da B |

O benchmark **não reabre** a v1: não entra jornada individual na Fase B, e não há migration nova agora.

### Contrato para a Fase B (capacidade desacoplada do singleton)

Ao implementar a 11B.2B-B, a matemática de capacidade **não** pode ler `RegraExpediente` da empresa diretamente em
todo lugar, de modo que uma fonte individual futura seja impossível. Criar **uma função pequena**, conceitualmente:

```
obter_capacidade_usuario(usuario, periodo) -> capacidade nominal por dia do período
```

- **v1:** devolve a capacidade da `RegraExpediente` da empresa (períodos do dia, dias especiais, fuso), como já
  desenhado em [planejamento-etapa.md](planejamento-etapa.md). O fator alocável continua sendo aplicado depois, por empresa.
- **Futuro:** poderá considerar override individual de jornada e ausências/férias, sem mudar quem a chama.
- **Sem excesso:** nada de hierarquia de classes, framework de estratégias nem tabela nova agora. É uma função com
  um ponto de extensão.

## 2. Backlog priorizado

Legenda: P1 = próximo ciclo de capacidade/Tráfego; P2 = produtividade da operação; "Posterior" = fora do 11B.2B.

### P1

| ID | Item | Observação |
| --- | --- | --- |
| `P1_CAPACIDADE_INDIVIDUAL` | Capacidade por pessoa | Conceito futuro: `RegraExpediente` da empresa como **fallback nominal**; **override opcional de jornada por usuário**; **ausências/férias** como redução individual por período; **dias especiais da empresa** continuam aplicáveis conforme regra a definir. **Não implementar agora**, não entra na 11B.2B-B. Hoje não há modelo de férias no código; exige desenho e migration próprios. |
| `P1_KANBAN_METRICA_ETAPA` | Métrica da etapa no cabeçalho da coluna do Kanban | Reaproveitar o que o Gargalos já calcula: **WIP** e, se fizer sentido, **tempo médio da etapa**. Sem nova coleta. |

### P1/P2 barato

| ID | Item | Observação |
| --- | --- | --- |
| `P2_CARTAO_TEMPO_OPERACIONAL_X_ESTIMATIVA` | Duração operacional próxima da estimativa da etapa, no cartão | Usar **sempre** os rótulos "**Tempo operacional em execução**" e "**Estimativa da etapa**". **Nunca** "horas trabalhadas", "tempo gasto pela pessoa" ou equivalente: o tempo operacional é o da tarefa naquele estado, não esforço de alguém. |

### P2

| ID | Item | Observação |
| --- | --- | --- |
| `P2_DURACAO_OPERACIONAL_HISTORICA` | Mostrar ao gestor a "duração operacional típica desta etapa" | **Informação auxiliar** para a decisão de estimar. **Não** preenche nem sugere automaticamente `esforco_estimado_minutos`. Ver correção abaixo. |
| `P2_SEQUENCIA_RESPONSAVEIS` | Passagem de bastão: ao entregar sua parte, a tarefa vai ao próximo responsável | Sem implementação. |
| `P2_DEPENDENCIAS_TAREFAS` | Tarefas pré-requisito e subsequentes (com possível reajuste de prazo) | Sem implementação. |
| `P2_REQUISITOS_ETAPA` | Campos exigidos para avançar de etapa | Sem implementação. |

### Correção de backlog: estimativa histórica

O estudo inicial listava "estimativa sugerida = média de `demanda_status_intervalos`". **Isso foi descartado como regra
automática**: tempo operacional **não** é esforço humano (uma tarefa pode ficar horas em execução sem ninguém
trabalhando, ou ser trabalhada em minutos). O item correto é `P2_DURACAO_OPERACIONAL_HISTORICA`, só informativo.
`esforco_estimado_minutos` continua sendo uma decisão de quem planeja.

### Posterior (não misturar com a 11B.2B)

Formulários de intake, recorrência de tarefas, automações, ações em massa e campos personalizados.

## 3. Fora de escopo (continua)

- Financeiro, rentabilidade, orçado × realizado.
- Ranking de pessoas, "quem trabalhou mais" e produtividade individual derivada de tempo operacional.
- Qualquer métrica de pessoa construída sobre `demanda_status_intervalos`: o tempo operacional é da tarefa, não da pessoa.

## 4. Princípios que este backlog preserva

- **Tempo operacional** (`demanda_status_intervalos`) ≠ **tempo pessoal** (`sessoes_trabalho`) ≠ **estimativa** ≠ **planejamento**.
- A carga futura usa estimativa e janela planejada, nunca tempo operacional como consumo de capacidade.
- Planejamento ≠ prazo (ver [planejamento-etapa.md](planejamento-etapa.md)).
