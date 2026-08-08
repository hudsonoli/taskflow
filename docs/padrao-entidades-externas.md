# Padrão: entidades internas × entidades externas

> Este documento existe por causa de um erro concreto. Ao migrar Cliente (Fase 2B), o
> padrão de Departamento foi copiado mecanicamente — incluindo `UNIQUE(empresa_id,
> nome_normalizado)`. O seed com os 126 clientes reais abortou, e a investigação mostrou que
> a constraint não descrevia o negócio: descrevia um domínio diferente.

## O erro que este documento evita

Departamento, Equipe e Cliente parecem a mesma coisa na estrutura: id + código de
referência + nome + status + arquivamento. A tentação é replicar o modelo inteiro.

Mas há uma diferença que muda a modelagem: **quem controla o nome**.

- Em Departamento e Equipe, o nome é **decidido pela própria empresa**. Ter dois
  departamentos "Criação" é erro de cadastro, e a constraint impede um problema real.
- Em Cliente, o nome é **um fato do mundo externo**. A empresa não escolhe como o cliente
  se chama, e nomes se repetem legitimamente.

## A evidência

Levantamento na base real de clientes (126 registros, importados do sistema anterior):

| Situação | Casos | Exemplo |
|---|---|---|
| Mesmo nome, documento diferente | 4 pares | `BRETAS CENTRO` em duas unidades: CNPJ `…0297-39` e `…0302-30` |
| Mesmo documento, nome diferente | 4 grupos | 3 empreendimentos `CMO – VARANDAS …` sob o mesmo CNPJ `10.748.163/0001-00` |
| Sem documento preenchido | 6 | cadastros antigos, incompletos mas válidos |

Filial e empreendimento são cadastros **corretos**. Nenhuma constraint de banco acomoda os
dois casos ao mesmo tempo, e forçar um deles significaria distorcer o dado real — renomear
"BRETAS CENTRO" para "BRETAS CENTRO (0297-39)" só para caber no schema.

**A integridade da informação vale mais do que impedir cadastros potencialmente válidos.**

## Regra

### Entidades organizacionais internas

A empresa controla o nome; repetição é erro de cadastro.

| Entidade | Regra de unicidade |
|---|---|
| **Departamento** | nome único por empresa (`uq_departamentos_empresa_nome_normalizado`) |
| **Equipe** | nome único por empresa (`uq_equipes_empresa_nome_normalizado`) |
| **GrupoCliente** | nome único por empresa — mantém a regra já implementada na Fase 2A |

A unicidade vale contra **arquivados** também: um nome liberado por arquivamento continua
reservado, e a tentativa de recriar devolve 409 com o id do arquivado, para a interface
oferecer *restaurar* em vez de só reclamar de duplicidade (ver
[padrao-arquivamento.md](padrao-arquivamento.md)).

### Entidades externas

O mundo controla o nome; repetição é fato, não erro.

| Entidade | Regra |
|---|---|
| **Cliente** | nome **não** é identidade · documento **não** é identidade · nem os dois juntos bloqueiam |
| **Fornecedor** | mesma regra, aplicada na Fase 2C. A base importada confirmou a previsão: 16 dos 133 registros sem documento e documento repetido entre cadastros distintos |

Unicidade em Cliente existe **apenas** onde é identidade de verdade:

```
uq_clientes_empresa_codigo_interno
uq_clientes_empresa_codigo_referencia
uq_clientes_empresa_ano_sequencial
```

## Identidade em entidade externa

| Identificador | Papel |
|---|---|
| `id` (UUID) | identidade **técnica** — PK, FK e rotas. Nunca exibido |
| `codigo_referencia` (`C26000001`) | identidade **funcional** — imutável, pesquisável, é o que o negócio usa |
| `codigo_interno` (`#2001`) | **ponte de importação/compatibilidade** — preserva a chave do sistema anterior. Nunca aceito pela API pública; só seeds e importadores o resolvem. Sai quando os domínios que o referenciam migrarem |

Nome nunca é chave de relacionamento. Importadores localizam **exclusivamente** por
`empresa_id + codigo_interno` — nunca por nome, nunca por documento, nunca por UUID (que
muda a cada ambiente e impediria reconstruir um banco vazio só com migrations + seeds).

## Coincidência gera alerta, não bloqueio

Ao criar ou alterar um Cliente, o backend procura registros com o mesmo nome e/ou o mesmo
documento e devolve **dados estruturados** na resposta de sucesso:

```jsonc
// 201 Created
{
  "...": "campos do cliente criado",
  "possiveisDuplicidades": [
    {
      "id": "…",
      "codigoReferencia": "C26000042",
      "nome": "BRETAS CENTRO",
      "documento": "39.346.861/0297-39",
      "status": "ativo",
      "motivo": "nome"          // nome | documento | nome_documento
    }
  ]
}
```

Regras do mecanismo:

- **o cadastro é sempre criado** — coincidência nunca vira 409;
- `motivo` é lista fechada, para o frontend decidir a apresentação sem interpretar texto livre;
- calculado **antes** do INSERT, senão o próprio registro apareceria no resultado; no update, o próprio id é excluído da busca;
- só nas respostas de escrita — em listagem seria uma consulta por linha, sem serventia;
- inclui arquivados de propósito: recriar um homônimo arquivado é exatamente quando o operador precisa ser avisado;
- **sem estado mutável no service** — a detecção é uma função pura sobre o banco, e o resultado trafega como retorno, não como atributo de instância (o service é singleton entre requisições concorrentes).

Na interface: mensagem informativa ("Encontramos clientes com dados semelhantes"), nunca
afirmando que são duplicados, sem merge automático, sem alterar o registro existente e sem
impedir o usuário de continuar.

**Deduplicação é regra de negócio com revisão humana, não constraint de banco.** Fica para
uma funcionalidade futura.

## Ao migrar um domínio novo

Antes de copiar `UNIQUE(empresa_id, nome_normalizado)`, responder:

1. **Quem decide o nome** — a empresa ou o mundo externo?
2. **Repetição é erro ou fato?** Levantar os dados reais antes de decidir; o schema deve descrever o negócio, não o contrário.
3. **Qual é a identidade funcional de verdade?** Em geral `codigo_referencia`, não o nome.
4. **Se coincidência não é erro, como o operador fica sabendo?** Alerta estruturado, não bloqueio.

Casos já decididos:

- **Fornecedor** — entidade externa, migrado na Fase 2C sem unicidade de nome nem de documento, com o mesmo alerta estruturado. Divergiu de Cliente em dois pontos deliberados: o diretório **não** inclui arquivados (nenhum domínio referencia fornecedor, então ele só serve para montar opções de vínculo novo) e o status não tem `suspenso` (seria estado sem regra de negócio).
- **Projeto** — regra própria, a decidir na fase correspondente. Nome de projeto pode repetir entre clientes diferentes e provavelmente não deve repetir dentro do mesmo cliente; isso é decisão de negócio, não herança automática de Departamento.

## Referências

- [padrao-arquivamento.md](padrao-arquivamento.md) — soft-delete, motivo obrigatório e conflito-arquivado
- [pendencias-arquiteturais.md](pendencias-arquiteturais.md) — divergências conhecidas entre domínios já migrados
- `backend/app/models/cliente.py` e `backend/app/models/fornecedor.py` — as decisões registradas junto do código
- `backend/app/services/cliente_service.py` e `fornecedor_service.py` — `detectar_possiveis_duplicidades`
- `backend/tests/test_cliente.py` e `test_fornecedor.py` — os casos permitidos e os três motivos de alerta
