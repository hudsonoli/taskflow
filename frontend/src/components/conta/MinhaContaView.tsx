"use client";

import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { KeyRound, ShieldCheck, Upload } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppData } from "@/lib/AppDataContext";
import { atualizarPerfilProprio } from "@/lib/api-backend";
import { coresIdentificacaoDisponiveis } from "@/lib/cores";
import { perfilUsuarioLabels } from "@/types/usuario";

export function MinhaContaView() {
  const { usuarioAtual, recarregarSessao } = useAppData();
  const fotoInputRef = useRef<HTMLInputElement>(null);

  const [nome, setNome] = useState(usuarioAtual?.nome ?? "");
  const [cargo, setCargo] = useState(usuarioAtual?.cargo ?? "");
  const [corIdentificacao, setCorIdentificacao] = useState(usuarioAtual?.corIdentificacao ?? coresIdentificacaoDisponiveis[0].id);
  const [fotoUrl, setFotoUrl] = useState(usuarioAtual?.fotoUrl);
  const [perfilSalvo, setPerfilSalvo] = useState(false);
  const [perfilErro, setPerfilErro] = useState<string | null>(null);
  const [salvandoPerfil, setSalvandoPerfil] = useState(false);

  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [senhaErro, setSenhaErro] = useState<string | null>(null);
  const [senhaSucesso, setSenhaSucesso] = useState(false);

  if (!usuarioAtual) {
    return <p className="text-sm text-zinc-400">Nenhum usuário selecionado.</p>;
  }

  const usuarioId = usuarioAtual.id;
  const nomeAtual = usuarioAtual.nome;

  function handleFotoSelecionada(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") setFotoUrl(reader.result);
    };
    reader.readAsDataURL(file);
  }

  async function handleSalvarPerfil() {
    setSalvandoPerfil(true);
    setPerfilErro(null);
    try {
      // fotoUrl não é enviado: ainda não existe upload real (a pré-visualização aqui é só
      // um data URL local, grande demais pra coluna do banco) — ver nota no rodapé da tela.
      await atualizarPerfilProprio(usuarioId, {
        nome: nome.trim() || nomeAtual,
        cargo: cargo || null,
        corIdentificacao,
      });
      await recarregarSessao();
      setPerfilSalvo(true);
      setTimeout(() => setPerfilSalvo(false), 2000);
    } catch (error) {
      setPerfilErro(error instanceof Error ? error.message : "Não foi possível salvar o perfil.");
    } finally {
      setSalvandoPerfil(false);
    }
  }

  function handleAlterarSenha() {
    setSenhaSucesso(false);
    if (!senhaAtual) {
      setSenhaErro("Informe a senha atual.");
      return;
    }
    if (novaSenha.length < 6) {
      setSenhaErro("A nova senha precisa ter pelo menos 6 caracteres.");
      return;
    }
    if (novaSenha !== confirmarSenha) {
      setSenhaErro("A confirmação não coincide com a nova senha.");
      return;
    }

    setSenhaErro(null);
    setSenhaSucesso(true);
    setSenhaAtual("");
    setNovaSenha("");
    setConfirmarSenha("");
    setTimeout(() => setSenhaSucesso(false), 2500);
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-6"
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Avatar nome={nome} corIdentificacao={corIdentificacao} fotoUrl={fotoUrl} className="h-14 w-14 shrink-0 rounded-2xl text-lg" />
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">{usuarioAtual.nome}</h1>
              <div className="mt-1">
                <Badge tone="blue">{perfilUsuarioLabels[usuarioAtual.perfil]}</Badge>
              </div>
            </div>
          </div>
          <Badge tone="green">Banco real</Badge>
        </div>
      </motion.div>

      <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-6">
        <div>
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
            Foto de perfil
          </span>
          <div className="flex items-center gap-3">
            <Avatar nome={nome} corIdentificacao={corIdentificacao} fotoUrl={fotoUrl} className="h-12 w-12 rounded-full text-sm" />
            <input ref={fotoInputRef} type="file" accept="image/*" className="hidden" onChange={handleFotoSelecionada} />
            <Button type="button" variant="secondary" onClick={() => fotoInputRef.current?.click()} className="px-3 py-2 text-xs">
              <Upload className="h-3.5 w-3.5" />
              Enviar foto
            </Button>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <Input label="Nome" value={nome} onChange={(event) => setNome(event.target.value)} />
          <Input label="Cargo" placeholder="Ex: Analista de Criação" value={cargo} onChange={(event) => setCargo(event.target.value)} />
        </div>

        <div className="mt-4">
          <Input label="E-mail" value={usuarioAtual.email} disabled />
        </div>

        <div className="mt-5">
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
            Cor de identificação
          </span>
          <div className="flex flex-wrap gap-2">
            {coresIdentificacaoDisponiveis.map((cor) => (
              <button
                key={cor.id}
                type="button"
                aria-label={cor.id}
                onClick={() => setCorIdentificacao(cor.id)}
                className={
                  corIdentificacao === cor.id
                    ? "h-7 w-7 rounded-full ring-2 ring-offset-2 ring-zinc-900 dark:ring-offset-zinc-900 dark:ring-zinc-100"
                    : "h-7 w-7 rounded-full"
                }
                style={{ backgroundColor: cor.hex }}
              />
            ))}
          </div>
        </div>

        <div className="mt-6 flex items-center gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800">
          <Button type="button" onClick={handleSalvarPerfil} disabled={salvandoPerfil}>
            {salvandoPerfil ? "Salvando…" : "Salvar perfil"}
          </Button>
          {perfilSalvo && <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Perfil atualizado.</span>}
          {perfilErro && <span className="text-xs font-medium text-red-500">{perfilErro}</span>}
        </div>
      </div>

      <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-6">
        <div className="flex items-center gap-2.5">
          <KeyRound className="h-4 w-4 text-zinc-400" />
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Alterar senha</p>
        </div>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">Informe a senha atual e escolha uma nova (mínimo 6 caracteres).</p>

        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Input label="Senha atual" type="password" value={senhaAtual} onChange={(event) => setSenhaAtual(event.target.value)} />
          <Input label="Nova senha" type="password" value={novaSenha} onChange={(event) => setNovaSenha(event.target.value)} />
          <Input label="Confirmar" type="password" value={confirmarSenha} onChange={(event) => setConfirmarSenha(event.target.value)} />
        </div>

        {senhaErro && <p className="mt-3 text-xs font-medium text-red-500">{senhaErro}</p>}
        {senhaSucesso && <p className="mt-3 text-xs font-medium text-emerald-600 dark:text-emerald-400">Senha alterada (simulado).</p>}

        <div className="mt-5 border-t border-zinc-100 pt-4 dark:border-zinc-800">
          <Button type="button" variant="secondary" onClick={handleAlterarSenha}>
            Alterar senha
          </Button>
        </div>

        <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-zinc-100 bg-zinc-50/70 p-3.5 text-xs text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950/30 dark:text-zinc-400">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Troca de senha ainda simulada nesta fase — sem envio de foto de perfil para um servidor real.
        </div>
      </div>
    </div>
  );
}
