"use client";

import { useId, useState } from "react";
import clsx from "clsx";
import { Check } from "lucide-react";
import { corParaPintar, estadoDoCampoDeCor, normalizarCorWorkflow, PALETA_WORKFLOW } from "@/lib/workflow-cor";

/**
 * Identidade visual do modelo de workflow. É o ÚNICO lugar que aplica a cor em `style` (cor é dado dinâmico — nunca classe Tailwind montada). A cor é só um ponto/swatch
 * ao lado do NOME (que sempre aparece em texto): não pinta fundo nem texto, então qualquer HEX é seguro de exibir e a cor nunca é o único sinal. Sem cor (ou valor inválido) = neutro.
 * Não comunica erro, sucesso, urgência nem estado — por isso não reutiliza os tons de prioridade/status.
 */
export function WorkflowCorPonto({ cor, className }: { cor: string | null | undefined; className?: string }) {
  const pintar = corParaPintar(cor);
  return (
    <span
      aria-hidden="true"
      data-workflow-cor={pintar ?? "neutra"}
      className={clsx("inline-block h-2.5 w-2.5 shrink-0 rounded-full ring-1 ring-black/10 dark:ring-white/20", pintar === null && "bg-zinc-300 dark:bg-zinc-600", className)}
      style={pintar ? { backgroundColor: pintar } : undefined}
    />
  );
}

/** `● NOME` — o nome continua sempre textual. */
export function WorkflowNomeComCor({ nome, cor, className }: { nome: string; cor: string | null | undefined; className?: string }) {
  return (
    <span className={clsx("inline-flex min-w-0 items-center gap-2", className)}>
      <WorkflowCorPonto cor={cor} />
      <span className="min-w-0 truncate">{nome}</span>
    </span>
  );
}

/**
 * Campo "Cor do workflow": atalhos da paleta + seletor nativo + HEX editável + preview + "Remover cor" (volta a `null`, sem converter para uma cor do sistema).
 * `valor` é a cor JÁ válida (ou `null`); o texto digitado pode estar incompleto e só um `#RRGGBB` válido é propagado.
 */
export function WorkflowCorField({ valor, onChange, nomePreview }: { valor: string | null; onChange: (cor: string | null) => void; nomePreview: string }) {
  const id = useId();
  const [texto, setTexto] = useState(valor ?? "");
  // A cor mudou por fora (paleta, seletor, remover): o texto acompanha — comparado no RENDER (padrão do projeto), sem tocar no que a pessoa está digitando se já equivale ao valor.
  const [valorVisto, setValorVisto] = useState(valor);
  if (valor !== valorVisto) {
    setValorVisto(valor);
    if (estadoDoCampoDeCor(texto).cor !== valor) setTexto(valor ?? "");
  }
  const invalida = !estadoDoCampoDeCor(texto).valida;
  return (
    <div>
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Cor do workflow</span>
      <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Cores sugeridas">
        {PALETA_WORKFLOW.map((opcao) => {
          const ativa = valor === opcao.hex;
          return (
            <button
              key={opcao.hex}
              type="button"
              title={opcao.nome}
              aria-label={`${opcao.nome} (${opcao.hex})`}
              aria-pressed={ativa}
              onClick={() => onChange(opcao.hex)}
              className={clsx("flex h-7 w-7 items-center justify-center rounded-full ring-1 ring-black/10 transition hover:scale-110 dark:ring-white/20", ativa && "outline outline-2 outline-offset-2 outline-indigo-500")}
              style={{ backgroundColor: opcao.hex }}
            >
              {ativa && <Check className="h-3.5 w-3.5 text-white mix-blend-difference" />}
            </button>
          );
        })}
      </div>
      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        <input
          type="color"
          aria-label="Cor do workflow — seletor de cor"
          value={valor ?? "#8B5CF6"}
          onChange={(event) => onChange(normalizarCorWorkflow(event.target.value))}
          className="h-10 w-12 shrink-0 cursor-pointer rounded-lg border border-field-line bg-field p-1"
        />
        <input
          id={id}
          type="text"
          spellCheck={false}
          autoComplete="off"
          maxLength={7}
          value={texto}
          aria-label="Cor do workflow — HEX"
          aria-invalid={invalida}
          aria-describedby={`${id}-ajuda`}
          placeholder="#8B5CF6"
          onChange={(event) => {
            const proximo = event.target.value.trim();
            setTexto(proximo);
            const resultado = estadoDoCampoDeCor(proximo);
            if (resultado.valida && resultado.cor !== valor) onChange(resultado.cor); // vazio = remover; incompleto/inválido não é propagado
          }}
          className="field w-32 rounded-xl px-3 py-2.5 font-mono text-sm"
        />
        <span className="inline-flex h-10 min-w-0 flex-1 items-center rounded-xl border border-zinc-200 bg-surface px-3 text-sm text-fg dark:border-zinc-700" aria-label="Pré-visualização">
          <WorkflowNomeComCor nome={nomePreview.trim() || "Nome do workflow"} cor={valor} />
        </span>
        <button
          type="button"
          disabled={valor === null && texto === ""}
          onClick={() => {
            setTexto("");
            onChange(null);
          }}
          className="text-xs font-medium text-indigo-600 hover:underline disabled:cursor-not-allowed disabled:opacity-40 dark:text-indigo-400"
        >
          Remover cor
        </button>
      </div>
      <p id={`${id}-ajuda`} className={clsx("mt-1.5 text-xs", invalida ? "text-danger" : "text-fg-muted")}>
        {invalida ? "Use o formato #RRGGBB (ex.: #8B5CF6)." : valor ? "A cor identifica o workflow ao lado do nome; não muda prioridade, status nem progresso." : "Sem cor personalizada: o workflow usa o ponto neutro."}
      </p>
    </div>
  );
}
