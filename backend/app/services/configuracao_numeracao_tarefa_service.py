"""Leitura do estado da numeração operacional de Demanda/Tarefa (Fase 2G.8B).

Estritamente read-only: nunca chama `reservar_proximo_operacional` (que consumiria/
incrementaria o contador de verdade) nem duplica esse algoritmo — só lê o valor atual de
`sequencias_operacionais` e o maior `numero_operacional` já emitido em `demandas`, monta o
DTO e calcula os dois campos derivados (`proximoNumeroEstimado`, `consistente`).

Não representa `codigo_referencia`/`sequencias_referencia` (esse é outro domínio, com prefixo
de letra e reinício anual) — só o contador contínuo de Demanda, que é o que a interface chama
de "Tarefa" e exibe como `#2063` no dia a dia (ver Fase 2G.8A, achado central).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.demanda_repository import DemandaRepository
from app.repositories.sequencia_operacional_repository import SequenciaOperacionalRepository
from app.schemas.configuracao_numeracao_tarefa import ConfiguracaoNumeracaoTarefaRead

# Mesma lista fechada de app/core/sequencias_operacionais.py (TIPOS_COM_NUMERO_OPERACIONAL) —
# hoje só "demanda" tem número operacional; não generalizar antes de existir um segundo caso.
TIPO_ENTIDADE_DEMANDA = "demanda"
ROTULO_ENTIDADE = "Tarefa"
FORMATO_EXIBICAO = "#<numero>"


class ConfiguracaoNumeracaoTarefaService:
    def __init__(
        self,
        sequencia_repository: SequenciaOperacionalRepository | None = None,
        demanda_repository: DemandaRepository | None = None,
    ) -> None:
        self.sequencia_repository = sequencia_repository or SequenciaOperacionalRepository()
        self.demanda_repository = demanda_repository or DemandaRepository()

    def obter(self, db: Session, *, empresa_id: str) -> ConfiguracaoNumeracaoTarefaRead:
        contador_atual = (
            self.sequencia_repository.get_ultimo_numero(
                db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE_DEMANDA
            )
            or 0
        )
        maior_numero_emitido = self.demanda_repository.maior_numero_operacional(db, empresa_id)

        # `>=`, não `==`: o contador pode ter sido inicializado via CLI acima do que já foi
        # emitido pelo próprio TaskFloww (continuidade com um sistema anterior) — isso é
        # esperado, não uma anomalia. Só `contador < maior_emitido` é inconsistência real
        # (ver Fase 2G.8B, kickoff item 5). Nunca corrigido automaticamente aqui — só
        # informado; correção é intervenção administrativa manual, fora desta tela.
        consistente = maior_numero_emitido is None or contador_atual >= maior_numero_emitido

        return ConfiguracaoNumeracaoTarefaRead(
            entidade=TIPO_ENTIDADE_DEMANDA,
            rotuloEntidade=ROTULO_ENTIDADE,
            contadorAtual=contador_atual,
            proximoNumeroEstimado=contador_atual + 1,
            maiorNumeroEmitido=maior_numero_emitido,
            consistente=consistente,
            formatoExibicao=FORMATO_EXIBICAO,
            gerenciadoAutomaticamente=True,
        )
