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
  /** `true` quando nada foi personalizado (aparência original do TaskFlow) */
  padrao: boolean;
  /** slug PÚBLICO da empresa dona desta marca (só no contexto por slug) — vai na URL do logo; nunca autoriza nada */
  slug?: string | null;
  /** nome de exibição PÚBLICO da empresa (fantasia ou razão) — identidade principal no ambiente tenant; nunca autoriza nada */
  nome?: string | null;
};

export type PersonalizacaoUpdatePayload = Partial<Pick<Branding, "corPrimaria" | "corSecundaria" | "tema">>;
