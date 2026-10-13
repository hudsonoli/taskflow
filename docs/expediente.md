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

## Dias especiais NÃO são inertes (leia antes de cadastrar)

Esta fase não ativa o novo controle, mas **um dia especial ATIVO já afeta**: (a) os dias úteis (`dia_aberto`, avanço de `dias_uteis`); (b) o gate de ENTRADA em `em_execucao` (feriado/recesso ativo = "hoje não é dia útil", 409 `FORA_DE_EXPEDIENTE`); (c) o cálculo de prazos/SLA (`calcular_data_limite` pula o dia ou usa os períodos do `trabalho_excepcional`). Sem nenhum dia especial cadastrado, o comportamento é idêntico ao anterior. A tela avisa isso na seção de dias especiais.

- **Não cadastrar dias especiais reais em produção** durante/depois do deploy desta fase, e **não habilitar feriados automáticos** (a API recusa ligar a flag).
- **P2_EXPEDIENTE_GATE_PROFILE_EXEMPTIONS**: o gate legado de entrada em execução ainda se aplica a admin/gestor (coberto por teste). Na Fase 2, admin/gestor/conta de sistema (e o usuário com `acesso_fora_expediente`) serão isentos. Até lá, dias especiais reais **não** devem ser usados como mecanismo de bloqueio.

## Tolerância legada × antecedência de acesso (decisão desta fase)

- `tolerancia_retomada_minutos` (produção: **30**) **não foi alterada**: continua sendo usada pelo gate de entrada em execução (hoje a entrada já vale às 12:30). Não é zerada nem convertida.
- `antecedencia_acesso_minutos` (30) é armazenada à parte e **não é lida por nenhuma autenticação/autorização** (`NEW_ACCESS_ANTICIPATION_ACTIVE_IN_AUTH = NÃO`); não substitui a tolerância no gate. Teste: variar a antecedência de 0 a 120 não muda nenhuma resposta do gate de entrada nem da janela de trabalho, e variar a tolerância não muda o acesso.
- Na Fase 2 a semântica é substituída de forma consciente: 12:30 = acesso permitido, 13:00 = trabalho permitido.

## Deploy e rollback em produção

- Produção está em `f2c6a9d41b87`; a migration `0047` é `a3c8e5f17d24` com `down_revision = f2c6a9d41b87` (cabeça única, caminho linear).
- **Backup do banco é obrigatório antes de aplicar a migration.**
- O downgrade devolve o legado manhã/tarde a partir dos 2 primeiros períodos de cada dia: dia com 1 período volta inativo e do 3º período em diante é descartado (**perda estrutural aceita**). Portanto, **se for preciso reverter DEPOIS de alterações reais na nova configuração, NÃO execute o downgrade às cegas**: restaure o snapshot do banco ou reconcilie antes os períodos (deixe cada dia com 0 ou exatamente 2 períodos). Reverter só o código (sem downgrade) é seguro: as colunas legadas ficam espelhadas para dias com 2 períodos.
