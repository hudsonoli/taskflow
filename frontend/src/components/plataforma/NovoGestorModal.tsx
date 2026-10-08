"use client";

import { useState, type FormEvent } from "react";
import { Check, Copy, KeyRound, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { criarGestorEmpresa } from "@/lib/plataforma-api";
import type { PlataformaEmpresa, PlataformaGestorCriado } from "@/types/plataforma";

const EMAIL_SIMPLES = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Cria o Gestor da empresa em foco. O perfil é SEMPRE Gestor (não há escolha) e a senha temporária é gerada pelo
 * servidor: ela aparece UMA vez, neste modal, logo após a criação. Fechar o modal descarta a senha da memória —
 * nada é guardado em storage, URL ou log, e a API nunca a devolve de novo.
 */
export function NovoGestorModal({
  open,
  empresa,
  onClose,
  onCriado,
}: {
  open: boolean;
  empresa: PlataformaEmpresa;
  onClose: () => void;
  onCriado: () => void;
}) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tentou, setTentou] = useState(false);
  const [criado, setCriado] = useState<PlataformaGestorCriado | null>(null);
  const [copiado, setCopiado] = useState(false);

  const erroNome = nome.trim() ? null : "Informe o nome do Gestor.";
  const erroEmail = EMAIL_SIMPLES.test(email.trim()) ? null : "Informe um e-mail válido.";

  function fechar() {
    if (salvando) return;
    // Descarta a senha temporária e o formulário: a próxima abertura começa do zero.
    setCriado(null);
    setCopiado(false);
    setNome("");
    setEmail("");
    setErro(null);
    setTentou(false);
    onClose();
  }

  async function enviar(event: FormEvent) {
    event.preventDefault();
    setTentou(true);
    if (erroNome || erroEmail) return;
    setSalvando(true);
    setErro(null);
    try {
      const resposta = await criarGestorEmpresa(empresa.id, { nome: nome.trim(), email: email.trim() });
      setCriado(resposta);
      onCriado();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível criar o Gestor.");
    } finally {
      setSalvando(false);
    }
  }

  async function copiar() {
    if (!criado) return;
    try {
      await navigator.clipboard.writeText(criado.senhaTemporaria);
      setCopiado(true);
    } catch {
      setCopiado(false); // sem permissão de área de transferência: a senha continua visível para cópia manual
    }
  }

  if (criado) {
    return (
      <Modal open={open} onClose={fechar} maxWidthClassName="max-w-md">
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
              <KeyRound className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-base font-semibold text-fg">Gestor criado</h2>
              <p className="mt-0.5 text-xs text-fg-muted">
                {criado.usuario.nome} · {criado.usuario.email}
              </p>
            </div>
          </div>

          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Senha temporária</p>
            <div className="mt-1.5 flex items-center gap-2">
              <code
                data-testid="senha-temporaria"
                className="flex-1 select-all rounded-xl border border-field-line bg-field px-3 py-2.5 font-mono text-sm tracking-wide text-fg"
              >
                {criado.senhaTemporaria}
              </code>
              <Button type="button" variant="secondary" onClick={() => void copiar()} aria-label="Copiar senha temporária">
                {copiado ? <Check size={14} /> : <Copy size={14} />} {copiado ? "Copiada" : "Copiar"}
              </Button>
            </div>
          </div>

          <p role="note" className="rounded-xl border border-amber-300/60 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
            Esta senha é exibida <strong>uma única vez</strong> e não pode ser consultada depois. Entregue-a por um canal seguro. No
            primeiro acesso o Gestor será obrigado a trocá-la.
          </p>

          <div className="flex justify-end">
            <Button type="button" onClick={fechar}>
              Concluir
            </Button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={fechar} maxWidthClassName="max-w-md">
      <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <div>
          <h2 className="text-base font-semibold text-fg">Novo Gestor — {empresa.nome}</h2>
          <p className="mt-1 text-xs text-fg-muted">
            O perfil é sempre Gestor. Uma senha temporária será gerada e exibida uma única vez após a criação.
          </p>
        </div>
        <div>
          <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={255} autoComplete="off" />
          {tentou && erroNome && <p className="mt-1 text-xs font-medium text-danger">{erroNome}</p>}
        </div>
        <div>
          <Input label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={255} autoComplete="off" />
          {tentou && erroEmail && <p className="mt-1 text-xs font-medium text-danger">{erroEmail}</p>}
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
            {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Criar Gestor
          </Button>
        </div>
      </form>
    </Modal>
  );
}
