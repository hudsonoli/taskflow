"use client";

import { FolderOpen } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { ArquivosContextView } from "./ArquivosContextView";

export function ArquivosView() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<FolderOpen className="h-5 w-5" />}
        title="Arquivos"
        description="Visão central de anexos, layouts e links — o mesmo arquivo de uma Demanda aparece aqui, sem duplicação."
      />
      <ArquivosContextView persistirNaUrl />
    </div>
  );
}
