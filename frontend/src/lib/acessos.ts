// Auditoria de acesso (Configurações → Acesso) — evento de login → linha da tabela. Lógica PURA (testável com `node --test`).
//
// Os dados são gravados pelo SERVIDOR no login (IP original, navegador e sistema operacional lidos da requisição HTTP, região a partir de
// cabeçalhos de localização da Cloudflare, quando habilitados): a tela só EXIBE. Eventos antigos (anteriores à Fase 7E) não têm esses campos: o IP que
// gravaram pode ser o do proxy interno e o User-Agent era o do servidor — não são "corrigidos" nem inventados.
import { parseNavegador, parseSistemaOperacional } from "./user-agent.ts";
import type { AcessoLoginEvento, EventoApi } from "../types/acesso.ts";

export const TIPO_LOGIN_SUCESSO = "auth.login_sucesso";
export const TEXTO_NAO_DISPONIVEL = "Não disponível";
export const TEXTO_DESCONHECIDO = "Desconhecido";

function texto(valor: unknown): string | null {
  return typeof valor === "string" && valor.trim() !== "" ? valor.trim() : null;
}

export function resolverAcessoLogin(evento: EventoApi): AcessoLoginEvento {
  const payload = evento.payload ?? {};
  const userAgentLegado = texto(payload.user_agent); // só eventos antigos o têm
  return {
    id: evento.id,
    usuarioId: evento.usuarioId,
    nome: texto(payload.nome) ?? "Usuário desconhecido",
    ip: texto(payload.ip_address),
    regiao: texto(payload.regiao),
    // novo: valores já resolvidos pelo servidor; antigo: cai no parser sobre o User-Agent que o evento guardou
    navegador: texto(payload.navegador) ?? (userAgentLegado ? parseNavegador(userAgentLegado) : TEXTO_DESCONHECIDO),
    sistemaOperacional:
      texto(payload.sistema_operacional) ?? (userAgentLegado ? parseSistemaOperacional(userAgentLegado) : TEXTO_DESCONHECIDO),
    ocorridoEm: evento.occurredAt,
  };
}

export function rotuloRegiao(acesso: Pick<AcessoLoginEvento, "regiao">): string {
  return acesso.regiao ?? TEXTO_NAO_DISPONIVEL;
}
