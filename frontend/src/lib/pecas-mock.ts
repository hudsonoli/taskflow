import { EMPRESA_PADRAO_ID, generateId } from "@/lib/ids";
import type { Peca } from "@/types/peca";
import pecasImportadasRaw from "@/lib/pecas-import.json";

export { EMPRESA_PADRAO_ID, generateId };

export const categoriasPecaDisponiveis = ["Digital", "Impresso", "Vídeo", "Mídia paga", "Conteúdo"];

/** Entrada de tempo: "2:30" | "2h30" | "2,5" | "150m" → minutos (inválido → null). */
export function parseHoursInput(value: string): number | null {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return null;

  const hourMinuteMatch = trimmed.match(/^(\d+)\s*[:h]\s*(\d{1,2})?$/);
  if (hourMinuteMatch) return Number(hourMinuteMatch[1]) * 60 + Number(hourMinuteMatch[2] ?? 0);

  const minuteMatch = trimmed.match(/^(\d+)\s*m(in)?$/);
  if (minuteMatch) return Number(minuteMatch[1]);

  const decimal = Number(trimmed.replace(",", "."));
  if (Number.isFinite(decimal) && decimal >= 0) return Math.round(decimal * 60);

  return null;
}

export function formatHoursMinutes(minutes: number | null): string {
  if (minutes === null || minutes <= 0) return "";
  const rounded = Math.max(0, Math.round(minutes));
  return `${Math.floor(rounded / 60)}:${String(rounded % 60).padStart(2, "0")}`;
}

export function parseValorInput(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const normalized = trimmed.includes(",") ? trimmed.replace(/\./g, "").replace(",", ".") : trimmed;
  const num = Number(normalized.replace(/[R$\s]/g, ""));
  return Number.isFinite(num) ? Math.round(num * 100) : null;
}

export function formatValorInput(centavos: number | null): string {
  if (centavos === null) return "";
  return (centavos / 100).toFixed(2).replace(".", ",");
}

export function formatBRL(centavos: number): string {
  return (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/** Soma dos valores de sindicato (Criação + Adaptação + Finalização) — 0 quando desativado. */
export function valorSindicatoTotalCentavos(peca: Peca): number {
  if (!peca.sindicatoAtivo) return 0;
  return (
    (peca.valorSindicatoCriacaoCentavos ?? 0) +
    (peca.valorSindicatoAdaptacaoCentavos ?? 0) +
    (peca.valorSindicatoFinalizacaoCentavos ?? 0)
  );
}

function criarPeca(seed: string, patch: Partial<Peca>): Peca {
  return {
    id: `peca-${seed}`,
    empresaId: EMPRESA_PADRAO_ID,
    nome: "",
    categoria: "",
    tempoEstimadoMinutos: null,
    tempoMedioMinutos: null,
    tempoCalculadoExecucaoMinutos: null,
    valorTabelaCentavos: null,
    sindicatoAtivo: false,
    valorSindicatoCriacaoCentavos: null,
    valorSindicatoAdaptacaoCentavos: null,
    valorSindicatoFinalizacaoCentavos: null,
    briefingPadrao: "",
    ativa: true,
    createdAt: "2026-07-01T09:00:00-03:00",
    updatedAt: "2026-07-01T09:00:00-03:00",
    ...patch,
  };
}

const pecasDemo: Peca[] = [
  criarPeca("1", {
    nome: "Post feed",
    categoria: "Digital",
    tempoEstimadoMinutos: 90,
    valorTabelaCentavos: 25000,
    briefingPadrao: "Formato 1080x1350px. Seguir identidade visual da marca. Incluir CTA claro.",
  }),
  criarPeca("2", {
    nome: "Stories (sequência de 3)",
    categoria: "Digital",
    tempoEstimadoMinutos: 60,
    valorTabelaCentavos: 18000,
    briefingPadrao: "Formato 1080x1920px. Sequência narrativa curta, com CTA no último quadro.",
  }),
  criarPeca("3", {
    nome: "Carrossel (5 slides)",
    categoria: "Digital",
    tempoEstimadoMinutos: 150,
    valorTabelaCentavos: 45000,
    briefingPadrao: "5 a 7 slides. Primeiro slide precisa reter atenção (hook). Último slide com CTA.",
  }),
  criarPeca("4", {
    nome: "VT 30s",
    categoria: "Vídeo",
    tempoEstimadoMinutos: 480,
    tempoMedioMinutos: 540,
    valorTabelaCentavos: 350000,
    sindicatoAtivo: true,
    valorSindicatoCriacaoCentavos: 50000,
    valorSindicatoFinalizacaoCentavos: 20000,
    briefingPadrao: "Roteiro aprovado previamente. Entregar em 16:9 e 9:16. Legendas embutidas.",
  }),
  criarPeca("5", {
    nome: "Banner digital",
    categoria: "Digital",
    tempoEstimadoMinutos: 45,
    valorTabelaCentavos: 15000,
    briefingPadrao: "Entregar nos formatos padrão de mídia (300x250, 728x90, 320x50).",
  }),
  criarPeca("6", {
    nome: "Landing page",
    categoria: "Digital",
    tempoEstimadoMinutos: 600,
    valorTabelaCentavos: 480000,
    briefingPadrao: "Wireframe aprovado previamente. Responsivo. Integração com formulário de captação.",
  }),
  criarPeca("7", {
    nome: "E-mail marketing",
    categoria: "Digital",
    tempoEstimadoMinutos: 120,
    valorTabelaCentavos: 30000,
    briefingPadrao: "Layout responsivo. Testar em principais clientes de e-mail antes do envio.",
  }),
  criarPeca("8", {
    nome: "Anúncio impresso (página inteira)",
    categoria: "Impresso",
    tempoEstimadoMinutos: 180,
    tempoMedioMinutos: 210,
    valorTabelaCentavos: 60000,
    sindicatoAtivo: true,
    valorSindicatoCriacaoCentavos: 15000,
    briefingPadrao: "Entregar em alta resolução (300dpi), CMYK, com sangria de 3mm.",
    ativa: false,
  }),
  criarPeca("9", {
    nome: "Configuração de campanha de mídia paga",
    categoria: "Mídia paga",
    tempoEstimadoMinutos: 120,
    valorTabelaCentavos: 40000,
    briefingPadrao: "Definir segmentação, verba diária, canais e período conforme plano de mídia aprovado.",
  }),
];

type PecaImportadaRaw = Omit<Peca, "tempoMedioMinutos" | "tempoCalculadoExecucaoMinutos" | "sindicatoAtivo">;

// A planilha original trazia a média de execução da peça no campo de tempo estimado (sem
// distinção de conceito) — aqui ela é realocada para "tempo médio", deixando "tempo estimado"
// livre para preenchimento manual (no sistema de origem, ficava em branco na maioria dos itens).
// "sindicatoAtivo" é derivado: true quando a planilha já trazia algum valor de sindicato > 0.
function migrarPecaImportada(raw: PecaImportadaRaw): Peca {
  const temValorSindicato =
    (raw.valorSindicatoCriacaoCentavos ?? 0) > 0 ||
    (raw.valorSindicatoAdaptacaoCentavos ?? 0) > 0 ||
    (raw.valorSindicatoFinalizacaoCentavos ?? 0) > 0;

  return {
    ...raw,
    tempoMedioMinutos: raw.tempoEstimadoMinutos,
    tempoEstimadoMinutos: null,
    tempoCalculadoExecucaoMinutos: null,
    sindicatoAtivo: temValorSindicato,
  };
}

const pecasImportadas = (pecasImportadasRaw as PecaImportadaRaw[]).map(migrarPecaImportada);

// "Adicionar as faltantes": mescla a planilha importada com os exemplos de demonstração,
// sem duplicar por nome (case-insensitive).
const nomesDemo = new Set(pecasDemo.map((peca) => peca.nome.trim().toLowerCase()));
const pecasImportadasSemDuplicar = pecasImportadas.filter((peca) => !nomesDemo.has(peca.nome.trim().toLowerCase()));

export const pecasMock: Peca[] = [...pecasDemo, ...pecasImportadasSemDuplicar];
