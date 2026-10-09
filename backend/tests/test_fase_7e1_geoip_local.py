"""Fase 7E.1 — GeoIP LOCAL (MaxMind GeoLite2-City, .mmdb) e proxy confiável configurável.

Nenhuma base real é usada: um `.mmdb` SINTÉTICO é gerado em disco (mmdb-writer) e lido pelo leitor de verdade (`maxminddb`). Nada depende
da internet. Garantias: região só em texto (Cidade, UF, País), IP privado nunca consultado, qualquer falha vira `None` e o login nunca
é afetado; a confiança em `X-Forwarded-For` continua restrita à sub-rede configurada.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import geoip
from app.core.cliente_ip import parse_redes_confiaveis, resolver_ip_cliente
from app.core.config import Settings
from app.core.geoip import GeoIPProvider, formatar_regiao, ip_consultavel, regiao_do_ip, status_geoip
from tests.fixtures.usuarios import SENHA_CONHECIDA, _criar_usuario_com_credencial

PROXY_DOCKER = ("172.18.0.4", 50000)


def _nomes(pt: str, en: str | None = None) -> dict:
    return {"names": {"pt-BR": pt, "en": en or pt}}


REGISTROS = {
    "8.8.8.0/24": {  # Brasília, DF, Brasil (com dados que NUNCA devem ser persistidos)
        "city": {**_nomes("Brasília", "Brasilia"), "geoname_id": 3469058},
        "subdivisions": [{"iso_code": "DF", **_nomes("Distrito Federal", "Federal District")}],
        "country": {"iso_code": "BR", **_nomes("Brasil", "Brazil")},
        "location": {"latitude": -15.7801, "longitude": -47.9292, "accuracy_radius": 20, "time_zone": "America/Sao_Paulo"},
        "postal": {"code": "70040"},
    },
    "2001:4860::/32": {  # IPv6: São Paulo, SP, Brasil
        "city": _nomes("São Paulo", "Sao Paulo"),
        "subdivisions": [{"iso_code": "SP", **_nomes("São Paulo", "Sao Paulo")}],
        "country": {"iso_code": "BR", **_nomes("Brasil", "Brazil")},
    },
    "9.9.9.0/24": {  # sem cidade: UF + país
        "subdivisions": [{"iso_code": "GO", **_nomes("Goiás", "Goias")}],
        "country": {"iso_code": "BR", **_nomes("Brasil", "Brazil")},
    },
    "4.4.4.0/24": {"country": {"iso_code": "BR", **_nomes("Brasil", "Brazil")}},  # só país
    "1.1.1.0/24": {  # Lisboa == região: sem repetir
        "city": _nomes("Lisboa", "Lisbon"),
        "subdivisions": [{"iso_code": "11", **_nomes("Lisboa", "Lisbon")}],
        "country": {"iso_code": "PT", **_nomes("Portugal")},
    },
    "5.5.5.0/24": {  # outro país: cidade, região por NOME, país
        "city": _nomes("Seattle"),
        "subdivisions": [{"iso_code": "WA", **_nomes("Washington")}],
        "country": {"iso_code": "US", **_nomes("Estados Unidos", "United States")},
    },
    "6.6.6.0/24": {  # só região (sem código ISO) no Brasil → cai no nome
        "subdivisions": [_nomes("Rio de Janeiro")],
        "country": {"iso_code": "BR", **_nomes("Brasil", "Brazil")},
    },
}


@pytest.fixture(scope="module")
def mmdb(tmp_path_factory) -> Path:
    from mmdb_writer import MMDBWriter
    from netaddr import IPSet

    escritor = MMDBWriter(ip_version=6, ipv4_compatible=True, database_type="GeoLite2-City", languages=["pt-BR", "en"],
                          description={"en": "base sintetica de teste", "pt-BR": "base sintetica de teste"})
    for rede, registro in REGISTROS.items():
        escritor.insert_network(IPSet([rede]), registro)
    caminho = tmp_path_factory.mktemp("geoip") / "GeoLite2-City.mmdb"
    escritor.to_db_file(str(caminho))
    return caminho


@pytest.fixture()
def provider(mmdb):
    p = GeoIPProvider(str(mmdb))
    yield p
    p.fechar()


# ======================================================================================
# REGIÃO (leitor real sobre .mmdb sintético)
# ======================================================================================


def test_ipv4_publico_cidade_uf_pais_brasil(provider) -> None:
    assert provider.regiao("8.8.8.8") == "Brasília, DF, Brasil"  # sigla DF, nunca "Federal District"/"Distrito Federal"


def test_ipv6_publico(provider) -> None:
    assert provider.regiao("2001:4860:4860::8888") == "São Paulo, SP, Brasil"


def test_fallback_progressivo(provider) -> None:
    assert provider.regiao("9.9.9.9") == "GO, Brasil"  # sem cidade
    assert provider.regiao("4.4.4.4") == "Brasil"  # só país
    assert provider.regiao("6.6.6.6") == "Rio de Janeiro, Brasil"  # sem ISO: o nome da região
    assert provider.regiao("8.8.4.4") is None  # ip fora da base: nada confiável


def test_outros_paises_usam_a_regiao_adequada_sem_repetir(provider) -> None:
    assert provider.regiao("5.5.5.5") == "Seattle, Washington, Estados Unidos"
    assert provider.regiao("1.1.1.1") == "Lisboa, Portugal"  # região == cidade não repete


def test_so_texto_e_persistido_nada_do_registro_bruto(provider, mmdb) -> None:
    import maxminddb

    bruto = maxminddb.open_database(str(mmdb)).get("8.8.8.8")
    assert "location" in bruto and "postal" in bruto  # a base TEM coordenadas e CEP...
    regiao = provider.regiao("8.8.8.8")
    assert regiao == "Brasília, DF, Brasil"  # ...mas o que sai é só o texto
    for sensivel in ("-15.78", "-47.92", "70040", "20", "3469058", "America/"):
        assert sensivel not in regiao
    assert isinstance(regiao, str)


@pytest.mark.parametrize("ip", ["10.1.2.3", "172.18.0.4", "192.168.0.9", "127.0.0.1", "::1", "169.254.1.1", "fe80::1", "fc00::1",
                                "100.64.0.1", "224.0.0.1", "ff02::1", "0.0.0.0", "::", "240.0.0.1", "192.0.2.1", "lixo", "", None])
def test_ip_nao_geolocalizavel_nunca_consulta_a_base(ip, mmdb) -> None:
    class Contador:
        chamadas = 0

        def get(self, _ip):
            Contador.chamadas += 1
            return REGISTROS["8.8.8.0/24"]

    p = GeoIPProvider(str(mmdb), abrir=lambda _caminho: Contador())
    assert ip_consultavel(ip) is False
    assert p.regiao(ip) is None
    assert Contador.chamadas == 0


# ======================================================================================
# BASE AUSENTE / INVÁLIDA / ERRO DE LEITURA — nunca derruba nada
# ======================================================================================


def test_variavel_ausente_desabilita(tmp_path) -> None:
    for vazio in (None, "", "   "):
        p = GeoIPProvider(vazio)
        assert (p.configurado, p.base_disponivel, p.regiao("8.8.8.8")) == (False, False, None)


def test_arquivo_ausente_desabilita_sem_expor_o_caminho(tmp_path, caplog) -> None:
    caminho = tmp_path / "pasta-secreta" / "nao-existe.mmdb"
    with caplog.at_level(logging.INFO, logger="app.core.geoip"):
        p = GeoIPProvider(str(caminho))
        assert (p.configurado, p.base_disponivel, p.regiao("8.8.8.8")) == (True, False, None)
    assert "desabilitado" in caplog.text
    assert "pasta-secreta" not in caplog.text  # o caminho do filesystem não vai ao log


def test_arquivo_invalido_desabilita_com_aviso_seguro(tmp_path, caplog) -> None:
    ruim = tmp_path / "corrompida.mmdb"
    ruim.write_bytes(b"isto nao e um banco MaxMind" * 50)
    with caplog.at_level(logging.INFO, logger="app.core.geoip"):
        p = GeoIPProvider(str(ruim))
        assert p.base_disponivel is False
        assert p.regiao("8.8.8.8") is None
    assert "arquivo inválido" in caplog.text and "corrompida" not in caplog.text


def test_erro_de_lookup_vira_none(mmdb) -> None:
    class Quebrado:
        def get(self, _ip):
            raise RuntimeError("falha de leitura")

    p = GeoIPProvider(str(mmdb), abrir=lambda _c: Quebrado())
    assert p.regiao("8.8.8.8") is None
    assert regiao_do_ip("8.8.8.8", Quebrado()) is None


def test_base_aberta_uma_vez_e_fechada_no_shutdown(mmdb) -> None:
    class Fake:
        abertas, fechadas = 0, 0

        def get(self, _ip):
            return REGISTROS["4.4.4.0/24"]

        def close(self):
            Fake.fechadas += 1

    def abrir(_c):
        Fake.abertas += 1
        return Fake()

    p = GeoIPProvider(str(mmdb), abrir=abrir)
    for _ in range(5):
        assert p.regiao("4.4.4.4") == "Brasil"
    assert Fake.abertas == 1  # sem reler o arquivo a cada login
    p.fechar()
    assert Fake.fechadas == 1
    assert p.regiao("4.4.4.4") == "Brasil" and Fake.abertas == 2  # novo processo/restart: reabre


def test_status_interno_sem_caminho(monkeypatch, mmdb) -> None:
    monkeypatch.setattr(geoip, "geoip_provider", lambda: GeoIPProvider(str(mmdb)))
    assert status_geoip() == {"GEOIP_ENABLED": True, "GEOIP_DATABASE_AVAILABLE": True}
    monkeypatch.setattr(geoip, "geoip_provider", lambda: GeoIPProvider(None))
    assert status_geoip() == {"GEOIP_ENABLED": False, "GEOIP_DATABASE_AVAILABLE": False}
    assert all(str(mmdb) not in str(v) for v in status_geoip().values())


def test_formatador_isolado() -> None:
    assert formatar_regiao(REGISTROS["8.8.8.0/24"]) == "Brasília, DF, Brasil"
    assert formatar_regiao({"country": {"iso_code": "BR"}}) == "Brasil"  # Brasil sempre em português
    for vazio in (None, {}, {"location": {"latitude": 1.0}}, "x", []):
        assert formatar_regiao(vazio) is None


# ======================================================================================
# LOGIN — o resultado fica gravado; falhas nunca bloqueiam
# ======================================================================================


def _login(app, empresa, usuario, *, ip: str | None) -> int:
    cliente = TestClient(app, client=PROXY_DOCKER)
    cab = {"X-Forwarded-For": ip} if ip else {}
    return cliente.post("/auth/login", json={"empresaCodigo": empresa.codigo_interno, "email": usuario.email, "senha": SENHA_CONHECIDA}, headers=cab).status_code


def _payload(client_admin, usuario_id: str) -> dict:
    eventos = client_admin.get("/eventos", params={"tipo": "auth.login_sucesso", "limit": 100}).json()
    return next(e["payload"] for e in eventos if e["usuarioId"] == usuario_id)


def test_login_grava_a_regiao_do_ip_publico_e_nenhum_dado_bruto(app, db_session, empresa, client_admin, monkeypatch, mmdb) -> None:
    monkeypatch.setattr(geoip, "geoip_provider", lambda: GeoIPProvider(str(mmdb)))
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="geo-ok")
    db_session.commit()
    assert _login(app, empresa, usuario, ip="8.8.8.8") == 200
    payload = _payload(client_admin, usuario.id)
    assert payload["ip_address"] == "8.8.8.8" and payload["regiao"] == "Brasília, DF, Brasil"
    persistido = str(payload)
    for sensivel in ("latitude", "longitude", "accuracy", "postal", "-15.78", "70040", "geoname", "time_zone"):
        assert sensivel not in persistido
    assert "user_agent" not in payload


def test_login_ip_privado_fica_sem_regiao(app, db_session, empresa, client_admin, monkeypatch, mmdb) -> None:
    monkeypatch.setattr(geoip, "geoip_provider", lambda: GeoIPProvider(str(mmdb)))
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="geo-priv")
    db_session.commit()
    assert _login(app, empresa, usuario, ip=None) == 200  # sem XFF o IP é o do proxy (privado)
    assert _payload(client_admin, usuario.id)["regiao"] is None


@pytest.mark.parametrize("modo", ["ausente", "invalida", "leitura_quebrada"])
def test_login_continua_com_qualquer_falha_do_geoip(app, db_session, empresa, client_admin, monkeypatch, tmp_path, modo) -> None:
    if modo == "ausente":
        provider = GeoIPProvider(str(tmp_path / "nao-existe.mmdb"))
    elif modo == "invalida":
        ruim = tmp_path / "ruim.mmdb"
        ruim.write_bytes(b"lixo" * 100)
        provider = GeoIPProvider(str(ruim))
    else:
        class Quebrado:
            def get(self, _ip):
                raise OSError("disco")

        arquivo = tmp_path / "x.mmdb"
        arquivo.write_bytes(b"x")
        provider = GeoIPProvider(str(arquivo), abrir=lambda _c: Quebrado())
    monkeypatch.setattr(geoip, "geoip_provider", lambda: provider)
    usuario = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo=f"geo-{modo}")
    db_session.commit()
    assert _login(app, empresa, usuario, ip="8.8.8.8") == 200  # nunca 500, nunca bloqueio
    payload = _payload(client_admin, usuario.id)
    assert (payload["ip_address"], payload["regiao"]) == ("8.8.8.8", None)


def test_boot_nao_falha_com_base_invalida(monkeypatch, tmp_path) -> None:
    import app.main as main

    ruim = tmp_path / "ruim.mmdb"
    ruim.write_bytes(b"lixo" * 100)
    monkeypatch.setattr(main, "geoip_provider", lambda: GeoIPProvider(str(ruim)))
    with TestClient(main.app) as cliente:  # executa o lifespan (startup + shutdown)
        assert cliente.get("/health").status_code == 200


# ======================================================================================
# TRUSTED_PROXY_CIDRS — configurável, sub-rede de produção, anti-spoofing preservado
# ======================================================================================


def test_trusted_proxy_cidrs_configuravel_e_padrao_quando_vazio(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "172.18.0.0/16")
    assert [str(r) for r in Settings().trusted_proxy_networks] == ["172.18.0.0/16"]
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "   ")  # vazio/branco = padrão (nunca "ninguém confia", que regrediria o IP)
    assert len(Settings().trusted_proxy_networks) > 1
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS")
    assert len(Settings().trusted_proxy_networks) > 1
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "172.18.0.0/16, 10.9.0.0/24")
    assert len(Settings().trusted_proxy_networks) == 2


def test_sub_rede_de_producao_confia_so_no_frontend_da_propria_rede() -> None:
    producao = parse_redes_confiaveis(["172.18.0.0/16"])  # taskflow_taskfloww_net (confirmada via docker network inspect)
    assert resolver_ip_cliente("172.18.0.4", "187.1.2.3", producao) == "187.1.2.3"  # o BFF (frontend) na rede da API
    # outra aplicação da rede `proxy` (172.21.0.0/16) ou qualquer IP público NÃO é confiável: o cabeçalho é ignorado
    assert resolver_ip_cliente("172.21.0.9", "1.2.3.4", producao) == "172.21.0.9"
    assert resolver_ip_cliente("187.9.9.9", "1.2.3.4", producao) == "187.9.9.9"
    # cliente forja a lista: vale o que o salto confiável acrescentou
    assert resolver_ip_cliente("172.18.0.4", "6.6.6.6, 187.1.2.3", producao) == "187.1.2.3"


# ======================================================================================
# ARQUIVOS DO REPOSITÓRIO — dependência, Git e compose
# ======================================================================================

RAIZ = Path(__file__).resolve().parents[2]


def test_dependencia_minima_fixada() -> None:
    texto = (RAIZ / "backend" / "requirements.txt").read_text(encoding="utf-8")
    assert "maxminddb==3.2.0" in texto
    assert "mmdb-writer" not in texto  # o gerador de fixture é só de teste
    assert "mmdb-writer==0.2.7" in (RAIZ / "backend" / "requirements-dev.txt").read_text(encoding="utf-8")
    for proibido in ("geoip2", "requests-geoip", "ipinfo", "ipstack", "ip2location"):
        assert proibido not in texto  # sem SDK pesado nem cliente de serviço externo


def test_base_geoip_e_licenca_fora_do_git() -> None:
    ignorado = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    for padrao in ("*.mmdb", "/geoip/", "GeoIP.conf"):
        assert padrao in ignorado
    assert not list(RAIZ.glob("**/*.mmdb")) or all("node_modules" in str(p) or ".venv" in str(p) for p in RAIZ.glob("**/*.mmdb"))


def test_compose_monta_a_pasta_geoip_somente_leitura() -> None:
    compose = RAIZ / "docker-compose.prod.yml"
    if not compose.exists():
        pytest.skip("compose de produção ausente")
    texto = compose.read_text(encoding="utf-8")
    assert "./geoip:/app/geoip:ro" in texto
    assert "GEOIP_DB_PATH: /app/geoip/GeoLite2-City.mmdb" in texto
    assert "MAXMIND" not in texto.upper().replace("MAXMIND GEOLITE2", "")  # nenhuma chave/licença no compose
    assert "LICENSE_KEY" not in texto.upper()
