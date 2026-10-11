"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Tabs } from "@/components/ui/Tabs";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { EmpresaDadosSection } from "@/components/plataforma/EmpresaDadosSection";
import { EmpresaPersonalizacaoSection } from "@/components/plataforma/EmpresaPersonalizacaoSection";
import { EmpresaUsuariosSection } from "@/components/plataforma/EmpresaUsuariosSection";
import { usePlataforma } from "@/components/plataforma/PlataformaContext";
import { STATUS_EMPRESA_ROTULO } from "@/lib/plataforma";
import { obterEmpresaPlataforma } from "@/lib/plataforma-api";
import type { PlataformaEmpresa, PlataformaEmpresaStatus } from "@/types/plataforma";

const ABAS = [
  { id: "dados", label: "Dados" },
  { id: "personalizacao", label: "Personalização" },
  { id: "usuarios", label: "Usuários" },
];
const TOM_STATUS: Record<PlataformaEmpresaStatus, BadgeTone> = { ativa: "green", inativa: "amber", arquivada: "neutral" };

export function EmpresaPlataformaView({ empresaId }: { empresaId: string }) {
  const { definirEmpresaEmFoco } = usePlataforma();
  const [empresa, setEmpresa] = useState<PlataformaEmpresa | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState("dados");

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      setEmpresa(await obterEmpresaPlataforma(empresaId));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar a empresa.");
    }
  }, [empresaId]);

  useEffect(() => {
    const timeout = setTimeout(() => void carregar(), 0);
    return () => clearTimeout(timeout);
  }, [carregar]);

  // "Empresa em foco" acompanha a empresa carregada e some ao sair da página.
  useEffect(() => {
    if (empresa) definirEmpresaEmFoco({ id: empresa.id, nome: empresa.nome, slug: empresa.slug });
    return () => definirEmpresaEmFoco(null);
  }, [empresa, definirEmpresaEmFoco]);

  if (erro) return <EstadoErro mensagem={erro} onRetry={carregar} />;
  if (!empresa) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-sm text-fg-muted shadow-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando empresa…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/gestao/empresas"
          className="inline-flex items-center gap-1.5 rounded text-xs font-semibold text-fg-muted hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          <ArrowLeft size={14} /> Empresas
        </Link>
        <h2 className="text-base font-semibold text-fg">{empresa.nome}</h2>
        <Badge tone={TOM_STATUS[empresa.status]}>{STATUS_EMPRESA_ROTULO[empresa.status]}</Badge>
      </div>

      <Tabs tabs={ABAS} activeTab={aba} onChange={setAba} />

      {aba === "dados" && <EmpresaDadosSection empresa={empresa} onAtualizada={setEmpresa} />}
      {aba === "personalizacao" && <EmpresaPersonalizacaoSection empresa={empresa} />}
      {aba === "usuarios" && <EmpresaUsuariosSection empresa={empresa} onMudou={carregar} />}
    </div>
  );
}
