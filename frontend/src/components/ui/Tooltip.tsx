import { cloneElement, isValidElement, useId, type ReactElement } from "react";

type TooltipPlacement = "bottom-start" | "right";

type TooltipProps = {
  content: string;
  placement?: TooltipPlacement;
  children: ReactElement<{ "aria-describedby"?: string }>;
};

// Único componente de tooltip do sistema — consolida as duas
// implementações divergentes que existiam em Header.tsx (abre para baixo)
// e AgendaList.tsx (abre para o lado, sem aria-describedby). Ambas migram
// para este componente (ver docs/design-system/13-tokens-visuais.md).
const placementClassNames: Record<TooltipPlacement, string> = {
  "bottom-start":
    "left-0 top-full mt-1.5 origin-top-left",
  right:
    "left-full top-1/2 ml-2 -translate-y-1/2 translate-x-1 origin-left group-hover:translate-x-0 group-focus-within:translate-x-0",
};

export function Tooltip({ content, placement = "bottom-start", children }: TooltipProps) {
  const id = useId();
  const trigger = isValidElement(children)
    ? cloneElement(children, { "aria-describedby": id })
    : children;

  return (
    <span className="group relative inline-flex">
      {trigger}
      <span
        id={id}
        role="tooltip"
        className={`pointer-events-none absolute z-20 w-max max-w-[220px] whitespace-nowrap rounded-lg bg-zinc-900 px-2.5 py-1.5 text-xs font-medium text-white opacity-0 shadow-lg transition-all duration-150 group-hover:opacity-100 group-focus-within:opacity-100 ${placementClassNames[placement]}`}
      >
        {content}
      </span>
    </span>
  );
}
