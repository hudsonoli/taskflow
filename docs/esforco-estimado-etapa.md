# Esforço estimado por etapa — Fase 11B.1

Implementação independente de prazo/deadline. Não altera capacidade, Tráfego, Pauta,
sessões, relatórios ou planejamento semanal. Nenhum deploy nesta fase.

## Persistência e contrato

Migration `0045_esforco_estimado_etapa.py`: revisão `d9f3b58e2a71`, anterior
`c8e2a47d1f93`. Adiciona somente `esforco_estimado_minutos INTEGER NULL` em
`workflow_modelo_etapas` e `demanda_workflow_etapas`, com checks de não negatividade.
Sem default ou backfill: registros existentes permanecem NULL. Downgrade remove as
duas colunas e seus checks; depois de uso real, isso descarta as estimativas novas.

- `NULL`: não estimado.
- `0`: esforço explicitamente nulo.
- Positivo: minutos de trabalho previstos, inclusive em etapas de aprovação.
- API: `esforcoEstimadoMinutos`, inteiro estrito entre 0 e 2.147.483.647 (INTEGER
  PostgreSQL), ou null. Rejeita negativos, strings, booleanos, floats inclusive 1.0 e overflow.
- UI aceita minutos ou horas/minutos, como `30 min`, `1h`, `1h30`, `1h 30min`.
  Vazio envia null. Nenhuma conversão usa quantidadeAntesDeadline/unidadePrazo.

## Template e snapshot

O template fornece o padrão; a materialização copia o valor para cada etapa da demanda.
Editar o template só afeta demandas criadas posteriormente. O snapshot pode receber
ajuste pontual sem trocar workflow, ordem, tipo, responsabilidades, status ou prazo.
Demanda sem workflow continua válida, sem etapa fictícia.

`PATCH /demandas/{demanda_id}/workflow/etapas/{etapa_id}/esforco` exige corpo com
`esforcoEstimadoMinutos` (inclusive null explícito); outros campos são recusados.
A rota resolve o escopo-base ou o acesso existente pela etapa atual; leitura global
da Pauta não concede escrita. A autoridade da etapa reutiliza a regra existente:
admin/gestor do tenant, responsável individual ou Head de departamento da etapa.
Não cria permissão nova. Token de plataforma não dá autoridade de tenant.

O ajuste pode ocorrer em qualquer etapa materializada acessível, inclusive futura
ou concluída; não é uma transição de workflow. Demanda arquivada precisa ser restaurada.
O read model expõe `podeEditarEsforco`, desativado em leitura global e para arquivadas.

A transação trava a demanda e relê as etapas. Uma mudança real publica
`demanda.workflow_esforco_alterado`, com ator, instante, etapa, valor anterior e novo
em minutos. No-op não gera evento. Falha ao publicar desfaz o ajuste. Escritas
concorrentes são serializadas, com cada evento registrando o valor anterior efetivo.
O template reutiliza `workflow_modelo.alterado`, incluindo valores anteriores/novos
por ordem; não há tabela paralela de auditoria.

## Totais derivados

DemandaRead calcula na leitura, também em lote, sem joins que dupliquem responsáveis:

- `estimadoConhecidoMinutos`: soma dos valores conhecidos; null quando nenhum existe.
- `etapasEstimadas`: inclui zero explícito.
- `etapasSemEstimativa`: quantidade de etapas NULL.
- `estimativaCompleta`: todas estimadas e pelo menos uma etapa.

Exemplo `[240, null, 0, 120]`: total conhecido 360, três estimadas, uma desconhecida,
cobertura incompleta. Sem workflow: total null, contagens zero, completa false.
Nenhum total é persistido. Estes valores não substituem os KPIs legados nesta fase.

## Validação DEV

Base Git inicial: `50524fed869b4be31c0b2083aa336ac07ad91ec5`, main/origin/main e remoto
iguais, árvore limpa. DEV local: `taskfloww_dev`, PostgreSQL em localhost:5433.
Alembic DEV anterior e restaurado: `c5b2e8a91d47` (o DEV estava atrás do código).

Snapshot custom pg_dump verificado antes do setup. Somente empresa, usuário, workflow
e demandas sintéticos foram criados. Exercício via HTTP TestClient da aplicação real,
conectado ao DEV, sem usar registros reais ou enviar mensagens:

1. Template A=240, B=NULL, C=0; primeira demanda preserva os três valores.
2. Template A=480; primeira demanda permanece 240; segunda recebe 480.
3. Ajuste da primeira para 120 preserva a segunda e o template em 480.
4. Prazo da etapa de três dias úteis permanece independente dos 120 minutos.
5. Histórico confirma ator, instante e alteração 240 → 120.

Restauração do dump após retornar o schema ao baseline. Dados de todas as tabelas,
sequências, colunas e índices idênticos ao snapshot. O PostgreSQL reescreveu casts
equivalentes de arrays em checks (`varchar[]::text[]` para casts dos literais);
comparação integral do schema normalizando exclusivamente essa representação não
apresentou diferenças. `DBSNAP_DIFF=vazio` é comparação lógica, não igualdade binária
do catálogo. Nenhum upload foi criado. Dumps ficam ignorados em backend/backups.

## Testes e limites

Testes de contrato/API em `test_esforco_etapa.py`, imutabilidade ampliada em
`test_demanda_workflow.py`, up/down e preservação em `test_migration_0045_esforco.py`.
Frontend: `test:esforco` testa conversão, null/zero, erros de gravação e integração
dos campos. A suíte frontend segue o padrão existente de funções executáveis e
verificações estruturais de componentes; não é um teste E2E de navegador.

Resultados em 12/10/2026:

| Gate | Resultado |
| --- | --- |
| Backend completo | 3.132 passaram; 245 avisos de depreciação |
| Backend focado final | 91 passaram, incluindo três casos de RBAC/arquivamento acrescentados após a coleta da suíte completa |
| Migration 0045 isolada | 1 passou (up/down, NULL, checks, dados preservados) |
| Frontend `test:*` | 32 scripts, 504 testes passaram |
| TypeScript | `tsc --noEmit` passou |
| Lint | passou |
| Build | passou; precisou executar fora do sandbox por restrição de acesso local do Next no Windows |
| Git | `git diff --check` passou |

O helper DEV teve uma falha de importação ao iniciar a limpeza; a restauração foi
concluída por uma execução corretiva, seguida da comparação lógica integral descrita
acima. O helper e os SQLs intermediários foram removidos; snapshot e evidências locais
permanecem ignorados, sem inclusão no Git.

O snapshot DEV foi restaurado: para executar a versão nova localmente depois desta
entrega, será necessário aplicar as migrations. Publicar código no Git não aplica
migrations e não constitui deploy.
