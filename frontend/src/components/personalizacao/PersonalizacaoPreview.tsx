"use client";

import { Sparkles } from "lucide-react";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { corSobre, gerarEscala, variaveisDaMarca } from "@/lib/branding-tokens";
import type { TemaVisual } from "@/types/personalizacao";

// Prévia ao vivo: um recorte do app (menu, botões, selo, campo) no tema e nas cores do RASCUNHO, isolado do
// resto da tela (data-theme próprio + variáveis inline). Usa as mesmas funções de contraste do app real.
export function PersonalizacaoPreview({
  primaria,
  secundaria,
  tema,
  logoSrc,
}: {
  primaria: string;
  secundaria: string;
  tema: TemaVisual;
  /** undefined → logo salvo · null → sem logo · string → arquivo escolhido (ainda não salvo) */
  logoSrc: string | null | undefined;
}) {
  const vars = variaveisDaMarca(primaria, secundaria);
  const escalaPrimaria = gerarEscala(primaria, 500);
  const gradiente = vars["--brand-gradient"] ?? `linear-gradient(135deg, ${primaria}, ${secundaria})`;
  const sobreGradiente = vars["--on-brand"] ?? "#ffffff";
  const ativo = tema === "escuro" ? escalaPrimaria[400] : escalaPrimaria[600];
  const fundoAtivo = tema === "escuro" ? `${escalaPrimaria[500]}26` : escalaPrimaria[50];

  return (
    <div
      data-theme={tema}
      style={vars}
      className="overflow-hidden rounded-xl border border-line bg-app text-fg"
      aria-label="Prévia da personalização"
    >
      <div className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
        <BrandLogo variant="header" srcOverride={logoSrc} />
        <span className="rounded-full px-3 py-1.5 text-xs font-medium" style={{ color: ativo, backgroundColor: fundoAtivo }}>
          Tarefas
        </span>
        <span className="text-xs font-medium text-fg-muted">Projetos</span>
      </div>
      <div className="flex flex-col gap-3 p-4">
        <div className="rounded-xl border border-line bg-surface p-4">
          <p className="text-sm font-semibold text-fg">Campanha de lançamento</p>
          <p className="mt-0.5 text-xs text-fg-muted">Texto secundário legível nos dois temas.</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-xs font-semibold"
              style={{ background: gradiente, color: sobreGradiente }}
            >
              <Sparkles size={13} /> Ação principal
            </span>
            <span
              className="inline-flex items-center rounded-full px-3.5 py-2 text-xs font-semibold"
              style={{ backgroundColor: secundaria, color: corSobre(secundaria) }}
            >
              Secundária
            </span>
            <span className="inline-flex items-center rounded-full border border-line-strong px-3.5 py-2 text-xs font-semibold text-fg-muted">
              Cancelar
            </span>
            <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ color: ativo, backgroundColor: fundoAtivo }}>
              Em andamento
            </span>
          </div>
        </div>
        <input
          readOnly
          tabIndex={-1}
          aria-hidden
          value=""
          placeholder="Campo de texto"
          className="w-full rounded-xl border border-field-line bg-field px-3 py-2.5 text-sm text-fg outline-none placeholder:text-placeholder"
        />
      </div>
    </div>
  );
}
