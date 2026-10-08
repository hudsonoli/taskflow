// Consulta de CNPJ na BrasilAPI (integração PÚBLICA: sem chave nem segredo) — lógica compartilhada por Clientes e
// Fornecedores. Parte pura (sem React, sem `server-only`), testável com `node --test`:
//
//   • validação/normalização do CNPJ (14 dígitos, dígitos verificadores) — só CNPJ válido é consultado; CPF nunca;
//   • mapeamento da resposta da BrasilAPI → `DadosConsultaCnpj` (só propriedades conhecidas, tudo opcional);
//   • classificação das falhas (inválido, não encontrado, limite, indisponível, tempo esgotado, rede);
//   • `camposParaFormulario`: devolve SÓ o que veio preenchido — valor vazio/null da API nunca apaga o que a pessoa digitou.
//
// A chamada à internet sai pela rota BFF `/api/consulta/cnpj/<cnpj>` (sem CORS, com timeout e erros normalizados); o
// navegador nunca fala direto com a BrasilAPI. A consulta é um auxílio: se falhar, o cadastro manual segue intacto.

export type DadosConsultaCnpj = {
  razaoSocial: string | null;
  nomeFantasia: string | null;
  cep: string | null;
  bairro: string | null;
  /** "Rua X, 123 - Sala 4" — o formato do campo único "Endereço (rua, número e complemento)" */
  enderecoCompleto: string | null;
  cidade: string | null;
  uf: string | null;
  telefone: string | null;
  email: string | null;
};

export type FalhaConsulta = "invalido" | "nao_encontrado" | "limite" | "indisponivel" | "timeout" | "rede";

export type ResultadoConsulta = { ok: true; dados: DadosConsultaCnpj } | { ok: false; falha: FalhaConsulta; mensagem: string };

export const MENSAGENS_CONSULTA: Record<FalhaConsulta, string> = {
  invalido: "Informe um CNPJ válido para buscar os dados.",
  nao_encontrado: "Não foi possível localizar os dados desse CNPJ. Você pode preencher manualmente.",
  limite: "Muitas consultas em pouco tempo. Aguarde alguns segundos e tente de novo, ou preencha manualmente.",
  indisponivel: "O serviço de consulta de CNPJ está indisponível agora. Você pode preencher manualmente.",
  timeout: "A consulta demorou demais e foi interrompida. Tente de novo ou preencha manualmente.",
  rede: "Não foi possível consultar agora (sem conexão com o serviço). Você pode preencher manualmente.",
};

export const URL_BRASILAPI_CNPJ = "https://brasilapi.com.br/api/cnpj/v1";
// A BrasilAPI recusa (403) clientes sem User-Agent identificável (o padrão do Node/Python cai nesse filtro).
export const USER_AGENT_CONSULTA = "TaskFloww/1.0";
export const TIMEOUT_SERVIDOR_MS = 8_000;
export const TIMEOUT_CLIENTE_MS = 12_000;

export function somenteDigitos(valor: string): string {
  return valor.replace(/\D/g, "");
}

/** CNPJ válido: 14 dígitos, não todos iguais, com os dois dígitos verificadores corretos. Aceita máscara. */
export function cnpjValido(valor: string): boolean {
  const digitos = somenteDigitos(valor);
  if (digitos.length !== 14 || /^(\d)\1{13}$/.test(digitos)) return false;
  const calcular = (base: string): number => {
    const pesos = base.length === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const soma = [...base].reduce((acc, d, i) => acc + Number(d) * pesos[i], 0);
    const resto = soma % 11;
    return resto < 2 ? 0 : 11 - resto;
  };
  const d1 = calcular(digitos.slice(0, 12));
  const d2 = calcular(digitos.slice(0, 12) + String(d1));
  return digitos.endsWith(`${d1}${d2}`);
}

function texto(valor: unknown, max = 255): string | null {
  if (typeof valor !== "string") return null;
  const limpo = valor.replace(/\s+/g, " ").trim();
  return limpo ? limpo.slice(0, max) : null;
}

function formatarCep(valor: unknown): string | null {
  const digitos = typeof valor === "string" || typeof valor === "number" ? somenteDigitos(String(valor)) : "";
  return digitos.length === 8 ? `${digitos.slice(0, 5)}-${digitos.slice(5)}` : null;
}

function formatarTelefone(valor: unknown): string | null {
  const digitos = typeof valor === "string" || typeof valor === "number" ? somenteDigitos(String(valor)) : "";
  if (digitos.length === 10) return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 6)}-${digitos.slice(6)}`;
  if (digitos.length === 11) return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 7)}-${digitos.slice(7)}`;
  return null;
}

/** Resposta de `GET /api/cnpj/v1/{cnpj}` → dados do formulário. `null` se o corpo não é um objeto reconhecível. */
export function mapearRespostaBrasilApi(bruto: unknown): DadosConsultaCnpj | null {
  if (!bruto || typeof bruto !== "object" || Array.isArray(bruto)) return null;
  const r = bruto as Record<string, unknown>;
  const razaoSocial = texto(r.razao_social);
  const nomeFantasia = texto(r.nome_fantasia);
  if (!razaoSocial && !nomeFantasia) return null; // sem nome nenhum não é um cadastro utilizável

  const logradouro = [texto(r.descricao_tipo_logradouro, 40), texto(r.logradouro)].filter(Boolean).join(" ");
  const numeroBruto = texto(r.numero, 20);
  const numero = numeroBruto && /^S\/?N$/i.test(numeroBruto) ? "S/N" : numeroBruto; // "SN" = sem número
  const complemento = texto(r.complemento, 120);
  let enderecoCompleto: string | null = null;
  if (logradouro) {
    enderecoCompleto = logradouro;
    if (numero) enderecoCompleto += `, ${numero}`;
    if (complemento) enderecoCompleto += ` - ${complemento}`;
  }
  const uf = texto(r.uf, 2)?.toUpperCase() ?? null;
  return {
    razaoSocial,
    nomeFantasia,
    cep: formatarCep(r.cep),
    bairro: texto(r.bairro),
    enderecoCompleto,
    cidade: texto(r.municipio),
    uf: uf && /^[A-Z]{2}$/.test(uf) ? uf : null,
    telefone: formatarTelefone(r.ddd_telefone_1),
    email: texto(r.email)?.toLowerCase() ?? null,
  };
}

/** Status HTTP da BrasilAPI → falha normalizada (usado pela rota BFF). 2xx não é falha. */
export function falhaPorStatus(status: number): FalhaConsulta {
  if (status === 400 || status === 404 || status === 422) return "nao_encontrado";
  if (status === 429) return "limite";
  return "indisponivel";
}

export type CamposDoFormulario = Partial<{
  nome: string;
  razaoSocial: string;
  email: string;
  telefone: string;
  cep: string;
  bairro: string;
  enderecoCompleto: string;
  cidade: string;
  uf: string;
}>;

/**
 * Campos que a consulta pode preencher no formulário — SÓ os que vieram com valor (vazio/null da API nunca substitui o
 * que já está no formulário). `nome` ("como é chamado") usa o nome fantasia e, sem ele, a razão social. `uf` só entra
 * se for uma das opções do formulário. Cada formulário usa apenas as chaves que realmente existem no seu rascunho.
 */
export function camposParaFormulario(dados: DadosConsultaCnpj, ufsValidas: readonly string[]): CamposDoFormulario {
  const campos: CamposDoFormulario = {};
  const nome = dados.nomeFantasia ?? dados.razaoSocial;
  if (nome) campos.nome = nome;
  if (dados.razaoSocial) campos.razaoSocial = dados.razaoSocial;
  if (dados.email) campos.email = dados.email;
  if (dados.telefone) campos.telefone = dados.telefone;
  if (dados.cep) campos.cep = dados.cep;
  if (dados.bairro) campos.bairro = dados.bairro;
  if (dados.enderecoCompleto) campos.enderecoCompleto = dados.enderecoCompleto;
  if (dados.cidade) campos.cidade = dados.cidade;
  if (dados.uf && ufsValidas.includes(dados.uf)) campos.uf = dados.uf;
  return campos;
}

type Fetch = (entrada: string, init?: RequestInit) => Promise<Response>;

/**
 * Consulta um CNPJ pelo BFF. Nunca lança: toda falha vira `{ ok: false, falha, mensagem }`. CNPJ inválido nem sai do
 * navegador. Cancelável por timeout (aborta a requisição) e por rede indisponível.
 */
export async function consultarCnpj(
  valor: string,
  opcoes: { fetchImpl?: Fetch; timeoutMs?: number } = {},
): Promise<ResultadoConsulta> {
  const falhar = (falha: FalhaConsulta): ResultadoConsulta => ({ ok: false, falha, mensagem: MENSAGENS_CONSULTA[falha] });
  if (!cnpjValido(valor)) return falhar("invalido");

  const fetchImpl: Fetch = opcoes.fetchImpl ?? ((entrada, init) => fetch(entrada, init));
  const controlador = new AbortController();
  const temporizador = setTimeout(() => controlador.abort(), opcoes.timeoutMs ?? TIMEOUT_CLIENTE_MS);
  try {
    const resposta = await fetchImpl(`/api/consulta/cnpj/${somenteDigitos(valor)}`, { cache: "no-store", signal: controlador.signal });
    if (resposta.ok) {
      const corpo = (await resposta.json().catch(() => null)) as { dados?: unknown } | null;
      const dados = mapearDadosJaNormalizados(corpo?.dados);
      return dados ? { ok: true, dados } : falhar("nao_encontrado");
    }
    const corpo = (await resposta.json().catch(() => null)) as { falha?: unknown } | null;
    const falha = corpo?.falha;
    if (falha === "invalido" || falha === "nao_encontrado" || falha === "limite" || falha === "indisponivel" || falha === "timeout" || falha === "rede") {
      return falhar(falha);
    }
    return falhar(falhaPorStatus(resposta.status));
  } catch (erro) {
    const abortou = erro instanceof Error && (erro.name === "AbortError" || erro.name === "TimeoutError");
    return falhar(abortou ? "timeout" : "rede");
  } finally {
    clearTimeout(temporizador);
  }
}

/** O BFF já devolve `DadosConsultaCnpj`; revalida o formato para nunca confiar às cegas no que chega ao formulário. */
function mapearDadosJaNormalizados(bruto: unknown): DadosConsultaCnpj | null {
  if (!bruto || typeof bruto !== "object") return null;
  const d = bruto as Record<string, unknown>;
  const campo = (valor: unknown): string | null => (typeof valor === "string" && valor.trim() ? valor : null);
  const dados: DadosConsultaCnpj = {
    razaoSocial: campo(d.razaoSocial),
    nomeFantasia: campo(d.nomeFantasia),
    cep: campo(d.cep),
    bairro: campo(d.bairro),
    enderecoCompleto: campo(d.enderecoCompleto),
    cidade: campo(d.cidade),
    uf: campo(d.uf),
    telefone: campo(d.telefone),
    email: campo(d.email),
  };
  return dados.razaoSocial || dados.nomeFantasia ? dados : null;
}
