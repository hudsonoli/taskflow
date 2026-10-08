import { NextResponse } from "next/server";
import { MENSAGENS_CONSULTA_CEP, URL_BRASILAPI_CEP, cepValido, mapearRespostaBrasilApiCep, somenteDigitos } from "@/lib/brasilApi";
import { chamarBrasilApi, exigirSessaoTenant, respostaDeFalha } from "@/lib/server/brasilApiBff";

// Consulta de CEP na BrasilAPI (pública, sem chave) — mesma infraestrutura do CNPJ (lib/server/brasilApiBff.ts). Exige sessão
// (não vira proxy aberto); só o CEP consultado sai daqui. Toda falha vira `{ falha, mensagem }`: o cadastro segue manual.
export async function GET(_request: Request, { params }: { params: Promise<{ cep: string }> }) {
  const semSessao = await exigirSessaoTenant();
  if (semSessao) return semSessao;

  const digitos = somenteDigitos((await params).cep);
  if (!cepValido(digitos)) return respostaDeFalha("invalido", MENSAGENS_CONSULTA_CEP);

  const resposta = await chamarBrasilApi(`${URL_BRASILAPI_CEP}/${digitos}`);
  if (!resposta.ok) return respostaDeFalha(resposta.falha, MENSAGENS_CONSULTA_CEP);
  const dados = mapearRespostaBrasilApiCep(resposta.corpo);
  return dados ? NextResponse.json({ dados }) : respostaDeFalha("nao_encontrado", MENSAGENS_CONSULTA_CEP);
}
