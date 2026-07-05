import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { equipesDisponiveis, responsaveisDisponiveis } from "@/lib/cliente-mock";
import type { ClienteContato, ClienteDraft, HistoricoCliente } from "@/types/cliente";

const statusOptions = [
  { value: "Ativo", label: "Ativo" },
  { value: "Inativo", label: "Inativo" },
];

const ufOptions = [
  { value: "", label: "Selecione" },
  { value: "SP", label: "SP" },
  { value: "RJ", label: "RJ" },
  { value: "MG", label: "MG" },
  { value: "PR", label: "PR" },
  { value: "SC", label: "SC" },
  { value: "RS", label: "RS" },
  { value: "Outro", label: "Outro" },
];

const tipoEnderecoOptions = [
  { value: "Comercial", label: "Comercial" },
  { value: "Cobrança", label: "Cobrança" },
  { value: "Entrega", label: "Entrega" },
];

const equipeResponsavelOptions = [
  { value: "", label: "Nenhuma" },
  ...equipesDisponiveis.map((equipe) => ({ value: equipe.id, label: equipe.nome })),
];

const responsavelOptions = [
  { value: "", label: "Nenhum" },
  ...responsaveisDisponiveis.map((responsavel) => ({
    value: responsavel.id,
    label: responsavel.nome,
  })),
];

type SectionProps = {
  draft: ClienteDraft;
  onChange: (updater: (current: ClienteDraft) => ClienteDraft) => void;
};

type DadosSectionProps = SectionProps & {
  onNomeFantasiaChange: (value: string) => void;
  onSiglaChange: (value: string) => void;
};

export function DadosSection({
  draft,
  onChange,
  onNomeFantasiaChange,
  onSiglaChange,
}: DadosSectionProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Input
        label="Código Interno"
        value={draft.codigoInterno}
        readOnly
        className="bg-zinc-50 text-zinc-500"
      />

      <Input
        label="CNPJ/CPF"
        value={draft.documento}
        readOnly
        className="bg-zinc-50 text-zinc-500"
      />

      <Input
        label="Nome Fantasia"
        value={draft.nomeFantasia}
        onChange={(event) => onNomeFantasiaChange(event.target.value)}
      />

      <Input
        label="Razão Social / Nome"
        value={draft.nomeRazaoSocial}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            nomeRazaoSocial: event.target.value,
          }))
        }
      />

      <Input
        label="Sigla"
        value={draft.sigla}
        onChange={(event) => onSiglaChange(event.target.value)}
      />

      <Select
        label="Status"
        options={statusOptions}
        value={draft.status}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            status: event.target.value as ClienteDraft["status"],
          }))
        }
      />

      <Input
        label="E-mail"
        type="email"
        value={draft.email}
        onChange={(event) =>
          onChange((current) => ({ ...current, email: event.target.value }))
        }
      />

      <Input
        label="Telefone"
        value={draft.telefone}
        onChange={(event) =>
          onChange((current) => ({ ...current, telefone: event.target.value }))
        }
      />

      <Input
        label="Celular"
        value={draft.celular}
        onChange={(event) =>
          onChange((current) => ({ ...current, celular: event.target.value }))
        }
      />

      <Input
        label="Site"
        value={draft.site}
        onChange={(event) =>
          onChange((current) => ({ ...current, site: event.target.value }))
        }
      />
    </div>
  );
}

export function EnderecoSection({ draft, onChange }: SectionProps) {
  function update(field: keyof ClienteDraft["endereco"], value: string) {
    onChange((current) => ({
      ...current,
      endereco: { ...current.endereco, [field]: value },
    }));
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Input
        label="CEP"
        value={draft.endereco.cep}
        onChange={(event) => update("cep", event.target.value)}
      />

      <Input
        label="Logradouro"
        value={draft.endereco.logradouro}
        onChange={(event) => update("logradouro", event.target.value)}
      />

      <Input
        label="Número"
        value={draft.endereco.numero}
        onChange={(event) => update("numero", event.target.value)}
      />

      <Input
        label="Complemento"
        value={draft.endereco.complemento}
        onChange={(event) => update("complemento", event.target.value)}
      />

      <Input
        label="Bairro"
        value={draft.endereco.bairro}
        onChange={(event) => update("bairro", event.target.value)}
      />

      <Input
        label="Cidade"
        value={draft.endereco.cidade}
        onChange={(event) => update("cidade", event.target.value)}
      />

      <Select
        label="UF"
        options={ufOptions}
        value={draft.endereco.uf}
        onChange={(event) => update("uf", event.target.value)}
      />

      <Input
        label="País"
        value={draft.endereco.pais}
        onChange={(event) => update("pais", event.target.value)}
      />

      <Select
        label="Tipo"
        options={tipoEnderecoOptions}
        value={draft.endereco.tipo}
        onChange={(event) => update("tipo", event.target.value)}
      />
    </div>
  );
}

export function EquipeSection({ draft, onChange }: SectionProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Select
        label="Equipe Responsável"
        options={equipeResponsavelOptions}
        value={draft.equipeResponsavelId ?? ""}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            equipeResponsavelId: event.target.value || undefined,
          }))
        }
      />

      <Select
        label="Responsável Comercial"
        options={responsavelOptions}
        value={draft.responsavelComercialId ?? ""}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            responsavelComercialId: event.target.value || undefined,
          }))
        }
      />

      <Select
        label="Responsável pelo Atendimento"
        options={responsavelOptions}
        value={draft.responsavelAtendimentoId ?? ""}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            responsavelAtendimentoId: event.target.value || undefined,
          }))
        }
      />
    </div>
  );
}

function createEmptyContato(): ClienteContato {
  return {
    id: `contato-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    nome: "",
    email: "",
    telefone: "",
    celular: "",
    cargo: "",
    aniversario: "",
    acessoPortal: false,
  };
}

export function ContatosSection({ draft, onChange }: SectionProps) {
  function updateContato(
    id: string,
    field: keyof ClienteContato,
    value: string | boolean
  ) {
    onChange((current) => ({
      ...current,
      contatos: current.contatos.map((contato) =>
        contato.id === id ? { ...contato, [field]: value } : contato
      ),
    }));
  }

  function addContato() {
    onChange((current) => ({
      ...current,
      contatos: [...current.contatos, createEmptyContato()],
    }));
  }

  function removeContato(id: string) {
    onChange((current) => ({
      ...current,
      contatos: current.contatos.filter((contato) => contato.id !== id),
    }));
  }

  return (
    <div className="space-y-4">
      {draft.contatos.length === 0 && (
        <EmptyState
          title="Nenhum contato adicionado"
          description="Adicione os contatos responsáveis por este cliente."
        />
      )}

      {draft.contatos.map((contato) => (
        <div key={contato.id} className="rounded-2xl border border-zinc-200 p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Nome"
              value={contato.nome}
              onChange={(event) =>
                updateContato(contato.id, "nome", event.target.value)
              }
            />

            <Input
              label="E-mail"
              type="email"
              value={contato.email}
              onChange={(event) =>
                updateContato(contato.id, "email", event.target.value)
              }
            />

            <Input
              label="Telefone"
              value={contato.telefone}
              onChange={(event) =>
                updateContato(contato.id, "telefone", event.target.value)
              }
            />

            <Input
              label="Celular"
              value={contato.celular}
              onChange={(event) =>
                updateContato(contato.id, "celular", event.target.value)
              }
            />

            <Input
              label="Cargo"
              value={contato.cargo}
              onChange={(event) =>
                updateContato(contato.id, "cargo", event.target.value)
              }
            />

            <Input
              label="Aniversário"
              type="date"
              value={contato.aniversario}
              onChange={(event) =>
                updateContato(contato.id, "aniversario", event.target.value)
              }
            />
          </div>

          <div className="mt-3 flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm text-zinc-700">
              <input
                type="checkbox"
                checked={contato.acessoPortal}
                onChange={(event) =>
                  updateContato(contato.id, "acessoPortal", event.target.checked)
                }
              />
              Permitir acesso ao portal
            </label>

            <button
              type="button"
              onClick={() => removeContato(contato.id)}
              className="text-xs font-medium text-zinc-400 underline decoration-dotted hover:text-zinc-700"
            >
              Remover
            </button>
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addContato}
        className="w-full rounded-2xl border border-dashed border-zinc-300 px-4 py-3 text-sm font-medium text-zinc-500 hover:bg-zinc-50"
      >
        + Adicionar Contato
      </button>
    </div>
  );
}

const historicoMock: HistoricoCliente[] = [
  {
    id: "evento-cliente-1",
    usuarioId: "sistema",
    usuario: "Sistema",
    dataHora: "05/07/2026 09:00",
    dispositivo: "Desktop - Chrome",
    ipOrigem: "192.168.0.10",
    acao: "Cliente criado.",
  },
];

export function HistoricoSection() {
  return (
    <div className="space-y-4">
      <Input label="Buscar por palavra-chave" placeholder="Buscar alterações..." />

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
              <tr key={evento.id} className="border-b border-zinc-100 last:border-0">
                <td className="px-4 py-3 font-medium text-zinc-900">{evento.usuario}</td>
                <td className="px-4 py-3 text-zinc-500">{evento.dataHora}</td>
                <td className="px-4 py-3 text-zinc-500">{evento.dispositivo}</td>
                <td className="px-4 py-3 text-zinc-500">{evento.ipOrigem}</td>
                <td className="px-4 py-3 text-zinc-500">{evento.acao}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
