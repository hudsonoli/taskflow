# Arquivos em lote (Fase 8B)

Na tela de Arquivos (`/arquivos` e as abas de Cliente/Projeto): seleção individual, seleção da página, seleção de **todos os resultados do
filtro**, download em ZIP e exclusão múltipla. Sem migration, sem storage nova.

## Contrato (`app/schemas/arquivo_lote.py`)

`POST /arquivos/resumo-lote`, `POST /arquivos/download-lote`, `POST /arquivos/excluir-lote` — mesmo corpo:

```json
{ "mode": "ids" | "all_filtered", "ids": [...], "excludedIds": [...], "filtros": { ... }, "contexto": { ... } }
```

- `ids` (até 500, sem repetição): só com `mode="ids"`. `excludedIds` (até 1000) e `filtros`: só com `mode="all_filtered"`. Combinação inválida → 422.
- `filtros` usa os **mesmos nomes e o mesmo formato CSV** de `GET /arquivos`, interpretados pelos mesmos parsers; `contexto` (`clienteId`/`projetoId`/`demandaId`)
  é o recorte fixo da tela e entra por **AND** — um filtro nunca o amplia.
- O navegador **não carrega IDs** de "todos os resultados": envia filtros + exceções e o servidor reexecuta a consulta autorizada
  (`DemandaArquivoRepository.selecionar_lote`, que compartilha `restringir_central` com a listagem).

## Autorização

Mesma regra da listagem e da exclusão individual: tenant do token + Demanda no **escopo-base** (`resolver_escopo_demanda`; a leitura pela Pauta
global não vale para o lote). Em `mode="ids"`, se **qualquer** ID não for autorizado/existente, a operação inteira falha com 404 e nada é alterado.

## Download (ZIP)

- Monta um arquivo temporário (`tempfile.mkstemp`, `zipfile.write` em blocos) e o entrega com `FileResponse`; o temporário é removido depois (ou na falha).
  Nada é carregado inteiro em memória e nada é escrito em `uploads/`. O proxy do frontend repassa o ZIP em stream.
- A transação do banco é encerrada antes de ler os arquivos.
- Tetos: **500 arquivos** e **500 MiB** (soma de `tamanho_bytes`) → 413. `PNG/JPG` são só armazenados; `PDF` usa deflate nível 1.
- **Links não entram** no ZIP (não têm arquivo); a contagem vai em `X-Lote-Links-Ignorados`. Seleção só de links → 404.
- **Arquivo físico ausente** → 409 `ARQUIVO_FISICO_AUSENTE` (com a quantidade) e **nenhum ZIP** — nunca se entrega um ZIP incompleto nem se mascara
  inconsistência de armazenamento (a exclusão individual tolera ausente; o download não).
- Nomes das entradas: saneados (sem caminho, controle ou caracteres proibidos; nomes reservados do Windows; limite de 120) e únicos sem diferenciar
  maiúsculas (`arte.pdf`, `arte (2).pdf`, …). Caminho físico vem sempre de `demanda_id` + `nome_fisico` do banco, confinado à raiz de uploads.
- Nome do ZIP: `taskfloww-arquivos-AAAAMMDD-HHMM.zip`.

## Exclusão

A exclusão é **definitiva** (registro + arquivo físico; não há soft delete de arquivo). Fluxo: pré-valida **todos** (`SELECT … FOR UPDATE`) → uma
transação remove os registros e grava **um evento `demanda.arquivo_removido` por arquivo** (`lote: true`) → só depois apaga os físicos. Se o commit
falhar, nada foi alterado. Falha de disco depois do commit não desfaz o banco: é registrada em log e devolvida em `arquivosFisicosNaoRemovidos`
(sobra órfã e inacessível, nunca silenciosa). Teto: 2000 arquivos por operação → 413.
