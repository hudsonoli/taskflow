"""Semeia o contador de número operacional — uma vez, antes do go-live.

    python -m app.cli.inicializar_numero_operacional --tipo-entidade demanda --ultimo-numero 2062

Existe por um requisito operacional único: a primeira Demanda criada no TaskFloww continua a
sequência que a equipe já usa no iClips. Informado `2062`, a próxima demanda nasce `#2063`.

## Por que NÃO existe `--forcar`

Uma operação capaz de reemitir números precisa de **fricção, não de flag**. Confirmação
interativa também não bastaria: ela protege contra engano, não contra decisão errada, e não
deixa rastro. Corrigir o contador depois do go-live é intervenção administrativa deliberada,
com procedimento manual documentado — e é assim que deve ser.

## Por que NÃO entra no seed_all

`seed_all` reconstrói um banco de desenvolvimento a partir do repositório. Continuidade com o
iClips é **dado de produção**: semeá-la a cada reconstrução faria toda base nova nascer com um
contador que só faz sentido em um lugar.

O piso tem duas camadas: este comando protege a intenção,
`UNIQUE(empresa_id, numero_operacional)` protege o dado — falhando o INSERT mesmo se alguém
adulterar o contador direto no banco.
"""

from __future__ import annotations

import argparse
import sys
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.core.sequencias_operacionais import TIPOS_COM_NUMERO_OPERACIONAL
from app.db.session import get_session_factory
from app.models.empresa import Empresa
from app.repositories.demanda_repository import DemandaRepository

EXIT_OK = 0
EXIT_ERRO = 1


class InicializacaoAbortada(RuntimeError):
    """Qualquer motivo para não gravar. Sempre aborta — não há caminho alternativo."""


def _resolver_empresa(db: Session, empresa_id: str | None) -> Empresa:
    """Omitir `--empresa-id` só é aceito quando não há ambiguidade.

    Com várias empresas, escolher uma por conta própria semearia o contador na errada — e o
    erro só apareceria na primeira demanda, com o número trocado.
    """
    if empresa_id:
        empresa = db.get(Empresa, empresa_id)
        if empresa is None:
            raise InicializacaoAbortada(f"Empresa {empresa_id!r} não encontrada.")
        return empresa

    empresas = list(db.scalars(select(Empresa).order_by(Empresa.created_at)))
    if not empresas:
        raise InicializacaoAbortada("Nenhuma empresa cadastrada — rode o seed antes.")
    if len(empresas) > 1:
        nomes = ", ".join(f"{e.nome} ({e.id})" for e in empresas)
        raise InicializacaoAbortada(
            f"Há {len(empresas)} empresas; informe --empresa-id explicitamente. Disponíveis: {nomes}"
        )
    return empresas[0]


def inicializar(
    db: Session, *, empresa_id: str | None, tipo_entidade: str, ultimo_numero: int
) -> str:
    """Grava o contador. Devolve a mensagem de sucesso; qualquer recusa levanta.

    Idempotente quando o valor gravado já é exatamente o solicitado — rodar duas vezes o mesmo
    comando não é erro, é repetição inofensiva.
    """
    if tipo_entidade not in TIPOS_COM_NUMERO_OPERACIONAL:
        suportados = ", ".join(sorted(TIPOS_COM_NUMERO_OPERACIONAL))
        raise InicializacaoAbortada(
            f"tipo-entidade {tipo_entidade!r} não usa número operacional. Suportados: {suportados}."
        )

    if ultimo_numero < 0:
        raise InicializacaoAbortada(
            f"--ultimo-numero não pode ser negativo (recebido: {ultimo_numero})."
        )

    empresa = _resolver_empresa(db, empresa_id)

    # Semear com demandas já emitidas reemitiria números que existem. O UNIQUE faria o INSERT
    # falhar depois; abortar aqui evita descobrir isso na cara do usuário.
    repository = DemandaRepository()
    emitidas = repository.contar_por_empresa(db, empresa.id)
    if emitidas:
        maior = repository.maior_numero_operacional(db, empresa.id)
        raise InicializacaoAbortada(
            f"A empresa {empresa.nome!r} já tem {emitidas} demanda(s) emitida(s) "
            f"(maior número operacional: {maior}). O contador não pode ser redefinido depois da "
            "primeira emissão — isso reemitiria números já usados."
        )

    atual = db.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_operacionais "
            "WHERE empresa_id = :e AND tipo_entidade = :t"
        ),
        {"e": empresa.id, "t": tipo_entidade},
    ).scalar_one_or_none()

    if atual is not None:
        if atual == ultimo_numero:
            return (
                f"Contador de {tipo_entidade!r} da empresa {empresa.nome!r} já está em "
                f"{ultimo_numero}. Nada alterado."
            )
        raise InicializacaoAbortada(
            f"Contador de {tipo_entidade!r} já gravado em {atual}; solicitado {ultimo_numero} "
            f"(diferença: {ultimo_numero - atual:+d}). Alterar um contador existente é "
            "intervenção administrativa manual — este comando não faz isso."
        )

    agora = agora_utc()
    db.execute(
        text(
            """
            INSERT INTO sequencias_operacionais
                (id, empresa_id, tipo_entidade, ultimo_numero, created_at, updated_at)
            VALUES (:id, :empresa_id, :tipo_entidade, :ultimo_numero, :agora, :agora)
            """
        ),
        {
            "id": str(uuid4()),
            "empresa_id": empresa.id,
            "tipo_entidade": tipo_entidade,
            "ultimo_numero": ultimo_numero,
            "agora": agora,
        },
    )
    db.commit()
    return (
        f"Contador de {tipo_entidade!r} da empresa {empresa.nome!r} inicializado em "
        f"{ultimo_numero}. A próxima demanda receberá #{ultimo_numero + 1}."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inicializar_numero_operacional",
        description="Semeia o contador de número operacional (uma vez, antes do go-live).",
    )
    parser.add_argument("--empresa-id", default=None, help="Opcional quando há uma única empresa.")
    parser.add_argument(
        "--tipo-entidade",
        required=True,
        choices=sorted(TIPOS_COM_NUMERO_OPERACIONAL),
    )
    parser.add_argument(
        "--ultimo-numero",
        required=True,
        type=int,
        help="Último número JÁ USADO no sistema de origem. A próxima demanda recebe este + 1.",
    )
    # Deliberadamente SEM --forcar. Ver a docstring do módulo.
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with get_session_factory()() as db:
        try:
            print(
                inicializar(
                    db,
                    empresa_id=args.empresa_id,
                    tipo_entidade=args.tipo_entidade,
                    ultimo_numero=args.ultimo_numero,
                )
            )
            return EXIT_OK
        except InicializacaoAbortada as exc:
            db.rollback()
            print(f"ABORTADO: {exc}", file=sys.stderr)
            return EXIT_ERRO


if __name__ == "__main__":
    raise SystemExit(main())
