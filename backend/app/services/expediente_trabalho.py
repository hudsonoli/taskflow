"""Gate de TRABALHO (entrar em execução) — a ÚNICA autoridade de horário para começar a trabalhar.

Usada por `DemandaService` (PATCH, criar já em execução, restaurar) e por `SessaoTrabalhoService.abrir` (sessão pessoal nova). Nenhum outro lugar decide horário.
Janela de trabalho NOMINAL (`esta_dentro_janela_trabalho`), fuso da empresa, dias especiais; isentos (admin, gestor, conta de sistema, `acesso_fora_expediente`) passam;
regra desligada libera. Recusa = `DemandaForaDeExpedienteError` → 409 `FORA_DE_EXPEDIENTE` (o mesmo contrato de sempre).
"""

from sqlalchemy.orm import Session

from app.core.expediente import (
    JanelaDia,
    RegraExpediente,
    esta_dentro_janela_trabalho,
    janela_do_dia,
    momento_local,
    usuario_sujeito_ao_expediente,
)
from app.models.usuario import Usuario
from app.services.regra_expediente_service import RegraExpedienteService


class DemandaForaDeExpedienteError(ValueError):
    """Tentativa de entrar em execução fora do expediente. Vira 409 estruturado.

    Carrega a janela de HOJE (não a regra inteira — a Fase 2G.3 tornou a regra por dia da
    semana, e o que a interface precisa pra dizer "quando poderá" é só o dia corrente) para
    a interface conseguir dizer *quando* poderá — sem repetir a regra no cliente. `dia_hoje`
    pode estar com as quatro janelas em `None` quando o dia não é útil (ex.: fim de semana no
    padrão inicial).
    """

    def __init__(self, message: str, *, dia_hoje: JanelaDia, tolerancia_retomada_minutos: int) -> None:
        super().__init__(message)
        self.dia_hoje = dia_hoje
        self.tolerancia_retomada_minutos = tolerancia_retomada_minutos


def detalhe_409_fora_de_expediente(exc: DemandaForaDeExpedienteError) -> dict:
    """Corpo do 409 estruturado — o mesmo para PATCH/criar/restaurar e para abrir sessão. A janela vem do servidor para não haver duas fontes da mesma regra."""
    return {
        "code": "FORA_DE_EXPEDIENTE",
        "message": str(exc),
        "expediente": {
            # Janela de HOJE — pode vir tudo `None` quando o dia não é útil.
            "manhaInicio": exc.dia_hoje.manha_inicio,
            "manhaFim": exc.dia_hoje.manha_fim,
            "tardeInicio": exc.dia_hoje.tarde_inicio,
            "tardeFim": exc.dia_hoje.tarde_fim,
            "toleranciaRetomadaMinutos": exc.tolerancia_retomada_minutos,
        },
    }


def garantir_trabalho_permitido(
    db: Session,
    empresa_id: str,
    usuario: Usuario | None,
    *,
    regra_override: RegraExpediente | None = None,
    regra_service: RegraExpedienteService | None = None,
) -> None:
    """Levanta `DemandaForaDeExpedienteError` se `usuario` está SUJEITO à política e agora é fora da janela de trabalho. `usuario=None` (sessão puramente
    departamental, sem pessoa) é tratado como sujeito: não há isento para liberar. `regra_override` é o gancho dos testes (fixtures dentro/fora do expediente)."""
    if usuario is not None and not usuario_sujeito_ao_expediente(
        perfil_base=usuario.perfil_base,
        is_system_account=bool(usuario.is_system_account),
        acesso_fora_expediente=bool(usuario.acesso_fora_expediente),
    ):
        return
    regra = regra_override or (regra_service or RegraExpedienteService()).get_regra_calculo(db, empresa_id=empresa_id)
    agora = momento_local(None, regra)  # relógio da EMPRESA (fuso da regra), nunca o do navegador
    if esta_dentro_janela_trabalho(agora, regra=regra):
        return

    # Dia efetivo de hoje: 0, 1, 2 ou mais períodos, já com feriado/recesso/trabalho excepcional (Fase Expediente 1).
    dia_hoje = janela_do_dia(regra, agora.date())
    if not dia_hoje.ativo:
        mensagem = "Fora do expediente: hoje não é dia útil"
    else:
        faixas = [f"{inicio} às {fim}" for inicio, fim in dia_hoje.lista_periodos()]
        mensagem = "Fora do expediente: execução permitida das " + (
            faixas[0] if len(faixas) == 1 else ", das ".join(faixas[:-1]) + " e das " + faixas[-1]
        )
    raise DemandaForaDeExpedienteError(mensagem, dia_hoje=dia_hoje, tolerancia_retomada_minutos=regra.tolerancia_retomada_minutos)
