from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.busca import interpretar_termo_busca
from app.models.fornecedor import Fornecedor

STATUS_ARQUIVADO = "arquivado"


class FornecedorRepository:
    """Só persistência e consultas — regras de duplicidade, transição, arquivamento e
    eventos ficam no service."""

    def create(self, db: Session, fornecedor: Fornecedor) -> Fornecedor:
        db.add(fornecedor)
        db.flush()
        return fornecedor

    def get_by_id(self, db: Session, fornecedor_id: str) -> Fornecedor | None:
        return db.get(Fornecedor, fornecedor_id)

    def get_by_codigo_interno(
        self, db: Session, *, empresa_id: str, codigo_interno: str
    ) -> Fornecedor | None:
        statement = select(Fornecedor).where(
            Fornecedor.empresa_id == empresa_id,
            Fornecedor.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_codigo_referencia(
        self, db: Session, *, empresa_id: str, codigo_referencia: str
    ) -> Fornecedor | None:
        statement = select(Fornecedor).where(
            Fornecedor.empresa_id == empresa_id,
            Fornecedor.codigo_referencia == codigo_referencia,
        )
        return db.scalars(statement).first()

    def listar_semelhantes(
        self,
        db: Session,
        *,
        empresa_id: str,
        nome_normalizado: str,
        documento_normalizado: str | None,
        excluir_id: str | None = None,
    ) -> list[Fornecedor]:
        """Candidatos a duplicidade — mesmo nome OU mesmo documento.

        Não existe UNIQUE de nome nem de documento (ver model): isto alimenta um AVISO,
        nunca um bloqueio. Inclui arquivados de propósito: recadastrar algo que já existe
        arquivado é exatamente o caso em que o operador precisa ser avisado.
        """
        condicoes = [Fornecedor.nome_normalizado == nome_normalizado]
        if documento_normalizado:
            condicoes.append(Fornecedor.documento_normalizado == documento_normalizado)

        statement = select(Fornecedor).where(Fornecedor.empresa_id == empresa_id, or_(*condicoes))
        if excluir_id:
            statement = statement.where(Fornecedor.id != excluir_id)
        return list(db.scalars(statement.order_by(Fornecedor.nome.asc())).all())

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Fornecedor]:
        statement = select(Fornecedor).where(Fornecedor.empresa_id == empresa_id)

        if status:
            statement = statement.where(Fornecedor.status == status)
        else:
            # Sem status explícito, arquivado fica oculto — filtro em SQL, antes da paginação.
            statement = statement.where(Fornecedor.status != STATUS_ARQUIVADO)

        # A decisão "isto é texto ou é documento?" mora INTEIRA em app/core/busca.py. Este
        # repository não extrai dígitos, não mede comprimento e não decide nada sobre o
        # termo: só traduz o TermoBusca já interpretado em condições SQL. Reimplementar a
        # regra aqui foi exatamente o que causou o incidente do Cliente, em que "QA FASE2B"
        # virou um ILIKE '%2%' sobre documento e devolveu quase a base inteira.
        termo = interpretar_termo_busca(search)
        if not termo.vazio:
            like = f"%{termo.texto}%"
            # Nome e os DOIS códigos. ILIKE cobre o case-insensitive por código
            # (f26000001 = F26000001). Nome nunca é identificador — é busca textual.
            condicoes = [
                Fornecedor.nome.ilike(like),
                Fornecedor.codigo_referencia.ilike(like),
                Fornecedor.codigo_interno.ilike(like),
            ]
            if termo.documento is not None:
                # Só quando o termo é plausivelmente um documento. Busca pela forma
                # normalizada, então "12345678000190" encontra "12.345.678/0001-90".
                condicoes.append(Fornecedor.documento_normalizado.ilike(f"%{termo.documento}%"))
            statement = statement.where(or_(*condicoes))

        statement = statement.order_by(Fornecedor.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Fornecedor]:
        """**Exclui arquivados** — divergência deliberada de ClienteRepository.list_diretorio.

        Cliente inclui arquivados porque Demanda e Projeto guardam referências históricas que
        precisam continuar resolvendo o nome. Nenhum domínio referencia fornecedor, então o
        diretório existe só para oferecer opções de vínculo novo, e arquivado nunca pode ser
        uma opção nova. Se um consumidor futuro precisar de resolução histórica, isso entra
        como parâmetro explícito (`incluir_arquivados`), nunca como padrão.
        """
        statement = (
            select(Fornecedor)
            .where(Fornecedor.empresa_id == empresa_id, Fornecedor.status != STATUS_ARQUIVADO)
            .order_by(Fornecedor.nome.asc())
        )
        return list(db.scalars(statement).all())

    def update(self, db: Session, fornecedor: Fornecedor) -> Fornecedor:
        db.add(fornecedor)
        db.flush()
        return fornecedor
