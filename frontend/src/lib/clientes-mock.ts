import { EMPRESA_PADRAO_ID, generateCodigoInterno, generateId } from "@/lib/ids";
import { responsaveisProjetoDisponiveis } from "@/lib/projetos-mock";
import { coresIdentificacaoDisponiveis, resolveCorIdentificacaoHex } from "@/lib/cores";
import { resolveTagIdPorNome } from "@/lib/grupos-cliente-mock";
import type { Cliente, ClienteHistoricoEvento, ClienteStatus, DocumentoTipo } from "@/types/cliente";
import clientesImportadosRaw from "@/lib/clientes-import.json";

export { EMPRESA_PADRAO_ID, generateCodigoInterno, generateId, responsaveisProjetoDisponiveis, coresIdentificacaoDisponiveis, resolveCorIdentificacaoHex };

export const statusClienteLabels: Record<ClienteStatus, string> = {
  ativo: "Ativo",
  suspenso: "Suspenso",
  inativo: "Inativo",
};

export const origensClienteDisponiveis = [
  "Indicação",
  "Prospecção ativa",
  "Site/Formulário",
  "Redes sociais",
  "Evento",
  "Outro",
];

export function detectDocumentType(rawValue: string): DocumentoTipo | null {
  const digits = rawValue.replace(/\D/g, "");
  if (digits.length === 11) return "cpf";
  if (digits.length === 14) return "cnpj";
  return null;
}

export function formatDocument(rawValue: string): string {
  const digits = rawValue.replace(/\D/g, "").slice(0, 14);

  if (digits.length <= 11) {
    return digits
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  }

  return digits
    .replace(/(\d{2})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1/$2")
    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
}

// Simula uma consulta de CNPJ (ex: Receita Federal). Sem integração real nesta fase.
export function mockDocumentoLookup(documento: string, tipo: DocumentoTipo): { nome: string; razaoSocial: string } {
  const digits = documento.replace(/\D/g, "");
  const sufixo = digits.slice(-4) || "0000";

  if (tipo === "cpf") {
    return { nome: `Cliente ${sufixo}`, razaoSocial: `Cliente ${sufixo}` };
  }
  return { nome: `Empresa ${sufixo}`, razaoSocial: `Empresa ${sufixo} Ltda` };
}

function criarHistorico(acao: string, seed: string): ClienteHistoricoEvento[] {
  return [
    {
      id: `hist-cliente-${seed}-1`,
      usuarioId: "user-1",
      usuario: "Hudson Cunha",
      acao,
      dataHora: "10/07/2026 09:15",
      ip: "192.168.1.10",
      dispositivo: "Chrome / Windows",
    },
  ];
}

const clientesDemo: Cliente[] = [
  {
    id: "cliente-1",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#1001",
    tipoDocumento: "cnpj",
    documento: "12.345.678/0001-90",
    nome: "Cliente Exemplo",
    razaoSocial: "Cliente Exemplo Ltda",
    email: "contato@clienteexemplo.com.br",
    whatsapp: "",
    cep: "",
    bairro: "",
    enderecoCompleto: "",
    cidade: "",
    uf: "",
    segmento: "",
    tagIds: [],
    origem: "Indicação",
    status: "ativo",
    responsavelComercialId: "user-4",
    clienteReferencial: true,
    contatos: [
      {
        id: "contato-cliente-1-1",
        nome: "Fernanda Ribeiro",
        email: "fernanda@clienteexemplo.com.br",
        telefone: "(62) 99999-0001",
        cargo: "Marketing",
        recebeEntregas: true,
      },
    ],
    avisarConclusaoPorEmail: true,
    feeMensal: 4500,
    horasContratadasMes: 40,
    observacoes: "",
    corIdentificacao: "blue",
    createdAt: "2026-07-01T09:00:00-03:00",
    updatedAt: "2026-07-10T11:18:00-03:00",
    historico: criarHistorico("Cliente criado", "1"),
  },
  {
    id: "cliente-2",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#1002",
    tipoDocumento: "cnpj",
    documento: "98.765.432/0001-10",
    nome: "Clínica Clare",
    razaoSocial: "Clínica Clare Ltda",
    email: "contato@clinicaclare.com.br",
    whatsapp: "",
    cep: "",
    bairro: "",
    enderecoCompleto: "",
    cidade: "",
    uf: "",
    segmento: "Saúde",
    tagIds: [],
    origem: "Site/Formulário",
    status: "suspenso",
    responsavelComercialId: "user-5",
    clienteReferencial: false,
    contatos: [],
    avisarConclusaoPorEmail: true,
    feeMensal: 2800,
    horasContratadasMes: 20,
    observacoes: "",
    corIdentificacao: "green",
    createdAt: "2026-07-02T10:00:00-03:00",
    updatedAt: "2026-07-11T08:50:00-03:00",
    historico: criarHistorico("Status alterado para Suspenso", "2"),
  },
  {
    id: "cliente-3",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#1003",
    tipoDocumento: "cnpj",
    documento: "11.222.333/0001-44",
    nome: "Loja Boxx",
    razaoSocial: "Loja Boxx Ltda",
    email: "contato@lojaboxx.com.br",
    whatsapp: "",
    cep: "",
    bairro: "",
    enderecoCompleto: "",
    cidade: "",
    uf: "",
    segmento: "Varejo",
    tagIds: [],
    origem: "Prospecção ativa",
    status: "ativo",
    responsavelComercialId: "user-2",
    clienteReferencial: false,
    contatos: [],
    avisarConclusaoPorEmail: true,
    feeMensal: 3200,
    horasContratadasMes: 30,
    observacoes: "",
    corIdentificacao: "orange",
    createdAt: "2026-06-01T08:45:00-03:00",
    updatedAt: "2026-06-30T17:40:00-03:00",
    historico: criarHistorico("Cliente criado", "3"),
  },
];

type ClienteImportadoRaw = Omit<Cliente, "tagIds" | "contatos" | "avisarConclusaoPorEmail"> & { tags: string[] };

// A planilha traz "tags" como nomes livres — resolvidos aqui para os tagIds
// do cadastro de Grupos de clientes (nunca usar nome como chave).
const clientesImportadosRawTyped = clientesImportadosRaw as ClienteImportadoRaw[];
const clientesImportados: Cliente[] = clientesImportadosRawTyped.map(({ tags, ...cliente }) => ({
  ...cliente,
  tagIds: tags.map((nome) => resolveTagIdPorNome(nome)).filter(Boolean),
  contatos: [],
  avisarConclusaoPorEmail: true,
}));

export const clientesMock: Cliente[] = [...clientesDemo, ...clientesImportados];

export function resolveResponsavelComercialNome(usuarioId: string): string {
  if (!usuarioId) return "Sem responsável";
  return responsaveisProjetoDisponiveis.find((usuario) => usuario.id === usuarioId)?.nome ?? usuarioId;
}
