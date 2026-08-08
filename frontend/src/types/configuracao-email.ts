export type ProvedorEmail = "google" | "m365" | "manual";

export type ConfiguracaoEmail = {
  id: string;
  empresaId: string;
  provedor: ProvedorEmail;
  // Preenchido apenas quando a conta é conectada via Google/M365 (simulado — sem OAuth real nesta fase).
  contaConectada?: string;
  nomeExibicao: string;
  emailDisparo: string;
  servidorSmtp: string;
  portaSmtp: number | null;
  usuarioSmtp: string;
  senhaSmtp: string;
  usarSsl: boolean;
  ativo: boolean;
  createdAt: string;
  updatedAt: string;
};

export type ConfiguracaoEmailFormDraft = Pick<
  ConfiguracaoEmail,
  "nomeExibicao" | "emailDisparo" | "servidorSmtp" | "portaSmtp" | "usuarioSmtp" | "senhaSmtp" | "usarSsl"
>;
