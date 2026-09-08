// Shape real de ConfiguracaoEmailRead (backend, Fase 2G.7B1) — camelCase via alias Pydantic,
// sem mapeamento manual no client. Singleton por Empresa: `id`/`createdAt`/`updatedAt` são
// `null` quando a Empresa ainda não salvou nada (GET devolve um DTO virtual, sem criar linha
// nenhuma — nunca interpretar `id === null` como erro).
//
// Nunca existe `smtpSenha`/`smtpSenhaCriptografada` aqui: o backend nunca devolve o segredo,
// só o booleano `smtpSenhaConfigurada`.
export type ConfiguracaoEmailRead = {
  id: string | null;
  smtpHost: string | null;
  smtpPort: number | null;
  smtpUsuario: string | null;
  smtpSenhaConfigurada: boolean;
  remetenteEmail: string | null;
  remetenteNome: string | null;
  usarTls: boolean;
  usarSsl: boolean;
  ativo: boolean;
  createdAt: string | null;
  updatedAt: string | null;
};

// Draft do formulário — usa "" internamente pros inputs (que exigem string), nunca enviado à
// API como "": a fronteira de escrita mapeia "" -> null em `configuracaoEmailDraftParaPayload`
// (api-backend.ts). `smtpPort` fica string aqui pelo mesmo motivo (input controlado vazio).
//
// `smtpSenha` tem semântica própria, diferente dos demais campos — três estados, nunca dois:
// - `""` (nunca enviado): campo em branco, sem intenção de mexer na senha — omitido do
//   payload, preserva o que já está salvo;
// - string não vazia: substitui o segredo;
// - a REMOÇÃO explícita não é representada por uma string aqui — é a flag `removerSenha`
//   abaixo, que vira `smtpSenha: null` só no payload (nunca `""`, que o backend rejeita com
//   422 — ver Fase 2G.7B1, kickoff 2G.7B2 item 11).
export type ConfiguracaoEmailFormDraft = {
  smtpHost: string;
  smtpPort: string;
  smtpUsuario: string;
  smtpSenha: string;
  removerSenha: boolean;
  remetenteEmail: string;
  remetenteNome: string;
  usarTls: boolean;
  usarSsl: boolean;
  ativo: boolean;
};

// Motivos finitos do teste de conexão (Fase 2G.7B1) — nunca inventar um motivo fora desta
// lista; o backend só devolve um destes dez.
export type ConfiguracaoEmailTesteMotivo =
  | "sucesso"
  | "configuracao_incompleta"
  | "dns_falhou"
  | "host_bloqueado"
  | "timeout"
  | "autenticacao_invalida"
  | "tls_invalido"
  | "conexao_recusada"
  | "erro_smtp"
  | "erro_desconhecido";

export type ConfiguracaoEmailTesteResultado = {
  sucesso: boolean;
  motivo: ConfiguracaoEmailTesteMotivo;
  mensagem: string;
};
