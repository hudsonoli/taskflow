import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import type { ClienteContato, ClienteDraft } from "@/types/cliente";

const situacaoOptions = [
  { value: "Ativo", label: "Ativo" },
  { value: "Inativo", label: "Inativo" },
];

const grupoOptions = [
  { value: "", label: "Selecione" },
  { value: "Padrão", label: "Padrão" },
  { value: "Premium", label: "Premium" },
  { value: "Institucional", label: "Institucional" },
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

const retencoesDisponiveis = ["IRRF", "PIS", "COFINS", "CSLL", "INSS", "ISS"];

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
        label="Razão Social"
        value={draft.razaoSocial}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            razaoSocial: event.target.value,
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

      <Select
        label="Grupo de Clientes"
        options={grupoOptions}
        value={draft.grupoCliente}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            grupoCliente: event.target.value,
          }))
        }
      />

      <Input
        label="Atendimento"
        value={draft.atendimento}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            atendimento: event.target.value,
          }))
        }
      />

      <Input
        label="Auxiliar"
        value={draft.auxiliar}
        onChange={(event) =>
          onChange((current) => ({ ...current, auxiliar: event.target.value }))
        }
      />

      <Input
        label="Sigla"
        value={draft.sigla}
        onChange={(event) => onSiglaChange(event.target.value)}
      />

      <Select
        label="Situação"
        options={situacaoOptions}
        value={draft.situacao}
        onChange={(event) =>
          onChange((current) => ({ ...current, situacao: event.target.value }))
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

export function ComplementaresSection({ draft, onChange }: SectionProps) {
  function update(
    field: keyof Omit<ClienteDraft["complementares"], "retencoesFiscais">,
    value: string
  ) {
    onChange((current) => ({
      ...current,
      complementares: { ...current.complementares, [field]: value },
    }));
  }

  function toggleRetencao(retencao: string) {
    onChange((current) => {
      const jaSelecionada =
        current.complementares.retencoesFiscais.includes(retencao);

      const retencoesFiscais = jaSelecionada
        ? current.complementares.retencoesFiscais.filter(
            (item) => item !== retencao
          )
        : [...current.complementares.retencoesFiscais, retencao];

      return {
        ...current,
        complementares: { ...current.complementares, retencoesFiscais },
      };
    });
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <Input
          label="Banco"
          value={draft.complementares.banco}
          onChange={(event) => update("banco", event.target.value)}
        />

        <Input
          label="Agência"
          value={draft.complementares.agencia}
          onChange={(event) => update("agencia", event.target.value)}
        />

        <Input
          label="Conta"
          value={draft.complementares.conta}
          onChange={(event) => update("conta", event.target.value)}
        />

        <Input
          label="Chave Pix"
          value={draft.complementares.chavePix}
          onChange={(event) => update("chavePix", event.target.value)}
        />

        <Input
          label="Setor"
          value={draft.complementares.setor}
          onChange={(event) => update("setor", event.target.value)}
        />
      </div>

      <Textarea
        label="Produtos e Serviços"
        value={draft.complementares.produtosServicos}
        onChange={(event) => update("produtosServicos", event.target.value)}
      />

      <Textarea
        label="Observação"
        value={draft.complementares.observacao}
        onChange={(event) => update("observacao", event.target.value)}
      />

      <div>
        <p className="mb-2 text-sm font-medium text-zinc-700">
          Retenções fiscais (mock)
        </p>

        <div className="flex flex-wrap gap-3">
          {retencoesDisponiveis.map((retencao) => (
            <label
              key={retencao}
              className="flex items-center gap-2 rounded-xl border border-zinc-200 px-3 py-2 text-sm text-zinc-700"
            >
              <input
                type="checkbox"
                checked={draft.complementares.retencoesFiscais.includes(
                  retencao
                )}
                onChange={() => toggleRetencao(retencao)}
              />
              {retencao}
            </label>
          ))}
        </div>
      </div>
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
        <div
          key={contato.id}
          className="rounded-2xl border border-zinc-200 p-4"
        >
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
                  updateContato(
                    contato.id,
                    "acessoPortal",
                    event.target.checked
                  )
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

export function HistoricoSection() {
  return (
    <div className="space-y-4">
      <Input label="Buscar por palavra-chave" placeholder="Buscar eventos..." />

      <EmptyState
        title="Nenhum evento registrado"
        description="O histórico de alterações deste cliente aparecerá aqui."
      />
    </div>
  );
}
