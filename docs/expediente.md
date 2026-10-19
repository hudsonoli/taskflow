# Expediente — Fase 3: pausa automática no fim dos períodos

> **Estado:** implementado em branch (`feature/expediente-fase3`), **não mergeado nem deployado** (aguarda revisão e o fechamento do Teste C da 11B.2A em produção). As seções das fases anteriores
> seguem válidas; onde a Fase 3 muda algo, está dito aqui.

## O que faz (e o que NÃO faz)

Com `pausarNoFimPeriodo` ligada (e o controle-mestre ativo), ao fim de **CADA período** do expediente (12:00, 18:00…) o **backend** pausa as Demandas em `em_execucao` da empresa, encerra as
sessões pessoais dos usuários sujeitos e grava `pausa_origem='expediente'`, `pausada_em = corte`. **Não faz logout** (política independente: 18:00 pausa, 18:10 desloga se configurado), **não
retoma** nada (às 13:00 a Demanda continua pausada; a pessoa decide voltar) e **não depende de navegador, aba, React ou relógio do cliente**.

## Tick

- `app/core/expediente_tick.py`: UMA `asyncio.Task` no `lifespan` (cancelada no shutdown), rodada a cada ~60 s (dorme até `HH:MM:01`), trabalho de banco em `asyncio.to_thread`. **Sem APScheduler, sem Redis, sem container novo.** Config: `EXPEDIENTE_TICK_HABILITADO` (padrão ligado; a suíte desliga) e `EXPEDIENTE_TICK_SEGUNDOS` (60). Uma rodada logo após subir (5 s) cobre restart.
- `ExpedientePausaService` (`app/services/expediente_pausa_service.py`): `executar_tick` (empresas com a pausa ligada) → `processar_empresa` (um corte).

## Corte efetivo = o horário CONFIGURADO

`cutoff_pendente` (app/core/expediente.py): o fim de período mais recente já passado; se o tick roda às 12:00:42, o corte é **12:00** — `pausada_em`, `fim_em` das sessões e o `occurred_at` dos eventos usam 12:00. Períodos/feriado/recesso/trabalho excepcional/ignorado vêm dos MESMOS helpers de calendário (`periodos_do_dia`); dia sem período não tem corte; períodos encostados (12:00 = início de outro) não têm corte entre eles. Tudo no fuso `regra_expediente.timezone`.

## Corte perdido (catch-up) — nunca retroativo

Um corte só é elegível se (a) é **posterior** à "armadura" da pausa (`pausa_automatica_ativada_em`) e (b) **nenhum período novo começou** depois dele. 12:00 com restart às 12:20 → processa; restart às 13:10 → **não** retro-pausa as 12:00 (o 2º período começou e pode haver trabalho legítimo); 18:00 com restart às 18:30 → processa. Corte processado com atraso > 5 min gera o aviso estruturado `expediente_corte_perdido_processado_em_catch_up`.

## Ligar no meio do intervalo (migration 0049)

`regra_expediente.pausa_automatica_ativada_em TIMESTAMPTZ NULL` (revisão `c6e1a38d5b92`, down `b4d7f2a96c31`). É o instante em que a pausa foi **armada**: ao ligar a flag, religar o controle-mestre, editar dias/fuso ou criar/alterar/remover dia especial **com a pausa ligada**; desligar limpa. Ligar às 12:15 **não** pausa o corte das 12:00 (armadura 12:15 > corte 12:00); o das 18:00 vale. NULL = nunca armada = nada é pausado. Persistido no banco — nenhuma heurística de memória de processo. Nasce NULL para todas as regras existentes; o deploy não pausa nada.

## Idempotência, multi-instância e atomicidade

- **Chave** `expediente:<empresa>:<dia-local>:<HH:MM>` → `eventos.correlation_id` = UUID v5 determinístico. Ao concluir, grava o registro `expediente.pausa_automatica_executada` (entidade = a empresa, mesmo `correlation_id`); antes de executar confere se ele existe. Sem esse registro um restart às 18:30 repausaria o que um isento reabriu às 18:05.
- **Advisory lock** `pg_try_advisory_xact_lock(hashtextextended(chave, 0))` por empresa+corte: outra instância no mesmo corte desiste (`lock_ocupado`); solta sozinho no commit/rollback/queda da conexão (sucesso, erro ou cancelamento).
- **Granularidade:** UMA transação por empresa+corte com um **SAVEPOINT por Demanda** — sessões fechadas, pausa e eventos de uma Demanda nunca ficam pela metade, sem uma transação por demanda solta. Se uma Demanda falha, as outras seguem e o registro de conclusão NÃO é gravado (a próxima rodada refaz só o que faltou; quem já foi pausada não duplica).
- **Serialização com o usuário:** o tick lê as Demandas `FOR UPDATE`; `update_demanda` (mudança de status) trava a linha ANTES do gate de horário e `abrir sessão` já travava. 11:59:59 × tick das 12:00: ou a transição vale antes do corte e o tick a pausa, ou o gate a recusa — nunca "sessão ativa + Demanda pausada".

## Quais Demandas e sessões

- **Pausa MESMO sem sessão** (o tempo operacional não depende de Play manual).
- Sessões de usuários **sujeitos** (operador comum, mesmo Head/Atendimento) são encerradas com motivo próprio **`fim_expediente`** (`fim_em = corte`; nunca duração negativa — fim anterior ao início é limitado ao início com warning `sessao_trabalho_fim_anterior_ao_inicio`). Sessão só de departamento (sem pessoa) é tratada como sujeita.
- Sobrou sessão ATIVA de pessoa **isenta** (admin, gestor, conta de sistema, `acesso_fora_expediente`) e usuário ativo? A Demanda **continua em execução** (a sessão do isento é preservada). Atividade NÃO é inferida só por ele ser responsável: precisa de sessão pessoal ativa. Isento inativo/bloqueado não segura a Demanda (e sua sessão é encerrada junto — nunca sessão ativa + Demanda pausada).
- Pausa manual segue `pausa_origem='manual'`; só o tick grava `expediente` (teste estrutural).

## Auditoria / ator

Ação do **SISTEMA**: `usuario_id = NULL` + `metadata {origem: "sistema", fonte: "expediente"}` — nenhum usuário real é usado. Eventos por execução, todos com o mesmo `correlation_id`: `demanda.status_alterado` (de=em_execucao, para=pausada, `pausaOrigem=expediente`, `automatico`, `cutoff`, `chaveExecucao`) por Demanda pausada; `sessao_trabalho_encerrada` (`motivoEncerramento=fim_expediente`, `origem=expediente`) por sessão fechada; `expediente.pausa_automatica_aplicada` por PESSOA afetada (só se `quantidade > 0`); `expediente.pausa_automatica_executada` (conclusão do corte).

## Aviso "Tarefas pausadas automaticamente."

Fonte = servidor. `GET /expediente/estado` (o polling único de ~30 s) traz `ultimaPausaAutomatica {eventoId, em, quantidade}` da pessoa. Afetados por evidência: responsáveis atuais da Demanda **e da etapa atual** pausada ∪ quem teve sessão encerrada nela — nada global; quem só teve a sessão fechada mas cuja Demanda continuou em execução (isento ativo) **não** recebe. O front (`PausaAutomaticaAviso`, `AvisoFlutuante`, ~5 s, `role=status`, sem vermelho) mostra só evento **novo** (`eventoId` não apresentado; `localStorage` por usuário com try/catch e fallback em memória), **recente** (≤ 10 min contra o `agora` do servidor) e `quantidade > 0`. Segurança não depende do localStorage.

## Abrir sessão pessoal é trabalho (gate)

Antes: `POST /sessoes-trabalho/abrir` só exigia a Demanda em `em_execucao` — entre 12:00 e o tick uma sessão nova abriria. Agora usa a MESMA autoridade (`garantir_trabalho_permitido`, módulo `app/services/expediente_trabalho.py`, também usado pelo `DemandaService`) sobre a **pessoa da sessão**: fora da janela → o mesmo 409 `FORA_DE_EXPEDIENTE`. Sessão só de departamento = sujeita.

## Limitações e o que continua fora

Sem retomada automática; sem sincronização de feriados (`feriadosAutomaticos` segue 422); sem Tráfego V2 / `demanda_status_intervalos` / 11B.2B. O botão manual do Tráfego segue como está. Métricas de duração do Tráfego V2 só serão expostas depois desta fase estar em produção.

---

# Expediente — Fase 2: bloqueio de acesso e logout automático

> **Estado:** **em produção** (Fase 2 deployada). As seções "Fase 1" abaixo continuam válidas como histórico do modelo; onde a Fase 2 muda algo, está dito aqui.

## Quatro conceitos, nunca misturados

| | O que é | Fase 2 |
| --- | --- | --- |
| **A. Acesso** | Poder entrar/usar o sistema: períodos antecipados em `antecedencia_acesso_minutos`. | **Enforçado** (403 `FORA_DO_EXPEDIENTE`) quando `bloquear_fora_expediente=true`. |
| **B. Trabalho** | Poder ENTRAR em `em_execucao`: só os períodos nominais. | **Enforçado** (409 `FORA_DE_EXPEDIENTE`, contrato antigo preservado). A **tolerância legada deixou de valer**. |
| **C. Logout automático** | Encerrar as sessões no horário próprio `logout_horario`. | **Enforçado** (401 por token anterior ao corte). |
| **D. Pausa automática** | Pausar Demandas ao fim dos períodos. | **NÃO existe** (Fase 3). `pausarNoFimPeriodo` segue recusada com 422. |

Exemplo oficial (09–12 / 13–18, antecedência 30, logout 18:10): acesso 08:30–12:00 e 12:30–18:00; trabalho 09:00–12:00 e 13:00–18:00; **12:30 = acesso SIM, trabalho NÃO**; 13:00 = trabalho SIM; 18:00–18:09 = sem acesso (se bloqueio ligado); 18:10 = corte do logout. Coberto minuto a minuto em `tests/test_expediente_fase2_core.py` e `_api.py`.

## Quem está sujeito

Só `perfil_base = operador` que **não** é conta de sistema e **não** tem `acesso_fora_expediente`. A autoridade é o `perfil_base`/a política — nunca um rótulo de tela, nem relações como Head/Atendimento (um operador que é Head continua sujeito). **Isentos** de acesso, trabalho e logout: admin, gestor, conta de sistema, operador com `acesso_fora_expediente=true` e o Administrador da Plataforma (token de plataforma é outro; a porta `/plataforma/acesso` e `/plataforma/sessao` não aplica o gate de expediente). Decisão em um ponto só: `usuario_sujeito_ao_expediente` (core) / `usuario_esta_sujeito_ao_expediente` (dependency).

## Backend

- **Gate de acesso** em `get_current_user_password_ready` (já era o gate de todas as rotas tenant). Fora da janela de ACESSO → `403 {detail: {code: "FORA_DO_EXPEDIENTE", message, proximoAcesso, proximoTrabalho, proximoTrabalhoFim, timezone}}`. 403 (sessão válida) e **nunca 401**.
- **Rotas fora do gate de expediente, por desenho (6):** `GET /auth/me`, `POST /auth/definir-senha-inicial`, `POST /auth/alterar-senha`, `GET /expediente/estado`, `GET /plataforma/acesso`, `POST /plataforma/sessao` (+ login/recuperação/público, que nem autenticam). Teste estrutural (`test_so_seis_rotas_...`) quebra se uma rota nova usar só `get_current_user`. Por isso **não há laço** login → 403 → login: o login em si nunca é 403, e `/auth/me` identifica a pessoa para montar a tela.
- **Logout automático** em `get_current_user` (vale também para `/auth/me` e `/expediente/estado`): `ultimo_corte_logout` = corte mais recente que já passou (hoje se `logout_horario` já chegou, senão ontem); token cujo `iat` é **anterior** ao corte → `401`. Token emitido no corte ou depois (novo login) segue valendo — **independente do bloqueio**: com logout ligado e bloqueio desligado, um login às 18:30 funciona; com bloqueio ligado, o login funciona e o uso é barrado com 403. A decisão é do servidor (claim `iat`, fuso da empresa) → vale para qualquer aba/navegador/dispositivo; nenhum `localStorage` entra.
- **Gate de trabalho** (`DemandaService._ensure_dentro_expediente(db, empresa_id, actor)`): `esta_dentro_janela_trabalho` + isenções. **Resolve `P2_EXPEDIENTE_GATE_PROFILE_EXEMPTIONS`** (admin/gestor/sistema/override não recebem 409). Regra desligada (`ativo=false`) libera.
  - **Três portas, UMA autoridade** (hardening pós-Fase 2): `PATCH /demandas/{id}`, `POST /demandas` com `status=em_execucao` e `POST /demandas/{id}/restaurar` (quando `status_anterior_arquivamento = em_execucao`) chamam o mesmo `_ensure_dentro_expediente`; nenhum decide horário por conta própria (teste estrutural). Recusa = o MESMO `409 FORA_DE_EXPEDIENTE` (nenhum código novo).
  - **Criar** recusado não cria a Demanda nem queima número/referência (o gate roda antes dos contadores). **Restaurar** recusado **não muda nada** — a Demanda segue arquivada; nunca é restaurada em silêncio com outro status (decisão de produto explícita seria necessária). Restaurar para qualquer outro status segue livre a qualquer hora.
- **`GET /expediente/estado`** passou a trazer, para a pessoa logada: `sujeitoAoExpediente`, `bloqueioAtivo`, `acessoPermitido`, `trabalhoPermitido`, `proximoAcesso`, `proximoTrabalho`, `proximoTrabalhoFim`, `timezone`. `dentroExpediente` agora é da **empresa** e da janela **nominal** (sem tolerância, sem isenção). Responde fora da janela (é o polling que avisa que o acesso voltou).
- **Cache** da regra por empresa (`get_regra_calculo_para_gate`): TTL 10 s, em memória do processo, **só a regra** (nunca a decisão por pessoa — `acesso_fora_expediente`/perfil vêm do usuário da própria requisição, então mudam na requisição seguinte). Invalidado ao salvar a regra e os dias especiais neste processo; com mais de um worker, o TTL limita o atraso. Somente leitura: **não cria** a regra padrão (empresa sem regra = sem política).
- **Config:** `bloquearForaExpediente` pode ser ligada; `logoutAutomaticoAtivo` + `logoutHorario` ("HH:MM", normalizado a minutos; ligar exige horário — 422). `pausarNoFimPeriodo` e `feriadosAutomaticos` continuam recusadas (422).
- **Migration `0048` (`b4d7f2a96c31`, down `a3c8e5f17d24`, cabeça única):** `logout_automatico_ativo BOOLEAN NOT NULL DEFAULT FALSE`, `logout_horario TIME NULL`, CHECK (ligado exige horário). Nasce **desligado**: o deploy não desloga ninguém e não altera as outras flags. Downgrade só remove o que ela criou.

## Frontend

- **Um único polling** (~30 s) de `/expediente/estado`: `lib/expediente-estado-store.ts` (store puro, timer só com assinantes, busca em voo compartilhada, rajada de 403 = 1 busca). Kanban, Meu Departamento, a tela de configuração e o guarda leem o mesmo store; o Kanban passou a usar `trabalhoPermitido` (decisão do servidor com isenções).
- **`ExpedienteGuard`** (só na área tenant; nunca em `/gestao`) mostra `ForaDoExpedienteView` ("Fora do horário de expediente", próximo acesso e próximo período no fuso da empresa, botão Sair). Duas fontes: o `403 FORA_DO_EXPEDIENTE` (via `aoRecusar` do mesmo fetch envolvido do hotfix de 401 — um único handler) e o poll. O poll mais novo vence: `acessoPermitido=true` devolve o app **sem novo login**; o 13:00 é que libera o trabalho.
- **401 × 403:** 401 (sessão expirada ou logout automático) → login do tenant com `reason=session_expired`; 403 `FORA_DO_EXPEDIENTE` → tela de expediente; **outro 403**, 404, 409, 422, 5xx → tratamento normal de cada tela.
- **Configurações → Horário de expediente:** quatro cartões independentes (controle, bloqueio, pausa "Em breve", logout + horário).

## Limitações registradas (Fase 3 resolve)

- **O logout automático trata AUTENTICAÇÃO.** Ele **não** encerra sessão de trabalho, **não** pausa Demanda e **não** cria `pausa_origem='expediente'`. Uma Demanda em execução continua em execução depois das 12:00/18:00/18:10 até alguém (ou a Fase 3) agir.
- Sem scheduler, sem toast de pausa, sem importação de feriados (`feriadosAutomaticos` travado), sem sessão própria do operador.
- Operador **sem** `acesso_fora_expediente` logado e **sem** nenhum isento ativo continua podendo ter trabalho em execução fora da janela até a Fase 3.
- `tolerancia_retomada_minutos` ficou **deprecated**: a coluna e `esta_dentro_expediente` permanecem por compatibilidade (testes, payload 409, rollback), sem autoridade sobre trabalho. Pode ser removida numa fase futura.
- **Ligar o bloqueio em produção** passa a barrar operadores fora da janela de acesso imediatamente (e o gate de trabalho já vale para eles pela nominal): avisar a operação antes de ligar; admin/gestor/isentos não são afetados.

---

# Expediente — fundação (Fase Expediente 1) — histórico

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
- **P2_EXPEDIENTE_GATE_PROFILE_EXEMPTIONS** — *resolvido na Fase 2*: o gate de entrada em execução isenta admin/gestor/conta de sistema/`acesso_fora_expediente`.

## Tolerância legada × antecedência de acesso (decisão da Fase 1 — SUPERADA pela Fase 2)

- `tolerancia_retomada_minutos` (produção: **30**) **não foi alterada**: continua sendo usada pelo gate de entrada em execução (hoje a entrada já vale às 12:30). Não é zerada nem convertida.
- `antecedencia_acesso_minutos` (30) é armazenada à parte e **não é lida por nenhuma autenticação/autorização** (`NEW_ACCESS_ANTICIPATION_ACTIVE_IN_AUTH = NÃO`); não substitui a tolerância no gate. Teste: variar a antecedência de 0 a 120 não muda nenhuma resposta do gate de entrada nem da janela de trabalho, e variar a tolerância não muda o acesso.
- Fase 2 (**implementada**): a semântica foi substituída de forma consciente — 12:30 = acesso permitido, trabalho NÃO; 13:00 = trabalho permitido. A tolerância deixou de ser autoridade (deprecated).

## Deploy e rollback em produção

- Produção está em `f2c6a9d41b87`; a migration `0047` é `a3c8e5f17d24` com `down_revision = f2c6a9d41b87` (cabeça única, caminho linear).
- **Backup do banco é obrigatório antes de aplicar a migration.**
- O downgrade devolve o legado manhã/tarde a partir dos 2 primeiros períodos de cada dia: dia com 1 período volta inativo e do 3º período em diante é descartado (**perda estrutural aceita**). Portanto, **se for preciso reverter DEPOIS de alterações reais na nova configuração, NÃO execute o downgrade às cegas**: restaure o snapshot do banco ou reconcilie antes os períodos (deixe cada dia com 0 ou exatamente 2 períodos). Reverter só o código (sem downgrade) é seguro: as colunas legadas ficam espelhadas para dias com 2 períodos.

## Decisões de produto aprovadas

O **logout automático** (horário próprio, independente) e o **bloqueio** estão na Fase 2 acima; a **pausa automática** abaixo continua sendo só desenho (Fase 3).

- **Pausa automática ≠ logout automático (independentes).** O fim de **qualquer** período do expediente (manhã, tarde, noite…) pausa as tarefas em execução, **sem** deslogar o usuário. O logout automático é uma regra à parte, com **horário fixo da empresa** (ex.: 18:10), configurável por conta própria.
- **Aviso da pausa automática:** toast discreto "Tarefas pausadas automaticamente." **somente quando houve mudança real** (alguma demanda foi de fato pausada); sem mudança, nenhum aviso.
- **Origem da pausa:** `pausa_origem = 'expediente'` (já existe a coluna) para distinguir da pausa manual.
- **Sessão expirada (hotfix 401):** a expiração do token (JWT 30 min) não é o logout automático. O front trata o 401 do tenant de forma central (`lib/sessao-expirada.ts`) e leva ao login do tenant com `?reason=session_expired`; o futuro logout automático pode reutilizar o mesmo caminho.

## Capacidade alocável (11B.2B-A)

`regra_expediente.percentual_capacidade_alocavel` (1..100, default 100) é o percentual do expediente
**nominal** disponível para planejamento de tarefas — não é produtividade. Editá-lo **não** rearma a pausa
automática nem altera horários, dias, fuso ou flags. Ver [planejamento-etapa.md](planejamento-etapa.md).
