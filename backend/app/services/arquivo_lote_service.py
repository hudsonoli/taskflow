"""Operações em lote sobre Arquivos (Fase 8B): resumo, download em ZIP e exclusão múltipla.

Princípios:
- NADA aqui decide autorização por conta própria: toda seleção nasce de `DemandaArquivoRepository.selecionar_lote`, que aplica tenant + escopo da
  Demanda + filtros no SQL (a mesma restrição da listagem e do download/exclusão individuais). IDs explícitos são sempre reconferidos nessa
  consulta: se QUALQUER um não for autorizado/existente, a operação inteira falha (404) e nada é alterado — nunca um ZIP/exclusão parcial calado;
- caminho físico vem SEMPRE de `demanda_id` + `nome_fisico` do banco (gerado pelo backend), nunca de nome fornecido por usuário, e é conferido contra a raiz de uploads;
- ZIP sem estourar memória: monta num arquivo temporário (`zipfile.write` copia em blocos), entrega com `FileResponse` e remove o temporário
  depois (ou na falha). Nada é escrito em `uploads/`, nada de Redis, nada carregado inteiro em RAM;
- a transação do banco é ENCERRADA antes de ler/enviar arquivos — não fica aberta durante o ZIP;
- exclusão: valida tudo → UMA transação (linhas + um evento por arquivo) → só então apaga os arquivos físicos (melhor esforço, como na exclusão
  individual; sobra de disco é órfã e inacessível, contada e registrada, nunca silenciosa).
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import unicodedata
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.demanda_arquivo_service as arquivo_modulo
from app.core.escopo import EscopoDemanda
from app.core.relogio import agora_utc
from app.domain.aprovacao_externa import ArquivoVinculadoAprovacaoExternaError
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_arquivo import DemandaArquivo
from app.repositories.demanda_arquivo_repository import DemandaArquivoRepository, FiltrosCentral
from app.schemas.arquivo_lote import ArquivosLoteExclusaoRead, ArquivosLoteResumoRead
from app.services.demanda_arquivo_service import DemandaArquivoService

logger = logging.getLogger(__name__)

# Tetos operacionais. Uploads são limitados a 20 MB cada, então 500 MiB cobre dezenas de arquivos grandes ou centenas de pequenos; o limite de
# bytes usa o `tamanho_bytes` gravado no upload (metadado confiável para anexo/layout).
ZIP_MAX_FILES = 500
ZIP_MAX_TOTAL_BYTES = 500 * 1024 * 1024
EXCLUSAO_MAX_FILES = 2000

# Formatos já comprimidos: só armazenar (CPU baixa); o resto, deflate nível 1 (rápido).
_EXTENSOES_JA_COMPRIMIDAS = frozenset({".png", ".jpg", ".jpeg"})
_NOME_ZIP_MAX = 120
_RESERVADOS_WINDOWS = frozenset({"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))})
_CARACTERES_PROIBIDOS = re.compile(r'[<>:"|?*\x00-\x1f\x7f]')


class ArquivoLoteNaoEncontradoError(LookupError):
    """Seleção vazia, ou algum ID explícito inexistente/fora do tenant/escopo (não revela qual). Vira 404."""


class ArquivoLoteLimiteError(ValueError):
    """Seleção grande demais para a operação. Vira 413."""


class ArquivoLoteFisicoAusenteError(RuntimeError):
    """Arquivo(s) sem conteúdo no armazenamento — nunca se entrega um ZIP incompleto. Vira 409."""

    def __init__(self, quantidade: int) -> None:
        super().__init__(f"{quantidade} arquivo(s) não está(ão) disponível(is) no armazenamento")
        self.quantidade = quantidade


@dataclass
class ZipPreparado:
    caminho: Path
    nome: str
    arquivos: int
    links_ignorados: int
    bytes_total: int


def nome_seguro_para_zip(nome_original: str | None, extensao_fisica: str = "") -> str:
    """Nome de entrada do ZIP: sem caminho (`../`, `/`, `\\`), sem controle/caracteres proibidos, sem pontos/espaços nas pontas, sem nome reservado do
    Windows, limitado a `_NOME_ZIP_MAX` preservando a extensão. Nunca vazio."""
    bruto = unicodedata.normalize("NFC", nome_original or "")
    base = bruto.replace("\\", "/").split("/")[-1]
    base = _CARACTERES_PROIBIDOS.sub("", base)
    base = re.sub(r"\s+", " ", base).strip(" .")
    if not base or base in {".", ".."}:
        base = f"arquivo{extensao_fisica}"
    stem, ponto, ext = base.rpartition(".")
    if not ponto:
        stem, ext = base, ""
    elif not stem:  # ".gitignore" etc.
        stem, ext = base, ""
    ext_com_ponto = f".{ext}" if ext else ""
    if stem.lower() in _RESERVADOS_WINDOWS:
        stem = f"_{stem}"
    if len(stem) + len(ext_com_ponto) > _NOME_ZIP_MAX:
        stem = stem[: max(1, _NOME_ZIP_MAX - len(ext_com_ponto))]
    return f"{stem.rstrip(' .') or 'arquivo'}{ext_com_ponto}"


def nomes_unicos_para_zip(nomes: Sequence[str]) -> list[str]:
    """`arte.pdf`, `arte (2).pdf`, `arte (3).pdf` — comparação sem diferenciar maiúsculas (extração em Windows/macOS), extensão preservada."""
    usados: set[str] = set()
    resultado: list[str] = []
    for nome in nomes:
        candidato = nome
        if candidato.lower() in usados:
            stem, ponto, ext = nome.rpartition(".")
            if not ponto:
                stem, ext = nome, ""
            contador = 2
            while True:
                candidato = f"{stem} ({contador}){'.' + ext if ext else ''}"
                if candidato.lower() not in usados:
                    break
                contador += 1
        usados.add(candidato.lower())
        resultado.append(candidato)
    return resultado


def nome_do_zip(agora=None) -> str:
    momento = agora or agora_utc()
    return f"taskfloww-arquivos-{momento.strftime('%Y%m%d-%H%M')}.zip"


class ArquivoLoteService:
    def __init__(
        self,
        repository: DemandaArquivoRepository | None = None,
        arquivo_service: DemandaArquivoService | None = None,
    ) -> None:
        self.repository = repository or DemandaArquivoRepository()
        self.arquivo_service = arquivo_service or DemandaArquivoService(repository=self.repository)

    # ----------------------------------------------------------------------------------
    # Seleção autorizada
    # ----------------------------------------------------------------------------------

    def _linhas_ids(
        self, db: Session, *, escopo: EscopoDemanda, filtros: FiltrosCentral, ids: Sequence[str], travar: bool = False
    ) -> list:
        linhas = self.repository.selecionar_lote(db, escopo=escopo, filtros=filtros, ids=ids, travar=travar)
        if len(linhas) != len(set(ids)):
            # inexistente, de outro tenant ou fora do escopo: indistinguíveis de propósito
            raise ArquivoLoteNaoEncontradoError("Um ou mais arquivos selecionados não foram encontrados")
        return linhas

    def _linhas_todos(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        filtros: FiltrosCentral,
        excluir_ids: Sequence[str],
        limite: int,
        somente_fisicos: bool = False,
        travar: bool = False,
    ) -> list:
        linhas = self.repository.selecionar_lote(
            db, escopo=escopo, filtros=filtros, excluir_ids=excluir_ids, limite=limite + 1, travar=travar, somente_fisicos=somente_fisicos
        )
        if len(linhas) > limite:
            raise ArquivoLoteLimiteError(f"A seleção tem mais de {limite} arquivos — refine os filtros")
        return linhas

    # ----------------------------------------------------------------------------------
    # Resumo
    # ----------------------------------------------------------------------------------

    def resumo(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        filtros: FiltrosCentral,
        ids: Sequence[str] | None,
        excluir_ids: Sequence[str],
    ) -> ArquivosLoteResumoRead:
        if ids is not None:
            linhas = self._linhas_ids(db, escopo=escopo, filtros=filtros, ids=ids)
            total = len(linhas)
            links = sum(1 for linha in linhas if linha.tipo == "link")
            tamanho = sum(linha.tamanho_bytes or 0 for linha in linhas)
        else:
            total, links, tamanho = self.repository.contar_lote(db, escopo=escopo, filtros=filtros, excluir_ids=excluir_ids)
        return ArquivosLoteResumoRead(
            total=int(total),
            links=int(links),
            arquivosFisicos=int(total) - int(links),
            tamanhoTotalBytes=int(tamanho),
            limiteZipArquivos=ZIP_MAX_FILES,
            limiteZipBytes=ZIP_MAX_TOTAL_BYTES,
            limiteExclusao=EXCLUSAO_MAX_FILES,
        )

    # ----------------------------------------------------------------------------------
    # Download em ZIP
    # ----------------------------------------------------------------------------------

    def _caminho_confiavel(self, demanda_id: str, nome_fisico: str | None) -> Path | None:
        """Caminho físico reconstruído do banco e confinado à raiz de uploads (sem symlink que escape); `None` se indisponível."""
        if not nome_fisico:
            return None
        caminho = self.arquivo_service.caminho_fisico(demanda_id, nome_fisico)
        try:
            raiz = Path(arquivo_modulo.UPLOADS_ROOT).resolve()
            real = caminho.resolve()
            if not real.is_relative_to(raiz) or not real.is_file():
                return None
        except OSError:
            return None
        return caminho

    def preparar_zip(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        filtros: FiltrosCentral,
        ids: Sequence[str] | None,
        excluir_ids: Sequence[str],
    ) -> ZipPreparado:
        if ids is not None:
            linhas = self._linhas_ids(db, escopo=escopo, filtros=filtros, ids=ids)
            fisicos = [linha for linha in linhas if linha.tipo != "link"]
            links = len(linhas) - len(fisicos)
            if len(fisicos) > ZIP_MAX_FILES:  # inalcançável com LIMITE_IDS=500, mantido como guarda do contrato
                raise ArquivoLoteLimiteError(f"O ZIP aceita no máximo {ZIP_MAX_FILES} arquivos")
        else:
            fisicos = self._linhas_todos(
                db, escopo=escopo, filtros=filtros, excluir_ids=excluir_ids, limite=ZIP_MAX_FILES, somente_fisicos=True
            )
            _total, links, _bytes = self.repository.contar_lote(db, escopo=escopo, filtros=filtros, excluir_ids=excluir_ids)
        if not fisicos:
            raise ArquivoLoteNaoEncontradoError("Nenhum arquivo para baixar na seleção (links não entram no ZIP)")

        bytes_total = sum(linha.tamanho_bytes or 0 for linha in fisicos)
        if bytes_total > ZIP_MAX_TOTAL_BYTES:
            raise ArquivoLoteLimiteError(f"O tamanho total passa de {ZIP_MAX_TOTAL_BYTES // (1024 * 1024)} MB — refine a seleção")

        # Metadados já em memória: encerra a transação ANTES de tocar em disco (não fica aberta durante o ZIP).
        itens = [
            (linha.demanda_id, linha.nome_fisico, linha.nome_original) for linha in fisicos
        ]
        db.rollback()

        caminhos = [self._caminho_confiavel(demanda_id, nome_fisico) for demanda_id, nome_fisico, _ in itens]
        ausentes = sum(1 for caminho in caminhos if caminho is None)
        if ausentes:
            # Não mascara inconsistência de armazenamento: nada de ZIP incompleto.
            raise ArquivoLoteFisicoAusenteError(ausentes)

        nomes = nomes_unicos_para_zip(
            [nome_seguro_para_zip(nome_original, Path(nome_fisico or "").suffix.lower()) for _, nome_fisico, nome_original in itens]
        )
        descritor, temporario = tempfile.mkstemp(prefix="tfzip-", suffix=".zip")
        os.close(descritor)
        destino = Path(temporario)
        try:
            with zipfile.ZipFile(destino, "w", allowZip64=True, strict_timestamps=False) as zf:
                for caminho, nome in zip(caminhos, nomes):
                    assert caminho is not None
                    comprimido = caminho.suffix.lower() not in _EXTENSOES_JA_COMPRIMIDAS
                    zf.write(
                        caminho,
                        arcname=nome,
                        compress_type=zipfile.ZIP_DEFLATED if comprimido else zipfile.ZIP_STORED,
                        compresslevel=1 if comprimido else None,
                    )
        except FileNotFoundError as exc:  # sumiu entre a conferência e a leitura
            destino.unlink(missing_ok=True)
            raise ArquivoLoteFisicoAusenteError(1) from exc
        except BaseException:
            destino.unlink(missing_ok=True)
            raise
        return ZipPreparado(caminho=destino, nome=nome_do_zip(), arquivos=len(fisicos), links_ignorados=links, bytes_total=bytes_total)

    # ----------------------------------------------------------------------------------
    # Exclusão
    # ----------------------------------------------------------------------------------

    def excluir(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        filtros: FiltrosCentral,
        ids: Sequence[str] | None,
        excluir_ids: Sequence[str],
        actor_usuario_id: str | None,
    ) -> ArquivosLoteExclusaoRead:
        try:
            if ids is not None:
                linhas = self._linhas_ids(db, escopo=escopo, filtros=filtros, ids=ids, travar=True)
            else:
                linhas = self._linhas_todos(
                    db, escopo=escopo, filtros=filtros, excluir_ids=excluir_ids, limite=EXCLUSAO_MAX_FILES, travar=True
                )
            if not linhas:
                raise ArquivoLoteNaoEncontradoError("Nenhum arquivo corresponde à seleção")

            arquivo_ids = [linha.id for linha in linhas]
            # Fase 9B: com as linhas JÁ travadas, nenhum arquivo preso a aprovação externa (em aberto ou decidida) pode estar na seleção — a
            # verificação é de TODOS antes de excluir qualquer um (nada parcial).
            protegidos = self.arquivo_service.aprovacao_repository.arquivos_protegidos(db, arquivo_ids)
            if protegidos:
                raise ArquivoVinculadoAprovacaoExternaError(len(protegidos))
            demanda_ids = sorted({linha.demanda_id for linha in linhas})
            demandas = {
                d.id: d
                for d in db.scalars(select(Demanda).where(Demanda.id.in_(demanda_ids), Demanda.empresa_id == escopo.empresa_id)).all()
            }

            now = agora_utc()
            removidos = (
                db.query(DemandaArquivo).filter(DemandaArquivo.id.in_(arquivo_ids)).delete(synchronize_session=False)
            )
            if removidos != len(arquivo_ids):  # travadas por FOR UPDATE: só ocorre em inconsistência real
                raise ArquivoLoteNaoEncontradoError("A seleção mudou durante a exclusão — nada foi excluído")
            for linha in linhas:
                self.arquivo_service.publicar_evento(
                    db,
                    demandas[linha.demanda_id],
                    DomainEventType.DEMANDA_ARQUIVO_REMOVIDO,
                    actor_usuario_id,
                    extra_payload={
                        "arquivoId": linha.id,
                        "nomeOriginal": linha.nome_original or linha.titulo,
                        "lote": True,
                    },
                    occurred_at=now,
                )
            db.commit()
        except Exception:
            db.rollback()
            raise

        # Depois do commit: melhor esforço, como na exclusão individual. Falha de disco não desfaz o que já é verdade no banco;
        # é contada, registrada e devolvida — nunca silenciosa.
        nao_removidos = 0
        for linha in linhas:
            if not linha.nome_fisico:
                continue
            try:
                self.arquivo_service.caminho_fisico(linha.demanda_id, linha.nome_fisico).unlink(missing_ok=True)
            except OSError:
                nao_removidos += 1
                logger.warning("exclusão em lote: arquivo físico não removido (arquivo_id=%s)", linha.id)
        return ArquivosLoteExclusaoRead(excluidos=len(linhas), arquivosFisicosNaoRemovidos=nao_removidos)
