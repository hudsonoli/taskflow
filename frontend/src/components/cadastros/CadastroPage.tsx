import type { ReactNode } from "react";

type CadastroPageProps = {
  title: string;
  description: string;
  toolbar: ReactNode;
  indicators: ReactNode;
  children: ReactNode;
};

export function CadastroPage({
  title,
  description,
  toolbar,
  indicators,
  children,
}: CadastroPageProps) {
  return (
    <div className="space-y-3 p-4 sm:p-5">
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">{title}</h2>
        <p className="mt-0.5 text-sm text-zinc-500">{description}</p>
      </div>

      {toolbar}
      {indicators}
      {children}
    </div>
  );
}
