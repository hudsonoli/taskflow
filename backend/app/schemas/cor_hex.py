"""Cor HEX canônica (`#RRGGBB`) usada como identidade visual (P1_WORKFLOW_COLOR). Sem nome CSS, rgb()/hsl(), `#FFF` nem classe de estilo: o banco guarda só o HEX, em maiúsculas."""

import re

_HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def normalizar_cor_hex(valor: object) -> str | None:
    """`None` continua `None` ("sem cor"); texto no formato `#RRGGBB` (qualquer caixa) vira `#RRGGBB` em maiúsculas; qualquer outra coisa levanta `ValueError` (vira 422)."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ValueError("cor deve ser um texto no formato #RRGGBB")
    candidato = valor.strip()
    if not _HEX.fullmatch(candidato):
        raise ValueError("cor deve estar no formato #RRGGBB")
    return candidato.upper()
