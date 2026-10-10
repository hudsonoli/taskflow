# Portal Externo de Aprovação (Fase 9B)

MVP do portal em que o **cliente** aprova ou pede ajustes de artefatos de uma tarefa **sem conta, sem senha e sem sessão**. O usuário interno gera um link
(*capability*); quem tem o link vê **somente** os artefatos daquela aprovação e responde.

> **Status de produção:** implementado e validado em DEV; **não implantado**. O Go-Live público está **bloqueado** pelo hardening da origem Cloudflare
> (`ORIGIN_HARDENING_REQUIRED=SIM`, `PRODUCTION_DEPLOY_BLOCKED_BY_ORIGIN_HARDENING=SIM`). Ver [Requisitos de Go-Live](#requisitos-de-go-live).

## Modelo

| Tabela | Papel |
|---|---|
| `aprovacoes_externas` | uma solicitação por link: etapa de aprovação, `token_hash` (SHA-256, único), instrução, validade, revogação, decisão, identidade **declarada**, destinatário pretendido |
| `aprovacao_externa_arquivos` | **snapshot** de cada artefato (`ordem`, nome, tamanho, MIME, `sha256`); `arquivo_id` é só a referência viva (`ON DELETE SET NULL`) |

- **Sem coluna `status`**: o estado é derivado — `aprovada`/`ajustes_solicitados` (decisão) > `revogada` > `expirada` > `obsoleta` (a etapa deixou de ser a atual, ou a Demanda foi arquivada) > `pendente`.
- No máximo **uma** solicitação aberta (nem decidida, nem revogada) por etapa: índice único parcial. Uma expirada continua "aberta" até ser revogada/substituída (`NOW()` não entra em índice).
- Decisão e revogação são mutuamente exclusivas (CHECK). Decisão é final.
- **Sem IP, user-agent, dispositivo ou geolocalização.** A identidade do aprovador é *declarada* (nome obrigatório, 3–120; e-mail opcional) e **não verificada**.
- `destinatario_nome/email` é só "para quem o link foi destinado" (snapshot do contato do Cliente, sem id de contato).

## Token

- `secrets.token_urlsafe(32)` (256 bits, 43 caracteres). Só existe em claro na **resposta da criação** (`Cache-Control: no-store`). O banco guarda o SHA-256.
- Nunca vai para log, evento, mensagem de erro, path ou query. Nos endpoints públicos viaja **no corpo JSON** (`POST`), e os erros 422 são montados à mão
  para não ecoar o `input` (o FastAPI devolveria o token).
- URL pública: `https://<app>/aprovacao#token=<TOKEN>` — o **fragmento** não é enviado ao servidor web. O fragmento permanece na barra de endereço
  (o link é reutilizável e legível depois da decisão); `Referrer-Policy: no-referrer`, `no-store` e `noindex` em toda a rota.
- O link é exibido **uma única vez**: *"O link é exibido somente agora. Para gerar outro, revogue e crie um novo."*

## Quem gerencia o link (interno)

`pode_gerenciar_aprovacao_externa` — **autoridade própria**, separada de `podeAvancar`/`podeRejeitar` (gerar um link não aprova nada):

| Pode | Não pode |
|---|---|
| responsável individual da etapa; Head de departamento da etapa; gestor/admin do tenant; responsável da Demanda | **Atendimento só por ser Atendimento**; operador sem relação; Administrador da Plataforma (token de plataforma é recusado) |

Só na etapa de aprovação **atual**, com a Demanda não arquivada e a etapa não pausada. Criar um novo link **revoga** o aberto anterior (`substituida`).

## Artefatos

- Tipo `layout` ou `anexo` físico, PNG/JPG/PDF; **1 a 10** arquivos; total ≤ **100 MiB**; da **mesma Demanda**; nunca `link`.
- Na criação: as linhas dos arquivos são travadas (`FOR UPDATE`), o conteúdo é lido de `uploads/`, confere a assinatura e o **SHA-256** é gravado no snapshot.
- Na entrega: confinamento ao diretório de uploads, **SHA-256 atual == snapshot** (senão não é servido), assinatura dos bytes. Imagem → `inline`; **PDF nunca inline** (`attachment`). O cliente pede por **`ordem`**, nunca por id.
- **Exclusão de arquivo** (individual e em lote 8B): bloqueada (`409 ARQUIVO_VINCULADO_APROVACAO_EXTERNA`) quando o arquivo está numa aprovação **aberta** ou **decidida** (evidência). Revogada sem decisão libera; o snapshot sobrevive com `arquivo_id = NULL`. O lote valida **todos** antes de excluir qualquer um.
- O `status_layout` do arquivo **não** é alterado pela decisão.

## Portal público

`POST /publico/aprovacoes/{consultar,decisao,artefato,logo}` (backend) atrás do BFF dedicado `/api/aprovacao/[acao]` (frontend): sem `tf_session`, sem JWT, sem
headers arbitrários, corpo estrito, 4 ações fechadas. A página `/aprovacao` ignora qualquer sessão do tenant (o `AppDataProvider` nem consulta a sessão ali) e o
HTML inicial sai com marca neutra — a marca real vem do token.

- **Consulta** devolve só: branding da empresa dona do link, identificador emitido e nome da tarefa, instrução, estado, validade, destinatário pretendido,
  artefatos (`ordem`, nome, tipo, MIME, tamanho) e, depois de decidido, o resultado. **Nunca** ids internos, e-mails internos, comentários, histórico, financeiro, responsáveis ou outros arquivos.
- **Link inexistente / malformado / revogado / expirado / obsoleto** → o **mesmo** `404` e a mesma mensagem: *"Este link de aprovação não está mais disponível."*
- **Decidido**: continua legível em modo somente leitura ("Aprovado em…" / "Ajustes solicitados em…"); nova decisão → `409 APROVACAO_JA_DECIDIDA`.
- **Decisão**: `aprovar` (sem motivo) ou `solicitar_ajustes` (motivo 3–1000, obrigatório). Texto sem HTML (`<`/`>` recusados), sempre renderizado como texto.
  Em etapa **sem etapa anterior** não há para onde devolver (`podeSolicitarAjustes=false`; `409 SEM_ETAPA_ANTERIOR`).

## Decisão = workflow existente, com ator externo explícito

A decisão reutiliza o núcleo do workflow (semântica 8A para aprovar, 8D para ajustes) **na mesma transação**, com `AtorExterno(nome, aprovacaoExternaId)`:

- `concluida_por_usuario_id = NULL` — **nunca** um `Usuario` fictício; a leitura da etapa traz `concluidaPorExternoNome` (derivado), exibido como *"Aprovada externamente por <nome>"*;
- eventos de workflow com `atorUsuarioId = NULL` e `atorExterno = {nome, aprovacaoExternaId}`; **sem e-mail** no payload;
- notificações: a próxima etapa (ou a devolvida) avisa seus responsáveis pelo mecanismo 8C/8D; os responsáveis da Demanda recebem "Cliente aprovou…" / "Cliente solicitou ajustes" — o autor é o **nome declarado**, nunca "Sistema" (o motivo dos ajustes fica no histórico);
- timeline sem duplicar: `aprovacao_externa_aprovada/_ajustes` existem só para notificação; a linha da timeline é a do próprio evento de workflow. Aparecem `aprovacao_externa_criada` e `_revogada`.

**Ação interna com link aberto** (aprovar/rejeitar na própria etapa) **revoga** o link na mesma transação (`etapa_decidida_internamente`).

### Concorrência

Ordem de locks fixa: **Demanda → solicitação → linhas de arquivo**. Duplo envio, aprovar × ajustes, interno × externo, criar link × avanço interno e excluir arquivo × criar aprovação têm
**um vencedor**; os demais veem o estado final (`409` ou link indisponível). Provado com sessões reais (threads + `Barrier`) em `tests/test_fase_9b_aprovacao_externa.py`.

## Retenção

- **Política inicial: 5 anos** para as evidências da decisão (solicitação, snapshot dos artefatos, identidade declarada, motivo).
- **Não há job de purge nesta fase.** Nada é apagado automaticamente; o `SET NULL` do arquivo só ocorre pela exclusão **permitida** (aprovação revogada sem decisão).
- Pendência: validação jurídica/LGPD do prazo e da base legal antes do Go-Live; o purge (e a anonimização de nome/e-mail declarados) entra numa fase própria.

## Requisitos de Go-Live

1. **Hardening da origem (P1):** restringir 80/443 do VPS aos IPs da Cloudflare. Enquanto a origem for acessível diretamente, o portal público **não** deve ser exposto. *(Não alterado nesta fase.)*
2. **Rate limit / WAF na Cloudflare** para `/aprovacao` e `/api/aprovacao/*` (consulta, decisão e artefato são públicas): limite por IP e por janela, desafio para excesso de 404. *(Não configurado nesta fase; a aplicação não guarda IP nem faz throttling próprio.)*
3. Validade padrão de 7 dias (1–30) e política de retenção de 5 anos aprovada.
4. Teste humano autenticado do fluxo em produção após o deploy.

## Fora do escopo (backlog)

Envio do link por e-mail; usuário/contato externo com login; múltiplas rodadas por link; verificação do e-mail declarado; job de retenção; sincronização do `status_layout` com a decisão.
