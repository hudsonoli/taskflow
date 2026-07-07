import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";

const statusOptions = [
  { value: "ativo", label: "Ativo" },
  { value: "em-revisao", label: "Em revisão" },
  { value: "inativo", label: "Inativo" },
];

export function DesignSystemInputs() {
  return (
    <WorkspaceSection
      title="Campos"
      description="Entradas de texto, seleção e textos longos."
    >
      <div className="grid gap-5 md:grid-cols-2">
        <Input
          label="Nome"
          placeholder="Digite o nome"
          defaultValue="Projeto Operacional"
        />

        <Input
          label="E-mail"
          placeholder="nome@empresa.com.br"
          defaultValue="contato@taskfloww.com.br"
        />

        <Select
          label="Status"
          defaultValue="em-revisao"
          options={statusOptions}
        />

        <Input label="Código interno" placeholder="#1001" defaultValue="#1001" />

        <div className="md:col-span-2">
          <Textarea
            label="Descrição"
            defaultValue="Briefing interno para validação do componente de texto longo."
          />
        </div>
      </div>
    </WorkspaceSection>
  );
}
