# Contrato frontend-backend de Clientes

## Objetivo

Esta fundacao separa tres representacoes:

```text
ClienteApiResponse (DTO da API)
  -> Cliente (modelo de dominio do frontend)
  -> ClienteDraft (estado temporario do formulario)
```

`ClienteApiResponse` espelha o JSON do backend. `Cliente` preserva os dados persistidos e acrescenta somente derivados de apresentacao, como `statusLabel` e `nomePrincipal`. `ClienteDraft` continua restrito ao formulario existente e nao e o contrato central da integracao.

Esta etapa nao realiza chamadas HTTP e mantem os mocks atuais.

## Mapeamento de campos

| Frontend | Backend | Observacoes |
|---|---|---|
| `Cliente.id` | `id` | UUID gerado pelo backend; nunca deve ser gerado pelo mapper de criacao. |
| `Cliente.empresaId` / draft `empresaId` | `empresaId` | Obrigatorio no POST; nao pertence ao PATCH. |
| `Cliente.agenciaId` | `agenciaId` | UUID opcional e anulavel. Ainda nao existe campo correspondente no formulario atual. |
| `Cliente.codigoInterno` / draft `codigoInterno` | `codigoInterno` | Obrigatorio no POST e permitido no PATCH. |
| `Cliente.tipoPessoa` | `tipoPessoa` | Valores da API: `fisica` e `juridica`. |
| draft `tipoDocumento = cpf` | `tipoPessoa = fisica` | Conversao explicita no mapper. |
| draft `tipoDocumento = cnpj` | `tipoPessoa = juridica` | Conversao explicita no mapper. |
| `Cliente.documento` / draft `documento` | `documento` | CPF/CNPJ e enviado somente com digitos. |
| `Cliente.razaoSocial` | `razaoSocial` | Usado para PJ; recebe `nomeRazaoSocial` do draft. |
| `Cliente.nome` | `nome` | Obrigatorio para PF; recebe `nomeRazaoSocial` do draft. |
| `Cliente.nomeFantasia` / draft `nomeFantasia` | `nomeFantasia` | Opcional e anulavel. |
| `Cliente.nomePrincipal` | derivado | Prioriza nome fantasia, razao social, nome e codigo interno. Nao e enviado. |
| `Cliente.sigla` / draft `sigla` | `sigla` | Opcional e anulavel. |
| `Cliente.email` / draft `email` | `email` | Opcional e anulavel. |
| `Cliente.telefone` / draft `telefone` | `telefone` | Opcional e anulavel. |
| `Cliente.celular` / draft `celular` | `celular` | Opcional e anulavel. |
| `Cliente.site` / draft `site` | `site` | Opcional e anulavel. |
| `Cliente.codigoExterno` | `codigoExterno` | Suportado pela API, mas sem campo no formulario atual. |
| `Cliente.observacoes` | `observacoes` | Suportado pela API, mas sem campo no formulario atual. |
| `Cliente.status` | `status` | Valores persistidos: `ativo`, `suspenso`, `inativo`. |
| `Cliente.statusLabel` | derivado de `status` | Rotulos visuais: `Ativo`, `Suspenso`, `Inativo`. Nao e enviado. |
| `Cliente.statusAlteradoAt` | `statusAlteradoAt` | Metadado somente de resposta. |
| `Cliente.statusAlteradoPorUsuarioId` | `statusAlteradoPorUsuarioId` | Metadado somente de resposta. |
| `Cliente.motivoStatus` | `motivoStatus` | Metadado somente de resposta. |
| `Cliente.createdAt` | `createdAt` | Data ISO somente de resposta. |
| `Cliente.updatedAt` | `updatedAt` | Data ISO somente de resposta. |

## Campos suportados

O POST suporta `empresaId`, `agenciaId`, `codigoInterno`, `tipoPessoa`, `documento`, `razaoSocial`, `nomeFantasia`, `nome`, `sigla`, `email`, `telefone`, `celular`, `site`, `codigoExterno`, `observacoes` e status inicial `ativo`.

O PATCH suporta os mesmos campos cadastrais, exceto `empresaId` e `status`. Strings vazias do draft sao normalizadas para `null` nos campos opcionais. O documento sempre e normalizado para digitos.

## Campos sem suporte no backend de Clientes

Os campos abaixo existem no draft visual, mas nao pertencem ao contrato atual da API:

- `equipeResponsavelId`;
- `responsavelComercialId`;
- `responsavelAtendimentoId`;
- `endereco`;
- `contatos`;
- `administrativo`;
- `historico`.

Esses campos sao omitidos pelos mapeadores de POST e PATCH. Na integracao HTTP futura, devem permanecer desabilitados ou explicitamente marcados como somente visuais ate existir contrato backend proprio. A interface nao deve indicar que foram persistidos.

`agenciaId`, `codigoExterno` e `observacoes` seguem a situacao inversa: a API os suporta, mas o formulario atual ainda nao os edita.

## Mudancas de status

Status nao deve ser enviado no PATCH. As transicoes usam endpoints dedicados:

| Acao | Endpoint | Payload |
|---|---|---|
| Suspender | `POST /clientes/{id}/suspender` | `{ motivo: string }` |
| Reativar | `POST /clientes/{id}/reativar` | `{ motivo?: string | null }` ou corpo ausente |
| Inativar | `POST /clientes/{id}/inativar` | `{ motivo: string }` |

A criacao aceita somente o status inicial `ativo`.

## Listagem e paginacao

A listagem aceita `status`, `tipoPessoa`, `agenciaId`, `busca`, `limit` e `offset`. A resposta atual e um array de clientes e nao informa `total`.

Sem total, a interface nao consegue calcular quantidade de paginas ou total global com precisao. A integracao deve usar `limit`/`offset` com a acao **Carregar mais**, encerrando quando a pagina retornar menos itens que o limite solicitado.

## Autenticacao e transporte

Todos os endpoints de Clientes exigem autenticacao Bearer e aceitam somente os perfis autorizados pelo backend. O frontend ainda nao possui sessao real nem transporte HTTP configurado.

A integracao HTTP depende primeiro de uma solucao de autenticacao real. Nao deve ser criado token fixo, token mock, armazenamento em `localStorage` ou qualquer mecanismo que exponha credenciais no bundle. A estrategia recomendada e sessao segura com cookie HttpOnly e transporte same-origin ou outra solucao aprovada na etapa de autenticacao.
