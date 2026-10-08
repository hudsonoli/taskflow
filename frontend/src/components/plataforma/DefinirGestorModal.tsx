"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Check, Copy, KeyRound, Loader2, UserCheck } from "lucide-react";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { criarGestorEmpresa, listarCandidatosGestor, promoverGestorEmpresa } from "@/lib/plataforma-api";
import type { PlataformaEmpresa, PlataformaGestorCriado, PlataformaUsuario } from "@/types/plataforma";

const EMAIL_SIMPLES = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Modo = "existente" | "novo";

/**
 * Define um Gestor da empresa em foco, de duas formas num único fluxo:
 *  • "Escolher usuário existente": promove um Usuário JÁ cadastrado NESTA empresa (a lista traz só candidatos elegíveis:
 *    ativos, com acesso, sem conta de sistema e que ainda não são Gestor). Mesmo cadastro, mesma senha — nada é gerado.
 *  • "Criar novo Gestor": nome + e-mail; o servidor força o perfil Gestor e gera a senha temporária, exibida UMA vez.
 * A autoridade é da PLATAFORMA; a empresa pode ter vários Gestores. Fechar o modal descarta a senha da memória.
 */
export function DefinirGestorModal({
  open,
  empresa,
  onClose,
  onDefinido,
}: {
  open: boolean;
  empresa: PlataformaEmpresa;
  onClose: () => void;
  onDefinido: () => void;
}) {
  const [modo, setModo] = useState<Modo>("existente");
  // candidatos: null = carregando; [] = nenhum elegível
  const [candidatos, setCandidatos] = useState<PlataformaUsuario[] | null>(null);
  const [erroLista, setErroLista] = useState<string | null>(null);
  const [escolhido, setEscolhido] = useState("");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tentou, setTentou] = useState(false);
  const [criado, setCriado] = useState<PlataformaGestorCriado | null>(null);
  const [promovido, setPromovido] = useState<PlataformaUsuario | null>(null);
  const [copiado, setCopiado] = useState(false);

  // Carrega os candidatos sempre que o modal abre (a lista muda a cada promoção/criação).
  useEffect(() => {
    if (!open) return;
    let cancelado = false;
    const timeout = setTimeout(async () => {
      setCandidatos(null);
      setErroLista(null);
      try {
        const lista = await listarCandidatosGestor(empresa.id);
        if (cancelado) return;
        setCandidatos(lista);
        // Sem ninguém para promover, o caminho útil é criar um novo Gestor.
        if (lista.length === 0) setModo("novo");
      } catch (error) {
        if (!cancelado) {
          setCandidatos([]);
          setErroLista(error instanceof Error ? error.message : "Não foi possível carregar os usuários.");
        }
      }
    }, 0);
    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
  }, [open, empresa.id]);

  const erroNome = nome.trim() ? null : "Informe o nome do Gestor.";
  const erroEmail = EMAIL_SIMPLES.test(email.trim()) ? null : "Informe um e-mail válido.";

  function fechar() {
    if (salvando) return;
    // Descarta a senha temporária e o formulário: a próxima abertura começa do zero.
    setCriado(null);
    setPromovido(null);
    setCopiado(false);
    setNome("");
    setEmail("");
    setEscolhido("");
    setModo("existente");
    setErro(null);
    setTentou(false);
    onClose();
  }

  async function promover() {
    if (!escolhido) {
      setTentou(true);
      return;
    }
    setSalvando(true);
    setErro(null);
    try {
      setPromovido(await promoverGestorEmpresa(empresa.id, escolhido));
      onDefinido();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível promover o usuário.");
    } finally {
      setSalvando(false);
    }
  }

  async function criar(event: FormEvent) {
    event.preventDefault();
    setTentou(true);
    if (erroNome || erroEmail) return;
    setSalvando(true);
    setErro(null);
    try {
      setCriado(await criarGestorEmpresa(empresa.id, { nome: nome.trim(), email: email.trim() }));
      onDefinido();
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

  if (promovido) {
    return (
      <Modal open={open} onClose={fechar} maxWidthClassName="max-w-md">
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
              <UserCheck className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-base font-semibold text-fg">Gestor definido</h2>
              <p className="mt-0.5 text-xs text-fg-muted">
                {promovido.nome} · {promovido.email}
              </p>
            </div>
          </div>
          <p className="text-sm text-fg-muted">
            O usuário agora é Gestor de {empresa.nome}. Ele continua entrando com a mesma senha — nenhuma senha foi gerada ou alterada.
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

  const semCandidatos = candidatos !== null && candidatos.length === 0;

  return (
    <Modal open={open} onClose={fechar} maxWidthClassName="max-w-md">
      <div className="flex flex-col gap-4">
        <div>
          <h2 className="text-base font-semibold text-fg">Definir Gestor — {empresa.nome}</h2>
          <p className="mt-1 text-xs text-fg-muted">A empresa pode ter mais de um Gestor. Escolha como definir este.</p>
        </div>

        <div role="radiogroup" aria-label="Como definir o Gestor" className="flex flex-col gap-2">
          {(
            [
              { valor: "existente", rotulo: "Escolher usuário existente", ajuda: "Promove um Usuário já cadastrado nesta empresa." },
              { valor: "novo", rotulo: "Criar novo Gestor", ajuda: "Cria um usuário já como Gestor, com senha temporária." },
            ] as const
          ).map(({ valor, rotulo, ajuda }) => {
            const ativo = modo === valor;
            const desabilitado = valor === "existente" && semCandidatos;
            return (
              <button
                key={valor}
                type="button"
                role="radio"
                aria-checked={ativo}
                disabled={desabilitado}
                onClick={() => {
                  setModo(valor);
                  setErro(null);
                  setTentou(false);
                }}
                className={clsx(
                  "flex items-start gap-3 rounded-xl border px-3 py-2.5 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-50",
                  ativo ? "border-indigo-500 bg-indigo-50/60 dark:bg-indigo-500/10" : "border-line hover:bg-surface-hover",
                )}
              >
                <span
                  aria-hidden
                  className={clsx(
                    "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2",
                    ativo ? "border-indigo-600 dark:border-indigo-400" : "border-field-line",
                  )}
                >
                  {ativo && <span className="h-2 w-2 rounded-full bg-indigo-600 dark:bg-indigo-400" />}
                </span>
                <span>
                  <span className="block text-sm font-semibold text-fg">{rotulo}</span>
                  <span className="block text-xs text-fg-muted">
                    {desabilitado ? "Nenhum usuário elegível nesta empresa (só Usuários ativos, com acesso, que ainda não são Gestor)." : ajuda}
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        {modo === "existente" ? (
          <div className="flex flex-col gap-3">
            {candidatos === null ? (
              <p className="flex items-center gap-2 text-xs text-fg-muted">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Carregando usuários…
              </p>
            ) : (
              <label className="block text-sm">
                <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Usuário da empresa</span>
                <select
                  value={escolhido}
                  onChange={(event) => setEscolhido(event.target.value)}
                  className="field w-full rounded-xl px-3 py-2.5 text-sm"
                  aria-invalid={tentou && !escolhido}
                >
                  <option value="">Selecione…</option>
                  {candidatos.map((usuario) => (
                    <option key={usuario.id} value={usuario.id}>
                      {usuario.nome} — {usuario.email}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {tentou && !escolhido && <p className="-mt-1 text-xs font-medium text-danger">Selecione o usuário.</p>}
            {erroLista && <p className="text-xs font-medium text-danger">{erroLista}</p>}
            <p className="text-xs text-fg-muted">
              O usuário mantém o mesmo cadastro, a mesma senha e as permissões individuais; só o perfil muda para Gestor.
            </p>
            {erro && (
              <p role="alert" className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-2.5 text-xs font-medium text-danger">
                {erro}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" disabled={salvando} onClick={fechar}>
                Cancelar
              </Button>
              <Button type="button" disabled={salvando || candidatos === null || semCandidatos} onClick={() => void promover()}>
                {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Promover a Gestor
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={criar} noValidate className="flex flex-col gap-4">
            <div>
              <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={255} autoComplete="off" />
              {tentou && erroNome && <p className="mt-1 text-xs font-medium text-danger">{erroNome}</p>}
            </div>
            <div>
              <Input label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={255} autoComplete="off" />
              {tentou && erroEmail && <p className="mt-1 text-xs font-medium text-danger">{erroEmail}</p>}
            </div>
            <p className="text-xs text-fg-muted">O perfil é sempre Gestor. Uma senha temporária será gerada e exibida uma única vez.</p>
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
        )}
      </div>
    </Modal>
  );
}
