import { EMPRESA_PADRAO_ID } from "@/lib/ids";
import type { ConfiguracaoEmail } from "@/types/configuracao-email";

export { EMPRESA_PADRAO_ID };

export const configuracaoEmailMock: ConfiguracaoEmail = {
  id: "configuracao-email-padrao",
  empresaId: EMPRESA_PADRAO_ID,
  provedor: "manual",
  contaConectada: undefined,
  nomeExibicao: "",
  emailDisparo: "",
  servidorSmtp: "",
  portaSmtp: null,
  usuarioSmtp: "",
  senhaSmtp: "",
  usarSsl: true,
  ativo: false,
  createdAt: "2026-08-02T09:00:00-03:00",
  updatedAt: "2026-08-02T09:00:00-03:00",
};
