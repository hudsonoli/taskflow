import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  clientesDisponiveis,
  departamentos,
  generateId,
  responsaveisDisponiveis,
} from "@/lib/equipe-mock";
import type { EquipeDraft, EquipeMembro, HistoricoEquipe } from "@/types/equipe";

const departamentoOptions = departamentos
  .filter((departamento) => departamento.ativo)
  .map((departamento) => ({ value: departamento.id, label: departamento.nome }));

const responsavelOptions = [
  { value: "", label: "Selecione" },
  ...responsaveisDisponiveis.map((responsavel) => ({
    value: responsavel.id,
    label: responsavel.nome,
  })),
];

const clienteOptions = [
  { value: "", label: "Nenhum" },
  ...clientesDisponiveis.map((cliente) => ({
    value: cliente.id,
    label: cliente.nome,
  })),
];

type SectionProps = {
  draft: EquipeDraft;
  onChange: (updater: (current: EquipeDraft) => EquipeDraft) => void;
};

export function DadosSection({ draft, onChange }: SectionProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Input
        label="Código Interno"
        value={draft.codigoInterno}
        readOnly
        className="bg-zinc-50 text-zinc-500"
      />

      <Input
        label="Nome da Equipe"
        value={draft.nome}
        onChange={(event) =>
          onChange((current) => ({ ...current, nome: event.target.value }))
        }
      />

      <Input
        label="Sigla"
        value={draft.sigla}
        onChange={(event) =>
          onChange((current) => ({ ...current, sigla: event.target.value }))
        }
      />

      <Select
        label="Departamento"
        options={departamentoOptions}
        value={draft.departamentoId}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            departamentoId: event.target.value,
          }))
        }
      />

      <Select
        label="Responsável"
        options={responsavelOptions}
        value={draft.responsavelId}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            responsavelId: event.target.value,
          }))
        }
      />

      <Select
        label="Cliente vinculado"
        options={clienteOptions}
        value={draft.clienteId ?? ""}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            clienteId: event.target.value || undefined,
          }))
        }
      />

      <label className="flex items-center gap-2 text-sm text-zinc-700">
        <input
          type="checkbox"
          checked={draft.ativa}
          onChange={(event) =>
            onChange((current) => ({ ...current, ativa: event.target.checked }))
          }
        />
        Equipe ativa
      </label>

      <div className="md:col-span-2">
        <Textarea
          label="Descrição"
          value={draft.descricao}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              descricao: event.target.value,
            }))
          }
        />
      </div>
    </div>
  );
}

function createEmptyMembro(): EquipeMembro {
  return {
    membroId: generateId("membro"),
    usuarioId: "",
    nome: "",
    papel: "",
  };
}

export function MembrosSection({ draft, onChange }: SectionProps) {
  function updateMembro(
    membroId: string,
    field: "usuarioId" | "papel",
    value: string
  ) {
    onChange((current) => ({
      ...current,
      membros: current.membros.map((membro) => {
        if (membro.membroId !== membroId) return membro;

        if (field === "usuarioId") {
          const usuario = responsaveisDisponiveis.find(
            (item) => item.id === value
          );
          return { ...membro, usuarioId: value, nome: usuario?.nome ?? "" };
        }

        return { ...membro, papel: value };
      }),
    }));
  }

  function addMembro() {
    onChange((current) => ({
      ...current,
      membros: [...current.membros, createEmptyMembro()],
    }));
  }

  function removeMembro(membroId: string) {
    onChange((current) => ({
      ...current,
      membros: current.membros.filter(
        (membro) => membro.membroId !== membroId
      ),
    }));
  }

  return (
    <div className="space-y-4">
      {draft.membros.length === 0 && (
        <EmptyState
          title="Nenhum membro adicionado"
          description="Adicione colaboradores para compor a equipe."
        />
      )}

      {draft.membros.map((membro, index) => (
        <div
          key={membro.membroId}
          className="rounded-2xl border border-zinc-200 p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-zinc-900">
              Membro {index + 1}
            </p>

            <button
              type="button"
              onClick={() => removeMembro(membro.membroId)}
              className="text-xs font-medium text-zinc-400 underline decoration-dotted hover:text-zinc-700"
            >
              Remover
            </button>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Select
              label="Colaborador"
              options={[
                { value: "", label: "Selecione" },
                ...responsaveisDisponiveis.map((usuario) => ({
                  value: usuario.id,
                  label: usuario.nome,
                })),
              ]}
              value={membro.usuarioId}
              onChange={(event) =>
                updateMembro(membro.membroId, "usuarioId", event.target.value)
              }
            />

            <Input
              label="Papel na equipe"
              value={membro.papel}
              onChange={(event) =>
                updateMembro(membro.membroId, "papel", event.target.value)
              }
            />
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addMembro}
        className="w-full rounded-2xl border border-dashed border-zinc-300 px-4 py-3 text-sm font-medium text-zinc-500 hover:bg-zinc-50"
      >
        + Novo Membro
      </button>
    </div>
  );
}

const acessoOptions: { field: keyof EquipeDraft["acesso"]; label: string }[] = [
  {
    field: "visualizarTodosProjetos",
    label: "Visualizar todos os projetos da empresa",
  },
  { field: "aprovarSla", label: "Aprovar SLA de tarefas" },
  { field: "gerenciarMembros", label: "Gerenciar membros da equipe" },
  { field: "visivelParaClientes", label: "Visível para clientes no portal" },
];

export function AcessoSection({ draft, onChange }: SectionProps) {
  function toggle(field: keyof EquipeDraft["acesso"]) {
    onChange((current) => ({
      ...current,
      acesso: { ...current.acesso, [field]: !current.acesso[field] },
    }));
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
          <tr>
            <th className="px-4 py-3 font-medium">Permissão</th>
            <th className="px-4 py-3 text-center font-medium">Ativo</th>
          </tr>
        </thead>

        <tbody>
          {acessoOptions.map((option) => (
            <tr
              key={option.field}
              className="border-b border-zinc-100 last:border-0"
            >
              <td className="px-4 py-3 font-medium text-zinc-900">
                {option.label}
              </td>

              <td className="px-4 py-3 text-center">
                <input
                  type="checkbox"
                  checked={draft.acesso[option.field]}
                  onChange={() => toggle(option.field)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const historicoMock: HistoricoEquipe[] = [
  {
    id: "evento-equipe-1",
    usuarioId: "sistema",
    usuario: "Sistema",
    dataHora: "04/07/2026 09:12",
    dispositivo: "Desktop - Chrome",
    ipOrigem: "192.168.0.10",
    acao: "Equipe criada.",
  },
];

export function HistoricoSection() {
  return (
    <div className="space-y-4">
      <Input
        label="Buscar por palavra-chave"
        placeholder="Buscar alterações..."
      />

      <div className="overflow-hidden rounded-2xl border border-zinc-200">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-4 py-3 font-medium">Usuário</th>
              <th className="px-4 py-3 font-medium">Data</th>
              <th className="px-4 py-3 font-medium">Dispositivo</th>
              <th className="px-4 py-3 font-medium">IP de Origem</th>
              <th className="px-4 py-3 font-medium">Descrição</th>
            </tr>
          </thead>

          <tbody>
            {historicoMock.map((evento) => (
              <tr
                key={evento.id}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-4 py-3 font-medium text-zinc-900">
                  {evento.usuario}
                </td>
                <td className="px-4 py-3 text-zinc-500">{evento.dataHora}</td>
                <td className="px-4 py-3 text-zinc-500">
                  {evento.dispositivo}
                </td>
                <td className="px-4 py-3 text-zinc-500">
                  {evento.ipOrigem}
                </td>
                <td className="px-4 py-3 text-zinc-500">{evento.acao}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
