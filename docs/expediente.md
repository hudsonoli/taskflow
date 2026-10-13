# Expediente — fundação (Fase Expediente 1)

Fase **somente de modelo, cálculo e configuração**. NADA bloqueia acesso e NADA pausa trabalho sozinho: não há gate global (`get_current_user_password_ready` intacto), nem erro `FORA_DO_EXPEDIENTE`, nem scheduler, nem pausa/encerramento automático, nem importação de feriados, nem sessão própria de operador. As flags `bloquear_fora_expediente`, `pausar_no_fim_periodo` e `feriados_automaticos` existem, nascem **falsas** e a API recusa ligá-las até as fases que as implementam.

## Modelo

| Tabela / campo | O que é |
| --- | --- |
| `regra_expediente_periodos` | Períodos por dia da semana (0 = fechado, 1 ou mais = aberto). `inicio < fim`, fim exclusivo, sem atravessar a meia-noite, sem sobreposição (validada no schema), no máximo 8 por dia. |
| `regra_expediente.antecedencia_acesso_minutos` (30) | Antecedência de **acesso** — não é trabalho. |
| `regra_expediente.timezone` | IANA, validado. Preenchido na migration com o `APP_TIMEZONE` atual (America/Sao_Paulo). |
| `regra_expediente_dias_especiais` (+ `_periodos`) | feriado / recesso / trabalho_excepcional / ignorado; origem automatico / manual; ativo. Cadastro **manual** em `/regra-expediente/dias-especiais`. |
| `usuarios.acesso_fora_expediente` | Isenção individual. Só o campo (e auditoria `usuario.alterado`). |
| `demandas.pausa_origem` / `pausada_em` | `manual` (grava a transição normal) · `expediente` (reservado, Fase 3) · `NULL`. O evento `demanda.status_alterado` ganha `pausaOrigem` ao pausar. |

## Janela de trabalho × janela de acesso (`app/core/expediente.py`)

- `esta_dentro_janela_trabalho` / `proximo_inicio_trabalho`: só os períodos (início inclusivo, fim exclusivo).
- `esta_dentro_janela_acesso` / `proximo_acesso`: cada período antecipado em `antecedencia_acesso_minutos`. Com 08–12/13–18 e 30 min: acesso 07:30–12:00 e 12:30–18:00; **07:30–07:59 e 12:30–12:59 dão acesso mas não são trabalho**.
- Precedência: dia especial vence a regra semanal; na mesma data a decisão **manual** ativa vence a **automática**; `feriado`/`recesso` fecham; `trabalho_excepcional` usa períodos próprios; `ignorado` neutraliza a data.
- Comparações por instante (`ZoneInfo`, seguro para horário de verão); o fuso é o da regra, nunca o do navegador.

## Compatibilidade com o modelo antigo (migration 0047)

- Estratégia **expand sem contract**: `regra_expediente_periodos` nasce COPIANDO `manha_*` → período 1 e `tarde_*` → período 2 (horários nominais, nenhum deslocado). As colunas legadas ficam (espelho quando o dia tem exatamente 2 períodos); só o CHECK antigo foi removido. Remoção das colunas = fase futura.
- **`tolerancia_retomada_minutos`** (OLD_BEHAVIOR): a ENTRADA em `em_execucao` é aceita X min antes do início do 2º período. **Não foi convertida nem somada aos períodos**: continua na coluna e continua sendo honrada por `esta_dentro_expediente` (o gate de entrada de sempre). Por isso o gate responde idêntico antes/depois (teste minuto a minuto sobre dados migrados) e o SLA — que enxerga os períodos nominais — não muda. Valor medido em produção (somente leitura): **30**, regra ativa, seg–sex 09:00–12:00 / 13:00–18:00.
- Downgrade: reconstrói `manha_*/tarde_*` dos 2 primeiros períodos; dia com 0/1 período volta inativo; do 3º período em diante é descartado (perda documentada).
- O gate de entrada e a calculadora de SLA passam a respeitar dias especiais ativos (sem nenhum cadastrado, nada muda).

## Backlog registrado (não implementado)

Gate de acesso e tela "Fora do expediente" · scheduler/pausa automática (decisão: pausar se não restar sessão de usuário isento) · importação BrasilAPI (apenas feriados **nacionais**; estaduais/municipais são manuais) · sessão própria do operador (só para si) · período que atravessa a meia-noite · remoção das colunas legadas.
