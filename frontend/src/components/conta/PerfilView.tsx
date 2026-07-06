"use client";

import { useState } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { currentUser, getCurrentUserInitials } from "@/lib/conta-mock";

const languageOptions = [
  { value: "pt-BR", label: "Português (Brasil)" },
  { value: "en-US", label: "English (United States)" },
  { value: "es-ES", label: "Español" },
];

const themeOptions = [
  { value: "system", label: "Sistema" },
  { value: "light", label: "Claro" },
  { value: "dark", label: "Escuro" },
];

const timezoneOptions = [
  { value: "America/Sao_Paulo", label: "America/Sao_Paulo" },
  { value: "America/Manaus", label: "America/Manaus" },
  { value: "Europe/Lisbon", label: "Europe/Lisbon" },
];

const profileMeta = {
  ultimoAcesso: "05/07/2026 às 18:42",
  ultimoIp: "192.168.0.24",
  ultimoDispositivo: "MacBook Pro - Chrome",
  ultimaAlteracao: "04/07/2026 às 09:18",
  responsavelAlteracao: "Sistema / João Silva",
};

export function PerfilView() {
  const [form, setForm] = useState({
    nome: currentUser.nome,
    email: currentUser.email,
    telefone: currentUser.telefone,
    celular: currentUser.celular,
    cargo: currentUser.cargo,
    departamento: currentUser.departamento,
    idioma: "pt-BR",
    tema: "system",
    fusoHorario: "America/Sao_Paulo",
    assinaturaEmail: `Atenciosamente,
João Silva`,
  });

  const avatarSrc = currentUser.avatarThumbnail ?? currentUser.avatarUrl;
  const initials = getCurrentUserInitials(currentUser.nome);

  function handleEditPhoto() {
    console.log("editar foto");
  }

  return (
    <div className="p-8">
      <PageHeader
        title="Perfil"
        description="Dados pessoais e preferências da sua conta."
      />

      <div className="grid gap-6 xl:grid-cols-[280px_1fr]">
        <div className="space-y-6">
          <Card>
            <div className="flex flex-col items-center text-center">
              <div className="relative flex h-28 w-28 items-center justify-center overflow-hidden rounded-full bg-zinc-900 text-3xl font-bold text-white shadow-sm">
                {avatarSrc ? (
                  <Image
                    src={avatarSrc}
                    alt={form.nome}
                    width={112}
                    height={112}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <span>{initials}</span>
                )}
              </div>

              <p className="mt-4 text-lg font-semibold text-zinc-900">{form.nome}</p>
              <p className="text-sm text-zinc-500">{form.cargo}</p>
              <p className="text-sm text-zinc-500">{form.departamento}</p>

              <Button variant="secondary" className="mt-5 w-full" onClick={handleEditPhoto}>
                Editar Foto
              </Button>
            </div>
          </Card>

          <Card>
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium text-zinc-500">Último acesso</p>
                <p className="mt-1 text-sm text-zinc-700">{profileMeta.ultimoAcesso}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-zinc-500">Último IP</p>
                <p className="mt-1 text-sm text-zinc-700">{profileMeta.ultimoIp}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-zinc-500">Dispositivo do último acesso</p>
                <p className="mt-1 text-sm text-zinc-700">{profileMeta.ultimoDispositivo}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium text-zinc-500">Última alteração do perfil</p>
                <p className="mt-1 text-sm text-zinc-700">{profileMeta.ultimaAlteracao}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-zinc-500">Usuário responsável</p>
                <p className="mt-1 text-sm text-zinc-700">{profileMeta.responsavelAlteracao}</p>
              </div>
            </div>
          </Card>
        </div>

        <Card>
          <div className="grid gap-5 md:grid-cols-2">
            <Input label="Nome" value={form.nome} onChange={(event) => setForm({ ...form, nome: event.target.value })} />
            <Input label="E-mail" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
            <Input label="Telefone" value={form.telefone} onChange={(event) => setForm({ ...form, telefone: event.target.value })} />
            <Input label="Celular" value={form.celular} onChange={(event) => setForm({ ...form, celular: event.target.value })} />
            <Input label="Cargo" value={form.cargo} onChange={(event) => setForm({ ...form, cargo: event.target.value })} />
            <Input label="Departamento" value={form.departamento} onChange={(event) => setForm({ ...form, departamento: event.target.value })} />
            <Select label="Idioma" options={languageOptions} value={form.idioma} onChange={(event) => setForm({ ...form, idioma: event.target.value })} />
            <Select label="Tema" options={themeOptions} value={form.tema} onChange={(event) => setForm({ ...form, tema: event.target.value })} />
            <Select label="Fuso horário" options={timezoneOptions} value={form.fusoHorario} onChange={(event) => setForm({ ...form, fusoHorario: event.target.value })} />
            <div className="md:col-span-2">
              <Textarea
                label="Assinatura de e-mail"
                value={form.assinaturaEmail}
                onChange={(event) => setForm({ ...form, assinaturaEmail: event.target.value })}
              />
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <Button type="button" onClick={() => console.log("save profile", form)}>
              Salvar
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
