---
description: Analisa o impacto de alterar uma entidade/arquivo/módulo do TaskFloww usando o Graphify, antes de tocar em código
---

Analise o impacto de alterar "$ARGUMENTS" no TaskFloww usando exclusivamente o Graphify (não altere nenhum arquivo nesta análise):

1. Rode `graphify explain "$ARGUMENTS"` para entender o nó/entidade e sua comunidade.
2. Rode `graphify query "quais arquivos e módulos dependem de $ARGUMENTS"` (BFS) para mapear consumidores diretos e indiretos.
3. Se a mudança envolve duas entidades (ex.: "Cliente" e "GrupoCliente"), rode `graphify path "<A>" "<B>"` para achar a relação exata entre elas.
4. Se `graphify query` truncar por budget, aumente `--budget` ou refine a pergunta em vez de assumir que os nós cortados são irrelevantes.

Resuma ao final:
- Comunidades atravessadas pela mudança.
- God nodes tocados (se algum aparecer no caminho — risco de blast radius maior).
- Lista concreta de arquivos que provavelmente precisarão mudar junto (model → schema → repository → service → routes → frontend types/mappers/hooks, conforme o padrão do projeto).
- Riscos de regressão específicos (não genéricos) — ex.: "X é consumido por Y, que assume Z sempre não-nulo".

Esta é uma análise, não uma implementação — não escreva nem edite nenhum arquivo como parte deste comando.
