from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.busca import interpretar_termo_busca
from app.models.projeto import Projeto
from app.models.projeto_departamento import ProjetoDepartamento
from app.models.projeto_equipe_membro import ProjetoEquipeMembro
from app.models.projeto_responsavel import ProjetoResponsavel

STATUS_ARQUIVADO = "arquivado"


class ProjetoRepository:
    """Só persistência e consultas — unicidade, transição, arquivamento, vínculos e eventos
    ficam no service."""

    def create(self, db: Session, projeto: Projeto) -> Projeto:
        db.add(projeto)
        db.flush()
        return projeto

    def get_by_id(self, db: Session, projeto_id: str) -> Projeto | None:
        return db.get(Projeto, projeto_id)

    def get_by_cliente_e_nome(
        self,
        db: Session,
        *,
        empresa_id: str,
        cliente_id: str | None,
        nome_normalizado: str,
        excluir_id: str | None = None,
    ) -> Projeto | None:
        """Localiza o conflito de unicidade ANTES do INSERT.

        `cliente_id IS NULL` precisa de `is_(None)`, não de `== None`: em SQL, `x = NULL`
        nunca é verdadeiro, e a checagem passaria sempre — deixando o índice parcial
        `uq_projetos_empresa_nome_sem_cliente` estourar como IntegrityError genérico em vez
        de virar um 409 explicativo.
        """
        statement = select(Projeto).where(
            Projeto.empresa_id == empresa_id,
            Projeto.nome_normalizado == nome_normalizado,
            Projeto.cliente_id.is_(None) if cliente_id is None else Projeto.cliente_id == cliente_id,
        )
        if excluir_id:
            statement = statement.where(Projeto.id != excluir_id)
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        cliente_id: str | None = None,
        departamento_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Projeto]:
        statement = select(Projeto).where(Projeto.empresa_id == empresa_id)

        if status:
            statement = statement.where(Projeto.status == status)
        else:
            # Sem status explícito, arquivado fica oculto — filtro em SQL, antes da paginação.
            statement = statement.where(Projeto.status != STATUS_ARQUIVADO)

        if cliente_id:
            statement = statement.where(Projeto.cliente_id == cliente_id)

        if departamento_id:
            statement = statement.where(
                Projeto.id.in_(
                    select(ProjetoDepartamento.projeto_id).where(
                        ProjetoDepartamento.departamento_id == departamento_id
                    )
                )
            )

        # A decisão "isto é texto ou é documento?" mora INTEIRA em app/core/busca.py. Este
        # repository não extrai dígitos nem decide nada sobre o termo — reimplementar a regra
        # foi o que causou o incidente do Cliente. Projeto não tem documento, então só o
        # ramo textual é usado; a chamada continua sendo a mesma para não haver duas formas
        # de interpretar um termo no sistema.
        termo = interpretar_termo_busca(search)
        if not termo.vazio:
            like = f"%{termo.texto}%"
            statement = statement.where(
                or_(
                    Projeto.nome.ilike(like),
                    Projeto.campanha.ilike(like),
                    Projeto.codigo_referencia.ilike(like),
                )
            )

        statement = statement.order_by(Projeto.nome.asc()).limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Projeto]:
        """**Exclui arquivados** — mesmo critério de Fornecedor: o diretório serve para
        oferecer opções de vínculo novo, e arquivado nunca é uma opção nova."""
        statement = (
            select(Projeto)
            .where(Projeto.empresa_id == empresa_id, Projeto.status != STATUS_ARQUIVADO)
            .order_by(Projeto.nome.asc())
        )
        return list(db.scalars(statement).all())

    def update(self, db: Session, projeto: Projeto) -> Projeto:
        db.add(projeto)
        db.flush()
        return projeto

    # --- vínculos N:N ---------------------------------------------------------------

    def listar_responsavel_ids(self, db: Session, projeto_id: str) -> list[str]:
        statement = (
            select(ProjetoResponsavel.usuario_id)
            .where(ProjetoResponsavel.projeto_id == projeto_id)
            .order_by(ProjetoResponsavel.usuario_id.asc())
        )
        return list(db.scalars(statement).all())

    def listar_departamento_ids(self, db: Session, projeto_id: str) -> list[str]:
        statement = (
            select(ProjetoDepartamento.departamento_id)
            .where(ProjetoDepartamento.projeto_id == projeto_id)
            .order_by(ProjetoDepartamento.departamento_id.asc())
        )
        return list(db.scalars(statement).all())

    def listar_equipe(self, db: Session, projeto_id: str) -> list[ProjetoEquipeMembro]:
        statement = (
            select(ProjetoEquipeMembro)
            .where(ProjetoEquipeMembro.projeto_id == projeto_id)
            .order_by(ProjetoEquipeMembro.usuario_id.asc())
        )
        return list(db.scalars(statement).all())

    # Versões em lote — uma query para a página inteira, em vez de N+1 ao serializar.

    def listar_responsavel_ids_em_lote(
        self, db: Session, projeto_ids: list[str]
    ) -> dict[str, list[str]]:
        return self._agrupar(
            db,
            projeto_ids,
            select(ProjetoResponsavel.projeto_id, ProjetoResponsavel.usuario_id).where(
                ProjetoResponsavel.projeto_id.in_(projeto_ids)
            ),
        )

    def listar_departamento_ids_em_lote(
        self, db: Session, projeto_ids: list[str]
    ) -> dict[str, list[str]]:
        return self._agrupar(
            db,
            projeto_ids,
            select(ProjetoDepartamento.projeto_id, ProjetoDepartamento.departamento_id).where(
                ProjetoDepartamento.projeto_id.in_(projeto_ids)
            ),
        )

    def listar_equipe_em_lote(
        self, db: Session, projeto_ids: list[str]
    ) -> dict[str, list[ProjetoEquipeMembro]]:
        if not projeto_ids:
            return {}
        statement = select(ProjetoEquipeMembro).where(
            ProjetoEquipeMembro.projeto_id.in_(projeto_ids)
        )
        agrupado: dict[str, list[ProjetoEquipeMembro]] = {pid: [] for pid in projeto_ids}
        for membro in db.scalars(statement).all():
            agrupado[membro.projeto_id].append(membro)
        for membros in agrupado.values():
            membros.sort(key=lambda m: m.usuario_id)
        return agrupado

    @staticmethod
    def _agrupar(db: Session, projeto_ids: list[str], statement) -> dict[str, list[str]]:
        if not projeto_ids:
            return {}
        agrupado: dict[str, list[str]] = {pid: [] for pid in projeto_ids}
        for projeto_id, valor in db.execute(statement).all():
            agrupado[projeto_id].append(valor)
        for valores in agrupado.values():
            valores.sort()
        return agrupado

    def adicionar_responsavel(self, db: Session, vinculo: ProjetoResponsavel) -> None:
        db.add(vinculo)
        db.flush()

    def remover_responsavel(self, db: Session, *, projeto_id: str, usuario_id: str) -> None:
        vinculo = db.get(ProjetoResponsavel, {"projeto_id": projeto_id, "usuario_id": usuario_id})
        if vinculo is not None:
            db.delete(vinculo)
            db.flush()

    def adicionar_departamento(self, db: Session, vinculo: ProjetoDepartamento) -> None:
        db.add(vinculo)
        db.flush()

    def remover_departamento(self, db: Session, *, projeto_id: str, departamento_id: str) -> None:
        vinculo = db.get(
            ProjetoDepartamento, {"projeto_id": projeto_id, "departamento_id": departamento_id}
        )
        if vinculo is not None:
            db.delete(vinculo)
            db.flush()

    def adicionar_membro(self, db: Session, vinculo: ProjetoEquipeMembro) -> None:
        db.add(vinculo)
        db.flush()

    def remover_membro(self, db: Session, *, projeto_id: str, usuario_id: str) -> None:
        vinculo = db.get(ProjetoEquipeMembro, {"projeto_id": projeto_id, "usuario_id": usuario_id})
        if vinculo is not None:
            db.delete(vinculo)
            db.flush()
