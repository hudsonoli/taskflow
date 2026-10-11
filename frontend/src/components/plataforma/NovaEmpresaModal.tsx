"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { erroDoCodigoInterno, erroDoSlug, sugerirSlug } from "@/lib/plataforma";
import { criarEmpresaPlataforma } from "@/lib/plataforma-api";

type Rascunho = { nome: string; nomeFantasia: string; documento: string; codigoInterno: string; slug: string };
const VAZIO: Rascunho = { nome: "", nomeFantasia: "", documento: "", codigoInterno: "", slug: "" };

export function NovaEmpresaModal({
  open,
  onClose,
  onCriada,
}: {
  open: boolean;
  onClose: () => void;
  onCriada: () => void;
}) {
  const router = useRouter();
  const [rascunho, setRascunho] = useState<Rascunho>(VAZIO);
  const [slugEditado, setSlugEditado] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tentou, setTentou] = useState(false);

  function atualizar(parcial: Partial<Rascunho>) {
    setRascunho((atual) => {
      const novo = { ...atual, ...parcial };
      // Enquanto a pessoa não mexeu no slug, ele acompanha o código interno (é só uma sugestão).
      if (parcial.codigoInterno !== undefined && !slugEditado) novo.slug = sugerirSlug(parcial.codigoInterno);
      return novo;
    });
  }

  function fechar() {
    if (salvando) return;
    setRascunho(VAZIO);
    setSlugEditado(false);
    setErro(null);
    setTentou(false);
    onClose();
  }

  const erroNome = rascunho.nome.trim() ? null : "Informe o nome da empresa.";
  const erroCodigo = erroDoCodigoInterno(rascunho.codigoInterno);
  const erroSlug = rascunho.slug.trim() ? erroDoSlug(rascunho.slug) : null; // vazio → o servidor deriva do código
  const invalido = Boolean(erroNome || erroCodigo || erroSlug);

  async function enviar(event: FormEvent) {
    event.preventDefault();
    setTentou(true);
    if (invalido) return;
    setSalvando(true);
    setErro(null);
    try {
      const criada = await criarEmpresaPlataforma({
        nome: rascunho.nome.trim(),
        nomeFantasia: rascunho.nomeFantasia.trim() || null,
        documento: rascunho.documento.trim() || null,
        codigoInterno: rascunho.codigoInterno.trim(),
        slug: rascunho.slug.trim() || null,
      });
      onCriada();
      setRascunho(VAZIO);
      setSlugEditado(false);
      setTentou(false);
      onClose();
      router.push(`/gestao/empresas/${criada.id}`);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível criar a empresa.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal open={open} onClose={fechar} maxWidthClassName="max-w-lg">
      <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <div>
          <h2 className="text-base font-semibold text-fg">Nova empresa</h2>
          <p className="mt-1 text-xs text-fg-muted">
            Depois de criada, personalize a identidade visual e crie o primeiro Gestor na página da empresa.
          </p>
        </div>

        <div>
          <Input label="Nome da empresa" value={rascunho.nome} onChange={(e) => atualizar({ nome: e.target.value })} maxLength={255} required />
          {tentou && erroNome && <p className="mt-1 text-xs font-medium text-danger">{erroNome}</p>}
        </div>
        <Input label="Nome fantasia (opcional)" value={rascunho.nomeFantasia} onChange={(e) => atualizar({ nomeFantasia: e.target.value })} maxLength={255} />
        <Input label="Documento (opcional)" value={rascunho.documento} onChange={(e) => atualizar({ documento: e.target.value })} maxLength={32} />

        <div>
          <Input
            label="Código interno"
            value={rascunho.codigoInterno}
            onChange={(e) => atualizar({ codigoInterno: e.target.value })}
            maxLength={64}
            className="font-mono uppercase"
            required
          />
          <p className="mt-1 text-xs text-fg-muted">Identificador de login de hoje. Fica em maiúsculas; só letras, números, hífen e sublinhado.</p>
          {(tentou || rascunho.codigoInterno) && erroCodigo && <p className="mt-1 text-xs font-medium text-danger">{erroCodigo}</p>}
        </div>

        <div>
          <Input
            label="Slug"
            value={rascunho.slug}
            onChange={(e) => {
              setSlugEditado(true);
              setRascunho((atual) => ({ ...atual, slug: e.target.value.toLowerCase() }));
            }}
            maxLength={40}
            className="font-mono"
          />
          <p className="mt-1 text-xs text-fg-muted">
            Identificador público de URL (3–40, minúsculas, números e hífen). Em branco, é gerado a partir do código.
          </p>
          {erroSlug && <p className="mt-1 text-xs font-medium text-danger">{erroSlug}</p>}
        </div>

        {erro && (
          <p role="alert" className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-2.5 text-xs font-medium text-danger">
            {erro}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" disabled={salvando} onClick={fechar}>
            Cancelar
          </Button>
          <Button type="submit" disabled={salvando}>
            {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Criar empresa
          </Button>
        </div>
      </form>
    </Modal>
  );
}
