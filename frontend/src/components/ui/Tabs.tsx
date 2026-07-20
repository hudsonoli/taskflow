type Tab = {
  id: string;
  label: string;
};

type TabsDensity = "compact" | "default";

type TabsProps = {
  tabs: Tab[];
  activeTab: string;
  onChange: (id: string) => void;
  density?: TabsDensity;
};

const tabPaddingClassNames: Record<TabsDensity, string> = {
  compact: "px-3 py-2",
  default: "px-4 py-3",
};

// default inalterado (text-sm font-medium, igual ao original) — os 7
// consumidores atuais de Tabs não mudam de aparência. compact é usado hoje
// só pelo fallback mobile de EntityFormNav.
const tabTextClassNames: Record<TabsDensity, string> = {
  compact: "text-[11px] font-normal",
  default: "text-sm font-medium",
};

export function Tabs({ tabs, activeTab, onChange, density = "default" }: TabsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto border-b border-zinc-100">
      {tabs.map((tab) => {
        const active = tab.id === activeTab;

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`shrink-0 rounded-t-sm border-b-2 ${tabPaddingClassNames[density]} ${tabTextClassNames[density]} transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 ${
              active
                ? "border-zinc-900 text-zinc-900"
                : "border-transparent text-zinc-500 hover:text-zinc-700"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
