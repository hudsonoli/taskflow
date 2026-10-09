"""Formato do identificador das tarefas (Fase 7D.1) — fonte ÚNICA, pura, sem banco.

O identificador é **emitido uma vez** e gravado em `demandas.identificador`; depois disso é imutável. Mudar a configuração afeta
só as próximas emissões — nada aqui é chamado na LEITURA de uma tarefa existente.

Composição: `PREFIXO` `SEP` `ANO` `SEP` `NÚMERO` (cada parte só entra se existir). O separador nunca é duplicado: se o prefixo já
termina no separador, não se acrescenta outro. Com o padrão histórico (`#`, sem separador, sem ano, 1 dígito) o resultado é `#15`.

    ("#",   "",  False, 1, 15)        -> #15
    ("TF",  "-", False, 5, 15)        -> TF-00015
    ("BOX", "-", True,  5, 15, 2026)  -> BOX-2026-00015
    ("",    "-", True,  5, 15, 2026)  -> 2026-00015
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PREFIXO_MAX = 16
SEPARADOR_MAX = 4
DIGITOS_MIN = 1
DIGITOS_MAX = 10
NUMERO_MAX = 2_147_483_647  # inteiro de `numero_operacional`

# Só caracteres seguros para um identificador que vai em tela, busca, URL e relatórios.
_CARACTERES_SEGUROS = re.compile(r"^[A-Za-z0-9#_./\-]*$")


class FormatoNumeracaoInvalidoError(ValueError):
    """Configuração de formato inválida (mensagem pronta para o usuário)."""


@dataclass(frozen=True)
class FormatoNumeracao:
    prefixo: str = "#"
    separador: str = ""
    incluir_ano: bool = False
    digitos: int = 1


FORMATO_PADRAO = FormatoNumeracao()


def validar_formato(formato: FormatoNumeracao) -> FormatoNumeracao:
    """Valida no servidor (nunca confiar no frontend). Devolve o próprio formato se válido."""
    if len(formato.prefixo) > PREFIXO_MAX:
        raise FormatoNumeracaoInvalidoError(f"O prefixo pode ter no máximo {PREFIXO_MAX} caracteres.")
    if len(formato.separador) > SEPARADOR_MAX:
        raise FormatoNumeracaoInvalidoError(f"O separador pode ter no máximo {SEPARADOR_MAX} caracteres.")
    for rotulo, valor in (("prefixo", formato.prefixo), ("separador", formato.separador)):
        if not _CARACTERES_SEGUROS.match(valor):
            raise FormatoNumeracaoInvalidoError(
                f"O {rotulo} aceita apenas letras, números e os símbolos # - _ . / (sem espaços)."
            )
    if not DIGITOS_MIN <= formato.digitos <= DIGITOS_MAX:
        raise FormatoNumeracaoInvalidoError(f"A quantidade de dígitos deve ficar entre {DIGITOS_MIN} e {DIGITOS_MAX}.")
    if not formato.prefixo and not formato.incluir_ano and formato.digitos == 1 and not formato.separador:
        # `15` puro seria indistinguível de busca por número e de qualquer inteiro: exige ao menos um marcador.
        raise FormatoNumeracaoInvalidoError("Informe um prefixo, inclua o ano ou use mais de 1 dígito.")
    if formato.prefixo and formato.prefixo[-1].isdigit() and not formato.separador:
        # `A1` + `1` e `A` + `11` virariam o mesmo texto (`A11`): a unicidade do identificador depende de a fronteira ser clara.
        raise FormatoNumeracaoInvalidoError(
            "Um prefixo que termina em número precisa de um separador (ex.: «-») para não confundir com o número da tarefa."
        )
    return formato


def formatar_identificador(formato: FormatoNumeracao, numero: int, ano: int) -> str:
    """Identificador da emissão `numero` no `ano` de emissão. Função pura."""
    partes = [formato.prefixo] if formato.prefixo else []
    if formato.incluir_ano:
        partes.append(str(ano))
    partes.append(f"{numero:0{formato.digitos}d}")

    resultado = ""
    for parte in partes:
        if resultado and formato.separador and not resultado.endswith(formato.separador):
            resultado += formato.separador
        resultado += parte
    return resultado


def descrever_formato(formato: FormatoNumeracao) -> str:
    """Modelo legível do formato (ex.: `BOX-<ano>-<número>`), para a tela."""
    partes = [formato.prefixo] if formato.prefixo else []
    if formato.incluir_ano:
        partes.append("<ano>")
    partes.append("<número>")
    resultado = ""
    for parte in partes:
        if resultado and formato.separador and not resultado.endswith(formato.separador):
            resultado += formato.separador
        resultado += parte
    return resultado
