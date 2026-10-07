# Perfil do usuário e Central de Notificações

## Menu do avatar
Cabeçalho (foto/iniciais, nome, cargo · departamento, e-mail, perfil) → **Perfil** (`/minha-conta`) · **Notificações** (`/notificacoes`, com badge) · **Alterar senha** (`/minha-conta#seguranca`) → **Tema** (Claro/Escuro/Sistema/Usar padrão da empresa — ver `personalizacao-visual.md`) → **Sair** → rodapé "Último acesso · IP" (último `auth.login_sucesso` do próprio usuário, o mesmo evento de Configurações → Acesso).

## Perfil (`/minha-conta`)
- **Autoedição restrita**: o usuário altera só **foto**, **telefone** e **cor de identificação**. Nome, e-mail, cargo, departamento e perfil aparecem somente leitura; `PATCH /usuarios/me` usa `extra="forbid"` (nome/sobrenome/e-mail/perfil/status/departamento/empresa/permissões → 422) e a identidade vem do token. A edição administrativa (`PATCH /usuarios/{id}`) não mudou.
- Telefone: o backend guarda só dígitos (`+` opcional), 8–15 dígitos; a máscara é só de exibição.
- **Alterar senha** usa a rota real `POST /auth/alterar-senha` (a tela antiga era simulada).

## Foto de perfil
- PNG ou JPEG, até 5 MB, qualquer proporção (exibida com `object-cover`; recomendado quadrada 512×512). Validada **pelos bytes** (PNG: assinatura/CRC/IEND; JPEG: segmentos, SOF e EOI); extensão e Content-Type declarados só podem concordar; SVG/HTML/PDF/executáveis/GIF/WebP recusados; truncado/corrompido → 422; >5 MB → 413.
- Arquivo em `uploads/usuarios/<empresa>/<usuario>/<nome gerado>` (volume `taskfloww_uploads`); o banco guarda só `foto_perfil_storage_key`/`foto_perfil_mime_type`. Troca = grava → persiste → remove o anterior; falha de banco descarta o novo.
- `POST|DELETE /usuarios/me/avatar`; `GET /usuarios/{id}/avatar?v=` (mesma empresa; outra empresa/inexistente/sem foto → 404; `nosniff`; cache imutável pela versão). `fotoUrl` passa a apontar para a foto própria quando existe (senão continua a foto do Google).
- Componente único `Avatar` (também `UserAvatar`): foto → senão iniciais com contraste automático.

## Central de Notificações (`/notificacoes`)
**Não existe tabela de notificações**: uma notificação é uma *visão tipada* dos eventos de domínio (`eventos`) das demandas em que o usuário é responsável (últimos 30 dias, catálogo fixo de tipos, nunca a própria ação). O único dado novo é o estado "lida" por usuário (`notificacao_leituras`; sem linha = não lida).
- **Minhas notificações**: atividade de outra pessoa nas minhas demandas (atribuição a mim, status, bloqueio/desbloqueio, ajuste, refação, anexo, arquivamento).
- **Sistema**: o mesmo catálogo, gerado sem ator humano (`usuario_id` nulo).
- **Prazos da equipe**: derivado de Demandas **no escopo real** (`core/escopo.py`, a mesma regra de `GET /demandas`) — atrasadas (prazo < agora), vencem hoje, próximos 7 dias; concluídas/canceladas/arquivadas não entram. Paginado no servidor.
- API: `GET /notificacoes` (categoria, apenasNaoLidas, limit ≤ 100, offset), `GET /notificacoes/resumo` (badge + totais de prazos), `POST /notificacoes/{evento}/lida`, `POST /notificacoes/lidas`, `GET /notificacoes/prazos-equipe?grupo=`.
- Badge único (`NotificacoesContext`): menu do avatar, sino e página leem a mesma contagem; marcar como lida reconcilia todos (a API devolve o resumo atualizado). Sem polling: recarrega ao abrir o menu/sino e ao voltar à aba.
- Migration `0040`: `usuarios.foto_perfil_*` + `notificacao_leituras` (aditiva, reversível).
- Testes: `npm run test:perfil` (funções puras) + `backend/tests/test_perfil_usuario.py`, `test_notificacoes.py`.
