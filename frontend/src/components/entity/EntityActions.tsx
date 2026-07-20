import { Button } from "@/components/ui/Button";

export type EntityActionVariant = "peek" | "edit";

export type EntityActionButton = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  tone?: "default" | "danger";
};

export type EntityActionsProps = {
  variant: EntityActionVariant;
  primaryAction: EntityActionButton;
  secondaryActions?: EntityActionButton[];
  // neutral continua sendo o default, alinhado ao default de
  // ui/Button.tsx — decisão revertida nesta fase (a hierarquia completa de
  // botões/ações será definida em fase própria). colorScheme="brand" é
  // usado explicitamente pelos consumidores que já adotaram a ação
  // principal em laranja (ex.: Clientes, Usuários).
  colorScheme?: "neutral" | "brand";
};

function ActionButton({
  action,
  isPrimary,
  colorScheme,
}: {
  action: EntityActionButton;
  isPrimary: boolean;
  colorScheme: "neutral" | "brand";
}) {
  const isDanger = action.tone === "danger";

  return (
    <Button
      type="button"
      variant={isDanger ? "danger" : isPrimary ? "primary" : "secondary"}
      size="sm"
      colorScheme={colorScheme}
      loading={action.loading}
      onClick={action.onClick}
      disabled={action.disabled}
    >
      {action.label}
    </Button>
  );
}

/**
 * Cluster de ações do rodapé do EntityDrawer. Ações são uma coleção genérica
 * (primaryAction/secondaryActions), não callbacks nomeados fixos
 * (onSave/onDelete/onDuplicate) — o conjunto de ações varia por entidade e
 * por permissão; a página decide o que incluir e nomeia seus próprios
 * handlers (entity-component-api.md, seção 8/12). Nunca abre ConfirmDialog
 * sozinho: tone="danger" é só sinalização visual, a confirmação de ações
 * destrutivas é responsabilidade da página.
 */
export function EntityActions({
  primaryAction,
  secondaryActions = [],
  colorScheme = "neutral",
}: EntityActionsProps) {
  return (
    <footer className="flex shrink-0 items-center justify-end gap-2 border-t border-zinc-100 px-3 py-2.5">
      {secondaryActions.map((action) => (
        <ActionButton key={action.label} action={action} isPrimary={false} colorScheme={colorScheme} />
      ))}

      <ActionButton action={primaryAction} isPrimary colorScheme={colorScheme} />
    </footer>
  );
}
