"use client";

import { useState } from "react";
import { UsersRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { Modal } from "@/components/ui/Modal";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { AJUDA_HERANCA } from "@/lib/responsabilidade-etapa";
import { useResponsaveisSelector } from "@/lib/useResponsaveisSelector";

/**
 * Responsáveis EXPLÍCITOS de uma etapa: pessoas e departamentos, vários de cada. Sem nenhum, a etapa usa os responsáveis gerais da tarefa (herança dinâmica — "Usar responsáveis da
 * tarefa" envia as duas listas vazias; nada é copiado). Serve à aba Workflow (grava no servidor) e à criação (guarda no rascunho): quem usa decide o que `onSalvar` faz.
 */
export function EditarResponsaveisEtapaModal({
  etapaNome,
  usuarioIds,
  departamentoIds,
  onSalvar,
  onClose,
  rotuloLimpar = "Usar responsáveis da tarefa",
}: {
  etapaNome: string;
  usuarioIds: string[];
  departamentoIds: string[];
  onSalvar: (usuarioIds: string[], departamentoIds: string[]) => Promise<void> | void;
  onClose: () => void;
  rotuloLimpar?: string;
}) {
  const { departamentos } = useDiretorioDepartamentos();
  const responsaveis = useResponsaveisSelector();
  const [usuarios, setUsuarios] = useState<string[]>(usuarioIds);
  const [deptos, setDeptos] = useState<string[]>(departamentoIds);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(u: string[], d: string[]) {
    if (salvando) return;
    setSalvando(true);
    setErro(null);
    try {
      await onSalvar(u, d);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível salvar os responsáveis da etapa.");
      setSalvando(false);
      return;
    }
    setSalvando(false);
  }

  return (
    <Modal open onClose={salvando ? () => {} : onClose} maxWidthClassName="max-w-lg">
      <div role="dialog" aria-label={`Responsáveis da etapa ${etapaNome}`} className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400">
            <UsersRound className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-fg">Responsáveis da etapa</h3>
            <p className="mt-0.5 text-sm text-fg-muted">{etapaNome}</p>
          </div>
        </div>

        <MemberSelector
          label="Pessoas"
          values={usuarios}
          onChange={setUsuarios}
          placeholder="Selecionar responsáveis…"
          buscarOpcoes={responsaveis.buscarOpcoes}
          resolverSelecionados={responsaveis.resolverSelecionados}
          ordenarSelecionados="nome"
          emptyLabel="Nenhum usuário encontrado"
        />
        <MultiSelect
          label="Departamentos"
          values={deptos}
          onChange={setDeptos}
          options={departamentos.filter((d) => d.status === "ativo").map((d) => ({ value: d.id, label: d.nome }))}
        />
        <p className="text-xs text-fg-muted">{AJUDA_HERANCA}</p>

        {erro && (
          <p role="alert" className="text-xs text-red-600 dark:text-red-400">
            {erro}
          </p>
        )}
        <div className="flex flex-wrap justify-between gap-2">
          <Button type="button" variant="secondary" onClick={() => void enviar([], [])} disabled={salvando}>
            {rotuloLimpar}
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={salvando}>
              Cancelar
            </Button>
            <Button type="button" onClick={() => void enviar(usuarios, deptos)} disabled={salvando}>
              {salvando ? "Salvando…" : "Salvar"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
