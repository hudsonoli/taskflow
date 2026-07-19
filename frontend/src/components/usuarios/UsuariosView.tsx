"use client";

import { useState } from "react";
import { Pencil } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { Button } from "@/components/ui/Button";
import {
  CadastroAvatar,
  CadastroIndicators,
  CadastroTable,
  CadastroToolbar,
  cadastroTableHeaderClassName,
  getCadastroTableCellClassNames,
} from "@/components/cadastros";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import type { Usuario } from "@/types/usuario-domain";
import { useUsuariosList } from "./useUsuariosList";

function usuarioStatusTone(
  status: Usuario["status"],
): "neutral" | "green" | "amber" | "red" {
  if (status === "ativo") return "green";
  if (status === "bloqueado") return "amber";
  if (status === "inativo") return "red";
  return "neutral";
}

export function UsuariosView() {
  const [searchQuery, setSearchQuery] = useState("");
  const { usuarios, status, error, retry } =
    useUsuariosList(searchQuery);

  const usuariosAtivos = usuarios.filter(
    (usuario) => usuario.status === "ativo",
  ).length;
  const usuariosGestao = usuarios.filter(
    (usuario) =>
      usuario.perfilBase === "admin" || usuario.perfilBase === "gestor",
  ).length;
  const { headerCell, cell } = getCadastroTableCellClassNames("compact");

  function renderUsuariosContent() {
    switch (status) {
      case "loading":
        return (
          <div
            role="status"
            aria-live="polite"
            className="rounded-2xl border border-zinc-100 bg-white px-4 py-10 text-center text-sm text-zinc-500 shadow-sm"
          >
            Carregando usuários...
          </div>
        );

      case "error":
        return (
          <EmptyStateIllustration
            size="compact"
            title="Não foi possível carregar os usuários"
            description={error}
            action={
              <Button size="sm" colorScheme="brand" onClick={retry}>
                Tentar novamente
              </Button>
            }
          />
        );

      case "empty":
        return (
          <EmptyStateIllustration
            size="compact"
            title="Nenhum usuário encontrado"
            description={
              searchQuery.trim()
                ? `A busca por "${searchQuery.trim()}" não retornou usuários.`
                : "Ainda não há usuários disponíveis."
            }
          />
        );

      case "success":
        return (
          <CadastroTable minWidth="820px">
            <thead className={cadastroTableHeaderClassName}>
              <tr>
                <th className={headerCell}>Usuário</th>
                <th className={headerCell}>Departamento</th>
                <th className={headerCell}>Perfil</th>
                <th className={headerCell}>Status</th>
                <th className={`${headerCell} text-right`}>Ações</th>
              </tr>
            </thead>

            <tbody>
              {usuarios.map((usuario) => (
                <tr
                  key={usuario.id}
                  className="border-b border-zinc-100 last:border-0"
                >
                  <td className={cell}>
                    <div className="flex min-w-0 items-center gap-2">
                      <CadastroAvatar label={usuario.nome} density="compact" />
                      <div className="flex min-w-0 items-baseline gap-1">
                        <span className="shrink-0 text-[11px] font-normal text-zinc-400">
                          {usuario.codigoInterno}
                        </span>
                        <span className="min-w-0 truncate text-[13px] font-normal text-zinc-900">
                          {usuario.nome}
                        </span>
                      </div>
                    </div>
                  </td>

                  <td
                    className={`${cell} text-[11px] font-normal text-zinc-500`}
                  >
                    —
                  </td>

                  <td className={cell}>
                    <StatusPill tone="neutral" density="compact">
                      {usuario.perfilLabel}
                    </StatusPill>
                  </td>

                  <td className={cell}>
                    <StatusPill
                      tone={usuarioStatusTone(usuario.status)}
                      density="compact"
                    >
                      {usuario.statusLabel}
                    </StatusPill>
                  </td>

                  <td className={`${cell} text-right`}>
                    <button
                      type="button"
                      disabled
                      aria-label={`Editar usuário ${usuario.nome}`}
                      title="Edição indisponível"
                      className="inline-flex h-7 w-7 cursor-not-allowed items-center justify-center rounded-full text-zinc-300"
                    >
                      <Pencil
                        className="h-3.5 w-3.5"
                        strokeWidth={2}
                        aria-hidden="true"
                      />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </CadastroTable>
        );
    }
  }

  return (
    <PageShell density="compact">
      <PageHeader
        title="Usuários"
        description="Gestão de usuários, cargos e permissões."
        size="section"
        actions={
          <Button size="sm" colorScheme="brand" disabled>
            Novo Usuário
          </Button>
        }
      />

      <CadastroIndicators
        density="compact"
        items={[
          { label: "Total", value: usuarios.length },
          { label: "Ativos", value: usuariosAtivos },
          { label: "Gestão", value: usuariosGestao },
        ]}
      />

      <CadastroToolbar
        density="compact"
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Pesquisar usuários..."
      />

      {renderUsuariosContent()}
    </PageShell>
  );
}
