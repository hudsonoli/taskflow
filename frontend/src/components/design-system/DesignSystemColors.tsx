import { Card } from "@/components/ui/Card";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";

const colors = [
  {
    name: "Background",
    value: "#f4f1ec",
    className: "bg-[#f4f1ec]",
  },
  {
    name: "Surface",
    value: "#ffffff",
    className: "bg-white",
  },
  {
    name: "Text",
    value: "#18181b",
    className: "bg-zinc-900",
  },
  {
    name: "Muted",
    value: "#71717a",
    className: "bg-zinc-500",
  },
  {
    name: "Border",
    value: "#f4f4f5",
    className: "bg-zinc-100",
  },
  {
    name: "Soft",
    value: "#faf8f4",
    className: "bg-[#faf8f4]",
  },
];

export function DesignSystemColors() {
  return (
    <WorkspaceSection
      title="Cores"
      description="Paleta base usada nas superfícies, bordas e textos."
    >
      <div className="grid gap-5 md:grid-cols-3">
        {colors.map((color) => (
          <Card key={color.name}>
            <div
              className={`h-16 rounded-2xl border border-zinc-100 ${color.className}`}
            />
            <p className="mt-4 text-sm font-semibold text-zinc-900">
              {color.name}
            </p>
            <p className="mt-1 font-mono text-xs text-zinc-500">
              {color.value}
            </p>
          </Card>
        ))}
      </div>
    </WorkspaceSection>
  );
}
