"use client";

import { useState, type FormEvent } from "react";
import { Loader2, Power, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Textarea } from "@/components/ui/Textarea";
import { erroDoCodigoInterno, erroDoSlug } from "@/lib/plataforma";
import {
  atualizarEmpresaPlataforma,
  inativarEmpresaPlataforma,
  reativarEmpresaPlataforma,
} from "@/lib/plataforma-api";
import type { PlataformaEmpresa, PlataformaEmpresaUpdate } from "@/types/plataforma";

type Rascunho = { nome: string; nomeFantasia: string; documento: string; codigoInterno: string; slug: string };

const rascunhoDe = (empresa: PlataformaEmpresa): Rascunho => ({
  nome: empresa.nome,
  nomeFantasia: empresa.nomeFantasia ?? "",
  documento: empresa.documento ?? "",
  codigoInterno: empresa.codigoInterno,
  slug: empresa.slug,
});

export function EmpresaDadosSection({
  empresa,
  onAtualizada,
}: {
  empresa: PlataformaEmpresa;
  onAtualizada: (empresa: PlataformaEmpresa) => void;
}) {
  const [rascunho, setRascunho] = useState<Rascunho>(() => rascunhoDe(empresa));
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [inativando, setInativando] = useState(false);
  const [motivo, setMotivo] = useState("");

  const original = rascunhoDe(empresa);
  const alterado = (Object.keys(original) as (keyof Rascunho)[]).some((campo) => rascunho[campo].trim() !== original[campo]);
  const mudouIdentificador = rascunho.codigoInterno.trim().toUpperCase() !== original.codigoInterno || rascunho.slug.trim() !== original.slug;
  const erroNome = rascunho.nome.trim() ? null : "Informe o nome da empresa.";
  const erroCodigo = erroDoCodigoInterno(rascunho.codigoInterno);
  const erroSlug = erroDoSlug(rascunho.slug);
  const invalido = Boolean(erroNome || erroCodigo || erroSlug);
  const inativa = empresa.status !== "ativa";

  function atualizar(parcial: Partial<Rascunho>) {
    setRascunho((atual) => ({ ...atual, ...parcial }));
    setSucesso(null);
  }

  async function salvar(event: FormEvent) {
    event.preventDefault();
    if (!alterado || invalido) return;
    const mudancas: PlataformaEmpresaUpdate = {};
    if (rascunho.nome.trim() !== original.nome) mudancas.nome = rascunho.nome.trim();
    if (rascunho.nomeFantasia.trim() !== original.nomeFantasia) mudancas.nomeFantasia = rascunho.nomeFantasia.trim();
    if (rascunho.documento.trim() !== original.documento) mudancas.documento = rascunho.documento.trim();
    if (rascunho.codigoInterno.trim().toUpperCase() !== original.codigoInterno) mudancas.codigoInterno = rascunho.codigoInterno.trim();
    if (rascunho.slug.trim() !== original.slug) mudancas.slug = rascunho.slug.trim();
    setSalvando(true);
    setErro(null);
    setSucesso(null);
    try {
      const atualizada = await atualizarEmpresaPlataforma(empresa.id, mudancas);
      onAtualizada(atualizada);
      setRascunho(rascunhoDe(atualizada));
      setSucesso("Dados da empresa salvos.");
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível salvar a empresa.");
    } finally {
      setSalvando(false);
    }
  }

  async function mudarSituacao() {
    setSalvando(true);
    setErro(null);
    setSucesso(null);
    try {
      const atualizada = inativa
        ? await reativarEmpresaPlataforma(empresa.id)
        : await inativarEmpresaPlataforma(empresa.id, motivo);
      onAtualizada(atualizada);
      setInativando(false);
      setMotivo("");
      setSucesso(inativa ? "Empresa reativada." : "Empresa inativada. Os dados foram preservados.");
    } catch (error) {
      setInativando(false);
      setErro(error instanceof Error ? error.message : "Não foi possível alterar a situação da empresa.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={salvar} noValidate className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-4 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Input label="Nome da empresa" value={rascunho.nome} onChange={(e) => atualizar({ nome: e.target.value })} maxLength={255} />
            {erroNome && <p className="mt-1 text-xs font-medium text-danger">{erroNome}</p>}
          </div>
          <Input label="Nome fantasia" value={rascunho.nomeFantasia} onChange={(e) => atualizar({ nomeFantasia: e.target.value })} maxLength={255} />
          <Input label="Documento" value={rascunho.documento} onChange={(e) => atualizar({ documento: e.target.value })} maxLength={32} />
          <div />
          <div>
            <Input
              label="Código interno"
              value={rascunho.codigoInterno}
              onChange={(e) => atualizar({ codigoInterno: e.target.value })}
              maxLength={64}
              className="font-mono uppercase"
            />
            {erroCodigo && <p className="mt-1 text-xs font-medium text-danger">{erroCodigo}</p>}
          </div>
          <div>
            <Input
              label="Slug"
              value={rascunho.slug}
              onChange={(e) => atualizar({ slug: e.target.value.toLowerCase() })}
              maxLength={40}
              className="font-mono"
            />
            {erroSlug && <p className="mt-1 text-xs font-medium text-danger">{erroSlug}</p>}
          </div>
        </div>

        {mudouIdentificador && !invalido && (
          <p role="note" className="rounded-xl border border-amber-300/60 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
            Atenção: o código interno é o identificador de login atual e o slug será o identificador público de URL. Alterar um deles
            muda como esta empresa é localizada — só altere se for realmente necessário.
          </p>
        )}

        {erro && (
          <p role="alert" className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-2.5 text-xs font-medium text-danger">
            {erro}
          </p>
        )}
        {sucesso && (
          <p role="status" className="rounded-xl border border-success/40 bg-success/10 px-3 py-2.5 text-xs font-medium text-success">
            {sucesso}
          </p>
        )}

        <div className="flex justify-end">
          <Button type="submit" disabled={salvando || !alterado || invalido}>
            {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Salvar alterações
          </Button>
        </div>
      </form>

      <section className="rounded-xl border border-line bg-surface p-4 shadow-sm" aria-labelledby="situacao-empresa">
        <h3 id="situacao-empresa" className="text-sm font-semibold text-fg">
          Situação da empresa
        </h3>
        {inativa ? (
          <>
            <p className="mt-1 text-xs text-fg-muted">
              Empresa inativa: os usuários não conseguem entrar. Nada foi apagado — reativar devolve o acesso.
              {empresa.motivoInativacao ? ` Motivo registrado: ${empresa.motivoInativacao}` : ""}
            </p>
            <div className="mt-3">
              <Button type="button" variant="secondary" disabled={salvando} onClick={() => void mudarSituacao()}>
                <RotateCcw size={14} /> Reativar empresa
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="mt-1 text-xs text-fg-muted">
              Inativar bloqueia o acesso de todos os usuários da empresa, sem apagar nenhum dado. Empresas nunca são excluídas.
            </p>
            {empresa.hospedaAdministradorPlataforma && (
              <p role="note" className="mt-2 text-xs font-medium text-amber-700 dark:text-amber-400">
                Esta empresa hospeda um Administrador da Plataforma ativo e não pode ser inativada.
              </p>
            )}
            <div className="mt-3">
              <Button
                type="button"
                variant="secondary"
                disabled={salvando || empresa.hospedaAdministradorPlataforma}
                onClick={() => setInativando(true)}
              >
                <Power size={14} /> Inativar empresa
              </Button>
            </div>
          </>
        )}
      </section>

      <Modal open={inativando} onClose={() => !salvando && setInativando(false)} maxWidthClassName="max-w-md">
        <h2 className="text-base font-semibold text-fg">Inativar “{empresa.nome}”?</h2>
        <p className="mt-2 text-sm text-fg-muted">
          Ninguém desta empresa conseguirá entrar enquanto ela estiver inativa. Os dados são preservados e você pode reativá-la depois.
        </p>
        <div className="mt-4">
          <Textarea label="Motivo (opcional)" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={500} rows={3} />
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" disabled={salvando} onClick={() => setInativando(false)}>
            Cancelar
          </Button>
          <Button type="button" disabled={salvando} onClick={() => void mudarSituacao()}>
            {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Inativar empresa
          </Button>
        </div>
      </Modal>
    </div>
  );
}
