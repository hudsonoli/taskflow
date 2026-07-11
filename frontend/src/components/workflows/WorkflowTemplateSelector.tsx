import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { workflowTemplatesMock } from "@/lib/workflows-mock";

type WorkflowTemplateSelectorProps = {
  selectedTemplateId: string;
  onTemplateChange: (templateId: string) => void;
  onApplyTemplate: () => void;
};

export function WorkflowTemplateSelector({
  selectedTemplateId,
  onTemplateChange,
  onApplyTemplate,
}: WorkflowTemplateSelectorProps) {
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
      <Select
        label="Template de workflow"
        value={selectedTemplateId}
        onChange={(event) => onTemplateChange(event.target.value)}
        options={workflowTemplatesMock.map((template) => ({
          value: template.id,
          label: template.nome,
        }))}
      />
      <Button type="button" onClick={onApplyTemplate}>
        Aplicar template
      </Button>
    </div>
  );
}
