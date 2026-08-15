"use client";

import { useState, type ReactNode } from "react";
import { MessageSquare, Send } from "lucide-react";
import { useAppData } from "@/lib/AppDataContext";
import { generateId } from "@/lib/demandas";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import type { Demanda } from "@/types/demanda";

function SectionShell({ children }: { children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <MessageSquare className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">Atividade</h3>
          <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            Histórico do que foi comentado sobre a tarefa pelas partes envolvidas.
          </p>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function AtividadeDemandaSection({
  demanda,
  onChange,
}: {
  demanda: Demanda;
  onChange: (demanda: Demanda) => void;
}) {
  const { usuarioAtual } = useAppData();
  const { usuarios } = useDiretorioUsuarios();
  const [texto, setTexto] = useState("");

  // Enquanto Demanda continuar mock, a menção grava codigoInterno (não o UUID real) — ver
  // lib/referencias.ts.
  function detectarMencoes(conteudo: string): string[] {
    const textoNormalizado = conteudo.toLowerCase();
    return usuarios
      .filter((usuario) => {
        const primeiroNome = usuario.nome.trim().split(/\s+/)[0]?.toLowerCase();
        return primeiroNome && textoNormalizado.includes(`@${primeiroNome}`);
      })
      .map((usuario) => usuario.codigoInterno);
  }

  function comentar() {
    const conteudo = texto.trim();
    if (!conteudo) return;

    onChange({
      ...demanda,
      comentarios: [
        {
          id: generateId("comentario-demanda"),
          usuarioId: usuarioAtual?.id ?? "user-1",
          usuario: usuarioAtual?.nome ?? "Você",
          texto: conteudo,
          dataHora: new Date().toLocaleString("pt-BR"),
          mencoes: detectarMencoes(conteudo),
        },
        ...demanda.comentarios,
      ],
      updatedAt: new Date().toISOString(),
    });
    setTexto("");
  }

  return (
    <SectionShell>
      <div className="flex items-start gap-2">
        <textarea
          value={texto}
          onChange={(event) => setTexto(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              comentar();
            }
          }}
          placeholder="Comentar sobre a tarefa…"
          rows={2}
          className="w-full resize-none rounded-xl border border-zinc-200 bg-zinc-50/70 py-2.5 px-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
        />
        <button
          type="button"
          onClick={comentar}
          disabled={!texto.trim()}
          className="inline-flex shrink-0 items-center justify-center rounded-xl bg-indigo-600 p-2.5 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Comentar"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {demanda.comentarios.map((comentario) => (
          <div
            key={comentario.id}
            className="rounded-2xl border border-zinc-100 bg-zinc-50/60 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/30"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{comentario.usuario}</p>
              <p className="text-xs text-zinc-400">{comentario.dataHora}</p>
            </div>
            <p className="mt-1.5 text-sm leading-6 text-zinc-600 dark:text-zinc-300">{comentario.texto}</p>
          </div>
        ))}
        {demanda.comentarios.length === 0 && (
          <p className="text-sm text-zinc-400">Nenhum comentário registrado ainda.</p>
        )}
      </div>
    </SectionShell>
  );
}
