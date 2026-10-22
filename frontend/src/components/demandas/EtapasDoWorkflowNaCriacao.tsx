"use client";

import { useState } from "react";
import { GitBranch, Pencil, RotateCcw } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import {
  aplicarAjusteDaEtapa,
  previsaoNaCriacao,
  removerAjusteDaEtapa,
  type EtapaDoModeloEmEdicao,
} from "@/lib/responsabilidade-etapa";
import { useUsuariosComIds } from "@/lib/useUsuariosComIds";
import { workflowEtapaTipoLabels, type WorkflowModelo } from "@/types/workflow-modelo";
import { EditarResponsaveisEtapaModal } from "./EditarResponsaveisEtapaModal";
import { ResponsabilidadeEtapa } from "./ResponsabilidadeEtapa";

/**
 * Etapas do workflow escolhido, NA CRIAÇÃO: cada etapa mostra departamento e responsável(is) (do modelo, do que for ajustado aqui ou herdado da tarefa) e pode ser ajustada
 * sem sair do formulário. O ajuste vale só para esta tarefa — o modelo de workflow nunca muda. Os ajustes seguem para o servidor junto com o cadastro (`workflowEtapasResponsaveis`,
 * por id da etapa do MODELO), na mesma transação; sem ajuste, a criação é a de sempre (responsáveis copiados do modelo).
 */
export function EtapasDoWorkflowNaCriacao({
  modelo,
  carregando,
  gerais,
  ajustes,
  onChange,
}: {
  modelo: WorkflowModelo | null;
  carregando: boolean;
  /** Responsáveis gerais da tarefa em edição (a herança das etapas sem vínculo próprio). */
  gerais: { usuarioIds: string[]; departamentoIds: string[] };
  ajustes: EtapaDoModeloEmEdicao[];
  onChange: (ajustes: EtapaDoModeloEmEdicao[]) => void;
}) {
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const { departamentos } = useDiretorioDepartamentos();
  const etapas = modelo?.etapas ?? [];
  const { usuarios, resolvendo } = useUsuariosComIds([
    ...etapas.flatMap((etapa) => etapa.usuarioResponsavelIds),
    ...ajustes.flatMap((ajuste) => ajuste.usuarioResponsavelIds),
    ...gerais.usuarioIds,
  ]);
  const nomeDoUsuario = (id: string) => usuarios.find((u) => u.id === id)?.nome ?? (resolvendo ? "Carregando…" : "Usuário indisponível");
  const nomeDoDepartamento = (id: string) => departamentos.find((d) => d.id === id)?.nome ?? id;
  const editando = etapas.find((etapa) => etapa.id === editandoId) ?? null;
  const ajusteDaEditada = ajustes.find((ajuste) => ajuste.modeloEtapaId === editandoId);

  return (
    <div className="mt-3 rounded-2xl border border-indigo-100 bg-indigo-50/40 p-3.5 dark:border-indigo-500/20 dark:bg-indigo-500/5">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
        <GitBranch className="h-3.5 w-3.5" />
        Etapas do workflow
      </div>
      {carregando ? (
        <p className="mt-2 text-xs text-fg-muted">Carregando etapas…</p>
      ) : (
        <ol className="mt-2 flex flex-col gap-2.5">
          {etapas.map((etapa, index) => {
            const ajuste = ajustes.find((item) => item.modeloEtapaId === etapa.id);
            const explicitos = ajuste
              ? { usuarioIds: ajuste.usuarioResponsavelIds, departamentoIds: ajuste.departamentoResponsavelIds }
              : { usuarioIds: etapa.usuarioResponsavelIds, departamentoIds: etapa.departamentoResponsavelIds };
            return (
              <li key={etapa.id} className="rounded-xl bg-surface/70 p-2.5 ring-1 ring-line/60">
                <div className="flex flex-wrap items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-500 text-[10px] font-bold text-primary-fg">{index + 1}</span>
                  <span className="min-w-0 flex-1 truncate font-medium">{etapa.nome}</span>
                  <Badge tone={etapa.tipo === "aprovacao" ? "amber" : "blue"}>{workflowEtapaTipoLabels[etapa.tipo]}</Badge>
                </div>
                <ResponsabilidadeEtapa
                  responsabilidade={previsaoNaCriacao(explicitos, gerais)}
                  nomeDoUsuario={nomeDoUsuario}
                  nomeDoDepartamento={nomeDoDepartamento}
                />
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Button type="button" variant="secondary" className="px-2.5 py-1 text-xs" onClick={() => setEditandoId(etapa.id)}>
                    <Pencil className="h-3 w-3" /> Definir responsáveis
                  </Button>
                  {ajuste && (
                    <Button type="button" variant="secondary" className="px-2.5 py-1 text-xs" onClick={() => onChange(removerAjusteDaEtapa(ajustes, etapa.id))}>
                      <RotateCcw className="h-3 w-3" /> Restaurar padrão do modelo
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
      {editando && (
        <EditarResponsaveisEtapaModal
          key={editando.id}
          etapaNome={editando.nome}
          usuarioIds={ajusteDaEditada ? ajusteDaEditada.usuarioResponsavelIds : editando.usuarioResponsavelIds}
          departamentoIds={ajusteDaEditada ? ajusteDaEditada.departamentoResponsavelIds : editando.departamentoResponsavelIds}
          onClose={() => setEditandoId(null)}
          onSalvar={(usuarioIds, departamentoIds) => {
            onChange(aplicarAjusteDaEtapa(ajustes, { modeloEtapaId: editando.id, usuarioResponsavelIds: usuarioIds, departamentoResponsavelIds: departamentoIds }));
            setEditandoId(null);
          }}
        />
      )}
    </div>
  );
}
