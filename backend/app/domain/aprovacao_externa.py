"""Contrato de domínio do Portal Externo de Aprovação (Fase 9B) compartilhado entre serviços SEM dependência circular (arquivos ⇄ aprovação)."""

CODIGO_ARQUIVO_VINCULADO = "ARQUIVO_VINCULADO_APROVACAO_EXTERNA"


class ArquivoVinculadoAprovacaoExternaError(RuntimeError):
    """O arquivo faz parte de uma aprovação externa em aberto ou decidida (evidência) — não pode ser excluído. Vira 409 com `codigo` estável.
    Solicitação revogada sem decisão NÃO protege o arquivo."""

    codigo = CODIGO_ARQUIVO_VINCULADO

    def __init__(self, quantidade: int = 1) -> None:
        super().__init__(
            "Este arquivo faz parte de uma aprovação externa em aberto ou já decidida e não pode ser excluído. "
            "Revogue a aprovação pendente, se for o caso."
            if quantidade == 1
            else f"{quantidade} arquivo(s) fazem parte de uma aprovação externa em aberto ou já decidida e não podem ser excluídos."
        )
        self.quantidade = quantidade
