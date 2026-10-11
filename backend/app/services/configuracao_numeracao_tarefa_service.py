"""Numeração operacional de Demanda/Tarefa — estado e configuração do FORMATO das próximas emissões (Fase 2G.8B → 7D.1).

- `obter` é somente leitura: nunca chama `reservar_proximo_*` (que consumiria o contador).
- `atualizar` muda só o FORMATO das próximas emissões e/ou o PRÓXIMO número. Nunca toca em demanda existente: o identificador
  emitido (`demandas.identificador`) é imutável — `#845` continua `#845` depois de a empresa passar a emitir `BOX-2026-00846`.
- Concorrência: o PATCH trava a MESMA linha de `sequencias_operacionais` que a emissão trava (`SELECT ... FOR UPDATE`) e valida o
  próximo número contra o maior emitido já definitivo, na mesma transação.

Não representa `codigo_referencia`/`sequencias_referencia` (outro domínio, com prefixo de letra e reinício anual).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.numeracao_formato import (
    FormatoNumeracao,
    FormatoNumeracaoInvalidoError,
    descrever_formato,
    formatar_identificador,
    validar_formato,
)
from app.core.relogio import agora_utc, ano_corrente
from app.repositories.demanda_repository import DemandaRepository
from app.repositories.sequencia_operacional_repository import SequenciaOperacionalRepository
from app.schemas.configuracao_numeracao_tarefa import ConfiguracaoNumeracaoTarefaRead, ConfiguracaoNumeracaoTarefaUpdate

# Mesma lista fechada de app/core/sequencias_operacionais.py (TIPOS_COM_NUMERO_OPERACIONAL) —
# hoje só "demanda" tem número operacional; não generalizar antes de existir um segundo caso.
TIPO_ENTIDADE_DEMANDA = "demanda"
ROTULO_ENTIDADE = "Tarefa"


class ProximoNumeroInvalidoError(ValueError):
    """Próximo número que colidiria com o histórico (mensagem pronta para o usuário)."""


class ConfiguracaoNumeracaoTarefaService:
    def __init__(
        self,
        sequencia_repository: SequenciaOperacionalRepository | None = None,
        demanda_repository: DemandaRepository | None = None,
    ) -> None:
        self.sequencia_repository = sequencia_repository or SequenciaOperacionalRepository()
        self.demanda_repository = demanda_repository or DemandaRepository()

    def obter(self, db: Session, *, empresa_id: str) -> ConfiguracaoNumeracaoTarefaRead:
        linha = self.sequencia_repository.get_linha(db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE_DEMANDA)
        contador_atual = linha.ultimo_numero if linha is not None else 0
        formato = (
            FormatoNumeracao(
                prefixo=linha.prefixo, separador=linha.separador, incluir_ano=linha.incluir_ano, digitos=linha.digitos
            )
            if linha is not None
            else FormatoNumeracao()
        )
        maior_numero_emitido, sem_identificador = self.demanda_repository.estatisticas_numeracao(db, empresa_id)
        return self._montar(contador_atual, formato, maior_numero_emitido, sem_identificador)

    def atualizar(
        self, db: Session, *, empresa_id: str, data: ConfiguracaoNumeracaoTarefaUpdate
    ) -> ConfiguracaoNumeracaoTarefaRead:
        try:
            linha = self.sequencia_repository.travar_linha(db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE_DEMANDA)
            formato = validar_formato(
                FormatoNumeracao(
                    prefixo=linha.prefixo if data.prefixo is None else data.prefixo,
                    separador=linha.separador if data.separador is None else data.separador,
                    incluir_ano=linha.incluir_ano if data.incluir_ano is None else data.incluir_ano,
                    digitos=linha.digitos if data.digitos is None else data.digitos,
                )
            )
            # Maior emitido lido DEPOIS do lock: uma emissão em curso já commitou (ou ainda não começou).
            maior_numero_emitido, sem_identificador = self.demanda_repository.estatisticas_numeracao(db, empresa_id)

            if data.proximo_numero is not None:
                minimo = (maior_numero_emitido or 0) + 1
                if data.proximo_numero < minimo:
                    raise ProximoNumeroInvalidoError(
                        f"O próximo número precisa ser pelo menos {minimo}: já existem tarefas até o número "
                        f"{maior_numero_emitido}, e reutilizar um número emitido geraria duplicidade."
                    )
                linha.ultimo_numero = data.proximo_numero - 1

            linha.prefixo = formato.prefixo
            linha.separador = formato.separador
            linha.incluir_ano = formato.incluir_ano
            linha.digitos = formato.digitos
            linha.updated_at = agora_utc()
            db.commit()
            return self._montar(linha.ultimo_numero, formato, maior_numero_emitido, sem_identificador)
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _montar(
        contador_atual: int, formato: FormatoNumeracao, maior_numero_emitido: int | None, sem_identificador: int
    ) -> ConfiguracaoNumeracaoTarefaRead:
        proximo = contador_atual + 1
        # `>=`, não `==`: o contador pode ter sido inicializado acima do que o TaskFlow emitiu (continuidade com um sistema
        # anterior) — esperado. Inconsistência real: sequência ATRÁS do maior emitido (reemitiria um número) ou tarefa sem
        # identificador. Nunca corrigido automaticamente aqui — só informado.
        motivo = None
        if maior_numero_emitido is not None and contador_atual < maior_numero_emitido:
            motivo = "O contador está atrás do maior número emitido: a próxima emissão colidiria com uma tarefa existente."
        elif sem_identificador:
            motivo = f"{sem_identificador} tarefa(s) sem identificador gravado."
        return ConfiguracaoNumeracaoTarefaRead(
            entidade=TIPO_ENTIDADE_DEMANDA,
            rotuloEntidade=ROTULO_ENTIDADE,
            contadorAtual=contador_atual,
            proximoNumero=proximo,
            proximoNumeroEstimado=proximo,
            maiorNumeroEmitido=maior_numero_emitido,
            consistente=motivo is None,
            motivoInconsistencia=motivo,
            formatoExibicao=descrever_formato(formato),
            gerenciadoAutomaticamente=True,
            prefixo=formato.prefixo,
            separador=formato.separador,
            incluirAno=formato.incluir_ano,
            digitos=formato.digitos,
            preview=formatar_identificador(formato, proximo, ano_corrente()),
        )


__all__ = [
    "ConfiguracaoNumeracaoTarefaService",
    "FormatoNumeracaoInvalidoError",
    "ProximoNumeroInvalidoError",
]
