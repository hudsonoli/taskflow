# Auditoria de acesso: IP público, região, navegador e sistema (Fases 7E / 7E.2)

Configurações → Acesso registra, em cada login real, **IP público**, **região aproximada**, **navegador** e **sistema operacional**.
Tudo é decidido pelo servidor, a partir da requisição HTTP — nada vem de campo enviado pelo frontend.

## 1. Cadeia e fonte de cada dado

```
visitante → Cloudflare → Nginx Proxy Manager (NPM) → BFF (Next.js) → API (FastAPI)
```

| Dado | Fonte |
|---|---|
| IP público | `CF-Connecting-IP` (Cloudflare) → fallback `X-Real-IP` / `X-Forwarded-For` do NPM → peer |
| Cidade / região / país | `CF-IPCity`, `CF-Region`, `CF-Region-Code`, `CF-IPCountry` (Cloudflare) |
| Navegador / sistema | `User-Agent` da requisição (parser local) |

Sem banco local, sem arquivo `.mmdb`, sem chave de licença e sem consulta externa durante o login: a Cloudflare já participa do tráfego e
só acrescenta cabeçalhos à requisição.

> Atrás da Cloudflare, o `X-Real-IP`/`X-Forwarded-For` do NPM trazem o IP da **borda da Cloudflare**, não o do visitante — por isso o IP
> público vem de `CF-Connecting-IP`.

## 2. Ação manual na Cloudflare (obrigatória para a região)

O IP funciona só com a Cloudflare na frente (`CF-Connecting-IP` é sempre enviado). Para a **região**, habilite o Managed Transform:

**Cloudflare Dashboard → domínio → Rules → Transform Rules → Managed Transforms → "Add visitor location headers" → Enable.**

Isso acrescenta `cf-ipcity`, `cf-ipcountry`, `cf-region` e `cf-region-code`. Sem isso a região fica "Não disponível" (o login e o IP
continuam normais). Nada na aplicação usa a API ou token da Cloudflare.

Não são lidos nem persistidos: `CF-IPLatitude`, `CF-IPLongitude`, `CF-Postal-Code`, `CF-Timezone`.

## 3. Quem confia em quem

1. **BFF**: lê `CF-Connecting-IP` (ou, sem Cloudflare, `X-Real-IP` / último `X-Forwarded-For`), valida que é UM IP, e lê os `CF-*` de
   localização. Decodifica, limita e valida cada valor e repassa à API **somente** estes cabeçalhos internos (valores em percent-encoding):
   `X-Taskflow-Client-IP`, `X-Taskflow-CF-City`, `X-Taskflow-CF-Region`, `X-Taskflow-CF-Region-Code`, `X-Taskflow-CF-Country` e o
   `User-Agent`. Nunca encaminha um `CF-*` do navegador como está, e o proxy genérico (`/api/backend/*`) não repassa cabeçalho algum do
   cliente. Só o login local e o do Google usam esse repasse.
2. **API**: só lê esses cabeçalhos (e `CF-*` direto) se a conexão **imediata** vier de uma rede de **`TRUSTED_PROXY_CIDRS`**. De qualquer
   outra origem, tudo é ignorado e vale o peer. Prioridade do IP: `X-Taskflow-Client-IP` → `CF-Connecting-IP` → cadeia do
   `X-Forwarded-For` (da direita para a esquerda) → peer. A região só é lida para IP **público**.

### Sub-rede de produção (confirmada no Docker)

```
docker network inspect taskflow_taskfloww_net     # 172.18.0.0/16  gateway 172.18.0.1
  taskfloww_db 172.18.0.2 · taskfloww_api 172.18.0.3 · taskfloww_front_prod 172.18.0.4
docker network inspect proxy                      # 172.21.0.0/16 (compartilhada com OUTRAS aplicações — NÃO confiar nela)
```

O par imediato da API é o frontend em `172.18.0.4`. No `.env` do servidor (`/docker/taskflow/.env`), no deploy:

```
TRUSTED_PROXY_CIDRS=172.18.0.0/16
```

- Sem a variável, vale o padrão (loopback + ranges privados): funciona, porém mais largo. **Em produção, fixe a sub-rede.**
- A sub-rede é atribuída pelo Docker; se a rede `taskflow_taskfloww_net` for recriada, **reconfirme** com `docker network inspect`.
- Valor inválido derruba o boot. Não defina `FORWARDED_ALLOW_IPS=*` no Uvicorn: a confiança é decidida num só lugar.

## 4. Formato da região

`Cidade, UF, País`, com fallback progressivo: Brasil → `Brasília, DF, Brasil` · sem cidade `DF, Brasil` · sem região `Brasil`. Outros países
→ `Seattle, Washington, Estados Unidos`. Nomes amigáveis para os países mais comuns; os demais mostram o código ISO. `XX` (sem informação)
e `T1` (Tor) da Cloudflare não são países. Persiste-se **apenas o texto**.

## 5. Risco conhecido: acesso direto à origem (hardening futuro)

Auditoria em leitura (sem varredura externa): o NPM publica `80/443` em `0.0.0.0` e as regras `DOCKER-USER` bloqueiam apenas `81`, `8000`,
`2900` e `9443`. Ou seja, **a origem pode ser alcançada sem passar pela Cloudflare** — quem fizer isso pode forjar `CF-Connecting-IP` e
`CF-IP*` e registrar um IP/região falsos na própria trilha de login (não ganha acesso: a senha continua exigida). Também qualquer contêiner da
rede `proxy` fala com o BFF. **Hardening recomendado (não aplicado)**: restringir `80/443` do host aos ranges oficiais da Cloudflare
(`cloudflare.com/ips`) em `DOCKER-USER`, ou usar Authenticated Origin Pulls / túnel.

## 6. Privacidade

Persistido no evento de login: `ip_address`, `navegador`, `sistema_operacional`, `regiao` (texto). Não persistido: User-Agent bruto,
latitude, longitude, CEP, fuso, objeto geográfico, ASN. Não há fornecedor novo: a Cloudflare já faz parte do tráfego do site.
