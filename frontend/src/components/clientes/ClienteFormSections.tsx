import {
  AdministrativeSection,
  BankingFields,
  EntityForm,
  FinancialValueField,
} from "@/components/entity";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { equipesDisponiveis, responsaveisDisponiveis } from "@/lib/cliente-mock";
import { toUppercaseField } from "@/lib/uppercase-field";
import type { ClienteContato, ClienteDraft } from "@/types/cliente";

// Foco laranja (token color-primary) aplicado via className — sem criar
// prop nova em Input/Select, que continuam compartilhados por outras 6
// telas de cadastro sem nenhuma alteração de comportamento.
const FOCUS_PRIMARY_CLASSNAME = "focus:!border-primary";

// Ordem oficial dos estados de Cliente — mantida em sincronia com
// ClienteStatus (types/cliente.ts) e com o mapeamento de cor em
// ClientesView.tsx (clienteStatusTone).
const statusOptions = [
  { value: "Ativo", label: "Ativo" },
  { value: "Suspenso", label: "Suspenso" },
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
  siglaEditavel: boolean;
};

export function DadosSection({
  draft,
  onChange,
  onNomeFantasiaChange,
  onSiglaChange,
  siglaEditavel,
}: DadosSectionProps) {
  return (
    <div className="grid gap-x-4 gap-y-2.5 md:grid-cols-2">
      <Input
        label="Código Interno"
        value={draft.codigoInterno}
        readOnly
        density="compact"
        className={`bg-zinc-50 text-zinc-500 ${FOCUS_PRIMARY_CLASSNAME}`}
      />

      <Input
        label="CNPJ/CPF"
        value={draft.documento}
        readOnly
        density="compact"
        className={`bg-zinc-50 text-zinc-500 ${FOCUS_PRIMARY_CLASSNAME}`}
      />

      <Input
        label="Nome Fantasia"
        value={draft.nomeFantasia}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => onNomeFantasiaChange(toUppercaseField(event.target.value))}
      />

      <Input
        label="Razão Social / Nome"
        value={draft.nomeRazaoSocial}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            nomeRazaoSocial: toUppercaseField(event.target.value),
          }))
        }
      />

      <div>
        <Input
          label="Sigla"
          value={draft.sigla}
          density="compact"
          readOnly={!siglaEditavel}
          title={
            siglaEditavel
              ? undefined
              : "A sigla é definida no cadastro inicial e não pode ser alterada depois."
          }
          className={
            siglaEditavel
              ? FOCUS_PRIMARY_CLASSNAME
              : `cursor-not-allowed bg-zinc-50 text-zinc-500 ${FOCUS_PRIMARY_CLASSNAME}`
          }
          onChange={
            siglaEditavel
              ? (event) => onSiglaChange(toUppercaseField(event.target.value))
              : undefined
          }
        />

        {!siglaEditavel ? (
          <p className="mt-1 text-[10px] font-normal leading-snug text-zinc-400">
            A sigla é definida no cadastro inicial e não pode ser alterada depois.
          </p>
        ) : null}
      </div>

      <Select
        label="Status"
        options={statusOptions}
        value={draft.status}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
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
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({ ...current, email: event.target.value }))
        }
      />

      <Input
        label="Telefone"
        value={draft.telefone}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({ ...current, telefone: event.target.value }))
        }
      />

      <Input
        label="Celular"
        value={draft.celular}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({ ...current, celular: event.target.value }))
        }
      />

      <Input
        label="Site"
        value={draft.site}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
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
    <div className="grid gap-x-4 gap-y-2.5 md:grid-cols-2">
      <Input
        label="CEP"
        value={draft.endereco.cep}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("cep", event.target.value)}
      />

      <Input
        label="Logradouro"
        value={draft.endereco.logradouro}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("logradouro", event.target.value)}
      />

      <Input
        label="Número"
        value={draft.endereco.numero}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("numero", event.target.value)}
      />

      <Input
        label="Complemento"
        value={draft.endereco.complemento}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("complemento", event.target.value)}
      />

      <Input
        label="Bairro"
        value={draft.endereco.bairro}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("bairro", event.target.value)}
      />

      <Input
        label="Cidade"
        value={draft.endereco.cidade}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("cidade", event.target.value)}
      />

      <Select
        label="UF"
        options={ufOptions}
        value={draft.endereco.uf}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("uf", event.target.value)}
      />

      <Input
        label="País"
        value={draft.endereco.pais}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("pais", event.target.value)}
      />

      <Select
        label="Tipo"
        options={tipoEnderecoOptions}
        value={draft.endereco.tipo}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) => update("tipo", event.target.value)}
      />
    </div>
  );
}

export function EquipeSection({ draft, onChange }: SectionProps) {
  return (
    <div className="grid gap-x-4 gap-y-2.5 md:grid-cols-2">
      <Select
        label="Equipe Responsável"
        options={equipeResponsavelOptions}
        value={draft.equipeResponsavelId ?? ""}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
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
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
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
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
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
          <div className="grid gap-x-4 gap-y-2.5 md:grid-cols-2">
            <Input
              label="Nome"
              value={contato.nome}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateContato(contato.id, "nome", event.target.value)
              }
            />

            <Input
              label="E-mail"
              type="email"
              value={contato.email}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateContato(contato.id, "email", event.target.value)
              }
            />

            <Input
              label="Telefone"
              value={contato.telefone}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateContato(contato.id, "telefone", event.target.value)
              }
            />

            <Input
              label="Celular"
              value={contato.celular}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateContato(contato.id, "celular", event.target.value)
              }
            />

            <Input
              label="Cargo"
              value={contato.cargo}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateContato(contato.id, "cargo", event.target.value)
              }
            />

            <Input
              label="Aniversário"
              type="date"
              value={contato.aniversario}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateContato(contato.id, "aniversario", event.target.value)
              }
            />
          </div>

          <div className="mt-3 flex items-center justify-between">
            <label className="flex items-center gap-2 text-[11px] font-normal text-zinc-500">
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

/**
 * Dados sensíveis (ver comentário de segurança em ClienteAdministrativo,
 * types/cliente.ts) — só aparece dentro do modo Edit do EntityDrawer, para
 * perfis autorizados (hasAdministrativeAccess, lib/access-control.ts),
 * nunca na tabela, no Peek ou em buscas. É a composição Cliente-específica
 * (lê/grava ClienteDraft.administrativo) dos componentes genéricos e
 * reutilizáveis de entity/ (AdministrativeSection, FinancialValueField,
 * BankingFields) — esses componentes não conhecem Cliente nem checam
 * permissão; quem decide isso é ClienteEditFormBody.tsx.
 */
export function AdministrativoSection({ draft, onChange }: SectionProps) {
  function updateFeeMensal<K extends keyof ClienteDraft["administrativo"]["feeMensal"]>(
    field: K,
    value: ClienteDraft["administrativo"]["feeMensal"][K]
  ) {
    onChange((current) => ({
      ...current,
      administrativo: {
        ...current.administrativo,
        feeMensal: { ...current.administrativo.feeMensal, [field]: value },
      },
    }));
  }

  return (
    <AdministrativeSection>
      <div>
        <h4 className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
          Financeiro
        </h4>

        <div className="mt-3">
          <EntityForm>
            <div className="col-span-12 md:col-span-6">
              <FinancialValueField
                label="Fee Mensal"
                value={draft.administrativo.feeMensal.valor}
                className={FOCUS_PRIMARY_CLASSNAME}
                onChange={(valor) => updateFeeMensal("valor", valor)}
              />
            </div>

            <div className="col-span-12 md:col-span-6">
              <Input
                label="Data de início"
                type="date"
                value={draft.administrativo.feeMensal.dataInicio}
                density="compact"
                className={FOCUS_PRIMARY_CLASSNAME}
                onChange={(event) => updateFeeMensal("dataInicio", event.target.value)}
              />
            </div>

            <div className="col-span-12">
              <Textarea
                label="Observação"
                value={draft.administrativo.feeMensal.observacao}
                density="compact"
                className={FOCUS_PRIMARY_CLASSNAME}
                onChange={(event) => updateFeeMensal("observacao", event.target.value)}
              />
            </div>
          </EntityForm>
        </div>
      </div>

      <div>
        <h4 className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
          Dados Bancários
        </h4>

        <div className="mt-3">
          <BankingFields
            value={draft.administrativo.dadosBancarios}
            className={FOCUS_PRIMARY_CLASSNAME}
            onChange={(updater) =>
              onChange((current) => ({
                ...current,
                administrativo: {
                  ...current.administrativo,
                  dadosBancarios: updater(current.administrativo.dadosBancarios),
                },
              }))
            }
          />
        </div>
      </div>
    </AdministrativeSection>
  );
}
