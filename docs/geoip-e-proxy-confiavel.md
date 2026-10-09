# GeoIP local e proxy confiável (Fases 7E / 7E.1)

Configurações → Acesso registra, em cada login real, **IP público**, **região aproximada**, **navegador** e **sistema operacional**.
Tudo é decidido pelo servidor, a partir da requisição HTTP — nada vem do frontend.

## 1. IP original e proxy confiável

Cadeia em produção: `internet → Nginx Proxy Manager (NPM) → frontend/BFF (Next.js) → API (FastAPI)`.

- O NPM define `X-Real-IP` (`$remote_addr`) e acrescenta o par ao `X-Forwarded-For`.
- O BFF repassa **um único IP válido** à API (`X-Forwarded-For`) e o `User-Agent` do navegador — só no login (local e Google).
- A API só considera o `X-Forwarded-For` se a conexão **imediata** vier de uma rede listada em **`TRUSTED_PROXY_CIDRS`**. De qualquer
  outra origem o cabeçalho é ignorado (anti-spoofing). A cadeia é lida da direita para a esquerda.

### Sub-rede de produção (confirmada no Docker)

```
docker network inspect taskflow_taskfloww_net     # 172.18.0.0/16  gateway 172.18.0.1
  taskfloww_db 172.18.0.2 · taskfloww_api 172.18.0.3 · taskfloww_front_prod 172.18.0.4
docker network inspect proxy                      # 172.21.0.0/16 (compartilhada com OUTRAS aplicações — NÃO confiar nela)
```

O par imediato da API é o frontend em `172.18.0.4`. Em produção, definir no `.env` do servidor (`/docker/taskflow/.env`):

```
TRUSTED_PROXY_CIDRS=172.18.0.0/16
```

- Sem a variável, vale o padrão (loopback + ranges privados): funciona, porém mais largo. **Em produção, fixe a sub-rede.**
- A sub-rede é atribuída pelo Docker; se a rede `taskflow_taskfloww_net` for recriada, **reconfirme** com `docker network inspect`.
- Valor inválido derruba o boot (confiança mal configurada não passa em silêncio).
- O próprio Uvicorn também sabe ler `X-Forwarded-For`, mas por padrão só de `127.0.0.1` (`FORWARDED_ALLOW_IPS`). **Não** defina
  `FORWARDED_ALLOW_IPS=*`: a confiança é decidida em um só lugar (`TRUSTED_PROXY_CIDRS`, `app/core/cliente_ip.py`).
- Limite conhecido: qualquer contêiner na rede `proxy` consegue falar com o frontend e, em tese, definir `X-Real-IP`. O risco é de
  registro de IP errado na auditoria (não de acesso); só aplicações da mesma VPS alcançam essa rede.

## 2. GeoIP local (MaxMind GeoLite2-City)

- Biblioteca: `maxminddb` (leitura local de `.mmdb`, sem rede, sem dependências). Nenhuma consulta a serviço externo, nenhum IP sai do servidor.
- Variável: `GEOIP_DB_PATH` (no `docker-compose.prod.yml`: `/app/geoip/GeoLite2-City.mmdb`).
- Compose: `./geoip:/app/geoip:ro` — a pasta `/docker/taskflow/geoip/` do host, **somente leitura**. Monta-se a pasta, não o arquivo: sem a
  base, nada quebra (GeoIP desabilitado, tela mostra «Não disponível»).
- A base **não** vai para o Git (`*.mmdb` e `/geoip/` estão no `.gitignore`). A chave de licença MaxMind **nunca** entra no código, no
  repositório, em log ou em `.env` da aplicação: ela é do administrador e só é usada para baixar o arquivo.
- Persistido no evento de login: **apenas o texto** (`Brasília, DF, Brasil`). Nunca latitude/longitude, raio, CEP, ASN nem o registro bruto.
- IP privado, loopback, link-local, multicast, reservado, não especificado ou CGNAT **nunca** é consultado.
- Se a variável faltar, o arquivo não existir ou for inválido: aviso seguro no log (sem caminho nem dado de usuário), GeoIP desabilitado;
  o boot e o login seguem normalmente.
- A base é aberta **uma vez** por processo e fechada no shutdown. **Trocar o `.mmdb` exige reiniciar a API.**

Logs úteis no startup da API: `GeoIP database loaded.` (ok) · `GeoIP desabilitado: ...` (motivo, sem dados sensíveis).

## 3. Instalar / atualizar a base (procedimento manual)

A MaxMind atualiza o GeoLite2 City periodicamente. Sem automação (nenhum cron com segredo foi criado).

1. Com a **sua** conta MaxMind (licença GeoLite2), baixe o `GeoLite2-City` em formato `.mmdb` (arquivo `.tar.gz` → extrair o `.mmdb`).
   A chave fica só com o administrador, no momento do download.
2. Valide o arquivo: tamanho > 0; `python -c "import maxminddb; r=maxminddb.open_database('GeoLite2-City.mmdb'); print(r.metadata().database_type)"`
   deve imprimir `GeoLite2-City`.
3. Substitua **atomicamente** no host: copie para `/docker/taskflow/geoip/GeoLite2-City.mmdb.novo` e `mv` para
   `/docker/taskflow/geoip/GeoLite2-City.mmdb` (mesmo sistema de arquivos → troca atômica). Permissão de leitura para todos (`644`).
4. Recrie **somente a API** em janela controlada: `docker compose -f docker-compose.prod.yml up -d --no-deps --force-recreate taskfloww_api`
   e confirme `healthy` e `GeoIP database loaded.` no log.
5. Mantenha o arquivo anterior até validar um login real.

Automação futura (não implementada, depende de aprovação): tarefa agendada que baixa, valida e troca o arquivo, com a chave guardada fora do repositório.

## 4. Diagnóstico

`app.core.geoip.status_geoip()` devolve `GEOIP_ENABLED` (há configuração) e `GEOIP_DATABASE_AVAILABLE` (base aberta) — só internamente, sem
endpoint público e sem caminho do sistema de arquivos.
