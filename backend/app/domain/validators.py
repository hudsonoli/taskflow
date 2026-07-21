import re

_CNPJ_PESOS_PRIMEIRO_DIGITO = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_CNPJ_PESOS_SEGUNDO_DIGITO = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def _calcular_digito_verificador(base: str, pesos: list[int]) -> int:
    soma = sum(int(digito) * peso for digito, peso in zip(base, pesos, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def validar_cnpj(documento: str | None) -> bool:
    """Valida CNPJ pelo algoritmo padrão de dígitos verificadores (módulo 11).

    Aceita o documento com ou sem pontuação (dígitos não numéricos são
    ignorados). Rejeita sequências de dígito repetido (ex.: "00000000000000"),
    que passariam no cálculo de dígito verificador mas nunca são CNPJs
    válidos emitidos.
    """
    if not documento:
        return False

    digitos = re.sub(r"\D", "", documento)
    if len(digitos) != 14:
        return False
    if digitos == digitos[0] * 14:
        return False

    primeiro_digito = _calcular_digito_verificador(digitos[:12], _CNPJ_PESOS_PRIMEIRO_DIGITO)
    segundo_digito = _calcular_digito_verificador(
        digitos[:12] + str(primeiro_digito), _CNPJ_PESOS_SEGUNDO_DIGITO
    )

    return digitos[-2:] == f"{primeiro_digito}{segundo_digito}"
