"use client";

import type { ReactNode } from "react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { ErrosOnboarding, RascunhoOnboarding } from "@/lib/plataforma";

type SecaoProps = {
  rascunho: RascunhoOnboarding;
  erros: ErrosOnboarding;
  /** erros só aparecem depois da primeira tentativa de salvar (ou quando o campo já foi preenchido) */
  mostrarErros: boolean;
  atualizar: (parcial: Partial<RascunhoOnboarding>) => void;
  desabilitado: boolean;
};

function Secao({ titulo, descricao, children }: { titulo: string; descricao?: string; children: ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-3 rounded-xl border border-line p-4">
      <legend className="px-1 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{titulo}</legend>
      {descricao && <p className="-mt-1 text-xs text-fg-muted">{descricao}</p>}
      {children}
    </fieldset>
  );
}

function Erro({ texto }: { texto?: string }) {
  return texto ? <p className="mt-1 text-xs font-medium text-danger">{texto}</p> : null;
}

/** Dados da empresa: só campos reais do modelo (nome, fantasia, documento, código interno) + o slug (parte permanente da URL `/e/<slug>/...`). */
export function SecaoDadosEmpresa({
  rascunho,
  erros,
  mostrarErros,
  atualizar,
  aoEditarSlug,
  desabilitado,
}: SecaoProps & { aoEditarSlug: (valor: string) => void }) {
  return (
    <Secao titulo="Dados da empresa">
      <div>
        <Input label="Nome da empresa" value={rascunho.nome} onChange={(e) => atualizar({ nome: e.target.value })} maxLength={255} required disabled={desabilitado} />
        {mostrarErros && <Erro texto={erros.nome} />}
      </div>
      <div>
        <Input
          label="Nome de exibição (opcional)"
          value={rascunho.nomeFantasia}
          onChange={(e) => atualizar({ nomeFantasia: e.target.value })}
          maxLength={255}
          disabled={desabilitado}
        />
        <p className="mt-1 text-xs text-fg-muted">Nome mostrado no login, no cabeçalho e no título da aba. Em branco, vale o nome da empresa.</p>
      </div>
      <Input label="Documento (opcional)" value={rascunho.documento} onChange={(e) => atualizar({ documento: e.target.value })} maxLength={32} disabled={desabilitado} />
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Input
            label="Código interno"
            value={rascunho.codigoInterno}
            onChange={(e) => atualizar({ codigoInterno: e.target.value })}
            maxLength={64}
            className="font-mono uppercase"
            required
            disabled={desabilitado}
          />
          {(mostrarErros || rascunho.codigoInterno) && <Erro texto={erros.codigoInterno} />}
        </div>
        <div>
          <Input
            label="Slug (endereço da empresa)"
            value={rascunho.slug}
            onChange={(e) => aoEditarSlug(e.target.value.toLowerCase())}
            maxLength={40}
            className="font-mono"
            disabled={desabilitado}
          />
          <Erro texto={erros.slug} />
        </div>
      </div>
      <p className="text-xs text-fg-muted">
        A empresa será acessada em <span className="font-mono">/e/{rascunho.slug.trim() || "slug"}/login</span>. O slug é <strong>permanente</strong> depois de criada (faz parte
        do login, dos links e do portal de aprovação): minúsculas, números e hífen, 3–40 caracteres, único. Ele é sugerido a partir do nome — ajuste se quiser (ex.: um nome curto, sem espaços ou acentos).
      </p>
    </Secao>
  );
}

/** Identidade visual: usa o mecanismo existente (cores/tema/logo) — aplicado logo depois de criar, sem novo sistema de temas. Tudo opcional. */
export function SecaoIdentidadeVisual({
  rascunho,
  erros,
  mostrarErros,
  atualizar,
  desabilitado,
  logo,
  erroLogo,
  aoEscolherLogo,
}: SecaoProps & { logo: File | null; erroLogo: string | null; aoEscolherLogo: (arquivo: File | null) => void }) {
  return (
    <Secao titulo="Identidade visual (opcional)" descricao="Logo e cores da empresa no login e no ambiente dela. Também dá para ajustar depois, na aba Personalização.">
      <div>
        <label className="block text-sm">
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Logo (PNG ou GIF, 320×132 px, até 2 MB)</span>
          <input
            type="file"
            accept="image/png,image/gif"
            disabled={desabilitado}
            onChange={(e) => aoEscolherLogo(e.target.files?.[0] ?? null)}
            className="field w-full rounded-xl px-3 py-2 text-sm"
          />
        </label>
        {logo && !erroLogo && <p className="mt-1 text-xs text-fg-muted">{logo.name}</p>}
        <Erro texto={erroLogo ?? undefined} />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <Input
            label="Cor principal"
            value={rascunho.corPrimaria}
            onChange={(e) => atualizar({ corPrimaria: e.target.value })}
            placeholder="#4f46e5"
            maxLength={7}
            className="font-mono"
            disabled={desabilitado}
          />
          {(mostrarErros || rascunho.corPrimaria) && <Erro texto={erros.corPrimaria} />}
        </div>
        <div>
          <Input
            label="Cor de destaque"
            value={rascunho.corSecundaria}
            onChange={(e) => atualizar({ corSecundaria: e.target.value })}
            placeholder="#7c3aed"
            maxLength={7}
            className="font-mono"
            disabled={desabilitado}
          />
          {(mostrarErros || rascunho.corSecundaria) && <Erro texto={erros.corSecundaria} />}
        </div>
        <Select
          label="Tema padrão"
          value={rascunho.tema}
          onChange={(e) => atualizar({ tema: e.target.value as RascunhoOnboarding["tema"] })}
          disabled={desabilitado}
          options={[
            { value: "", label: "Padrão do TaskFlow" },
            { value: "claro", label: "Claro" },
            { value: "escuro", label: "Escuro" },
          ]}
        />
      </div>
    </Secao>
  );
}

/** Acesso inicial: o primeiro Gestor (sempre perfil Gestor, só desta empresa). O servidor gera uma senha TEMPORÁRIA (exibida uma única vez) e o Gestor cria a PRÓPRIA senha no primeiro acesso. */
export function SecaoAcessoInicial({ rascunho, erros, mostrarErros, atualizar, desabilitado }: SecaoProps) {
  return (
    <Secao titulo="Acesso inicial — primeiro Gestor" descricao="O Gestor administra a empresa por dentro. Uma senha temporária será gerada e exibida uma única vez. No primeiro acesso, o Gestor deverá criar sua senha pessoal.">
      <div>
        <Input label="Nome do Gestor" value={rascunho.gestorNome} onChange={(e) => atualizar({ gestorNome: e.target.value })} maxLength={255} autoComplete="off" disabled={desabilitado} />
        {mostrarErros && <Erro texto={erros.gestorNome} />}
      </div>
      <div>
        <Input
          label="E-mail do Gestor"
          type="email"
          value={rascunho.gestorEmail}
          onChange={(e) => atualizar({ gestorEmail: e.target.value })}
          maxLength={255}
          autoComplete="off"
          disabled={desabilitado}
        />
        {mostrarErros && <Erro texto={erros.gestorEmail} />}
      </div>
    </Secao>
  );
}
