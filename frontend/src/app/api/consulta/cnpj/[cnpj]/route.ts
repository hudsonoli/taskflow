import { NextResponse } from "next/server";
import {
  MENSAGENS_CONSULTA,
  URL_BRASILAPI_CNPJ,
  cnpjValido,
  mapearRespostaBrasilApi,
  somenteDigitos,
} from "@/lib/brasilApi";
import { chamarBrasilApi, exigirSessaoTenant, respostaDeFalha } from "@/lib/server/brasilApiBff";

// Consulta de CNPJ na BrasilAPI (pública, sem chave): o navegador pede AQUI, nunca direto ao serviço externo (sem CORS, com
// timeout e erros normalizados — infraestrutura em lib/server/brasilApiBff.ts, compartilhada com o CEP). Exige sessão só para
// não virar proxy aberto; o único dado que sai é o CNPJ (público). Toda falha vira `{ falha, mensagem }`: o formulário segue manual.
export async function GET(_request: Request, { params }: { params: Promise<{ cnpj: string }> }) {
  const semSessao = await exigirSessaoTenant();
  if (semSessao) return semSessao;

  const digitos = somenteDigitos((await params).cnpj);
  if (!cnpjValido(digitos)) return respostaDeFalha("invalido", MENSAGENS_CONSULTA);

  const resposta = await chamarBrasilApi(`${URL_BRASILAPI_CNPJ}/${digitos}`);
  if (!resposta.ok) return respostaDeFalha(resposta.falha, MENSAGENS_CONSULTA);
  const dados = mapearRespostaBrasilApi(resposta.corpo);
  return dados ? NextResponse.json({ dados }) : respostaDeFalha("nao_encontrado", MENSAGENS_CONSULTA);
}
