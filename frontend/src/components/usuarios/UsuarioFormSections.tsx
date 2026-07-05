import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  departamentos,
  generateId,
  generateInitials,
  mockCepLookup,
  paginasPrincipais,
  perfis,
} from "@/lib/usuario-mock";
import type {
  HistoricoUsuario,
  UsuarioDraft,
  UsuarioEndereco,
  UsuarioInformacoes,
} from "@/types/usuario";

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
    <div className="grid gap-4 md:grid-cols-2">
      <Input
        label="Código Interno"
        value={draft.codigoInterno}
        readOnly
        className="bg-zinc-50 text-zinc-500"
      />

      <Input
        label="Nome"
        value={draft.nome}
        onChange={(event) =>
          onChange((current) => ({ ...current, nome: event.target.value }))
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

      <Input
        label="Squad"
        value={draft.squad}
        onChange={(event) =>
          onChange((current) => ({ ...current, squad: event.target.value }))
        }
      />

      <Select
        label="Página Principal"
        options={paginaOptions}
        value={draft.paginaPrincipal}
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
        onChange={(event) =>
          onChange((current) => ({ ...current, perfil: event.target.value }))
        }
      />

      <label className="flex items-center gap-2 text-sm text-zinc-700">
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

      <label className="flex items-center gap-2 text-sm text-zinc-700">
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
          <p className="mb-2 text-sm font-semibold text-zinc-900">{grupo}</p>

          <div className="overflow-hidden rounded-2xl border border-zinc-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Módulo</th>
                  <th className="px-4 py-3 text-center font-medium">
                    Leitura
                  </th>
                  <th className="px-4 py-3 text-center font-medium">
                    Escrita
                  </th>
                  <th className="px-4 py-3 text-center font-medium">
                    Excluir
                  </th>
                  <th className="px-4 py-3 text-center font-medium">
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
                      <td className="px-4 py-3 font-medium text-zinc-900">
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
            <p className="text-sm font-semibold text-zinc-900">
              Endereço {index + 1}
            </p>

            <button
              type="button"
              onClick={() => removeEndereco(endereco.id)}
              className="text-xs font-medium text-zinc-400 underline decoration-dotted hover:text-zinc-700"
            >
              Remover
            </button>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="CEP"
              value={endereco.cep}
              onChange={(event) => updateCep(endereco.id, event.target.value)}
            />

            <Input
              label="Logradouro"
              value={endereco.logradouro}
              onChange={(event) =>
                updateEndereco(endereco.id, "logradouro", event.target.value)
              }
            />

            <Input
              label="Número"
              value={endereco.numero}
              onChange={(event) =>
                updateEndereco(endereco.id, "numero", event.target.value)
              }
            />

            <Input
              label="Complemento"
              value={endereco.complemento}
              onChange={(event) =>
                updateEndereco(endereco.id, "complemento", event.target.value)
              }
            />

            <Input
              label="Bairro"
              value={endereco.bairro}
              onChange={(event) =>
                updateEndereco(endereco.id, "bairro", event.target.value)
              }
            />

            <Input
              label="Caixa Postal"
              value={endereco.caixaPostal}
              onChange={(event) =>
                updateEndereco(endereco.id, "caixaPostal", event.target.value)
              }
            />

            <Input
              label="País"
              value={endereco.pais}
              onChange={(event) =>
                updateEndereco(endereco.id, "pais", event.target.value)
              }
            />

            <Select
              label="UF"
              options={ufOptions}
              value={endereco.uf}
              onChange={(event) =>
                updateEndereco(endereco.id, "uf", event.target.value)
              }
            />

            <Input
              label="Cidade"
              value={endereco.cidade}
              onChange={(event) =>
                updateEndereco(endereco.id, "cidade", event.target.value)
              }
            />

            <Select
              label="Tipo"
              options={tipoEnderecoOptions}
              value={endereco.tipo}
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
        className="w-full rounded-2xl border border-dashed border-zinc-300 px-4 py-3 text-sm font-medium text-zinc-500 hover:bg-zinc-50"
      >
        + Novo Endereço
      </button>
    </div>
  );
}

export function InformacoesSection({ draft, onChange }: SectionProps) {
  function update(field: keyof UsuarioInformacoes, value: string) {
    onChange((current) => ({
      ...current,
      informacoes: { ...current.informacoes, [field]: value },
    }));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-zinc-900 text-lg font-semibold text-white">
          {generateInitials(draft.nome)}
        </div>

        <button
          type="button"
          className="rounded-2xl border border-dashed border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-500 hover:bg-zinc-50"
        >
          Alterar foto (mock)
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Input
          label="Telefone"
          value={draft.informacoes.telefone}
          onChange={(event) => update("telefone", event.target.value)}
        />

        <Input
          label="Celular"
          value={draft.informacoes.celular}
          onChange={(event) => update("celular", event.target.value)}
        />

        <Input
          label="Data de Nascimento"
          type="date"
          value={draft.informacoes.dataNascimento}
          onChange={(event) => update("dataNascimento", event.target.value)}
        />

        <Input
          label="Chave Pix"
          value={draft.informacoes.chavePix}
          onChange={(event) => update("chavePix", event.target.value)}
        />

        <Input
          label="Banco"
          value={draft.informacoes.banco}
          onChange={(event) => update("banco", event.target.value)}
        />

        <Input
          label="Agência"
          value={draft.informacoes.agencia}
          onChange={(event) => update("agencia", event.target.value)}
        />

        <Input
          label="Conta"
          value={draft.informacoes.conta}
          onChange={(event) => update("conta", event.target.value)}
        />

        <Input
          label="RG"
          value={draft.informacoes.rg}
          onChange={(event) => update("rg", event.target.value)}
        />

        <Input
          label="CPF"
          value={draft.informacoes.cpf}
          onChange={(event) => update("cpf", event.target.value)}
        />
      </div>
    </div>
  );
}

const historicoMock: HistoricoUsuario[] = [
  {
    id: "evento-1",
    usuarioId: "sistema",
    usuario: "Sistema",
    dataHora: "04/07/2026 09:12",
    dispositivo: "Desktop - Chrome",
    ipOrigem: "192.168.0.10",
    acao: "Cadastro criado.",
  },
  {
    id: "evento-2",
    usuarioId: "user-1",
    usuario: "Hudson Cunha",
    dataHora: "04/07/2026 09:20",
    dispositivo: "Desktop - Chrome",
    ipOrigem: "192.168.0.10",
    acao: "Departamento atualizado.",
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
