// Personalização visual da Empresa (Configurações → Personalizar). Mesmo shape da API
// (`PersonalizacaoRead`, camelCase via alias Pydantic) — leitura administrativa e pública são idênticas e não
// trazem ids nem caminhos do servidor.
export type TemaVisual = "claro" | "escuro";

export type Branding = {
  corPrimaria: string;
  corSecundaria: string;
  tema: TemaVisual;
  logoDisponivel: boolean;
  /** muda a cada troca de logo — vai na URL para quebrar o cache do navegador */
  logoVersao: string | null;
  /** `true` quando nada foi personalizado (aparência original do TaskFloww) */
  padrao: boolean;
  /** slug PÚBLICO da empresa dona desta marca (só no contexto por slug) — vai na URL do logo; nunca autoriza nada */
  slug?: string | null;
};

export type PersonalizacaoUpdatePayload = Partial<Pick<Branding, "corPrimaria" | "corSecundaria" | "tema">>;
