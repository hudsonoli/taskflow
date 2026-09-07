"""Criptografia do segredo SMTP (Fase 2G.7B1) — único lugar do projeto que importa Fernet.

`ConfiguracaoEmailService` nunca manipula cipher diretamente: só chama `criptografar`/
`descriptografar` daqui. Nenhuma rota, nenhum schema, nenhum outro service deveria precisar
importar `cryptography` — se precisar, é sinal de que o segredo está vazando de camada.

## Por que a chave não é obrigatória no boot

`Settings.email_config_encryption_key` (app/core/config.py) não tem guarda de produção, ao
contrário de `AUTH_SECRET_KEY` — a ausência da chave não pode derrubar o TaskFloww inteiro por
uma feature que uma Empresa pode nunca configurar. Em vez disso, a validação acontece aqui, na
hora exata em que a chave é necessária: salvar uma senha nova, descriptografar uma existente,
ou testar conexão. Ler a configuração (GET) ou fazer PATCH em campos que não tocam a senha
NUNCA passam por este módulo — ver ConfiguracaoEmailService.

## Nunca logar segredo

Nenhuma função aqui deve, em nenhuma circunstância, incluir `senha`, `ciphertext` ou `chave`
em uma mensagem de exceção, log ou retorno — só o TIPO do problema (chave ausente/inválida,
ciphertext ilegível). `Fernet.decrypt` já não ecoa o ciphertext na sua própria exceção
(`InvalidToken` não carrega o valor), mas os wrappers abaixo são explícitos mesmo assim: nunca
fazer `str(exc)` de uma exceção de criptografia rumo a uma resposta de API ou log.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class ChaveCriptografiaAusenteError(RuntimeError):
    """`EMAIL_CONFIG_ENCRYPTION_KEY` não está definida no ambiente. Erro operacional — quem
    chama deve mapear pra uma resposta HTTP controlada, nunca deixar vazar como 500 cru com
    traceback (a mensagem aqui já é segura para log, não menciona nenhum segredo)."""


class ChaveCriptografiaInvalidaError(RuntimeError):
    """`EMAIL_CONFIG_ENCRYPTION_KEY` está definida mas não é uma chave Fernet válida (não é
    32 bytes urlsafe-base64). Nunca aceitar string arbitrária silenciosamente — ver Fase
    2G.7A, item 6."""


class CiphertextInvalidoError(RuntimeError):
    """O valor armazenado em `smtp_senha_criptografada` não pôde ser descriptografado com a
    chave atual — ciphertext corrompido, ou a chave foi rotacionada/trocada sem
    re-criptografar os dados existentes. Nunca apagar a configuração por causa disto (ver
    Fase 2G.7A, item 23) — quem chama decide o que fazer (ex.: GET continua informando
    `smtpSenhaConfigurada=true` sem tentar decifrar; teste de conexão retorna resultado
    controlado)."""


class ConfiguracaoEmailCryptoService:
    """Criptografia simétrica autenticada (Fernet) do segredo SMTP. Sem estado — a chave é
    lida do Settings a cada chamada (nunca cacheada em atributo de instância), pra sempre
    refletir o ambiente atual sem exigir reinício do processo em testes."""

    def __init__(self, chave: str | None = None) -> None:
        # `chave` explícita é só para teste (injetar uma chave válida sem depender de env
        # var) — em produção/uso real, `None` faz ler de Settings a cada chamada.
        self._chave_injetada = chave

    def _obter_fernet(self) -> Fernet:
        chave = self._chave_injetada if self._chave_injetada is not None else self._ler_chave_do_ambiente()
        if not chave:
            raise ChaveCriptografiaAusenteError(
                "EMAIL_CONFIG_ENCRYPTION_KEY não está configurada — não é possível "
                "criptografar/descriptografar a senha SMTP."
            )
        try:
            return Fernet(chave.encode("utf-8") if isinstance(chave, str) else chave)
        except (ValueError, TypeError) as exc:
            raise ChaveCriptografiaInvalidaError(
                "EMAIL_CONFIG_ENCRYPTION_KEY não é uma chave Fernet válida."
            ) from exc

    @staticmethod
    def _ler_chave_do_ambiente() -> str | None:
        from app.core.config import get_settings

        return get_settings().email_config_encryption_key

    def criptografar(self, senha: str) -> str:
        fernet = self._obter_fernet()
        token = fernet.encrypt(senha.encode("utf-8"))
        return token.decode("utf-8")

    def descriptografar(self, ciphertext: str) -> str:
        fernet = self._obter_fernet()
        try:
            valor = fernet.decrypt(ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            raise CiphertextInvalidoError(
                "Não foi possível descriptografar a senha SMTP armazenada — ciphertext "
                "corrompido ou chave de criptografia divergente da usada para gravar."
            ) from exc
        return valor.decode("utf-8")
