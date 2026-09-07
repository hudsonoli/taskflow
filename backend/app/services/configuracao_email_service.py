"""Configuração de disparo SMTP — singleton por Empresa (Fase 2G.7B1).

## GET nunca escreve

Ao contrário de `RegraExpedienteService.get_ou_criar` (que semeia um padrão na primeira
leitura), `get_ou_default` aqui é estritamente read-only: sem registro, devolve um DTO
default VIRTUAL — sem `add`/`flush`/`commit`. O registro físico só nasce no primeiro `PATCH`
(ver `atualizar`). Ver Fase 2G.7B1, kickoff item 1, para o racional completo.

## Segredo nunca passa por aqui como texto — exceto no exato instante de uso

`atualizar` criptografa antes de gravar; `testar_conexao` descriptografa só o suficiente pra
montar `ParametrosTesteSmtp` e nunca inclui o valor em nenhum retorno. Nenhum método deste
service devolve `smtp_senha`/ciphertext pra fora — só `ConfiguracaoEmailRead.smtpSenhaConfigurada`
(booleano).
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.configuracao_email import ConfiguracaoEmail
from app.repositories.configuracao_email_repository import ConfiguracaoEmailRepository
from app.schemas.configuracao_email import (
    ConfiguracaoEmailRead,
    ConfiguracaoEmailTesteResultado,
    ConfiguracaoEmailUpdate,
)
from app.services.configuracao_email_crypto_service import (
    ChaveCriptografiaAusenteError,
    ChaveCriptografiaInvalidaError,
    CiphertextInvalidoError,
    ConfiguracaoEmailCryptoService,
)
from app.services.configuracao_email_smtp_service import (
    ConfiguracaoEmailSmtpService,
    MOTIVO_ERRO_DESCONHECIDO,
    ParametrosTesteSmtp,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "configuracao_email"

# Defaults do DTO virtual (sem registro) e do registro físico recém-criado — mesmos valores
# nos dois lugares, únicos defaults do domínio (ver Fase 2G.7A, item 8: TLS explícito é a
# recomendação V1, SSL implícito só quando necessário).
DEFAULT_USAR_TLS = True
DEFAULT_USAR_SSL = False
DEFAULT_ATIVO = False


class ConfiguracaoEmailValidationError(ValueError):
    """Erro de validação de negócio que não cabe no schema Pydantic sozinho — hoje só o
    conflito TLS/SSL no ESTADO FINAL após merge (o schema já recusa os dois `True` no mesmo
    payload, mas não sabe o valor persistido do campo que não foi enviado)."""


class ConfiguracaoEmailService:
    def __init__(
        self,
        repository: ConfiguracaoEmailRepository | None = None,
        crypto: ConfiguracaoEmailCryptoService | None = None,
        smtp_service: ConfiguracaoEmailSmtpService | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or ConfiguracaoEmailRepository()
        self.crypto = crypto or ConfiguracaoEmailCryptoService()
        self.smtp_service = smtp_service or ConfiguracaoEmailSmtpService()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Leitura — ZERO escrita
    # ----------------------------------------------------------------------------------

    def get_ou_default(self, db: Session, *, empresa_id: str) -> ConfiguracaoEmailRead:
        """Read-only estrito: nenhum `add`/`flush`/`commit` acontece aqui, nunca — nem quando
        não existe registro. Ver docstring do módulo."""
        registro = self.repository.get_by_empresa(db, empresa_id)
        return self.to_read(registro)

    # ----------------------------------------------------------------------------------
    # Escrita — cria ou atualiza o singleton, uma transação só
    # ----------------------------------------------------------------------------------

    def atualizar(
        self,
        db: Session,
        data: ConfiguracaoEmailUpdate,
        *,
        empresa_id: str,
        actor_usuario_id: str | None,
    ) -> ConfiguracaoEmailRead:
        try:
            registro, eh_criacao = self._obter_ou_montar_singleton(db, empresa_id=empresa_id)
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            now = agora_utc()

            campos_alterados: list[str] = []
            senha_alterada = False
            senha_removida = False

            if "smtp_host" in updates and updates["smtp_host"] != registro.smtp_host:
                registro.smtp_host = updates["smtp_host"]
                campos_alterados.append("smtpHost")
            if "smtp_port" in updates and updates["smtp_port"] != registro.smtp_port:
                registro.smtp_port = updates["smtp_port"]
                campos_alterados.append("smtpPort")
            if "smtp_usuario" in updates and updates["smtp_usuario"] != registro.smtp_usuario:
                registro.smtp_usuario = updates["smtp_usuario"]
                campos_alterados.append("smtpUsuario")
            if "remetente_email" in updates and updates["remetente_email"] != registro.remetente_email:
                registro.remetente_email = updates["remetente_email"]
                campos_alterados.append("remetenteEmail")
            if "remetente_nome" in updates and updates["remetente_nome"] != registro.remetente_nome:
                registro.remetente_nome = updates["remetente_nome"]
                campos_alterados.append("remetenteNome")
            if "usar_tls" in updates and updates["usar_tls"] != registro.usar_tls:
                registro.usar_tls = updates["usar_tls"]
                campos_alterados.append("usarTls")
            if "usar_ssl" in updates and updates["usar_ssl"] != registro.usar_ssl:
                registro.usar_ssl = updates["usar_ssl"]
                campos_alterados.append("usarSsl")
            if "ativo" in updates and updates["ativo"] != registro.ativo:
                registro.ativo = updates["ativo"]
                campos_alterados.append("ativo")

            # `smtp_senha` — três estados (ver docstring de ConfiguracaoEmailUpdate). Omitido
            # não aparece em `updates` (exclude_unset) e não entra em nenhum destes dois "if".
            if "smtp_senha" in updates:
                nova_senha = updates["smtp_senha"]
                if nova_senha is None:
                    if registro.smtp_senha_criptografada is not None:
                        registro.smtp_senha_criptografada = None
                        senha_removida = True
                        campos_alterados.append("smtpSenha")
                else:
                    # Criptografa ANTES de tocar o registro — se a chave estiver ausente/
                    # inválida, a exceção propaga sem deixar o registro em estado parcial
                    # (nenhum `repository.update`/`create` foi chamado ainda neste ponto).
                    registro.smtp_senha_criptografada = self.crypto.criptografar(nova_senha)
                    senha_alterada = True
                    campos_alterados.append("smtpSenha")

            # Validação de ESTADO FINAL (após merge) — cobre o caso em que só um dos dois
            # campos foi enviado e conflita com o valor já persistido do outro. O schema já
            # recusa os dois `True` no MESMO payload; isto é a garantia complementar.
            if registro.usar_tls and registro.usar_ssl:
                raise ConfiguracaoEmailValidationError(
                    "usarTls e usarSsl não podem estar ativos ao mesmo tempo"
                )

            if eh_criacao:
                registro.created_at = now
                registro.updated_at = now
                # Reatribui `registro`: no caminho de corrida (IntegrityError), o objeto
                # devolvido é `existente` (o que a transação vencedora inseriu), NUNCA o
                # `registro` transiente cujo INSERT falhou — chamar `db.refresh()` num objeto
                # que nunca foi persistido com sucesso levantaria erro (não está na identity
                # map da sessão após o rollback). Ver docstring de `_criar_com_retry`.
                registro = self._criar_com_retry(db, registro, empresa_id=empresa_id)
            elif campos_alterados:
                registro.updated_at = now
                self.repository.update(db, registro)

            if eh_criacao or campos_alterados:
                self._publish_event(
                    db,
                    registro,
                    actor_usuario_id,
                    campos_alterados=campos_alterados,
                    senha_alterada=senha_alterada,
                    senha_removida=senha_removida,
                    occurred_at=now,
                )

            db.commit()
            db.refresh(registro)
            return self.to_read(registro)
        except Exception:
            db.rollback()
            raise

    def _obter_ou_montar_singleton(self, db: Session, *, empresa_id: str) -> tuple[ConfiguracaoEmail, bool]:
        """Busca o registro existente; se não houver, MONTA (em memória, sem `add`/`flush`
        ainda) um novo `ConfiguracaoEmail` com os defaults do domínio. O segundo valor da
        tupla (`eh_criacao`) é quem `atualizar` usa pra decidir create-vs-update — nunca um
        sentinela sobrecarregado em `created_at` (que a coluna `NOT NULL` do banco não
        aceitaria de qualquer forma; aqui ele já nasce com um valor real, ver `atualizar`)."""
        existente = self.repository.get_by_empresa(db, empresa_id)
        if existente is not None:
            return existente, False

        now = agora_utc()
        novo = ConfiguracaoEmail(
            id=str(uuid4()),
            empresa_id=empresa_id,
            smtp_host=None,
            smtp_port=None,
            smtp_usuario=None,
            smtp_senha_criptografada=None,
            remetente_email=None,
            remetente_nome=None,
            usar_tls=DEFAULT_USAR_TLS,
            usar_ssl=DEFAULT_USAR_SSL,
            ativo=DEFAULT_ATIVO,
            created_at=now,
            updated_at=now,
        )
        return novo, True

    def _criar_com_retry(self, db: Session, registro: ConfiguracaoEmail, *, empresa_id: str) -> ConfiguracaoEmail:
        """Concorrência do primeiro PATCH (Fase 2G.7B1, item 15): duas requisições podem ver
        "não existe" ao mesmo tempo. `UNIQUE(empresa_id)` é a garantia final — a que perder a
        corrida recebe `IntegrityError` no `flush`, faz rollback (obrigatório: a sessão fica
        suja depois de um flush que falhou) e RELÊ o registro que a vencedora criou, aplicando
        os MESMOS campos já calculados em `registro` sobre ele — nunca insere uma segunda
        linha, nunca perde a intenção da requisição perdedora.

        SEMPRE devolve o objeto que `atualizar` deve usar dali em diante — nunca o `registro`
        original quando o INSERT dele falhou (esse objeto nunca chega a ter uma linha própria
        no banco; ficaria transiente/fora da identity map da sessão depois do rollback, e um
        `db.refresh()` posterior sobre ele levantaria erro)."""
        try:
            self.repository.create(db, registro)
            return registro
        except IntegrityError:
            db.rollback()
            existente = self.repository.get_by_empresa(db, empresa_id)
            if existente is None:
                raise
            existente.smtp_host = registro.smtp_host
            existente.smtp_port = registro.smtp_port
            existente.smtp_usuario = registro.smtp_usuario
            existente.smtp_senha_criptografada = registro.smtp_senha_criptografada
            existente.remetente_email = registro.remetente_email
            existente.remetente_nome = registro.remetente_nome
            existente.usar_tls = registro.usar_tls
            existente.usar_ssl = registro.usar_ssl
            existente.ativo = registro.ativo
            existente.updated_at = registro.updated_at
            self.repository.update(db, existente)
            return existente

    # ----------------------------------------------------------------------------------
    # Teste de conexão — somente leitura da configuração salva
    # ----------------------------------------------------------------------------------

    def testar_conexao(self, db: Session, *, empresa_id: str) -> ConfiguracaoEmailTesteResultado:
        registro = self.repository.get_by_empresa(db, empresa_id)

        senha_texto_claro: str | None = None
        if registro is not None and registro.smtp_senha_criptografada is not None:
            try:
                senha_texto_claro = self.crypto.descriptografar(registro.smtp_senha_criptografada)
            except (ChaveCriptografiaAusenteError, ChaveCriptografiaInvalidaError, CiphertextInvalidoError):
                # Erro controlado (Fase 2G.7A, item 23/kickoff item 26-27) — nunca propaga
                # como 500 cru; o teste simplesmente não consegue avaliar autenticação.
                return ConfiguracaoEmailTesteResultado(
                    sucesso=False,
                    motivo=MOTIVO_ERRO_DESCONHECIDO,
                    mensagem="Não foi possível acessar a senha SMTP armazenada para testar a conexão.",
                )

        parametros = ParametrosTesteSmtp(
            smtp_host=registro.smtp_host if registro else None,
            smtp_port=registro.smtp_port if registro else None,
            smtp_usuario=registro.smtp_usuario if registro else None,
            smtp_senha=senha_texto_claro,
            usar_tls=registro.usar_tls if registro else DEFAULT_USAR_TLS,
            usar_ssl=registro.usar_ssl if registro else DEFAULT_USAR_SSL,
        )
        resultado = self.smtp_service.testar(parametros)
        return ConfiguracaoEmailTesteResultado(
            sucesso=resultado.sucesso, motivo=resultado.motivo, mensagem=resultado.mensagem
        )

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, registro: ConfiguracaoEmail | None) -> ConfiguracaoEmailRead:
        if registro is None:
            return ConfiguracaoEmailRead(
                id=None,
                smtpHost=None,
                smtpPort=None,
                smtpUsuario=None,
                smtpSenhaConfigurada=False,
                remetenteEmail=None,
                remetenteNome=None,
                usarTls=DEFAULT_USAR_TLS,
                usarSsl=DEFAULT_USAR_SSL,
                ativo=DEFAULT_ATIVO,
                createdAt=None,
                updatedAt=None,
            )
        return ConfiguracaoEmailRead(
            id=registro.id,
            smtpHost=registro.smtp_host,
            smtpPort=registro.smtp_port,
            smtpUsuario=registro.smtp_usuario,
            smtpSenhaConfigurada=registro.smtp_senha_criptografada is not None,
            remetenteEmail=registro.remetente_email,
            remetenteNome=registro.remetente_nome,
            usarTls=registro.usar_tls,
            usarSsl=registro.usar_ssl,
            ativo=registro.ativo,
            createdAt=registro.created_at,
            updatedAt=registro.updated_at,
        )

    # ----------------------------------------------------------------------------------
    # Evento
    # ----------------------------------------------------------------------------------

    def _publish_event(
        self,
        db: Session,
        registro: ConfiguracaoEmail,
        actor_usuario_id: str | None,
        *,
        campos_alterados: list[str],
        senha_alterada: bool,
        senha_removida: bool,
        occurred_at: datetime,
    ) -> None:
        # Payload estritamente não sensível — NUNCA smtpUsuario (preferência conservadora do
        # kickoff, item 16), NUNCA senha/ciphertext/chave. `DomainEventPublisher.publish` já
        # recusa qualquer payload com chave sensível catalogada (ver contains_sensitive_key em
        # domain_event_publisher.py) como segunda camada de defesa, não a única.
        self.event_publisher.publish(
            db,
            tipo=DomainEventType.CONFIGURACAO_EMAIL_ALTERADA,
            empresa_id=registro.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=registro.id,
            usuario_id=actor_usuario_id,
            payload={
                "smtpHost": registro.smtp_host,
                "smtpPort": registro.smtp_port,
                "remetenteEmail": registro.remetente_email,
                "usarTls": registro.usar_tls,
                "usarSsl": registro.usar_ssl,
                "ativo": registro.ativo,
                "senhaAlterada": senha_alterada,
                "senhaRemovida": senha_removida,
                "camposAlterados": campos_alterados,
            },
            occurred_at=occurred_at,
        )
