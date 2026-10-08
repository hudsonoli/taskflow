"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, UserPlus, Users } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { DefinirGestorModal } from "@/components/plataforma/DefinirGestorModal";
import { separarGestores } from "@/lib/plataforma";
import { listarUsuariosEmpresa } from "@/lib/plataforma-api";
import { perfilUsuarioLabels } from "@/types/usuario";
import type { PlataformaEmpresa, PlataformaUsuario } from "@/types/plataforma";

// Rótulo visível do perfil técnico (o operador aparece como "Usuário", como em todo o app).
const ROTULO_PERFIL: Record<PlataformaUsuario["perfilBase"], string> = {
  admin: perfilUsuarioLabels.admin,
  gestor: perfilUsuarioLabels.gestor,
  operador: perfilUsuarioLabels.operador,
};
const TOM_STATUS: Record<PlataformaUsuario["status"], BadgeTone> = { ativo: "green", inativo: "amber", bloqueado: "red", arquivado: "neutral" };
const ROTULO_STATUS: Record<PlataformaUsuario["status"], string> = { ativo: "Ativo", inativo: "Inativo", bloqueado: "Bloqueado", arquivado: "Arquivado" };

/**
 * Usuários da empresa em foco (só metadados). "Gestores da empresa" lista os próprios usuários com perfil Gestor — não há
 * cadastro paralelo de Gestor, e a empresa pode ter vários. Os demais (Usuário, Admin legado) aparecem abaixo. A API já
 * omite as contas de sistema. Depois de promover ou criar um Gestor a lista é recarregada na hora (sem reload da página).
 */
export function EmpresaUsuariosSection({ empresa, onMudou }: { empresa: PlataformaEmpresa; onMudou: () => void }) {
  const [usuarios, setUsuarios] = useState<PlataformaUsuario[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [novoAberto, setNovoAberto] = useState(false);

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      setUsuarios(await listarUsuariosEmpresa(empresa.id));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar os usuários.");
    }
  }, [empresa.id]);

  useEffect(() => {
    const timeout = setTimeout(() => void carregar(), 0);
    return () => clearTimeout(timeout);
  }, [carregar]);

  const { gestores, demais } = usuarios ? separarGestores(usuarios) : { gestores: [], demais: [] };
  // Enquanto a lista carrega, usa a contagem da empresa; depois, a própria lista (todos os usuários com perfil Gestor).
  const quantidade = usuarios ? gestores.length : empresa.gestoresAtivos;
  const semGestor = quantidade === 0;
  const podeCriar = empresa.status === "ativa";

  return (
    <div className="flex flex-col gap-4">
      <section aria-labelledby="gestores-da-empresa" className="rounded-xl border border-line bg-surface shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="min-w-0">
            <h3 id="gestores-da-empresa" className="text-sm font-semibold text-fg">
              Gestores da empresa · {usuarios ? gestores.length : "…"}
            </h3>
            <p className="mt-0.5 max-w-2xl text-xs text-fg-muted">
              {semGestor
                ? "Esta empresa ainda não tem Gestor. O Gestor administra a empresa por dentro (usuários, equipes, cadastros): escolha um usuário existente ou crie um novo."
                : "Gestores são usuários da própria empresa com perfil Gestor. A empresa pode ter mais de um: adicione outro escolhendo um usuário existente ou criando um novo."}
            </p>
            {!podeCriar && <p className="mt-1 text-xs font-medium text-amber-700 dark:text-amber-400">Reative a empresa para criar um Gestor.</p>}
          </div>
          <Button type="button" disabled={!podeCriar} onClick={() => setNovoAberto(true)}>
            <UserPlus size={14} /> {semGestor ? "Definir Gestor" : "Adicionar Gestor"}
          </Button>
        </div>

        {gestores.length > 0 && (
          <div className="overflow-x-auto border-t border-line">
            <table className="w-full min-w-[480px] text-left text-sm" aria-label="Gestores da empresa">
              <thead>
                <tr className="border-b border-line text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">E-mail</th>
                  <th className="px-4 py-3">Situação</th>
                </tr>
              </thead>
              <tbody>
                {gestores.map((usuario) => (
                  <tr key={usuario.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 font-semibold text-fg">{usuario.nome}</td>
                    <td className="px-4 py-3 text-fg-muted">{usuario.email}</td>
                    <td className="px-4 py-3">
                      <Badge tone={TOM_STATUS[usuario.status]}>{ROTULO_STATUS[usuario.status]}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {erro ? (
        <EstadoErro mensagem={erro} onRetry={carregar} />
      ) : !usuarios ? (
        <div className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-sm text-fg-muted shadow-sm">
          <Loader2 className="h-4 w-4 animate-spin" /> Carregando usuários…
        </div>
      ) : demais.length === 0 ? (
        gestores.length === 0 ? (
          <EmptyState icon={<Users size={18} />} title="Nenhum usuário nesta empresa" description="Crie o primeiro Gestor para começar." />
        ) : null
      ) : (
        <section aria-labelledby="demais-usuarios" className="rounded-xl border border-line bg-surface shadow-sm">
          <h3 id="demais-usuarios" className="p-4 text-sm font-semibold text-fg">
            Demais usuários · {demais.length}
          </h3>
          <div className="overflow-x-auto border-t border-line">
            <table className="w-full min-w-[520px] text-left text-sm" aria-label="Demais usuários da empresa">
              <thead>
                <tr className="border-b border-line text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">E-mail</th>
                  <th className="px-4 py-3">Perfil</th>
                  <th className="px-4 py-3">Situação</th>
                </tr>
              </thead>
              <tbody>
                {demais.map((usuario) => (
                  <tr key={usuario.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 font-semibold text-fg">{usuario.nome}</td>
                    <td className="px-4 py-3 text-fg-muted">{usuario.email}</td>
                    <td className="px-4 py-3">
                      <Badge tone="blue">{ROTULO_PERFIL[usuario.perfilBase]}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={TOM_STATUS[usuario.status]}>{ROTULO_STATUS[usuario.status]}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <DefinirGestorModal
        open={novoAberto}
        empresa={empresa}
        onClose={() => setNovoAberto(false)}
        onDefinido={() => {
          void carregar();
          onMudou();
        }}
      />
    </div>
  );
}
