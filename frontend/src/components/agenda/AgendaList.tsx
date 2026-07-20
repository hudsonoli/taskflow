"use client";

import Image from "next/image";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Tooltip } from "@/components/ui/Tooltip";
import { Phone, Mail, MessageCircle, Copy, CopyPlus } from "lucide-react";
import type { AgendaContato } from "@/types/agenda";

type AgendaListProps = {
  contacts: AgendaContato[];
};

const tipoChips: Record<
  AgendaContato["tipo"],
  { label: string; className: string }
> = {
  clientes: { label: "Cliente", className: "bg-blue-50 text-blue-700 border-blue-100" },
  fornecedores: { label: "Fornecedor", className: "bg-amber-50 text-amber-700 border-amber-100" },
  usuarios: { label: "Usuário", className: "bg-emerald-50 text-emerald-700 border-emerald-100" },
  parceiros: { label: "Parceiro", className: "bg-violet-50 text-violet-700 border-violet-100" },
  freelancers: { label: "Freelancer", className: "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-100" },
  transportadoras: { label: "Transportadora", className: "bg-sky-50 text-sky-700 border-sky-100" },
  leads: { label: "Lead", className: "bg-orange-50 text-orange-700 border-orange-100" },
  outros: { label: "Outro", className: "bg-zinc-50 text-zinc-700 border-zinc-200" },
};

function getInitials(nome: string) {
  const words = nome.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
}

function ActionIconButton({
  label,
  icon: Icon,
}: {
  label: string;
  icon: typeof Phone;
}) {
  return (
    <Tooltip content={label} placement="right">
      <button
        type="button"
        aria-label={label}
        className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-zinc-200 bg-white text-zinc-600 transition hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-1"
        onClick={() => console.log(label)}
      >
        <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
      </button>
    </Tooltip>
  );
}

function formatInteraction(value?: string) {
  if (!value) return null;
  const date = new Date(value);
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export function AgendaList({ contacts }: AgendaListProps) {
  if (contacts.length === 0) {
    return (
      <EmptyState
        title="Nenhum contato encontrado."
        description="Tente alterar os filtros ou a pesquisa."
      />
    );
  }

  return (
    <div className="space-y-4">
      {contacts.map((contact) => {
        const chip = tipoChips[contact.tipo];
        const avatarSrc = contact.avatarThumbnail ?? contact.avatarUrl;
        const initials = getInitials(contact.nome);
        const lastInteraction = formatInteraction(contact.ultimaInteracao);

        return (
          <Card key={contact.id}>
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl bg-zinc-900 text-sm font-semibold text-white">
                  {avatarSrc ? (
                    <Image
                      src={avatarSrc}
                      alt={contact.nome}
                      width={56}
                      height={56}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span>{initials}</span>
                  )}
                </div>

                <div className="min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-lg font-semibold text-zinc-900">
                      {contact.nome}
                    </h3>
                    <span
                      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${chip.className}`}
                    >
                      {chip.label}
                    </span>
                  </div>

                  <p className="text-sm text-zinc-500">
                    {contact.cargo} · {contact.departamento}
                  </p>

                  <p className="text-sm text-zinc-500">{contact.empresa}</p>

                  {lastInteraction ? (
                    <p className="text-xs text-zinc-400">
                      Última interação: {lastInteraction}
                    </p>
                  ) : null}

                  <div className="grid gap-1 text-sm text-zinc-600">
                    <p><span className="font-medium text-zinc-900">E-mail:</span> {contact.email}</p>
                    <p><span className="font-medium text-zinc-900">Telefone:</span> {contact.telefone}</p>
                    <p><span className="font-medium text-zinc-900">Celular:</span> {contact.celular}</p>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                <ActionIconButton label="Telefone" icon={Phone} />
                <ActionIconButton label="Email" icon={Mail} />
                <ActionIconButton label="WhatsApp" icon={MessageCircle} />
                <ActionIconButton label="Copiar telefone" icon={Copy} />
                <ActionIconButton label="Copiar email" icon={CopyPlus} />
                <Button type="button" variant="secondary" disabled>
                  Histórico
                </Button>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
