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
import {
  departamentos,
  generateId,
  generateInitials,
  mockCepLookup,
  paginasPrincipais,
  perfis,
} from "@/lib/usuario-mock";
import type { UsuarioDraft, UsuarioEndereco } from "@/types/usuario";

// Mesmo padrão de foco laranja de ClienteFormSections.tsx — className
// passthrough, sem prop nova em Input/Select.
const FOCUS_PRIMARY_CLASSNAME = "focus:!border-primary";

const departamentoOptions = departamentos
  .filter((departamento) => departamento.ativo)
  .map((departamento) => ({
    value: departamento.id,
    label: departamento.nome,
  }));

const perfilOptions = perfis.map((item) => ({ value: item, label: item }));

const paginaOptions = paginasPrincipais.map((item) => ({
  value: item,
  label: item,
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
  { value: "Residencial", label: "Residencial" },
  { value: "Contábil", label: "Contábil" },
  { value: "Correspondência", label: "Correspondência" },
];

type SectionProps = {
  draft: UsuarioDraft;
  onChange: (updater: (current: UsuarioDraft) => UsuarioDraft) => void;
};

export function DadosSection({ draft, onChange }: SectionProps) {
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
        label="Nome"
        value={draft.nome}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({ ...current, nome: event.target.value }))
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

      <Select
        label="Departamento"
        options={departamentoOptions}
        value={draft.departamentoId}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            departamentoId: event.target.value,
          }))
        }
      />

      <Input
        label="Squad"
        value={draft.squad}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({ ...current, squad: event.target.value }))
        }
      />

      <Select
        label="Página Principal"
        options={paginaOptions}
        value={draft.paginaPrincipal}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            paginaPrincipal: event.target.value,
          }))
        }
      />

      <Select
        label="Perfil"
        options={perfilOptions}
        value={draft.perfil}
        density="compact"
        className={FOCUS_PRIMARY_CLASSNAME}
        onChange={(event) =>
          onChange((current) => ({
            ...current,
            perfil: event.target.value as UsuarioDraft["perfil"],
          }))
        }
      />

      <label className="flex items-center gap-2 text-[11px] font-normal text-zinc-500">
        <input
          type="checkbox"
          checked={draft.acessoSistema}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              acessoSistema: event.target.checked,
            }))
          }
        />
        Acesso ao sistema
      </label>

      <label className="flex items-center gap-2 text-[11px] font-normal text-zinc-500">
        <input
          type="checkbox"
          checked={draft.emAtividade}
          onChange={(event) =>
            onChange((current) => ({
              ...current,
              emAtividade: event.target.checked,
            }))
          }
        />
        Em atividade
      </label>
    </div>
  );
}

/**
 * Matriz de permissões — mantida como está (própria tabela interna, não
 * convertida para EntityForm/12 colunas): é uma grade genuinamente
 * tabular (módulo × leitura/escrita/excluir/aprovar), não um formulário de
 * campos. Redesenhar essa matriz está fora do escopo desta migração
 * visual.
 */
export function PermissoesSection({ draft, onChange }: SectionProps) {
  function toggle(
    id: string,
    campo: "leitura" | "escrita" | "excluir" | "aprovar"
  ) {
    onChange((current) => ({
      ...current,
      permissoes: current.permissoes.map((item) =>
        item.id === id ? { ...item, [campo]: !item[campo] } : item
      ),
    }));
  }

  const grupos = Array.from(
    new Set(draft.permissoes.map((item) => item.grupo))
  );

  return (
    <div className="space-y-6">
      {grupos.map((grupo) => (
        <div key={grupo}>
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            {grupo}
          </p>

          <div className="overflow-hidden rounded-2xl border border-zinc-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
                <tr>
                  <th className="px-4 py-3 text-[11px] font-medium">Módulo</th>
                  <th className="px-4 py-3 text-center text-[11px] font-medium">
                    Leitura
                  </th>
                  <th className="px-4 py-3 text-center text-[11px] font-medium">
                    Escrita
                  </th>
                  <th className="px-4 py-3 text-center text-[11px] font-medium">
                    Excluir
                  </th>
                  <th className="px-4 py-3 text-center text-[11px] font-medium">
                    Aprovar
                  </th>
                </tr>
              </thead>

              <tbody>
                {draft.permissoes
                  .filter((item) => item.grupo === grupo)
                  .map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-zinc-100 last:border-0"
                    >
                      <td className="px-4 py-3 text-[11px] font-normal text-zinc-900">
                        {item.modulo}
                      </td>

                      <td className="px-4 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={item.leitura}
                          onChange={() => toggle(item.id, "leitura")}
                        />
                      </td>

                      <td className="px-4 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={item.escrita}
                          onChange={() => toggle(item.id, "escrita")}
                        />
                      </td>

                      <td className="px-4 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={item.excluir}
                          onChange={() => toggle(item.id, "excluir")}
                        />
                      </td>

                      <td className="px-4 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={item.aprovar}
                          onChange={() => toggle(item.id, "aprovar")}
                        />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

function createEmptyEndereco(): UsuarioEndereco {
  return {
    id: generateId("endereco"),
    cep: "",
    logradouro: "",
    numero: "",
    complemento: "",
    bairro: "",
    caixaPostal: "",
    pais: "Brasil",
    uf: "",
    cidade: "",
    tipo: "Comercial",
  };
}

export function EnderecosSection({ draft, onChange }: SectionProps) {
  function updateEndereco(
    id: string,
    field: keyof UsuarioEndereco,
    value: string
  ) {
    onChange((current) => ({
      ...current,
      enderecos: current.enderecos.map((endereco) =>
        endereco.id === id ? { ...endereco, [field]: value } : endereco
      ),
    }));
  }

  function updateCep(id: string, value: string) {
    const digits = value.replace(/\D/g, "").slice(0, 8);

    onChange((current) => ({
      ...current,
      enderecos: current.enderecos.map((endereco) => {
        if (endereco.id !== id) return endereco;

        const atualizado = { ...endereco, cep: digits };

        if (digits.length === 8) {
          return { ...atualizado, ...mockCepLookup(digits) };
        }

        return atualizado;
      }),
    }));
  }

  function addEndereco() {
    onChange((current) => ({
      ...current,
      enderecos: [...current.enderecos, createEmptyEndereco()],
    }));
  }

  function removeEndereco(id: string) {
    onChange((current) => ({
      ...current,
      enderecos: current.enderecos.filter((endereco) => endereco.id !== id),
    }));
  }

  return (
    <div className="space-y-4">
      {draft.enderecos.length === 0 && (
        <EmptyState
          title="Nenhum endereço adicionado"
          description="Adicione ao menos um endereço para o colaborador."
        />
      )}

      {draft.enderecos.map((endereco, index) => (
        <div
          key={endereco.id}
          className="rounded-2xl border border-zinc-200 p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
              Endereço {index + 1}
            </p>

            <button
              type="button"
              onClick={() => removeEndereco(endereco.id)}
              className="text-[11px] font-medium text-zinc-400 underline decoration-dotted hover:text-zinc-700"
            >
              Remover
            </button>
          </div>

          <div className="grid gap-x-4 gap-y-2.5 md:grid-cols-2">
            <Input
              label="CEP"
              value={endereco.cep}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) => updateCep(endereco.id, event.target.value)}
            />

            <Input
              label="Logradouro"
              value={endereco.logradouro}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "logradouro", event.target.value)
              }
            />

            <Input
              label="Número"
              value={endereco.numero}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "numero", event.target.value)
              }
            />

            <Input
              label="Complemento"
              value={endereco.complemento}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "complemento", event.target.value)
              }
            />

            <Input
              label="Bairro"
              value={endereco.bairro}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "bairro", event.target.value)
              }
            />

            <Input
              label="Caixa Postal"
              value={endereco.caixaPostal}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "caixaPostal", event.target.value)
              }
            />

            <Input
              label="País"
              value={endereco.pais}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "pais", event.target.value)
              }
            />

            <Select
              label="UF"
              options={ufOptions}
              value={endereco.uf}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "uf", event.target.value)
              }
            />

            <Input
              label="Cidade"
              value={endereco.cidade}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "cidade", event.target.value)
              }
            />

            <Select
              label="Tipo"
              options={tipoEnderecoOptions}
              value={endereco.tipo}
              density="compact"
              className={FOCUS_PRIMARY_CLASSNAME}
              onChange={(event) =>
                updateEndereco(endereco.id, "tipo", event.target.value)
              }
            />
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addEndereco}
        className="w-full rounded-2xl border border-dashed border-zinc-300 px-4 py-3 text-[13px] font-medium text-zinc-500 hover:bg-zinc-50"
      >
        + Novo Endereço
      </button>
    </div>
  );
}

/**
 * Dados pessoais apenas — chavePix/banco/agencia/conta não vivem mais aqui
 * (Opção A aprovada): saíram para AdministrativoSection, protegidos por
 * hasAdministrativeAccess. Esta seção nunca deve voltar a acumular dado
 * financeiro/bancário.
 */
export function InformacoesSection({ draft, onChange }: SectionProps) {
  function update(field: keyof UsuarioDraft["informacoes"], value: string) {
    onChange((current) => ({
      ...current,
      informacoes: { ...current.informacoes, [field]: value },
    }));
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-zinc-900 text-sm font-semibold text-white">
          {generateInitials(draft.nome)}
        </div>

        <button
          type="button"
          className="rounded-2xl border border-dashed border-zinc-300 px-4 py-2 text-[13px] font-medium text-zinc-500 hover:bg-zinc-50"
        >
          Alterar foto (mock)
        </button>
      </div>

      <div className="grid gap-x-4 gap-y-2.5 md:grid-cols-2">
        <Input
          label="Telefone"
          value={draft.informacoes.telefone}
          density="compact"
          className={FOCUS_PRIMARY_CLASSNAME}
          onChange={(event) => update("telefone", event.target.value)}
        />

        <Input
          label="Celular"
          value={draft.informacoes.celular}
          density="compact"
          className={FOCUS_PRIMARY_CLASSNAME}
          onChange={(event) => update("celular", event.target.value)}
        />

        <Input
          label="Data de Nascimento"
          type="date"
          value={draft.informacoes.dataNascimento}
          density="compact"
          className={FOCUS_PRIMARY_CLASSNAME}
          onChange={(event) => update("dataNascimento", event.target.value)}
        />

        <Input
          label="RG"
          value={draft.informacoes.rg}
          density="compact"
          className={FOCUS_PRIMARY_CLASSNAME}
          onChange={(event) => update("rg", event.target.value)}
        />

        <Input
          label="CPF"
          value={draft.informacoes.cpf}
          density="compact"
          className={FOCUS_PRIMARY_CLASSNAME}
          onChange={(event) => update("cpf", event.target.value)}
        />
      </div>
    </div>
  );
}

/**
 * Dados sensíveis (ver comentário de segurança em UsuarioAdministrativo,
 * types/usuario.ts) — só aparece dentro do modo Edit do EntityDrawer, para
 * perfis autorizados (hasAdministrativeAccess, lib/access-control.ts),
 * nunca na tabela, no Peek ou em buscas. Composição Usuário-específica dos
 * componentes genéricos e reutilizáveis de entity/ (AdministrativeSection,
 * FinancialValueField, BankingFields) — os mesmos usados por Clientes, sem
 * nenhuma duplicação de componente. salario é despesa; nunca confundido
 * com Fee Mensal de Clientes (receita).
 */
export function AdministrativoSection({ draft, onChange }: SectionProps) {
  function updateSalario<K extends keyof UsuarioDraft["administrativo"]["salario"]>(
    field: K,
    value: UsuarioDraft["administrativo"]["salario"][K]
  ) {
    onChange((current) => ({
      ...current,
      administrativo: {
        ...current.administrativo,
        salario: { ...current.administrativo.salario, [field]: value },
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
                label="Salário"
                value={draft.administrativo.salario.valor}
                className={FOCUS_PRIMARY_CLASSNAME}
                onChange={(valor) => updateSalario("valor", valor)}
              />
            </div>

            <div className="col-span-12 md:col-span-6">
              <Input
                label="Data de início"
                type="date"
                value={draft.administrativo.salario.dataInicio}
                density="compact"
                className={FOCUS_PRIMARY_CLASSNAME}
                onChange={(event) => updateSalario("dataInicio", event.target.value)}
              />
            </div>

            <div className="col-span-12">
              <Textarea
                label="Observação"
                value={draft.administrativo.salario.observacao}
                density="compact"
                className={FOCUS_PRIMARY_CLASSNAME}
                onChange={(event) => updateSalario("observacao", event.target.value)}
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
