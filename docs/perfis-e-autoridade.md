# Perfis e autoridade sobre Usuários (Fase 1A)

Modelo de produto: **Administrador da Plataforma** (fora do RBAC tenant — Fase 1B) → **Gestor** (autoridade máxima da
empresa) → **Usuário**. Esta fase não mexe em banco, JWT, API de leitura nem na conta do proprietário.

## Valores técnicos × rótulos

| Rótulo visível | `perfil_base` | Observação |
|---|---|---|
| Gestor | `gestor` | Autoridade máxima da empresa; pode haver mais de um |
| Usuário | `operador` | Só o rótulo mudou (`perfilUsuarioLabels.operador`). Enum, API, JWT e CHECK intactos |
| (legado) | `admin` | Continua válido internamente (CHECK, bootstrap, conta de sistema). **Nunca é emitido** pela API normal |

## Quem administra quem (backend — `app/core/autoridade_usuarios.py`)

- **Admin legado** (como ator): cria/edita **Gestor** e **Usuário**; nunca atribui `admin`.
- **Gestor**: administra **somente Usuário** — criar, editar, suspender, reativar, bloquear/desbloquear, excluir/restaurar e
  permissões individuais. Nunca outro Gestor, o admin legado, a conta de sistema, nem a si mesmo.
- **Usuário** (mesmo com `usuarios.*` por concessão): só age sobre Usuário. Concessão não é hierarquia.
- Ninguém suspende/bloqueia/exclui a si mesmo nem troca o próprio perfil por esta API (autoatendimento é `/usuarios/me`).
- `POST/PATCH /usuarios` com `perfilBase="admin"` → **422** (schema `UsuarioPerfilBaseAtribuivel`). Seeds e o CLI de
  bootstrap criam `Usuario` direto no model e continuam podendo usar `admin`.
- Falta de autoridade → **403**; operação que deixaria a empresa sem Gestor → **409**.

Defaults: o Gestor passou a ter `usuarios.criar`, `usuarios.editar`, `usuarios.suspender` e `permissoes.gerenciar`
(`DEFAULTS_POR_PERFIL`); o piso de `require_permissoes_gerenciar` é `{admin, gestor}`. A regra de ALVO (sobre quem) fica no
service e na rota de permissões — permissão diz *se*, não *sobre quem*.

## Último Gestor

Uma empresa não perde o último **Gestor ativo** (status `ativo`, `acesso_sistema`, não conta de sistema) por inativar,
bloquear, excluir, tirar o acesso ou rebaixar. Vale para qualquer ator (é proteção do estado). Uma empresa que **ainda não
tem nenhum Gestor** (estado legado em produção: só a conta de sistema) não é afetada — o alvo teria que ser Gestor.

## Privacidade da conta de sistema

Eventos cujo **ator** (`eventos.usuario_id`) é uma conta `is_system_account` não aparecem para o tenant:

| Superfície | Tenant normal (inclui Gestor e admin legado) | A própria conta de sistema |
|---|---|---|
| `GET /eventos` (Acessos) e `GET /eventos/{id}` | oculto (`/{id}` → 404) | vê normalmente |
| `GET /demandas/{id}/historico` | passos desse ator ocultos | vê a timeline completa |

Eventos automáticos (`usuario_id` nulo) nunca são escondidos por esta regra. É só **visibilidade**: nenhum evento é apagado ou
alterado. `EventoRepository.list(..., ocultar_atores_de_sistema=True)` aplica o filtro; o default continua `False` (consumo
interno não é filtrado).

**Notificações (hotfix pré-deploy):** `GET /notificacoes` resolvia o autor por JOIN em `usuarios`, então o responsável de uma
demanda recebia o NOME REAL da conta de sistema. Agora a notificação **continua existindo** (nada é escondido nem apagado), mas o
autor de uma conta de sistema é exibido como **"Sistema"** e a atividade vai para a aba **Sistema** (a categoria passa a ser
"sem ator humano": `usuario_id` nulo **ou** ator `is_system_account`). A regra mora num ponto só,
`NotificacaoService._ator_e_conta_de_sistema` (decide por `is_system_account`, nunca por e-mail/nome), e vale para a listagem, a
contagem de não lidas (`/resumo`) e "marcar todas por categoria". O nome real nem sai do banco (CASE no SELECT).

**Ainda fora do escopo (acompanhar):** a listagem de arquivos de demanda devolve `usuarioNome` de quem enviou e pode expor o nome
de uma conta de sistema; comentários expõem `autorUsuarioId`. Mesma regra a aplicar em tarefa própria.

## Frontend

- `lib/autoridadeUsuarios.ts` (puro, testado em `npm run test:rbac`) decide o que MOSTRAR a partir do perfil e das permissões da
  sessão (nunca e-mail): "Nova pessoa", Editar/Excluir por linha, perfis oferecidos no formulário (admin legado: Gestor e
  Usuário; Gestor: só Usuário; nunca Admin) e a área de Permissões (o Gestor só vê Usuários). A API repete tudo.
- O PATCH só envia `perfilBase` quando o perfil mudou.
