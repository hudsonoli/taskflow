"""Portal Externo de Aprovação (Fase 9B) — link-capability para o CLIENTE aprovar ou pedir ajustes, sem conta, sem sessão e sem `Usuario`.

Princípios:
- o token (`secrets.token_urlsafe(32)`, 256 bits) existe em claro SÓ na resposta da criação; o banco guarda o SHA-256. Ele resolve empresa, Demanda, etapa e
  artefatos — o cliente nunca informa um id. Token nunca vai para log, evento, URL/path/query do backend ou mensagem de erro;
- estado DERIVADO (sem coluna): decisão > revogada > expirada > obsoleta (a etapa deixou de ser a atual / Demanda arquivada) > pendente;
- ORDEM DE LOCKS fixa: Demanda → solicitação (→ linhas de arquivo na criação). Criar link, aprovar/rejeitar internamente e decidir externamente disputam a
  MESMA Demanda: um vencedor, os demais veem o estado final (409 / link indisponível);
- a decisão externa REUSA o núcleo do workflow (`DemandaWorkflowService.aprovar_etapa` / `rejeitar_etapa`, semântica 8A/8D) com `AtorExterno`, tudo numa
  transação: decisão + avanço/devolução + eventos + notificações;
- artefatos são SNAPSHOTS (nome, tamanho, MIME, SHA-256) e só saem do disco se o arquivo ainda confere com o hash;
- NADA identifica o cliente além do que ele declara (nome obrigatório, e-mail opcional — não verificados). IP/user-agent/geolocalização NÃO são gravados.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.demanda_arquivo_service as arquivo_modulo
from app.core.relogio import agora_utc
from app.core.workflow_autoridade import departamentos_head_para_workflow, pode_gerenciar_aprovacao_externa
from app.domain.aprovacao_externa import ArquivoVinculadoAprovacaoExternaError
from app.domain.event_types import DomainEventType
from app.models.aprovacao_externa import AprovacaoExterna, AprovacaoExternaArquivo
from app.models.cliente import Cliente
from app.models.demanda import Demanda
from app.models.demanda_arquivo import DemandaArquivo
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.repositories.aprovacao_externa_repository import AprovacaoExternaRepository
from app.repositories.demanda_repository import DemandaRepository
from app.schemas.aprovacao_externa import (
    AprovacaoExternaArtefatoRead,
    AprovacaoExternaCriadaRead,
    AprovacaoExternaCriar,
    AprovacaoExternaDecisaoRead,
    AprovacaoExternaEstadoRead,
    AprovacaoExternaRead,
    AprovacaoPublicaArtefatoRead,
    AprovacaoPublicaDecisao,
    AprovacaoPublicaDecisaoRead,
    AprovacaoPublicaDecisaoResultadoRead,
    AprovacaoPublicaRead,
    ContatoClienteRead,
    token_com_formato_valido,
)
from app.services.configuracao_personalizacao_service import ConfiguracaoPersonalizacaoService, PersonalizacaoLogoNaoEncontradoError
from app.services.demanda_service import DemandaService
from app.services.demanda_workflow_service import (
    AtorExterno,
    DemandaWorkflowConflitoError,
    DemandaWorkflowEtapaNaoEncontradaError,
    DemandaWorkflowAcaoInvalidaError,
    DemandaWorkflowSemAutoridadeError,
    DemandaWorkflowService,
)

logger = logging.getLogger(__name__)

TIPOS_ARQUIVO_APROVAVEIS = frozenset({"anexo", "layout"})
TOTAL_MAX_BYTES = 100 * 1024 * 1024
LEITURA_BLOCO = 1024 * 1024
MAX_CONTATOS = 20
MOTIVO_REVOGACAO_MANUAL = "manual"
MOTIVO_REVOGACAO_SUBSTITUIDA = "substituida"

ESTADOS_LEGIVEIS_PELO_CLIENTE = ("pendente", "aprovada", "ajustes_solicitados")


def hash_token_aprovacao(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ======================================================================================
# Erros
# ======================================================================================


class AprovacaoExternaIndisponivelError(LookupError):
    """Portal: link inexistente, revogado, expirado ou obsoleto — TODOS iguais para quem consulta (404 neutro, sem distinguir)."""


class AprovacaoExternaJaDecididaError(RuntimeError):
    """Portal: a solicitação já tem decisão (duplo envio, aprovar × ajustes). Vira 409; o estado final continua legível."""


class AprovacaoExternaConflitoError(RuntimeError):
    """409 com `codigo` estável (interno e portal)."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


class AprovacaoExternaSemAutoridadeError(PermissionError):
    """Interno: não pode gerenciar o link desta etapa. Vira 403."""


class AprovacaoExternaNaoEncontradaError(LookupError):
    """Interno: etapa/solicitação que não é desta Demanda. Vira 404."""


class AprovacaoExternaEntradaInvalidaError(ValueError):
    """Interno: etapa que não é de aprovação, arquivo inelegível/ausente, limites. Vira 422."""


# ======================================================================================
# Estado derivado
# ======================================================================================


def derivar_estado(
    aprovacao: AprovacaoExterna, *, etapa_atual_id: str | None, demanda_arquivada: bool, agora: datetime
) -> str:
    """decisão > revogada > expirada > obsoleta > pendente. Decisão e revogação são exclusivas no banco; a precedência define o resto."""
    if aprovacao.decisao is not None:
        return aprovacao.decisao
    if aprovacao.revogada_em is not None:
        return "revogada"
    if aprovacao.expira_em <= agora:
        return "expirada"
    if demanda_arquivada or etapa_atual_id != aprovacao.workflow_etapa_id:
        return "obsoleta"
    return "pendente"


def _tipo_do_artefato(content_type: str) -> str:
    return "pdf" if content_type == "application/pdf" else "imagem"


@dataclass
class ArtefatoServido:
    conteudo: bytes
    media_type: str
    inline: bool
    nome: str


class AprovacaoExternaService:
    def __init__(
        self,
        repository: AprovacaoExternaRepository | None = None,
        demanda_repository: DemandaRepository | None = None,
        demanda_service: DemandaService | None = None,
        workflow_service: DemandaWorkflowService | None = None,
        personalizacao_service: ConfiguracaoPersonalizacaoService | None = None,
    ) -> None:
        self.repository = repository or AprovacaoExternaRepository()
        self.demanda_repository = demanda_repository or DemandaRepository()
        self.demanda_service = demanda_service or DemandaService(repository=self.demanda_repository)
        self.workflow_service = workflow_service or DemandaWorkflowService(
            repository=self.demanda_repository, demanda_service=self.demanda_service, aprovacao_repository=self.repository
        )
        self.personalizacao_service = personalizacao_service or ConfiguracaoPersonalizacaoService()

    # ----------------------------------------------------------------------------------
    # Apoio
    # ----------------------------------------------------------------------------------

    def _etapa_atual_id(self, db: Session, demanda_id: str) -> str | None:
        etapas = self.demanda_repository.listar_etapas_workflow_em_lote(db, [demanda_id]).get(demanda_id, [])
        atual = next((e for e in etapas if e.status != "concluida"), None)
        return atual.id if atual else None

    def _estado(self, db: Session, aprovacao: AprovacaoExterna, demanda: Demanda, agora: datetime) -> str:
        return derivar_estado(
            aprovacao,
            etapa_atual_id=self._etapa_atual_id(db, demanda.id),
            demanda_arquivada=demanda.status == "arquivada",
            agora=agora,
        )

    # ======================================================================================
    # INTERNO — gerenciar o link da etapa de aprovação atual
    # ======================================================================================

    def _carregar_etapa(self, db: Session, demanda: Demanda, etapa_id: str) -> tuple[list[DemandaWorkflowEtapa], DemandaWorkflowEtapa]:
        etapas = self.demanda_repository.listar_etapas_workflow_travadas(db, demanda.id)
        etapa = next((e for e in etapas if e.id == etapa_id), None)
        if etapa is None:
            raise AprovacaoExternaNaoEncontradaError("Etapa não encontrada nesta tarefa")
        return etapas, etapa

    def _pode_gerenciar(self, db: Session, usuario: Usuario, demanda: Demanda, etapa: DemandaWorkflowEtapa) -> bool:
        usuarios = self.demanda_repository.listar_etapa_responsavel_ids_em_lote(db, [etapa.id]).get(etapa.id, [])
        departamentos = self.demanda_repository.listar_etapa_departamento_ids_em_lote(db, [etapa.id]).get(etapa.id, [])
        responsaveis_demanda = list(
            db.scalars(select(DemandaResponsavel.usuario_id).where(DemandaResponsavel.demanda_id == demanda.id)).all()
        )
        return pode_gerenciar_aprovacao_externa(
            usuario,
            usuario_responsavel_ids=usuarios,
            departamento_responsavel_ids=departamentos,
            departamentos_head=departamentos_head_para_workflow(db, usuario),
            demanda_responsavel_ids=responsaveis_demanda,
        )

    def _validar_etapa_gerenciavel(
        self, db: Session, usuario: Usuario, demanda: Demanda, etapa: DemandaWorkflowEtapa, etapas: list[DemandaWorkflowEtapa], *, exigir_atual: bool
    ) -> None:
        """422 (tipo) → 403 (autoridade) → 409 (arquivada / não atual / pausada), mesma ordem do workflow: autoridade antes de revelar o estado."""
        if etapa.tipo != "aprovacao":
            raise AprovacaoExternaEntradaInvalidaError("Só uma etapa de aprovação pode ter link de aprovação externa")
        if not self._pode_gerenciar(db, usuario, demanda, etapa):
            raise AprovacaoExternaSemAutoridadeError("Você não tem autoridade para gerenciar a aprovação externa desta etapa")
        if demanda.status == "arquivada":
            raise DemandaWorkflowConflitoError("DEMANDA_ARQUIVADA", "Demanda arquivada não pode ter aprovação externa — restaure-a antes")
        if exigir_atual:
            atual = next((e for e in etapas if e.status != "concluida"), None)
            if atual is None:
                raise DemandaWorkflowConflitoError("WORKFLOW_CONCLUIDO", "O workflow desta tarefa já foi concluído")
            if atual.id != etapa.id:
                codigo = "ETAPA_JA_CONCLUIDA" if etapa.status == "concluida" else "ETAPA_NAO_ATUAL"
                raise DemandaWorkflowConflitoError(codigo, "Esta não é a etapa atual do workflow")
            if etapa.status == "pausada":
                raise DemandaWorkflowConflitoError("ETAPA_PAUSADA", "A etapa atual está pausada")

    def consultar_etapa(self, db: Session, demanda: Demanda, *, etapa_id: str, usuario: Usuario) -> AprovacaoExternaEstadoRead:
        """Painel interno: o que o usuário pode fazer + a solicitação mais recente da etapa. Leitura (sem lock): `podeGerenciar` é o mesmo critério de
        criar/revogar (tipo aprovação, etapa atual, não pausada, Demanda não arquivada, autoridade) e o endpoint reavalia tudo."""
        etapas = self.demanda_repository.listar_etapas_workflow_em_lote(db, [demanda.id]).get(demanda.id, [])
        etapa = next((e for e in etapas if e.id == etapa_id), None)
        if etapa is None:
            raise AprovacaoExternaNaoEncontradaError("Etapa não encontrada nesta tarefa")
        agora = agora_utc()
        atual = next((e for e in etapas if e.status != "concluida"), None)
        pode = bool(
            etapa.tipo == "aprovacao"
            and atual is not None
            and atual.id == etapa.id
            and etapa.status != "pausada"
            and demanda.status != "arquivada"
            and self._pode_gerenciar(db, usuario, demanda, etapa)
        )
        ultima = self.repository.ultima_da_etapa(db, etapa.id)
        leitura = (
            self._para_read(db, ultima, estado=derivar_estado(
                ultima, etapa_atual_id=atual.id if atual else None, demanda_arquivada=demanda.status == "arquivada", agora=agora
            ))
            if ultima is not None
            else None
        )
        return AprovacaoExternaEstadoRead(
            podeGerenciar=pode,
            atual=leitura,
            contatos=self._contatos_do_cliente(db, demanda) if pode else [],
        )

    def _contatos_do_cliente(self, db: Session, demanda: Demanda) -> list[ContatoClienteRead]:
        if demanda.cliente_id is None:
            return []
        cliente = db.scalar(select(Cliente).where(Cliente.id == demanda.cliente_id, Cliente.empresa_id == demanda.empresa_id))
        brutos = (cliente.contatos if cliente is not None else None) or []
        contatos = [
            ContatoClienteRead(
                nome=str(item.get("nome") or "").strip()[:120],
                email=(str(item.get("email")).strip().lower()[:254] if item.get("email") else None),
                cargo=(str(item.get("cargo")).strip()[:120] if item.get("cargo") else None),
                recebeEntregas=bool(item.get("recebeEntregas")),
            )
            for item in brutos
            if isinstance(item, dict) and str(item.get("nome") or "").strip()
        ]
        contatos.sort(key=lambda contato: not contato.recebe_entregas)  # quem recebe entregas primeiro (sort estável)
        return contatos[:MAX_CONTATOS]

    def _para_read(self, db: Session, aprovacao: AprovacaoExterna, *, estado: str) -> AprovacaoExternaRead:
        artefatos = self.repository.artefatos(db, aprovacao.id)
        criador = db.get(Usuario, aprovacao.criada_por_usuario_id) if aprovacao.criada_por_usuario_id else None
        decisao = (
            AprovacaoExternaDecisaoRead(
                decisao=aprovacao.decisao,
                decididaEm=aprovacao.decidida_em,
                nomeAprovador=aprovacao.nome_aprovador,
                emailAprovador=aprovacao.email_aprovador,
                motivo=aprovacao.motivo,
            )
            if aprovacao.decisao is not None and aprovacao.decidida_em is not None and aprovacao.nome_aprovador
            else None
        )
        return AprovacaoExternaRead(
            id=aprovacao.id,
            etapaId=aprovacao.workflow_etapa_id,
            estado=estado,
            instrucao=aprovacao.instrucao,
            criadaEm=aprovacao.criada_em,
            criadaPorNome=criador.nome if criador is not None else None,
            expiraEm=aprovacao.expira_em,
            revogadaEm=aprovacao.revogada_em,
            revogadaMotivo=aprovacao.revogada_motivo,
            destinatarioNome=aprovacao.destinatario_nome,
            destinatarioEmail=aprovacao.destinatario_email,
            artefatos=[
                AprovacaoExternaArtefatoRead(
                    ordem=artefato.ordem,
                    nome=artefato.nome_original,
                    contentType=artefato.content_type,
                    tamanhoBytes=artefato.tamanho_bytes,
                    arquivoId=artefato.arquivo_id,
                )
                for artefato in artefatos
            ],
            decisao=decisao,
        )

    # ----------------------------------------------------------------------------------
    # Criar
    # ----------------------------------------------------------------------------------

    def _snapshot_dos_arquivos(self, db: Session, demanda: Demanda, arquivo_ids: list[str]) -> list[dict]:
        """Trava as linhas dos arquivos (cria × exclui), confere que são DESTA Demanda e elegíveis, e calcula o SHA-256 do que está em disco AGORA."""
        travados = {
            arquivo.id: arquivo
            for arquivo in db.scalars(
                select(DemandaArquivo)
                .where(DemandaArquivo.id.in_(arquivo_ids), DemandaArquivo.demanda_id == demanda.id)
                .order_by(DemandaArquivo.id.asc())  # ordem determinística de locks entre criações concorrentes
                .with_for_update()
                .execution_options(populate_existing=True)
            ).all()
        }
        if len(travados) != len(set(arquivo_ids)):
            # inexistente ou de OUTRA Demanda/empresa: indistinguíveis de propósito
            raise AprovacaoExternaEntradaInvalidaError("Um ou mais arquivos não pertencem a esta tarefa")

        raiz = Path(arquivo_modulo.UPLOADS_ROOT).resolve()
        snapshot: list[dict] = []
        total = 0
        for arquivo_id in arquivo_ids:  # ordem pedida = ordem exibida ao cliente
            arquivo = travados[arquivo_id]
            if arquivo.tipo not in TIPOS_ARQUIVO_APROVAVEIS or not arquivo.nome_fisico:
                raise AprovacaoExternaEntradaInvalidaError("Links não podem ser enviados para aprovação — escolha arquivos PNG, JPG ou PDF")
            extensao = Path(arquivo.nome_fisico).suffix.lower()
            if extensao not in arquivo_modulo.ALLOWED_EXTENSIONS:
                raise AprovacaoExternaEntradaInvalidaError("Só arquivos PNG, JPG ou PDF podem ser enviados para aprovação")
            caminho = Path(arquivo_modulo.UPLOADS_ROOT) / "demandas" / demanda.id / arquivo.nome_fisico
            try:
                real = caminho.resolve()
                if not real.is_relative_to(raiz) or not real.is_file():
                    raise AprovacaoExternaEntradaInvalidaError("Um dos arquivos não está disponível no armazenamento")
                digest = hashlib.sha256()
                tamanho = 0
                prefixo = b""
                with real.open("rb") as fisico:
                    while bloco := fisico.read(LEITURA_BLOCO):
                        if not prefixo:
                            prefixo = bloco[:16]
                        digest.update(bloco)
                        tamanho += len(bloco)
            except OSError as exc:
                raise AprovacaoExternaEntradaInvalidaError("Um dos arquivos não está disponível no armazenamento") from exc
            if tamanho == 0 or not arquivo_modulo._bytes_correspondem_a_assinatura(prefixo, extensao):
                raise AprovacaoExternaEntradaInvalidaError("O conteúdo de um dos arquivos não corresponde ao tipo informado")
            total += tamanho
            if total > TOTAL_MAX_BYTES:
                raise AprovacaoExternaEntradaInvalidaError(f"O total dos arquivos passa de {TOTAL_MAX_BYTES // (1024 * 1024)} MB")
            snapshot.append(
                {
                    "arquivo_id": arquivo.id,
                    "nome_original": (arquivo.nome_original or "arquivo")[:255],
                    "tamanho_bytes": tamanho,
                    "content_type": arquivo_modulo._MIME_CANONICO[extensao],
                    "sha256": digest.hexdigest(),
                }
            )
        return snapshot

    def criar(
        self, db: Session, demanda: Demanda, *, etapa_id: str, payload: AprovacaoExternaCriar, usuario: Usuario
    ) -> AprovacaoExternaCriadaRead:
        """Gera um NOVO link para a etapa de aprovação ATUAL. Lock da Demanda primeiro (serializa com aprovar/rejeitar internos e decisão externa); o link
        aberto anterior da etapa — mesmo expirado — é revogado (`substituida`) na mesma transação. O token só existe na resposta."""
        try:
            self.demanda_repository.bloquear_demanda_para_atualizacao(db, demanda)
            etapas, etapa = self._carregar_etapa(db, demanda, etapa_id)
            self._validar_etapa_gerenciavel(db, usuario, demanda, etapa, etapas, exigir_atual=True)

            snapshot = self._snapshot_dos_arquivos(db, demanda, [str(i) for i in payload.arquivo_ids])

            agora = agora_utc()
            anterior = self.repository.aberta_da_etapa(db, etapa.id, travar=True)
            if anterior is not None:
                anterior.revogada_em = agora
                anterior.revogada_por_usuario_id = usuario.id
                anterior.revogada_motivo = MOTIVO_REVOGACAO_SUBSTITUIDA
                db.flush()  # libera a vaga no índice único parcial ANTES de inserir a nova
                self._publicar_revogada(db, demanda, etapa, anterior, usuario, agora, MOTIVO_REVOGACAO_SUBSTITUIDA)

            token = secrets.token_urlsafe(32)
            aprovacao = AprovacaoExterna(
                id=str(uuid4()),
                empresa_id=demanda.empresa_id,
                demanda_id=demanda.id,
                workflow_etapa_id=etapa.id,
                token_hash=hash_token_aprovacao(token),
                instrucao=payload.instrucao,
                criada_em=agora,
                criada_por_usuario_id=usuario.id,
                expira_em=agora + timedelta(days=payload.validade_dias),
                destinatario_nome=payload.destinatario_nome,
                destinatario_email=payload.destinatario_email,
            )
            artefatos = [
                AprovacaoExternaArquivo(aprovacao_externa_id=aprovacao.id, ordem=indice, **dados)
                for indice, dados in enumerate(snapshot, start=1)
            ]
            self.repository.adicionar(db, aprovacao, artefatos)
            self.demanda_service.publicar_evento_demanda(
                db,
                demanda,
                DomainEventType.DEMANDA_APROVACAO_EXTERNA_CRIADA,
                usuario.id,
                extra_payload={
                    "aprovacaoExternaId": aprovacao.id,
                    "etapaId": etapa.id,
                    "etapaNome": etapa.nome,
                    "etapaOrdem": etapa.ordem,
                    "expiraEm": aprovacao.expira_em.isoformat(),
                    "quantidadeArtefatos": len(artefatos),
                    "destinatarioNome": aprovacao.destinatario_nome,
                    "atorUsuarioId": usuario.id,
                },
                occurred_at=agora,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(aprovacao)
        leitura = self._para_read(db, aprovacao, estado="pendente")
        return AprovacaoExternaCriadaRead(**leitura.model_dump(by_alias=True), token=token)

    # ----------------------------------------------------------------------------------
    # Revogar
    # ----------------------------------------------------------------------------------

    def _publicar_revogada(
        self, db: Session, demanda: Demanda, etapa: DemandaWorkflowEtapa, aprovacao: AprovacaoExterna, usuario: Usuario, agora: datetime, motivo: str
    ) -> None:
        self.demanda_service.publicar_evento_demanda(
            db,
            demanda,
            DomainEventType.DEMANDA_APROVACAO_EXTERNA_REVOGADA,
            usuario.id,
            extra_payload={
                "aprovacaoExternaId": aprovacao.id,
                "etapaId": etapa.id,
                "etapaNome": etapa.nome,
                "etapaOrdem": etapa.ordem,
                "motivo": motivo,
                "atorUsuarioId": usuario.id,
            },
            occurred_at=agora,
        )

    def revogar(self, db: Session, demanda: Demanda, *, etapa_id: str, aprovacao_id: str, usuario: Usuario) -> AprovacaoExternaRead:
        """Revoga a solicitação (o cliente passa a ver "link indisponível"). Decidida não se revoga (409). Já revogada: idempotente, sem novo evento."""
        try:
            self.demanda_repository.bloquear_demanda_para_atualizacao(db, demanda)
            etapas, etapa = self._carregar_etapa(db, demanda, etapa_id)
            self._validar_etapa_gerenciavel(db, usuario, demanda, etapa, etapas, exigir_atual=False)
            existente = self.repository.por_id_da_etapa(db, aprovacao_id=aprovacao_id, etapa_id=etapa.id, demanda_id=demanda.id)
            if existente is None:
                raise AprovacaoExternaNaoEncontradaError("Aprovação externa não encontrada nesta etapa")
            aprovacao = self.repository.travar_por_id(db, existente.id)
            assert aprovacao is not None
            if aprovacao.decisao is not None:
                raise AprovacaoExternaConflitoError(
                    "APROVACAO_EXTERNA_JA_DECIDIDA", "Esta aprovação externa já foi decidida pelo cliente e não pode ser revogada"
                )
            if aprovacao.revogada_em is None:
                agora = agora_utc()
                aprovacao.revogada_em = agora
                aprovacao.revogada_por_usuario_id = usuario.id
                aprovacao.revogada_motivo = MOTIVO_REVOGACAO_MANUAL
                db.flush()
                self._publicar_revogada(db, demanda, etapa, aprovacao, usuario, agora, MOTIVO_REVOGACAO_MANUAL)
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(aprovacao)
        atual_id = self._etapa_atual_id(db, demanda.id)
        return self._para_read(
            db,
            aprovacao,
            estado=derivar_estado(aprovacao, etapa_atual_id=atual_id, demanda_arquivada=demanda.status == "arquivada", agora=agora_utc()),
        )

    # ======================================================================================
    # PÚBLICO — portador do token
    # ======================================================================================

    def _resolver(self, db: Session, token: str) -> tuple[AprovacaoExterna, Demanda, Empresa]:
        """token → solicitação + Demanda + Empresa ATIVA, ou `Indisponivel` (inexistente, empresa inativa, inconsistência). Sem lock, sem estado."""
        if not token_com_formato_valido(token):
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
        aprovacao = self.repository.por_token_hash(db, hash_token_aprovacao(token))
        if aprovacao is None:
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
        demanda = db.get(Demanda, aprovacao.demanda_id)
        empresa = db.get(Empresa, aprovacao.empresa_id)
        if demanda is None or empresa is None or demanda.empresa_id != empresa.id or empresa.status != "ativa":
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
        return aprovacao, demanda, empresa

    def _resolver_legivel(self, db: Session, token: str) -> tuple[AprovacaoExterna, Demanda, Empresa, str]:
        aprovacao, demanda, empresa = self._resolver(db, token)
        estado = self._estado(db, aprovacao, demanda, agora_utc())
        if estado not in ESTADOS_LEGIVEIS_PELO_CLIENTE:  # revogada / expirada / obsoleta: nada de dado interno, nem o motivo
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
        return aprovacao, demanda, empresa, estado

    def consultar_publico(self, db: Session, token: str) -> AprovacaoPublicaRead:
        aprovacao, demanda, empresa, estado = self._resolver_legivel(db, token)
        artefatos = self.repository.artefatos(db, aprovacao.id)
        decisao = (
            AprovacaoPublicaDecisaoRead(decisao=aprovacao.decisao, decididaEm=aprovacao.decidida_em)
            if aprovacao.decisao is not None and aprovacao.decidida_em is not None
            else None
        )
        etapas = self.demanda_repository.listar_etapas_workflow_em_lote(db, [demanda.id]).get(demanda.id, [])
        etapa = next((e for e in etapas if e.id == aprovacao.workflow_etapa_id), None)
        return AprovacaoPublicaRead(
            empresa=self.personalizacao_service.get_publico_da_empresa(db, empresa),
            demandaIdentificador=demanda.identificador,
            demandaNome=demanda.nome,
            instrucao=aprovacao.instrucao,
            estado=estado,
            expiraEm=aprovacao.expira_em,
            destinatarioNome=aprovacao.destinatario_nome,
            podeSolicitarAjustes=bool(etapa is not None and any(outra.ordem < etapa.ordem for outra in etapas)),
            artefatos=[
                AprovacaoPublicaArtefatoRead(
                    ordem=artefato.ordem,
                    nome=artefato.nome_original,
                    tipo=_tipo_do_artefato(artefato.content_type),
                    contentType=artefato.content_type,
                    tamanhoBytes=artefato.tamanho_bytes,
                )
                for artefato in artefatos
            ],
            decisao=decisao,
        )

    def logo_publico(self, db: Session, token: str) -> tuple[Path, str, str]:
        """Logo da empresa DO TOKEN (nunca de slug/cookie do cliente). Só para quem tem um link legível."""
        _aprovacao, _demanda, empresa, _estado = self._resolver_legivel(db, token)
        try:
            return self.personalizacao_service.ler_logo_da_empresa(db, empresa)
        except PersonalizacaoLogoNaoEncontradoError as exc:
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.") from exc

    def obter_artefato(self, db: Session, token: str, ordem: int) -> ArtefatoServido:
        """Bytes do artefato `ordem` da solicitação. Só sai do disco se: ainda é desta Demanda, é arquivo físico elegível, o caminho fica confinado em
        `uploads`, o SHA-256 AGORA é o do snapshot e a assinatura bate com a extensão. Imagem → inline; PDF → sempre `attachment`. Qualquer falha →
        indisponível (sem detalhe)."""
        aprovacao, demanda, _empresa, _estado = self._resolver_legivel(db, token)
        artefato = self.repository.artefato_por_ordem(db, aprovacao.id, ordem)
        if artefato is None or artefato.arquivo_id is None:
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
        arquivo = db.get(DemandaArquivo, artefato.arquivo_id)
        if (
            arquivo is None
            or arquivo.demanda_id != aprovacao.demanda_id
            or arquivo.tipo not in TIPOS_ARQUIVO_APROVAVEIS
            or not arquivo.nome_fisico
        ):
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
        extensao = Path(arquivo.nome_fisico).suffix.lower()
        raiz = Path(arquivo_modulo.UPLOADS_ROOT).resolve()
        caminho = Path(arquivo_modulo.UPLOADS_ROOT) / "demandas" / aprovacao.demanda_id / arquivo.nome_fisico
        try:
            real = caminho.resolve()
            if not real.is_relative_to(raiz) or not real.is_file() or real.stat().st_size != artefato.tamanho_bytes:
                raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
            conteudo = real.read_bytes()  # ≤ 20 MB por arquivo; lido UMA vez e servido exatamente o que foi conferido (sem TOCTOU)
        except OSError as exc:
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.") from exc
        if (
            hashlib.sha256(conteudo).hexdigest() != artefato.sha256
            or not arquivo_modulo._bytes_correspondem_a_assinatura(conteudo[:16], extensao)
        ):
            logger.warning("aprovação externa: artefato não confere com o snapshot (aprovacao_externa_id=%s ordem=%s)", aprovacao.id, ordem)
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
        media_type = arquivo_modulo._MIME_CANONICO[extensao]
        return ArtefatoServido(
            conteudo=conteudo, media_type=media_type, inline=arquivo_modulo._DISPOSITION_INLINE.get(extensao, False), nome=artefato.nome_original
        )

    # ----------------------------------------------------------------------------------
    # Decidir
    # ----------------------------------------------------------------------------------

    def decidir(self, db: Session, payload: AprovacaoPublicaDecisao) -> AprovacaoPublicaDecisaoResultadoRead:
        """Uma decisão do cliente: aprovar (avança a etapa) ou solicitar ajustes (devolve, semântica 8D). UMA transação: decisão + workflow + eventos +
        notificações. Locks: Demanda → solicitação. Vencedor único: duplo envio / aprovar × ajustes / interno × externo → o perdedor vê 409 (já decidida)
        ou o link indisponível."""
        existente, demanda, empresa = self._resolver(db, payload.token)
        aprovar = payload.decisao == "aprovar"
        try:
            self.demanda_repository.bloquear_demanda_para_atualizacao(db, demanda)
            aprovacao = self.repository.travar_por_id(db, existente.id)
            if aprovacao is None:
                raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")
            agora = agora_utc()
            if aprovacao.decisao is not None:
                raise AprovacaoExternaJaDecididaError("Esta aprovação já foi respondida.")
            if aprovacao.revogada_em is not None or aprovacao.expira_em <= agora or empresa.status != "ativa":
                raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.")

            aprovacao.decisao = "aprovada" if aprovar else "ajustes_solicitados"
            aprovacao.decidida_em = agora
            aprovacao.nome_aprovador = payload.nome
            aprovacao.email_aprovador = payload.email
            aprovacao.motivo = payload.motivo
            db.flush()

            ator = AtorExterno(nome=payload.nome, aprovacao_externa_id=aprovacao.id)
            tipo_evento = (
                DomainEventType.DEMANDA_APROVACAO_EXTERNA_APROVADA if aprovar else DomainEventType.DEMANDA_APROVACAO_EXTERNA_AJUSTES
            )

            def registrar(etapa: DemandaWorkflowEtapa, instante: datetime) -> None:
                # Para a central de notificações (responsáveis da Demanda). Sem e-mail, sem motivo (o motivo fica no evento de workflow).
                self.demanda_service.publicar_evento_demanda(
                    db,
                    demanda,
                    tipo_evento,
                    None,
                    extra_payload={
                        "aprovacaoExternaId": aprovacao.id,
                        "etapaId": etapa.id,
                        "etapaNome": etapa.nome,
                        "etapaOrdem": etapa.ordem,
                        "atorUsuarioId": None,
                        "atorExterno": {"nome": payload.nome, "aprovacaoExternaId": aprovacao.id},
                    },
                    occurred_at=instante,
                )

            # O núcleo faz commit/rollback da transação inteira (inclui a decisão gravada acima).
            if aprovar:
                self.workflow_service.aprovar_etapa(db, demanda, etapa_id=aprovacao.workflow_etapa_id, actor=ator, durante=registrar)
            else:
                self.workflow_service.rejeitar_etapa(
                    db, demanda, etapa_id=aprovacao.workflow_etapa_id, motivo=payload.motivo or "", actor=ator, durante=registrar
                )
            decidida_em = aprovacao.decidida_em
        except DemandaWorkflowConflitoError as exc:
            db.rollback()
            if exc.codigo == "SEM_ETAPA_ANTERIOR":
                raise AprovacaoExternaConflitoError(
                    "SEM_ETAPA_ANTERIOR", "Esta etapa não tem etapa anterior: não é possível solicitar ajustes por aqui."
                ) from exc
            # etapa não é mais a atual, workflow concluído, pausada, demanda arquivada: o link virou obsoleto
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.") from exc
        except (DemandaWorkflowEtapaNaoEncontradaError, DemandaWorkflowAcaoInvalidaError, DemandaWorkflowSemAutoridadeError) as exc:
            db.rollback()
            raise AprovacaoExternaIndisponivelError("Este link de aprovação não está mais disponível.") from exc
        except Exception:
            db.rollback()
            raise
        return AprovacaoPublicaDecisaoResultadoRead(
            estado="aprovada" if aprovar else "ajustes_solicitados", decididaEm=decidida_em
        )

    # ======================================================================================
    # Exclusão de arquivos: proteção
    # ======================================================================================

    def garantir_arquivos_desvinculados(self, db: Session, arquivo_ids: list[str]) -> None:
        """Chamada DEPOIS de travar as linhas dos arquivos (`FOR UPDATE`): bloqueia a exclusão de arquivos presos a uma aprovação externa aberta ou
        decidida. Revogada sem decisão não protege. Em lote, a verificação é de TODOS antes de excluir qualquer um."""
        protegidos = self.repository.arquivos_protegidos(db, arquivo_ids)
        if protegidos:
            raise ArquivoVinculadoAprovacaoExternaError(len(protegidos))
