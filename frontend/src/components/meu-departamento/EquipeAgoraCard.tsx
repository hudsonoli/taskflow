"use client";

import { rotuloDemanda } from "@/lib/referencias";
import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Users } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { listarEquipeAgora, type MembroEquipeAgora } from "@/lib/api-backend";

/**
 * "Quem está trabalhando agora" no departamento que o Head lidera (Fase 7C). A fonte é a SESSÃO DE TRABALHO ativa de cada
 * colaborador — nunca o status da demanda, presença online ou último acesso: sem sessão, a pessoa aparece como "Sem atividade em
 * execução" (e não como "offline"). Não mostra horário nem duração: é "quem está fazendo o quê", não vigilância de tempo.
 *
 * O servidor só responde ao Head DESTE departamento (403 para os demais). Montado com `key={departamentoId}`: ao mudar o departamento
 * atual (revalidação de contexto), o componente recomeça do zero e nunca mostra gente do departamento anterior.
 */
export function EquipeAgoraCard({ departamentoId }: { departamentoId: string }) {
  const [membros, setMembros] = useState<MembroEquipeAgora[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [atualizando, setAtualizando] = useState(false);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    let cancelado = false;
    listarEquipeAgora(departamentoId)
      .then((resultado) => {
        if (cancelado) return;
        setMembros(resultado);
        setErro(null);
        setAtualizando(false);
      })
      .catch((falha) => {
        if (cancelado) return;
        setErro(falha instanceof Error ? falha.message : "Não foi possível carregar a equipe.");
        setAtualizando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [departamentoId, versao]);

  const atualizar = useCallback(() => {
    setAtualizando(true);
    setVersao((atual) => atual + 1);
  }, []);

  const emExecucao = membros?.filter((membro) => membro.emExecucao.length > 0).length ?? 0;

  return (
    <section aria-label="Quem está trabalhando agora" className="rounded-2xl border border-line bg-surface shadow-sm">
      <div className="flex items-start justify-between gap-3 border-b border-zinc-100 px-5 py-4 dark:border-zinc-800">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Users className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-fg">Quem está trabalhando agora</h2>
            <p className="text-xs text-fg-muted">
              Pelas sessões de trabalho abertas.{membros ? ` ${emExecucao} de ${membros.length} em execução.` : ""}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={atualizar}
          disabled={atualizando}
          aria-label="Atualizar quem está trabalhando agora"
          className="rounded-full p-2 text-fg-subtle transition hover:bg-surface-hover hover:text-fg disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${atualizando ? "animate-spin" : ""}`} />
        </button>
      </div>

      {erro ? (
        <p className="px-5 py-5 text-sm text-red-600">{erro}</p>
      ) : membros === null ? (
        <p className="px-5 py-5 text-sm text-fg-subtle">Carregando…</p>
      ) : membros.length === 0 ? (
        <p className="px-5 py-5 text-sm text-fg-subtle">Nenhum colaborador ativo neste departamento.</p>
      ) : (
        <ul className="max-h-80 divide-y divide-zinc-100 overflow-y-auto dark:divide-zinc-800">
          {membros.map((membro) => (
            <li key={membro.usuarioId} className="flex items-start gap-3 px-5 py-3">
              <Avatar nome={membro.nome} corIdentificacao={membro.corIdentificacao ?? "blue"} fotoUrl={membro.fotoUrl ?? undefined} className="h-8 w-8 shrink-0 rounded-full text-xs" />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-fg">{membro.nome}</p>
                {membro.emExecucao.length === 0 ? (
                  <p className="text-xs text-fg-subtle">Sem atividade em execução</p>
                ) : (
                  membro.emExecucao.map((atividade) => (
                    <p key={atividade.demandaId} className="truncate text-xs text-emerald-700 dark:text-emerald-400">
                      <span className="font-medium">Em execução:</span>{" "}
                      {atividade.numeroOperacional !== null ? `${rotuloDemanda(atividade)} — ` : ""}
                      {atividade.nome ?? "Tarefa"}
                    </p>
                  ))
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
