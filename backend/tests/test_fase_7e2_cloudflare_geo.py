"""Fase 7E.2 — IP público e região aproximada vindos da CLOUDFLARE (substitui o GeoIP local da 7E.1, que nunca foi para produção).

Cadeia: Cloudflare → NPM → BFF → API. O BFF sanitiza e repassa cabeçalhos internos `X-Taskflow-*`; a API só os lê (e os `CF-*` diretos) quando o
peer imediato é um proxy confiável. Sem banco local, sem chave de licença, sem consulta externa. Coleta mínima: só o TEXTO da região.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.cliente_ip import conexao_de_proxy_confiavel, ip_publico, parse_redes_confiaveis, resolver_ip_cliente
from app.core.config import Settings
from app.core.regiao_cloudflare import decodificar_texto, formatar_regiao, regiao_da_requisicao
from tests.fixtures.usuarios import SENHA_CONHECIDA, _criar_usuario_com_credencial

PROXY_DOCKER = ("172.18.0.4", 50000)
REDES = parse_redes_confiaveis(["172.18.0.0/16"])  # sub-rede de produção (taskflow_taskfloww_net)
UA_CHROME_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
RAIZ = Path(__file__).resolve().parents[2]

CF_BRASILIA = {
    "X-Taskflow-Client-IP": "187.1.2.3",
    "X-Taskflow-CF-City": "Bras%C3%ADlia",
    "X-Taskflow-CF-Region": "Federal%20District",
    "X-Taskflow-CF-Region-Code": "DF",
    "X-Taskflow-CF-Country": "BR",
}


def _requisicao(headers: dict[str, str], peer: tuple[str, int] | None = PROXY_DOCKER) -> Request:
    escopo = {"type": "http", "method": "POST", "path": "/auth/login", "query_string": b"", "client": peer,
              "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()]}
    return Request(escopo)


# ======================================================================================
# IP: CF-Connecting-IP e cabeçalho interno, só de proxy confiável
# ======================================================================================


def test_cf_connecting_ip_ipv4_e_ipv6_de_proxy_confiavel() -> None:
    assert resolver_ip_cliente("172.18.0.4", None, REDES, ip_encaminhado=[None, "187.1.2.3"]) == "187.1.2.3"
    assert resolver_ip_cliente("172.18.0.4", None, REDES, ip_encaminhado=["2804:14d:1::5"]) == "2804:14d:1::5"


def test_prioridade_interno_depois_cf_depois_cadeia_depois_peer() -> None:
    assert resolver_ip_cliente("172.18.0.4", "9.9.9.9", REDES, ip_encaminhado=["187.1.1.1", "187.2.2.2"]) == "187.1.1.1"
    assert resolver_ip_cliente("172.18.0.4", "9.9.9.9", REDES, ip_encaminhado=[None, "187.2.2.2"]) == "187.2.2.2"
    assert resolver_ip_cliente("172.18.0.4", "9.9.9.9", REDES, ip_encaminhado=[None, None]) == "9.9.9.9"  # cadeia
    assert resolver_ip_cliente("172.18.0.4", None, REDES, ip_encaminhado=[None, None]) == "172.18.0.4"  # peer


@pytest.mark.parametrize("ruim", ["abc", "<script>", "1.2.3", "999.1.1.1", "187.1.2.3, 6.6.6.6", "187.1.2.3 6.6.6.6", "", "x" * 500])
def test_cf_connecting_ip_invalido_ou_lista_e_descartado_nunca_o_primeiro_item(ruim) -> None:
    assert resolver_ip_cliente("172.18.0.4", "187.9.9.9", REDES, ip_encaminhado=[ruim]) == "187.9.9.9"  # cai na cadeia
    assert resolver_ip_cliente("172.18.0.4", None, REDES, ip_encaminhado=[ruim]) == "172.18.0.4"


def test_cabecalhos_de_conexao_nao_confiavel_sao_ignorados() -> None:
    assert resolver_ip_cliente("187.9.9.9", "1.1.1.1", REDES, ip_encaminhado=["6.6.6.6", "7.7.7.7"]) == "187.9.9.9"
    assert resolver_ip_cliente("172.21.0.9", None, REDES, ip_encaminhado=["6.6.6.6"]) == "172.21.0.9"  # rede `proxy` compartilhada
    assert conexao_de_proxy_confiavel("172.18.0.4", REDES) and not conexao_de_proxy_confiavel("172.21.0.9", REDES)
    assert not conexao_de_proxy_confiavel(None, REDES) and not conexao_de_proxy_confiavel("lixo", REDES)


@pytest.mark.parametrize("ip", ["10.1.2.3", "172.18.0.4", "192.168.0.9", "127.0.0.1", "::1", "169.254.1.1", "fe80::1", "fc00::1",
                                "100.64.0.1", "224.0.0.1", "ff02::1", "0.0.0.0", "::", "240.0.0.1", "192.0.2.1", "lixo", "", None])
def test_ip_nao_publico(ip) -> None:
    assert ip_publico(ip) is False


def test_ip_publico_ipv4_e_ipv6() -> None:
    assert ip_publico("187.1.2.3") and ip_publico("2804:14d:1::5") and ip_publico("::ffff:187.1.2.3")


# ======================================================================================
# REGIÃO: formatação a partir dos campos da Cloudflare
# ======================================================================================


def test_brasil_cidade_uf_pais() -> None:
    assert formatar_regiao("Brasília", "Federal District", "DF", "BR") == "Brasília, DF, Brasil"  # sigla, nunca "Federal District"
    assert formatar_regiao("São Paulo", "São Paulo", "SP", "br") == "São Paulo, SP, Brasil"


def test_fallbacks_progressivos() -> None:
    assert formatar_regiao(None, "Federal District", "DF", "BR") == "DF, Brasil"  # sem cidade
    assert formatar_regiao("Brasília", None, None, "BR") == "Brasília, Brasil"  # sem região
    assert formatar_regiao(None, None, None, "BR") == "Brasil"  # só país
    assert formatar_regiao("", " ", "", "BR") == "Brasil"
    assert formatar_regiao("Goiânia", "Goiás", None, "BR") == "Goiânia, Goiás, Brasil"  # sem código: o nome da região
    assert formatar_regiao(None, None, None, None) is None  # sem header de localização
    assert formatar_regiao("Brasília", "DF", "DF", None) == "Brasília, DF"  # sem país: o que houver


def test_outros_paises_usam_a_regiao_por_nome_sem_repetir() -> None:
    assert formatar_regiao("Seattle", "Washington", "WA", "US") == "Seattle, Washington, Estados Unidos"
    assert formatar_regiao("Lisboa", "Lisboa", "11", "PT") == "Lisboa, Portugal"
    assert formatar_regiao("Buenos Aires", None, "C", "AR") == "Buenos Aires, C, Argentina"  # sem nome: o código
    assert formatar_regiao(None, None, None, "NP") == "NP"  # país sem nome amigável mapeado: o código ISO, sem inventar tradução


@pytest.mark.parametrize("pais", ["XX", "T1", "xx", "BRA", "B", "1", "<>", "", None])
def test_pais_invalido_sem_informacao_ou_tor_nao_vira_pais(pais) -> None:
    assert formatar_regiao(None, None, None, pais) is None


def test_valores_malformados_sao_limpos_ou_descartados() -> None:
    assert decodificar_texto("Bras%C3%ADlia") == "Brasília"  # percent-encoding do BFF
    assert decodificar_texto("Brasília") == "Brasília"
    assert decodificar_texto("BrasÃ­lia") == "Brasília"  # UTF-8 cru lido como latin1 pelo servidor HTTP é reparado
    assert decodificar_texto("São Paulo") == "São Paulo"  # texto já correto não é "reparado"
    assert decodificar_texto("%ZZ") == "%ZZ"  # percent inválido: segue como texto, sem exceção
    assert decodificar_texto("%FF%FE") is None  # UTF-8 inválido → descartado
    assert decodificar_texto("<script>alert(1)</script>") == "script alert(1) /script"
    assert decodificar_texto("A\x00B\x1fC\r\nD") == "A B C D"  # controle e quebras de linha
    assert decodificar_texto("   ") is None and decodificar_texto(None) is None
    assert len(decodificar_texto("x" * 5000)) == 80
    assert formatar_regiao("<b>Cidade</b>", "R", "ZZZZZZZZZZ", "BR") == "b Cidade /b, R, Brasil"  # código de região inválido não entra


def test_so_texto_de_regiao_nenhum_dado_geografico_e_lido() -> None:
    # latitude/longitude/CEP/fuso nem são consultados: a função só recebe cidade, região, código e país
    import inspect

    assert list(inspect.signature(formatar_regiao).parameters) == ["cidade", "regiao", "regiao_codigo", "pais"]


# ======================================================================================
# REGIÃO NA REQUISIÇÃO: só de proxy confiável e só para IP público
# ======================================================================================


def test_regiao_da_requisicao_com_cabecalhos_internos_do_bff() -> None:
    assert regiao_da_requisicao(_requisicao(CF_BRASILIA), "187.1.2.3", REDES) == "Brasília, DF, Brasil"


def test_regiao_da_requisicao_com_cabecalhos_cf_diretos_de_proxy_confiavel() -> None:
    cf = {"CF-IPCity": "Seattle", "CF-Region": "Washington", "CF-Region-Code": "WA", "CF-IPCountry": "US"}
    assert regiao_da_requisicao(_requisicao(cf), "187.1.2.3", REDES) == "Seattle, Washington, Estados Unidos"


def test_regiao_ignorada_de_origem_nao_confiavel_spoof() -> None:
    assert regiao_da_requisicao(_requisicao(CF_BRASILIA, peer=("187.9.9.9", 40000)), "187.9.9.9", REDES) is None
    assert regiao_da_requisicao(_requisicao(CF_BRASILIA, peer=("172.21.0.9", 40000)), "187.1.2.3", REDES) is None  # rede proxy
    assert regiao_da_requisicao(_requisicao(CF_BRASILIA, peer=None), "187.1.2.3", REDES) is None


def test_regiao_nao_se_aplica_a_ip_privado() -> None:
    for ip in ("10.0.0.5", "172.18.0.4", "127.0.0.1", "fe80::1", None):
        assert regiao_da_requisicao(_requisicao(CF_BRASILIA), ip, REDES) is None


def test_sem_cabecalhos_de_localizacao_managed_transform_desligado() -> None:
    assert regiao_da_requisicao(_requisicao({"X-Taskflow-Client-IP": "187.1.2.3"}), "187.1.2.3", REDES) is None
    assert regiao_da_requisicao(_requisicao({}), "187.1.2.3", REDES) is None


def test_cabecalhos_malformados_nunca_levantam() -> None:
    ruim = {"X-Taskflow-CF-City": "%FF%FE\x00", "X-Taskflow-CF-Region": "<>" * 100, "X-Taskflow-CF-Region-Code": "!!!", "X-Taskflow-CF-Country": "ZZZ9"}
    regiao_da_requisicao(_requisicao(ruim), "187.1.2.3", REDES)  # nunca levanta exceção, seja qual for o valor
    assert regiao_da_requisicao(_requisicao({"X-Taskflow-CF-Country": "ZZZ9", "X-Taskflow-CF-City": "%FF"}), "187.1.2.3", REDES) is None


# ======================================================================================
# LOGIN HTTP — o que fica gravado e o que NUNCA fica
# ======================================================================================


def _login(app, empresa, usuario, *, peer, headers) -> int:
    cliente = TestClient(app, client=peer)
    return cliente.post(
        "/auth/login",
        json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": SENHA_CONHECIDA},
        headers=headers,
    ).status_code


def _payload(client_admin, usuario_id: str) -> dict:
    eventos = client_admin.get("/eventos", params={"tipo": "auth.login_sucesso", "limit": 100}).json()
    return next(e["payload"] for e in eventos if e["usuarioId"] == usuario_id)


def _operador(db_session, empresa, prefixo):
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo=prefixo)
    db_session.commit()
    return usuario


def test_login_grava_ip_regiao_navegador_e_so_com_a_cadeia_cloudflare(app, db_session, empresa, client_admin) -> None:
    usuario = _operador(db_session, empresa, "cf-ok")
    cabecalhos = {**CF_BRASILIA, "User-Agent": UA_CHROME_WIN}
    assert _login(app, empresa, usuario, peer=PROXY_DOCKER, headers=cabecalhos) == 200
    payload = _payload(client_admin, usuario.id)
    assert payload["ip_address"] == "187.1.2.3"
    assert payload["regiao"] == "Brasília, DF, Brasil"
    assert (payload["navegador"], payload["sistema_operacional"]) == ("Chrome 153", "Windows")
    assert "user_agent" not in payload  # User-Agent bruto nunca é persistido


def test_login_nao_persiste_coordenadas_cep_nem_fuso_mesmo_se_chegarem(app, db_session, empresa, client_admin) -> None:
    usuario = _operador(db_session, empresa, "cf-min")
    cabecalhos = {**CF_BRASILIA, "CF-IPLatitude": "-15.7801", "CF-IPLongitude": "-47.9292", "CF-Postal-Code": "70040", "CF-Timezone": "America/Sao_Paulo",
                  "X-Taskflow-CF-Latitude": "-15.78", "User-Agent": UA_CHROME_WIN}
    assert _login(app, empresa, usuario, peer=PROXY_DOCKER, headers=cabecalhos) == 200
    payload = _payload(client_admin, usuario.id)
    assert sorted(k for k in payload if k in {"ip_address", "regiao", "navegador", "sistema_operacional", "user_agent"}) == [
        "ip_address", "navegador", "regiao", "sistema_operacional"]
    persistido = str(payload)
    for sensivel in ("-15.78", "-47.92", "70040", "America/Sao_Paulo", "latitude", "longitude", "postal", "timezone"):
        assert sensivel not in persistido


def test_login_com_cf_connecting_ip_direto_de_proxy_confiavel(app, db_session, empresa, client_admin) -> None:
    usuario = _operador(db_session, empresa, "cf-direto")
    cabecalhos = {"CF-Connecting-IP": "2804:14d:1::5", "CF-IPCity": "São Paulo", "CF-Region": "São Paulo", "CF-Region-Code": "SP", "CF-IPCountry": "BR"}
    assert _login(app, empresa, usuario, peer=PROXY_DOCKER, headers={k: v.encode("utf-8") for k, v in cabecalhos.items()}) == 200
    payload = _payload(client_admin, usuario.id)
    assert payload["ip_address"] == "2804:14d:1::5" and payload["regiao"] == "São Paulo, SP, Brasil"


def test_spoof_de_cabecalhos_cloudflare_por_origem_nao_confiavel(app, db_session, empresa, client_admin) -> None:
    usuario = _operador(db_session, empresa, "cf-spoof")
    forjados = {**CF_BRASILIA, "CF-Connecting-IP": "1.2.3.4", "CF-IPCity": "Paris", "CF-IPCountry": "FR", "X-Forwarded-For": "5.6.7.8"}
    assert _login(app, empresa, usuario, peer=("187.9.9.9", 40000), headers=forjados) == 200
    payload = _payload(client_admin, usuario.id)
    assert payload["ip_address"] == "187.9.9.9"  # o peer: nada do que o cliente escreveu vale
    assert payload["regiao"] is None


def test_login_continua_sem_headers_de_localizacao_e_com_headers_malformados(app, db_session, empresa, client_admin) -> None:
    sem = _operador(db_session, empresa, "cf-sem")
    assert _login(app, empresa, sem, peer=PROXY_DOCKER, headers={"X-Taskflow-Client-IP": "187.1.2.3", "User-Agent": UA_CHROME_WIN}) == 200
    assert (_payload(client_admin, sem.id)["ip_address"], _payload(client_admin, sem.id)["regiao"]) == ("187.1.2.3", None)  # IP ok, região indisponível

    ruim = _operador(db_session, empresa, "cf-ruim")
    malformados = {"X-Taskflow-Client-IP": "lixo", "X-Taskflow-CF-City": "%FF%FE", "X-Taskflow-CF-Country": "ZZZ9", "CF-Connecting-IP": "1.2.3.4, 5.6.7.8"}
    assert _login(app, empresa, ruim, peer=PROXY_DOCKER, headers=malformados) == 200  # nunca bloqueia
    payload = _payload(client_admin, ruim.id)
    assert payload["ip_address"] == "172.18.0.4" and payload["regiao"] is None


def test_regiao_nao_e_gravada_para_ip_privado_mesmo_com_headers(app, db_session, empresa, client_admin) -> None:
    usuario = _operador(db_session, empresa, "cf-priv")
    assert _login(app, empresa, usuario, peer=PROXY_DOCKER, headers={**CF_BRASILIA, "X-Taskflow-Client-IP": "10.0.0.5"}) == 200
    payload = _payload(client_admin, usuario.id)
    assert (payload["ip_address"], payload["regiao"]) == ("10.0.0.5", None)


def test_login_com_falha_tambem_grava_ip_e_regiao_reais(app, db_session, empresa, client_admin) -> None:
    usuario = _operador(db_session, empresa, "cf-falha")
    resposta = TestClient(app, client=PROXY_DOCKER).post(
        "/auth/login", json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": "errada-123"},
        headers={**CF_BRASILIA, "User-Agent": UA_CHROME_WIN})
    assert resposta.status_code == 401
    eventos = client_admin.get("/eventos", params={"tipo": "auth.login_falha", "limit": 50}).json()
    meu = next(e for e in eventos if e["usuarioId"] == usuario.id)
    assert (meu["payload"]["ip_address"], meu["payload"]["regiao"]) == ("187.1.2.3", "Brasília, DF, Brasil")


def test_login_local_e_google_usam_o_mesmo_caminho() -> None:
    rotas = (RAIZ / "backend" / "app" / "api" / "routes" / "auth.py").read_text(encoding="utf-8")
    assert rotas.count("regiao=regiao_da_requisicao(request, ip)") == 2  # /auth/login e /auth/google
    assert rotas.count("ip = extract_client_ip(request)") == 2


# ======================================================================================
# TRUSTED_PROXY_CIDRS — configurável e seguro (preservado da 7E)
# ======================================================================================


def test_trusted_proxy_cidrs_configuravel_e_padrao_quando_vazio(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "172.18.0.0/16")
    assert [str(r) for r in Settings().trusted_proxy_networks] == ["172.18.0.0/16"]
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "   ")  # vazio/branco = padrão (nunca "ninguém confia", que regrediria o IP)
    assert len(Settings().trusted_proxy_networks) > 1
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS")
    assert len(Settings().trusted_proxy_networks) > 1


def test_sub_rede_de_producao_confia_so_no_frontend_da_propria_rede() -> None:
    assert resolver_ip_cliente("172.18.0.4", "187.1.2.3", REDES) == "187.1.2.3"
    assert resolver_ip_cliente("172.21.0.9", "1.2.3.4", REDES) == "172.21.0.9"  # outra aplicação da rede `proxy`
    assert resolver_ip_cliente("187.9.9.9", "1.2.3.4", REDES) == "187.9.9.9"


# ======================================================================================
# MAXMIND REMOVIDO — nada de dependência, mount, variável ou arquivo
# ======================================================================================


def test_maxmind_nao_existe_mais_no_projeto() -> None:
    assert not (RAIZ / "backend" / "app" / "core" / "geoip.py").exists()
    for arquivo in ("backend/requirements.txt", "backend/requirements-dev.txt"):
        texto = (RAIZ / arquivo).read_text(encoding="utf-8").lower()
        assert "maxminddb" not in texto and "mmdb" not in texto and "geoip" not in texto, arquivo
    compose = RAIZ / "docker-compose.prod.yml"
    if compose.exists():
        texto = compose.read_text(encoding="utf-8")
        assert "geoip" not in texto.lower() and ".mmdb" not in texto
    ignorado = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "mmdb" not in ignorado and "GeoIP.conf" not in ignorado
    for fonte in (RAIZ / "backend" / "app").rglob("*.py"):
        conteudo = fonte.read_text(encoding="utf-8")
        assert "maxminddb" not in conteudo and "GEOIP_DB_PATH" not in conteudo, fonte
