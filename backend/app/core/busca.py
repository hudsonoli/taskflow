"""Interpretação de termo de busca — regra única, pura e testável.

## Por que este módulo existe

Um incidente real: a busca de Cliente extraía os dígitos de **qualquer** termo e os usava
como filtro parcial de documento. O termo `"QA FASE2B"` virou `documento_normalizado ILIKE
'%2%'`, que casa com praticamente todo CNPJ — a busca devolveu 91 clientes em vez dos 3
esperados, e uma operação em lote sobre esse resultado atingiu registros indevidos.

O erro não foi o operador em lote: foi a busca prometer precisão e entregar abrangência.
Uma consulta que devolve resultado demais é perigosa justamente porque parece ter
funcionado.

## A regra

Busca **textual** e busca por **documento** são coisas semanticamente diferentes e passaram
a ser decididas separadamente:

- **texto** — sempre ativo. Cobre nome, razão social e os dois códigos (`C26000001`,
  `#2001`), case-insensitive;
- **documento** — só ativa quando o termo **parece um documento**: composto apenas de
  dígitos e pontuação de documento, com ao menos `MIN_DIGITOS_DOCUMENTO` dígitos.

Qualquer caractere fora de `0-9 . / - espaço` significa intenção textual. Letras são o caso
óbvio (`"QA FASE2B"`, `"Cliente 2026"`, `"C26000025"`) — ninguém digita letras querendo
buscar CPF/CNPJ. Mas `#` também conta: `"#2001"` é `codigoInterno`, e sem essa regra os
quatro dígitos o transformariam numa varredura de documentos contendo "2001".

O mínimo de dígitos protege o outro lado: `"1"` ou `"12"` casariam com quase tudo. Quatro é
o menor pedaço de documento que ainda discrimina (o sufixo `0245` de uma filial, por
exemplo) — foi o caso de uso real que motivou permitir busca parcial.

O mínimo vale **só para documento**. A busca textual não tem comprimento mínimo, então um
termo de um caractere alcança quase toda a base — todo `codigoReferencia` contém os dígitos
do ano (`C26…`, `F26…`), e o código é pesquisável de propósito. Isso é casamento textual
legítimo, não o incidente descrito acima, e está mantido conscientemente; se um mínimo
textual for adotado, ele entra aqui e vale para todos os domínios de uma vez. Ver
docs/pendencias-arquiteturais.md, item 3.

Exemplos:

    "BRETAS"               -> texto
    "C26000025"            -> texto (casa codigo_referencia)
    "#2001"                -> texto (casa codigo_interno; "#" não é pontuação de documento)
    "Cliente 2026"         -> texto (tem letras)
    "QA FASE2B"            -> texto (tem letras — o incidente)
    "39.346.861/0245-08"   -> texto + documento "39346861024508"
    "39346861024508"       -> texto + documento
    "0245"                 -> texto + documento (parcial válido)
    "12"                   -> texto (poucos dígitos)
"""

from __future__ import annotations

from dataclasses import dataclass

# Menor trecho de documento que ainda discrimina. Abaixo disso a busca parcial casaria com
# quase toda a base e deixaria de ser busca.
MIN_DIGITOS_DOCUMENTO = 4

# Pontuação que aparece de fato em CPF/CNPJ digitados. Qualquer outro caractere (letra, "#",
# "*", etc.) indica que a pessoa está buscando texto, não documento.
PONTUACAO_DOCUMENTO = frozenset(".-/ ")


@dataclass(frozen=True)
class TermoBusca:
    """Resultado da interpretação. `documento` e `numero` são None quando o respectivo ramo
    não deve ser ativado — nunca vazio/zero, para o chamador não precisar testar dois casos.

    Cada domínio usa o que lhe cabe: Cliente e Fornecedor olham `documento`; Demanda olha
    `numero`. `texto` vale sempre.
    """

    texto: str
    documento: str | None
    numero: int | None = None

    @property
    def vazio(self) -> bool:
        return not self.texto


def _interpretar_numero(texto: str) -> int | None:
    """Número operacional da Demanda (`2063`, `#2063`).

    **Igualdade exata, não busca parcial** — é a diferença que dispensa comprimento mínimo:
    `numero_operacional = 2063` casa um registro, nunca uma faixa. O mínimo de
    MIN_DIGITOS_DOCUMENTO existe porque `documento` usa ILIKE parcial, que alarga; aqui não
    há o que alargar.

    Aceita `#` na frente porque é como a operação escreve. `#` continua fora de
    PONTUACAO_DOCUMENTO, então `#2001` segue com `documento = None` — a regressão da Fase 2B
    permanece válida sem alteração.
    """
    candidato = texto.removeprefix("#")
    if not candidato.isdigit():
        return None
    valor = int(candidato)
    # Guarda contra termo absurdamente longo virando bigint fora de faixa no Postgres.
    return valor if valor <= 2_147_483_647 else None


def interpretar_termo_busca(termo: str | None) -> TermoBusca:
    """Decide o que fazer com o que a pessoa digitou. Função pura — sem banco, sem I/O."""
    texto = (termo or "").strip()
    if not texto:
        return TermoBusca(texto="", documento=None, numero=None)

    numero = _interpretar_numero(texto)

    # Qualquer caractere que não seja dígito nem pontuação de documento significa intenção
    # textual. É o que impede que "QA FASE2B" (letras) e "#2001" (código) sejam lidos como
    # documento.
    if any(c not in PONTUACAO_DOCUMENTO and not c.isdigit() for c in texto):
        return TermoBusca(texto=texto, documento=None, numero=numero)

    digitos = "".join(caractere for caractere in texto if caractere.isdigit())
    if len(digitos) < MIN_DIGITOS_DOCUMENTO:
        return TermoBusca(texto=texto, documento=None, numero=numero)

    return TermoBusca(texto=texto, documento=digitos, numero=numero)
