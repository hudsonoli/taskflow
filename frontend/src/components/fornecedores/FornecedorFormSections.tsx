import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  categoriasFornecedor,
  generateContatoId,
} from "@/lib/fornecedor-mock";
import type {
  FornecedorContato,
  FornecedorDraft,
} from "@/types/fornecedor";

const statusOptions = [
  { value: "Ativo", label: "Ativo" },
  { value: "Inativo", label: "Inativo" },
];

const categoriaOptions = categoriasFornecedor.map((categoria) => ({
  value: categoria,
  label: categoria,
}));

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
  { value: "Correspondência", label: "Correspondência" },
  { value: "Entrega", label: "Entrega" },
];

type SectionProps = {
  draft: FornecedorDraft;
  onChange: (
    updater: (current: FornecedorDraft) => FornecedorDraft
  ) => void;
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
        onChange={(event) =>
          onNomeFantasiaChange(event.target.value)
        }
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
        label="Categoria"
        options={categoriaOptions}
        value={draft.categoria}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            categoria:
              event.target.value as FornecedorDraft["categoria"],
          }))
        }
      />
      <Select
        label="Status"
        options={statusOptions}
        value={draft.status}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            status: event.target.value as FornecedorDraft["status"],
          }))
        }
      />
      <Input
        label="E-mail"
        type="email"
        value={draft.email}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            email: event.target.value,
          }))
        }
      />
      <Input
        label="Telefone"
        value={draft.telefone}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            telefone: event.target.value,
          }))
        }
      />
      <Input
        label="Celular"
        value={draft.celular}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            celular: event.target.value,
          }))
        }
      />
      <Input
        label="Site"
        value={draft.site}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            site: event.target.value,
          }))
        }
      />
    </div>
  );
}

export function EnderecoSection({
  draft,
  onChange,
}: SectionProps) {
  function update(
    field: keyof FornecedorDraft["endereco"],
    value: string
  ) {
    onChange((current) => ({
      ...current,
      endereco: {
        ...current.endereco,
        [field]: value,
      },
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
        onChange={(event) =>
          update("logradouro", event.target.value)
        }
      />
      <Input
        label="Número"
        value={draft.endereco.numero}
        onChange={(event) => update("numero", event.target.value)}
      />
      <Input
        label="Complemento"
        value={draft.endereco.complemento}
        onChange={(event) =>
          update("complemento", event.target.value)
        }
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

function createEmptyContato(): FornecedorContato {
  return {
    contatoId: generateContatoId(),
    nome: "",
    cargo: "",
    email: "",
    telefone: "",
    celular: "",
  };
}

export function ContatosSection({
  draft,
  onChange,
}: SectionProps) {
  function updateContato(
    contatoId: string,
    field: keyof FornecedorContato,
    value: string
  ) {
    onChange((current) => ({
      ...current,
      contatos: current.contatos.map((contato) =>
        contato.contatoId === contatoId
          ? { ...contato, [field]: value }
          : contato
      ),
    }));
  }

  function addContato() {
    onChange((current) => ({
      ...current,
      contatos: [...current.contatos, createEmptyContato()],
    }));
  }

  function removeContato(contatoId: string) {
    onChange((current) => ({
      ...current,
      contatos: current.contatos.filter(
        (contato) => contato.contatoId !== contatoId
      ),
    }));
  }

  return (
    <div className="space-y-4">
      {draft.contatos.length === 0 && (
        <EmptyState
          title="Nenhum contato adicionado"
          description="Adicione os contatos deste fornecedor."
        />
      )}

      {draft.contatos.map((contato) => (
        <div
          key={contato.contatoId}
          className="rounded-2xl border border-zinc-200 p-4"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Nome"
              value={contato.nome}
              onChange={(event) =>
                updateContato(
                  contato.contatoId,
                  "nome",
                  event.target.value
                )
              }
            />
            <Input
              label="Cargo"
              value={contato.cargo}
              onChange={(event) =>
                updateContato(
                  contato.contatoId,
                  "cargo",
                  event.target.value
                )
              }
            />
            <Input
              label="E-mail"
              type="email"
              value={contato.email}
              onChange={(event) =>
                updateContato(
                  contato.contatoId,
                  "email",
                  event.target.value
                )
              }
            />
            <Input
              label="Telefone"
              value={contato.telefone}
              onChange={(event) =>
                updateContato(
                  contato.contatoId,
                  "telefone",
                  event.target.value
                )
              }
            />
            <Input
              label="Celular"
              value={contato.celular}
              onChange={(event) =>
                updateContato(
                  contato.contatoId,
                  "celular",
                  event.target.value
                )
              }
            />
          </div>

          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={() => removeContato(contato.contatoId)}
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

export function HistoricoSection({ draft }: SectionProps) {
  if (draft.historico.length === 0) {
    return (
      <EmptyState
        title="Nenhum histórico registrado"
        description="As alterações deste fornecedor aparecerão aqui."
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
          <tr>
            <th className="px-4 py-3 font-medium">Usuário</th>
            <th className="px-4 py-3 font-medium">Data</th>
            <th className="px-4 py-3 font-medium">Descrição</th>
          </tr>
        </thead>
        <tbody>
          {draft.historico.map((evento) => (
            <tr
              key={evento.id}
              className="border-b border-zinc-100 last:border-0"
            >
              <td className="px-4 py-3 font-medium text-zinc-900">
                {evento.usuario}
              </td>
              <td className="px-4 py-3 text-zinc-500">
                {evento.dataHora}
              </td>
              <td className="px-4 py-3 text-zinc-500">
                {evento.acao}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
