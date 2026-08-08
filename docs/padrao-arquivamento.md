# Padrão de arquivamento (soft-delete permanente)

Este documento descreve o contrato usado para "Excluir" em qualquer entidade do domínio.
A referência atual é **Usuário** (`backend/app/services/usuario_service.py`). Quando
Cliente e Fornecedor forem migrados para o backend, copiar este contrato campo por campo,
nome por nome — não reinterpretar.

## Regra central

"Excluir" nunca apaga a linha do banco nem troca o ID. O registro é **arquivado**: some da
listagem padrão, mas continua existindo pra sempre, com auditoria de quem/quando/por quê.
Se alguém tentar recriar o mesmo registro (mesmo e-mail/documento/código interno), a API
detecta o conflito com o arquivado e devolve o ID dele pra a UI oferecer restaurar em vez
de duplicar.

Restaurar **sempre** volta pro estado mais conservador (`inativo`) — nunca reativa
sozinho, mesmo que o registro estivesse `ativo` antes de ser arquivado. Reativar de
`inativo` pra `ativo` continua sendo uma ação administrativa explícita separada.

## Campos de auditoria (mesmos 6 nomes em toda entidade)

| Campo (API, camelCase) | Coluna (banco, snake_case) | Tipo |
|---|---|---|
| `arquivadoAt` | `arquivado_at` | timestamp, nullable |
| `arquivadoPorUsuarioId` | `arquivado_por_usuario_id` | `String(36)` no banco (mesmo tipo do `id` da entidade — **não** `sqlalchemy.Uuid`, pra não criar uma representação física diferente do mesmo identificador); `UUID` no schema Pydantic, só pra validar o formato na borda da API |
| `motivoArquivamento` | `motivo_arquivamento` | string, nullable no banco (`NOT NULL` é aplicado no schema/serviço, não como constraint — a coluna precisa aceitar `NULL` pras linhas que nunca foram arquivadas) |
| `restauradoAt` | `restaurado_at` | timestamp, nullable |
| `restauradoPorUsuarioId` | `restaurado_por_usuario_id` | mesmo tratamento de `arquivadoPorUsuarioId` |
| `statusAnteriorArquivamento` | `status_anterior_arquivamento` | string, nullable — só auditoria, **nunca** usado para decidir o destino do restore |

Os campos representam só o **último ciclo** de arquivar/restaurar — não são limpos na
próxima transição, mas também não acumulam histórico de ciclos anteriores. O histórico
completo (todos os ciclos, todas as entidades) vive nos **eventos de domínio**, não no
registro.

Nenhum dos dois campos de ator (`arquivadoPorUsuarioId`/`restauradoPorUsuarioId`) tem
`ForeignKey` — são campos de auditoria soltos, não uma relação obrigatória.

## Endpoints e métodos de serviço

- Método de serviço: `excluir_<entidade>(db, id, *, motivo_arquivamento: str, actor_usuario_id: str)`
  — os dois parâmetros são **obrigatórios**, sem valor default. Bloqueia se o registro já
  está arquivado.
- Método de serviço: `restaurar_<entidade>(db, id, *, actor_usuario_id: str)` —
  `actor_usuario_id` obrigatório. Só funciona a partir de `arquivado`. Sempre define o
  status como `inativo` (ou o equivalente mais conservador da entidade).
- Rota: `POST /<entidade>/{id}/excluir` — corpo `{"motivoArquivamento": "..."}`.
- Rota: `POST /<entidade>/{id}/restaurar` — sem corpo.

## Listagem

A exclusão de registros arquivados da listagem padrão é uma **condição SQL** no
repository (`WHERE status != 'arquivado'`), adicionada **antes** de `.limit()/.offset()` —
nunca um filtro em Python depois de buscar os dados. Passar `status=arquivado`
explicitamente continua consultando normalmente (é assim que a UI encontra um registro pra
oferecer restaurar).

## Conflito de criação (HTTP 409)

Ao criar um registro cujo identificador único (e-mail pra Usuário; CNPJ/documento pra
Cliente/Fornecedor) já pertence a um registro arquivado, a API devolve:

```
HTTP 409
{
  "detail": {
    "code": "<ENTIDADE>_ARQUIVADO_EXISTENTE",
    "<entidade>ArquivadoId": "...",
    "message": "..."
  }
}
```

O corpo do `code`/ID fica **aninhado sob `"detail"`** — é assim que o handler padrão de
exceção do FastAPI serializa um `HTTPException(detail={...})`. Confirmado por teste real
(curl) contra `POST /usuarios/{id}/excluir` → tentativa de recriar com o mesmo e-mail, não
assumido. Ao implementar o mesmo padrão pra outra entidade, confirmar de novo com uma
chamada real antes de escrever o parser do frontend — não copiar o formato às cegas.

## Concorrência

Além da checagem otimista antes do insert (`_ensure_email_available`/equivalente), o
`create_<entidade>` trata `IntegrityError` do `commit()`: em caso de corrida entre duas
criações concorrentes com o mesmo identificador, faz `rollback()`, reconsulta o registro em
conflito e decide entre o erro de conflito comum e o de conflito-arquivado, conforme o
status encontrado. As `UniqueConstraint`s do banco continuam valendo inclusive contra
linhas arquivadas — são elas que garantem a integridade mesmo sob concorrência.

## Preservação de IDs ao migrar os `*-import.json`

Ao migrar Cliente/Fornecedor a partir dos arquivos de importação
(`frontend/src/lib/*-import.json`), preservar o `codigoInterno`/ID legado de cada registro
— necessário pras referências que hoje são só IDs de mock em domínios que ainda não
migraram (Tarefas, Projetos, Demandas).

Enquanto nenhuma tabela real referenciar `usuario.id`/`cliente.id`/`fornecedor.id` por FK,
o seed pode ser recriado do zero a qualquer momento. A partir do momento em que
Tarefas/Projetos/Demandas passarem a referenciar esses IDs, os seeds futuros **não podem
mais gerar UUIDs novos** — precisam preservar os IDs já emitidos.
