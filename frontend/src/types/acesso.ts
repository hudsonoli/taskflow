// Evento de auditoria — formato genérico devolvido por GET /eventos no backend real.
export type EventoApi = {
  id: string;
  empresaId: string;
  agenciaId: string | null;
  tipo: string;
  entidadeTipo: string;
  entidadeId: string;
  usuarioId: string | null;
  payload: Record<string, unknown>;
  occurredAt: string;
  createdAt: string;
};

// Login bem-sucedido, já resolvido para exibição no módulo Acesso.
export type AcessoLoginEvento = {
  id: string;
  usuarioId: string | null;
  nome: string;
  /** IP público/original do cliente, resolvido pelo servidor (eventos antigos podem ter o IP interno do proxy). */
  ip: string | null;
  /** Região aproximada do IP (cabeçalhos da Cloudflare, quando habilitados); `null` = "Não disponível". */
  regiao: string | null;
  navegador: string;
  sistemaOperacional: string;
  ocorridoEm: string;
};
