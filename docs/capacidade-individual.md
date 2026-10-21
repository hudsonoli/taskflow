# Capacidade individual e ausências — Fase 11B.2D-A (fundação backend)

Jornada semanal **opcional** por pessoa e **ausências por data** (férias, afastamento, folga, outro) que reduzem a capacidade da
Carga. Só backend: sem UI administrativa, sem frontend. A Carga ([carga-semanal.md](carga-semanal.md)) continua calculando o
**planejamento** exatamente como antes; só o **denominador de capacidade por pessoa** passa a poder variar.

## Hierarquia

```
RegraExpediente da empresa   ── fallback (e autoridade global: fuso, ativo/desligado, dias especiais, fator alocável)
        ↓
Jornada individual opcional  ── SUBSTITUI a semana recorrente (dia sem período = 0, sem fallback dia a dia)
        ↓
Ausências (DATE, dia inteiro) ── zeram o dia; sobreposição nunca desconta duas vezes
        ↓
Dias especiais da empresa    ── feriado/recesso fecham para todos; trabalho excepcional: interseção com a jornada
        ↓
percentual_capacidade_alocavel da empresa ── aplicado por último (round half-up, inteiros). Não existe fator por pessoa
```

- **Expediente da empresa desligado** (`ativo=false`) ou ausente: `capacidadeIndisponivel="expediente_desligado"`, mesmo que haja jornada
  individual. Nenhuma jornada reativa capacidade e, nesse caso, nem se consultam jornadas/ausências.
- **Sem jornada individual**: usa exatamente os períodos semanais da empresa (nada é copiado para a pessoa). Voltar ao padrão =
  `DELETE /usuarios/{id}/jornada` (remove a linha).

## Precedência diária (função pura `periodos_do_usuario_no_dia`)

1. Ausência no dia → 0.
2. Dia especial **fechado** (feriado/recesso ativo) → 0 para todos.
3. Dia especial **trabalho excepcional**: sem jornada individual usa os períodos do especial; **com** jornada usa a **interseção**
   dos períodos da jornada naquele dia da semana com os do especial. A jornada é o limite da pessoa: o dia especial nunca a expande
   (jornada 09–15 × especial 09–18 = 09–15; jornada sem período naquele dia da semana = 0).
4. Dia normal: períodos da jornada individual, ou da semana da empresa.

A interseção é feita em minutos sobre períodos já unidos: nunca conta o mesmo minuto duas vezes (`[09–12, 13–17] ∩ [10–14] = [10–12, 13–14]`).

## Modelo (migration `0052`, revisão `f1b7c3a95d28`, aditiva, sem backfill)

| Tabela | Papel |
| --- | --- |
| `usuario_jornadas` | `UNIQUE(usuario_id)`; **a existência da linha** = "tem jornada personalizada" (sem boolean redundante) |
| `usuario_jornada_periodos` | `jornada_id` (CASCADE), `dia_semana` 0..6, `ordem`, `inicio < fim`; mesmo padrão de `regra_expediente_periodos` |
| `usuario_ausencias` | `tipo ∈ {ferias, afastamento, folga, outro}`, `inicio`/`fim` DATE (`fim >= inicio`), `observacao` ≤ 500 |

Usuários existentes não recebem jornada e nenhuma ausência é criada. Ausências **podem se sobrepor** (sem constraint de exclusão): o
cálculo trabalha com o conjunto de **datas** cobertas. Ausência é **dia inteiro** (sem horas, meio período, banco de horas ou saldo de férias).

## API

| Método | Rota | Permissão |
| --- | --- | --- |
| `GET` | `/usuarios/{id}/jornada` | `usuarios.visualizar` |
| `PUT` | `/usuarios/{id}/jornada` | `usuarios.editar` + regra de alvo |
| `DELETE` | `/usuarios/{id}/jornada` ("Usar expediente da empresa") | `usuarios.editar` + regra de alvo |
| `GET` | `/usuarios/{id}/ausencias?desde=&ate=` | `usuarios.visualizar` |
| `POST` | `/usuarios/{id}/ausencias` | `usuarios.editar` + regra de alvo |
| `PATCH` | `/usuarios/{id}/ausencias/{ausenciaId}` | `usuarios.editar` + regra de alvo |
| `DELETE` | `/usuarios/{id}/ausencias/{ausenciaId}` | `usuarios.editar` + regra de alvo |

- `GET jornada`: `{usuarioId, personalizada, dias:[{diaSemana, periodos:[{inicio,fim}]}×7]}`. Com `personalizada=false`, `dias` é a
  semana da **empresa** (consulta do fallback).
- `PUT jornada`: substitui a grade inteira; dia não enviado = fechado; sem sobreposição; `inicio < fim`; no máx. 8 períodos/dia; mesma
  grade = no-op. Uma jornada sem nenhum período é válida (capacidade 0 explícita).
- Ausência: remoção **física**; o histórico são os eventos (mesmo padrão dos dias especiais do expediente).

### Autoridade (nada novo)

Reaproveita o RBAC de **editar Usuário**: `usuarios.editar` (admin e gestor por padrão) **mais** a regra de alvo de
`app/core/autoridade_usuarios` imposta no service — admin legado administra Gestor e Usuário; gestor (ou quem tem `usuarios.*` por
override) só administra Usuário (`operador`). Operador comum recebe 403; sem token 401; usuário de outra empresa = 404 (igual a
inexistente). Conta de sistema não tem jornada nem ausência (403). Consequência: um gestor **não** edita a própria jornada nem a de
outro gestor — só o admin legado (a mesma regra do PATCH de Usuário). Nenhuma permissão financeira, nenhum perfil novo.

### Auditoria

`usuario.jornada_alterada` (`acao: criada|substituida`), `usuario.jornada_removida`, `usuario.ausencia_criada|alterada|removida`, na
**mesma transação** da mudança; payload com `usuarioAfetadoId` e antes/depois essenciais (grade compacta; tipo e datas da ausência). A
observação livre **não** vai para o evento (`observacaoAlterada: bool`). No-op não gera evento.

## Integração com a Carga

`obter_capacidade_usuario(usuario, periodo, regra=, percentual_alocavel=, configuracao=)` continua sendo o único ponto que decide a
capacidade de uma pessoa, agora com a `ConfiguracaoCapacidade` (jornada + datas ausentes) **já carregada** — nunca consulta o banco.
A Carga carrega, em **duas consultas fixas** (jornadas+períodos e ausências que tocam a semana) para todos os elegíveis, e calcula em memória
(sem N+1: 14 consultas com 3 ou com 200+ usuários; era 12). Só com o expediente da empresa ligado.

- **Distribuição da estimativa pelas semanas** continua usando o calendário da **empresa** (peso = minutos nominais do dia): jornada e
  ausência de alguém **não** movem carga entre semanas nem alteram o rateio entre responsáveis. Só `capacidade*`, `saldoMin` e
  `ocupacaoPercentual` mudam.
- **Departamento**: capacidade = soma das capacidades reais das pessoas elegíveis (não "n × padrão"); o pool continua à parte.
- **Semana atual**: conta de hoje a domingo; ausência em dia anterior a hoje não afeta a capacidade restante.
- **Campos aditivos** por pessoa em `pessoas[]`: `capacidadeOrigem` (`empresa` | `individual`) e `diasAusentes` (dias **considerados** da
  semana cobertos por ausência, inclusive os que o expediente já fechava). Ambos `null` com a capacidade indisponível.
  `semana.dias[].minutosNominais` continua sendo o calendário da empresa por dia.
- Ausência **não** inativa o usuário; usuário inativo continua fora da capacidade.

## Fora desta fase

UI de edição de jornada/férias, ausência por hora/meio período, banco de horas, saldo de férias, aprovação de férias, fator alocável por
pessoa, importação de feriados por pessoa, cache e qualquer mudança no planejamento (estimativa, janela, rateio, pools).

## UI administrativa (11B.2D-B, só frontend)

Local: **Configurações → Usuários → editar → aba "Jornada e ausências"** (só ao editar; sem tela global). Código:
`frontend/src/components/usuarios/capacidade/`, regras puras em `frontend/src/lib/usuario-capacidade.ts` (testes: `npm run test:usuario-capacidade`).

- **Jornada de trabalho:** "Usar expediente da empresa" (padrão; só um resumo de leitura, nada é copiado) ou "Jornada personalizada"
  (grade semanal com 0..n períodos por dia, mesmo componente e mesma validação do Horário de expediente). Escolher "personalizada" só
  pré-preenche a tela com o expediente atual; **nada é gravado até Salvar** (`PUT` da grade inteira). Voltar ao padrão pede confirmação
  curta e chama `DELETE`.
- **Ausências:** lista (tipo traduzido, período, observação; atuais/futuras primeiro, passadas esmaecidas), modal de criar/editar
  (`POST`/`PATCH` só com o que mudou) e remoção com confirmação. Sobreposição é só um aviso (o backend aceita).
- **Autoridade:** reaproveita `podeEditarUsuario` (usuarios.editar + hierarquia de alvo) que a lista de Usuários já usa; o backend é a
  barreira (403 mostra a mensagem da API). Quem pode ver mas não editar um usuário (ex.: gestor vendo outro gestor ou a si mesmo)
  tem o botão **"Jornada"** na lista, que abre a mesma seção em **somente leitura**.
- **Requisições:** ao abrir, 1 `GET jornada` + 1 `GET ausências` em paralelo; as mutations usam a resposta da API (sem refetch global).
- **Carga:** a linha da pessoa mostra, em texto secundário, "Jornada personalizada" e/ou "N dias com ausência no período" (`diasAusentes` =
  dias do período consultado cobertos por ausência, **não** "dias descontados"). O cliente nunca recalcula capacidade.
- Não há "Minha jornada"/"Minhas férias", fator alocável por pessoa, nem edição de feriados aqui.
