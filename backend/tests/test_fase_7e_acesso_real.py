"""Fase 7E — auditoria de acesso real: IP original, navegador, sistema operacional e região aproximada.

- o IP é o do cliente, não o do proxy: `X-Forwarded-For` só vale quando a conexão IMEDIATA vem de um proxy confiável (anti-spoofing);
- navegador e SO saem do `User-Agent` DA REQUISIÇÃO (parser local); o User-Agent completo não é persistido;
- região por GeoIP LOCAL e opcional: IP privado nunca é consultado e nenhuma falha afeta o login;
- a trilha de acesso é da EMPRESA da sessão (admin/gestor), nunca de outra.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import geoip
from app.core.cliente_ip import normalizar_ip, parse_redes_confiaveis, resolver_ip_cliente
from app.core.geoip import formatar_regiao, ip_consultavel, regiao_do_ip
from app.core.user_agent import parse_user_agent
from tests.fixtures.usuarios import SENHA_CONHECIDA, _criar_usuario_com_credencial
from tests.test_configuracao_numeracao_tarefa import _cliente_para_outra_empresa

PROXY_DOCKER = ("172.18.0.4", 50000)
REDES = parse_redes_confiaveis(["127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"])

UA_CHROME_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"


# ======================================================================================
# IP ORIGINAL (função pura)
# ======================================================================================


def test_conexao_direta_usa_o_peer() -> None:
    assert resolver_ip_cliente("187.1.2.3", None, REDES) == "187.1.2.3"
    assert resolver_ip_cliente("2804:14d:1::5", None, REDES) == "2804:14d:1::5"


def test_cliente_nao_confiavel_nao_forja_o_ip_com_x_forwarded_for() -> None:
    # conexão direta de um IP PÚBLICO (não é proxy da infraestrutura) dizendo que é outro: o cabeçalho é ignorado
    assert resolver_ip_cliente("187.9.9.9", "1.2.3.4", REDES) == "187.9.9.9"
    assert resolver_ip_cliente("187.9.9.9", "1.2.3.4, 10.0.0.1", REDES) == "187.9.9.9"


def test_proxy_confiavel_encaminha_o_ip_original() -> None:
    assert resolver_ip_cliente("172.18.0.4", "187.1.2.3", REDES) == "187.1.2.3"
    assert resolver_ip_cliente("172.18.0.4", "2804:14d:1::5", REDES) == "2804:14d:1::5"


def test_cadeia_percorrida_da_direita_e_o_cabecalho_do_cliente_nao_vence() -> None:
    # o cliente mandou "6.6.6.6" à esquerda; o proxy externo acrescentou o IP real; um segundo salto interno confiável
    assert resolver_ip_cliente("172.18.0.4", "6.6.6.6, 187.1.2.3, 172.21.0.3", REDES) == "187.1.2.3"
    # nunca o primeiro item da lista (controlado pelo cliente)
    assert resolver_ip_cliente("172.18.0.4", "6.6.6.6, 187.1.2.3", REDES) == "187.1.2.3"
    # todos os saltos confiáveis: resta o mais à esquerda confiável (não inventa um público)
    assert resolver_ip_cliente("172.18.0.4", "10.0.0.7, 172.21.0.3", REDES) == "10.0.0.7"


def test_entrada_invalida_na_cadeia_nao_e_aceita_como_ip() -> None:
    assert resolver_ip_cliente("172.18.0.4", "abc", REDES) == "172.18.0.4"
    assert resolver_ip_cliente("172.18.0.4", "<script>, 187.1.2.3", REDES) == "187.1.2.3"
    assert resolver_ip_cliente("172.18.0.4", "187.1.2.3, lixo", REDES) == "172.18.0.4"  # lixo interrompe: fica o salto confiável
    assert resolver_ip_cliente("172.18.0.4", "x" * 5000, REDES) == "172.18.0.4"
    assert resolver_ip_cliente(None, "187.1.2.3", REDES) is None
    assert resolver_ip_cliente("testclient", "187.1.2.3", REDES) is None  # peer que não é IP


def test_normalizacao_porta_colchetes_zona_e_ipv4_mapeado() -> None:
    assert str(normalizar_ip("187.1.2.3:51234")) == "187.1.2.3"
    assert str(normalizar_ip("[2804:14d:1::5]:443")) == "2804:14d:1::5"
    assert str(normalizar_ip("fe80::1%eth0")) == "fe80::1"
    assert str(normalizar_ip("::ffff:187.1.2.3")) == "187.1.2.3"
    assert str(normalizar_ip("2804:014D:0001:0000:0000:0000:0000:0005")) == "2804:14d:1::5"  # compactado/minúsculo
    assert resolver_ip_cliente("172.18.0.4", "187.1.2.3:4444", REDES) == "187.1.2.3"  # nunca armazena a porta
    for ruim in (None, "", "   ", "1.2.3", "999.1.1.1", "1.2.3.4.5", "::g", "[::1", "a" * 100):
        assert normalizar_ip(ruim) is None


def test_redes_confiaveis_mal_configuradas_falham_alto() -> None:
    with pytest.raises(ValueError):
        parse_redes_confiaveis(["nao-e-cidr"])
    assert parse_redes_confiaveis(["", " 10.0.0.0/8 "])[0].prefixlen == 8


def test_sem_proxy_configurado_nada_e_confiavel() -> None:
    assert resolver_ip_cliente("172.18.0.4", "187.1.2.3", ()) == "172.18.0.4"


# ======================================================================================
# USER-AGENT
# ======================================================================================


@pytest.mark.parametrize(
    ("user_agent", "navegador", "sistema"),
    [
        (UA_CHROME_WIN, "Chrome 153", "Windows"),
        (UA_CHROME_WIN.replace("Windows NT 10.0", "Windows NT 11.0"), "Chrome 153", "Windows"),  # nunca adivinha 10/11
        (UA_CHROME_WIN + " Edg/153.0.0.0", "Edge 153", "Windows"),
        ("Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0", "Firefox 145", "Linux"),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15", "Safari 26", "macOS"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1", "Safari 26", "iOS"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/153.0.0.0 Mobile/15E148 Safari/604.1", "Chrome 153", "iOS"),
        ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36", "Chrome 153", "Android"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 OPR/120.0.0.0", "Opera 120", "Windows"),
        ("Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36", "Chrome 153", "ChromeOS"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari/605.1.15", "Safari", "Windows"),  # sem versão: melhor "Safari"
    ],
)
def test_user_agent_navegador_e_sistema(user_agent, navegador, sistema) -> None:
    info = parse_user_agent(user_agent)
    assert (info.navegador, info.sistema) == (navegador, sistema)
    assert info.sistema_versao is None  # versão do SO não é confiável no UA moderno


@pytest.mark.parametrize("user_agent", [None, "", "   ", "node", "undici", "curl/8.4.0", "python-httpx/0.27", "Googlebot/2.1", "\x00\x01\x02", "Mozilla", pytest.param("a" * 100_000, id="gigante")])
def test_user_agent_ausente_robo_ou_malformado_nao_inventa_nem_levanta(user_agent) -> None:
    info = parse_user_agent(user_agent)
    assert info.navegador is None


def test_user_agent_so_o_sistema_quando_nao_ha_navegador() -> None:
    info = parse_user_agent("curl/8.4.0 (x86_64-pc-linux-gnu)")
    assert info.navegador is None  # robô nunca vira "Chrome"/"Linux" por acidente de navegador
    assert parse_user_agent("Mozilla/5.0 (X11; Linux x86_64)").sistema == "Linux"


# ======================================================================================
# GEOIP (local, opcional, nunca bloqueia)
# ======================================================================================


class _Leitor:
    def __init__(self, registro=None, erro=None) -> None:
        self.registro, self.erro, self.chamadas = registro, erro, []

    def get(self, ip):
        self.chamadas.append(ip)
        if self.erro:
            raise self.erro
        return self.registro


BRASILIA = {
    "city": {"names": {"pt-BR": "Brasília", "en": "Brasilia"}},
    "subdivisions": [{"iso_code": "DF", "names": {"en": "Federal District"}}],
    "country": {"iso_code": "BR", "names": {"pt-BR": "Brasil", "en": "Brazil"}},
}


def test_formato_da_regiao() -> None:
    assert formatar_regiao(BRASILIA) == "Brasília, DF, Brasil"
    assert formatar_regiao({"subdivisions": BRASILIA["subdivisions"], "country": BRASILIA["country"]}) == "DF, Brasil"
    assert formatar_regiao({"country": BRASILIA["country"]}) == "Brasil"
    assert formatar_regiao({"country": {"names": {"en": "Brazil"}}}) == "Brazil"  # cai no inglês
    for vazio in (None, {}, {"city": {}}, "texto", []):
        assert formatar_regiao(vazio) is None
    assert "latitude" not in str(formatar_regiao({**BRASILIA, "location": {"latitude": -15.7, "longitude": -47.9}}))


def test_regiao_encontrada_e_nao_encontrada() -> None:
    assert regiao_do_ip("187.1.2.3", _Leitor(BRASILIA)) == "Brasília, DF, Brasil"
    assert regiao_do_ip("187.1.2.3", _Leitor(None)) is None


@pytest.mark.parametrize("ip", ["10.1.2.3", "172.18.0.4", "192.168.0.9", "127.0.0.1", "::1", "169.254.1.1", "fe80::1", "100.64.0.1", "0.0.0.0", "224.0.0.1", "lixo", "", None])
def test_ip_privado_local_reservado_ou_invalido_nunca_e_consultado(ip) -> None:
    leitor = _Leitor(BRASILIA)
    assert ip_consultavel(ip) is False
    assert regiao_do_ip(ip, leitor) is None
    assert leitor.chamadas == []


def test_falha_do_geoip_vira_none_nunca_excecao() -> None:
    assert regiao_do_ip("187.1.2.3", _Leitor(erro=RuntimeError("base corrompida"))) is None


def test_sem_base_configurada_a_regiao_e_indisponivel(monkeypatch) -> None:
    geoip._leitor_padrao.cache_clear()
    assert regiao_do_ip("187.1.2.3") is None  # GEOIP_DB_PATH ausente: sem consulta externa, sem erro
    geoip._leitor_padrao.cache_clear()


# ======================================================================================
# LOGIN REAL (HTTP) — o que fica gravado
# ======================================================================================


def _login(app, empresa, usuario, *, peer, headers=None) -> None:
    cliente = TestClient(app, client=peer)
    resposta = cliente.post(
        "/auth/login",
        json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": SENHA_CONHECIDA},
        headers=headers or {},
    )
    assert resposta.status_code == 200, resposta.text


def _acessos(client_admin: TestClient, usuario_id: str | None = None) -> list[dict]:
    resposta = client_admin.get("/eventos", params={"tipo": "auth.login_sucesso", "limit": 100})
    assert resposta.status_code == 200, resposta.text
    return [e for e in resposta.json() if usuario_id is None or e["usuarioId"] == usuario_id]


def test_login_via_proxy_confiavel_grava_ip_publico_navegador_e_so(app, db_session, empresa, client_admin) -> None:
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="acesso")
    db_session.commit()
    _login(app, empresa, usuario, peer=PROXY_DOCKER, headers={"X-Forwarded-For": "187.1.2.3", "User-Agent": UA_CHROME_WIN})
    (evento,) = _acessos(client_admin, usuario.id)
    payload = evento["payload"]
    assert payload["ip_address"] == "187.1.2.3"  # o do usuário, não o 172.18.0.4 do proxy
    assert payload["navegador"] == "Chrome 153"
    assert payload["sistema_operacional"] == "Windows"
    assert "user_agent" not in payload  # minimização: o User-Agent completo não é persistido
    assert payload["regiao"] is None  # sem base GeoIP configurada: indisponível, nunca erro


def test_login_direto_nao_aceita_x_forwarded_for_forjado(app, db_session, empresa, client_admin) -> None:
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="spoof")
    db_session.commit()
    _login(app, empresa, usuario, peer=("187.9.9.9", 40000), headers={"X-Forwarded-For": "1.2.3.4", "User-Agent": UA_CHROME_WIN})
    (evento,) = _acessos(client_admin, usuario.id)
    assert evento["payload"]["ip_address"] == "187.9.9.9"


def test_user_agent_vem_do_cabecalho_nunca_do_corpo(app, db_session, empresa, client_admin) -> None:
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="ua")
    db_session.commit()
    cliente = TestClient(app, client=PROXY_DOCKER)
    resposta = cliente.post(
        "/auth/login",
        json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": SENHA_CONHECIDA,
              "userAgent": "Mozilla Firefox/1", "navegador": "Hack", "ipAddress": "6.6.6.6"},
        headers={"User-Agent": "curl/8.4.0", "X-Forwarded-For": "187.1.2.3"},
    )
    assert resposta.status_code == 200
    payload = _acessos(client_admin, usuario.id)[0]["payload"]
    assert (payload["navegador"], payload["ip_address"]) == (None, "187.1.2.3")  # o corpo foi ignorado


def test_login_sem_user_agent_e_ipv6(app, db_session, empresa, client_admin) -> None:
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="v6")
    db_session.commit()
    _login(app, empresa, usuario, peer=PROXY_DOCKER, headers={"X-Forwarded-For": "2804:14d:1::5"})
    payload = _acessos(client_admin, usuario.id)[0]["payload"]
    assert payload["ip_address"] == "2804:14d:1::5"
    assert payload["navegador"] is None and payload["sistema_operacional"] is None  # a tela mostra "Desconhecido"


def test_regiao_encontrada_aparece_e_ip_privado_nao_consulta(app, db_session, empresa, client_admin, monkeypatch) -> None:
    leitor = _Leitor(BRASILIA)
    monkeypatch.setattr(geoip, "_leitor_padrao", lambda: leitor)
    publico = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="geo1")
    interno = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="geo2")
    db_session.commit()
    _login(app, empresa, publico, peer=PROXY_DOCKER, headers={"X-Forwarded-For": "187.1.2.3"})
    _login(app, empresa, interno, peer=PROXY_DOCKER)  # sem XFF: o IP é o do próprio proxy (privado)
    assert _acessos(client_admin, publico.id)[0]["payload"]["regiao"] == "Brasília, DF, Brasil"
    assert _acessos(client_admin, interno.id)[0]["payload"]["regiao"] is None
    assert leitor.chamadas == ["187.1.2.3"]  # o IP privado nunca chegou ao GeoIP


def test_falha_do_geoip_nao_bloqueia_o_login(app, db_session, empresa, client_admin, monkeypatch) -> None:
    monkeypatch.setattr(geoip, "_leitor_padrao", lambda: _Leitor(erro=RuntimeError("base corrompida")))
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="geof")
    db_session.commit()
    _login(app, empresa, usuario, peer=PROXY_DOCKER, headers={"X-Forwarded-For": "187.1.2.3"})
    payload = _acessos(client_admin, usuario.id)[0]["payload"]
    assert (payload["ip_address"], payload["regiao"]) == ("187.1.2.3", None)


def test_login_com_falha_tambem_grava_o_ip_real(app, db_session, empresa, client_admin) -> None:
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="falha")
    db_session.commit()
    cliente = TestClient(app, client=PROXY_DOCKER)
    resposta = cliente.post(
        "/auth/login",
        json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": "errada-123"},
        headers={"X-Forwarded-For": "187.1.2.3", "User-Agent": UA_CHROME_WIN},
    )
    assert resposta.status_code == 401
    eventos = client_admin.get("/eventos", params={"tipo": "auth.login_falha", "limit": 50}).json()
    ok = [e for e in eventos if e["usuarioId"] == usuario.id]
    assert ok and ok[0]["payload"]["ip_address"] == "187.1.2.3" and ok[0]["payload"]["navegador"] == "Chrome 153"


# ======================================================================================
# TENANT E AUTORIZAÇÃO DA TELA DE ACESSO
# ======================================================================================


def test_acesso_e_da_empresa_da_sessao_nao_vaza_entre_tenants(app, db_session, empresa, outra_empresa, client_admin) -> None:
    usuario_a = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="ta")
    usuario_b = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="tb")
    client_b = _cliente_para_outra_empresa(app, db_session, outra_empresa)
    db_session.commit()
    _login(app, empresa, usuario_a, peer=PROXY_DOCKER, headers={"X-Forwarded-For": "187.1.1.1"})
    _login(app, outra_empresa, usuario_b, peer=PROXY_DOCKER, headers={"X-Forwarded-For": "187.2.2.2"})
    ips_a = {e["payload"]["ip_address"] for e in _acessos(client_admin)}
    ips_b = {e["payload"]["ip_address"] for e in _acessos(client_b)}
    assert "187.1.1.1" in ips_a and "187.2.2.2" not in ips_a
    assert "187.2.2.2" in ips_b and "187.1.1.1" not in ips_b
    # empresaId de outra empresa não amplia o escopo
    assert client_admin.get("/eventos", params={"empresaId": outra_empresa.id}).status_code == 403


def test_tela_de_acesso_exige_autenticacao_e_perfil_administrativo(client, client_operador, client_gestor) -> None:
    assert client.get("/eventos", params={"tipo": "auth.login_sucesso"}).status_code == 401
    assert client_operador.get("/eventos", params={"tipo": "auth.login_sucesso"}).status_code == 403
    assert client_gestor.get("/eventos", params={"tipo": "auth.login_sucesso"}).status_code == 200


def test_trusted_proxy_cidrs_invalido_derruba_o_boot() -> None:
    from dataclasses import replace

    from app.core.config import Settings

    with pytest.raises(ValueError, match="TRUSTED_PROXY_CIDRS"):
        replace(Settings(), trusted_proxy_cidrs="isto-nao-e-cidr")
