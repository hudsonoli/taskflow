from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.repositories.demanda_repository import DemandaRepository
from app.repositories.evento_repository import EventoRepository
from app.schemas.relatorio import ContagemAjustesRead, RelatorioAjustesProjetoRead
from app.services.projeto_service import ProjetoNotFoundError, ProjetoService

TIPO_ENTIDADE_DEMANDA = "demanda"

# Só estes três — `demanda.retorno_cliente_registrado` e qualquer outro tipo de evento (status,
# comentário, checklist, arquivo, criação) não fazem parte de Ajustes/Refações (Fase 2F.4).
_TIPO_EVENTO_PARA_CAMPO: dict[str, str] = {
    DomainEventType.DEMANDA_AJUSTE_INTERNO_REGISTRADO.value: "ajustes_internos",
    DomainEventType.DEMANDA_AJUSTE_CLIENTE_REGISTRADO.value: "ajustes_cliente",
    DomainEventType.DEMANDA_REFACAO_REGISTRADA.value: "refacoes",
}

_CONTAGEM_ZERADA = {"ajustes_internos": 0, "ajustes_cliente": 0, "refacoes": 0}


class RelatorioService:
    def __init__(
        self,
        projeto_service: ProjetoService | None = None,
        demanda_repository: DemandaRepository | None = None,
        evento_repository: EventoRepository | None = None,
    ) -> None:
        self.projeto_service = projeto_service or ProjetoService()
        self.demanda_repository = demanda_repository or DemandaRepository()
        self.evento_repository = evento_repository or EventoRepository()

    def ajustes_por_projeto(
        self, db: Session, *, empresa_id: str, projeto_id: str
    ) -> RelatorioAjustesProjetoRead:
        """Levanta `ProjetoNotFoundError` (mesma exceção de `ProjetoService`, não uma nova) se
        o Projeto não existir OU pertencer a outra empresa — as duas situações viram o mesmo
        404 na rota, para não confirmar a outro tenant que um UUID existe em outra empresa.
        Reaproveita `projeto_service.get_projeto`, que já é o mecanismo scoped existente; não
        há uma segunda forma de validar Projeto aqui.
        """
        projeto = self.projeto_service.get_projeto(db, projeto_id)
        if projeto.empresa_id != empresa_id:
            raise ProjetoNotFoundError("Projeto não encontrado")

        demanda_ids = self.demanda_repository.listar_ids_por_projeto(
            db, empresa_id=empresa_id, projeto_id=projeto_id
        )

        linhas = self.evento_repository.contar_por_tipo_e_entidade(
            db,
            empresa_id=empresa_id,
            entidade_tipo=TIPO_ENTIDADE_DEMANDA,
            entidade_ids=demanda_ids,
            tipos=list(_TIPO_EVENTO_PARA_CAMPO.keys()),
        )

        # `total` é a soma das mesmas linhas que montam `por_demanda` — uma agregação só,
        # nunca uma segunda query para o total.
        por_demanda: dict[str, dict[str, int]] = {}
        total = dict(_CONTAGEM_ZERADA)
        for demanda_id, tipo, quantidade in linhas:
            campo = _TIPO_EVENTO_PARA_CAMPO[tipo]
            contagem = por_demanda.setdefault(demanda_id, dict(_CONTAGEM_ZERADA))
            contagem[campo] += quantidade
            total[campo] += quantidade

        return RelatorioAjustesProjetoRead(
            total=ContagemAjustesRead(**total),
            por_demanda={
                demanda_id: ContagemAjustesRead(**contagem)
                for demanda_id, contagem in por_demanda.items()
            },
        )
