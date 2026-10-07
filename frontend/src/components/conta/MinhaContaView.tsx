"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ImageUp, KeyRound, Loader2, Lock, Trash2 } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppData } from "@/lib/AppDataContext";
import { alterarMinhaSenha, atualizarMeuPerfil, enviarMinhaFoto, removerMinhaFoto } from "@/lib/api-backend";
import { coresIdentificacaoDisponiveis } from "@/lib/cores";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { formatarTelefone, mascararTelefoneDigitando, validarFotoNoNavegador } from "@/lib/notificacoes";
import { perfilUsuarioLabels } from "@/types/usuario";

/**
 * Perfil do usuário (rota /minha-conta): FOTO · DADOS PESSOAIS · SEGURANÇA.
 *
 * Autoedição restrita: o próprio usuário altera só foto, telefone e cor de identificação. Nome, e-mail, cargo,
 * departamento e perfil são exibidos (somente leitura) — quem altera é a administração; o backend recusa
 * qualquer outro campo no autoatendimento (422).
 */
export function MinhaContaView() {
  const { usuarioAtual, recarregarSessao } = useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  const fotoInputRef = useRef<HTMLInputElement>(null);

  const [telefone, setTelefone] = useState(formatarTelefone(usuarioAtual?.telefone));
  const [corIdentificacao, setCorIdentificacao] = useState(usuarioAtual?.corIdentificacao ?? coresIdentificacaoDisponiveis[0].id);
  const [salvandoDados, setSalvandoDados] = useState(false);
  const [dadosSalvos, setDadosSalvos] = useState(false);
  const [dadosErro, setDadosErro] = useState<string | null>(null);

  const [fotoNova, setFotoNova] = useState<File | null>(null);
  const [fotoPrevia, setFotoPrevia] = useState<string | null>(null);
  const [fotoErro, setFotoErro] = useState<string | null>(null);
  const [fotoOcupada, setFotoOcupada] = useState(false);

  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [senhaErro, setSenhaErro] = useState<string | null>(null);
  const [senhaSucesso, setSenhaSucesso] = useState(false);
  const [trocandoSenha, setTrocandoSenha] = useState(false);

  // Pré-visualização local da foto escolhida (liberada ao trocar/desmontar).
  useEffect(() => {
    if (!fotoNova) return;
    const url = URL.createObjectURL(fotoNova);
    const timeout = setTimeout(() => setFotoPrevia(url), 0);
    return () => {
      clearTimeout(timeout);
      URL.revokeObjectURL(url);
    };
  }, [fotoNova]);

  if (!usuarioAtual) {
    return <p className="text-sm text-fg-subtle">Nenhum usuário selecionado.</p>;
  }

  const usuario = usuarioAtual;
  const departamento = usuario.departamentoId ? departamentos.find((item) => item.id === usuario.departamentoId) : undefined;
  const temFotoPropria = Boolean(usuario.fotoUrl?.startsWith("/usuarios/"));

  function escolherFoto(event: React.ChangeEvent<HTMLInputElement>) {
    const arquivo = event.target.files?.[0];
    event.target.value = "";
    if (!arquivo) return;
    const erro = validarFotoNoNavegador(arquivo);
    setFotoErro(erro);
    if (erro) return;
    setFotoNova(arquivo);
  }

  function cancelarFoto() {
    setFotoNova(null);
    setFotoPrevia(null);
    setFotoErro(null);
  }

  async function salvarFoto() {
    if (!fotoNova) return;
    setFotoOcupada(true);
    setFotoErro(null);
    try {
      await enviarMinhaFoto(fotoNova);
      await recarregarSessao(); // o avatar novo aparece em todo o app
      cancelarFoto();
    } catch (error) {
      setFotoErro(error instanceof Error ? error.message : "Não foi possível enviar a foto.");
    } finally {
      setFotoOcupada(false);
    }
  }

  async function removerFoto() {
    setFotoOcupada(true);
    setFotoErro(null);
    try {
      await removerMinhaFoto();
      await recarregarSessao();
      cancelarFoto();
    } catch (error) {
      setFotoErro(error instanceof Error ? error.message : "Não foi possível remover a foto.");
    } finally {
      setFotoOcupada(false);
    }
  }

  async function salvarDados() {
    setSalvandoDados(true);
    setDadosErro(null);
    try {
      await atualizarMeuPerfil({ telefone: telefone.trim() ? telefone : null, corIdentificacao });
      await recarregarSessao();
      setDadosSalvos(true);
      setTimeout(() => setDadosSalvos(false), 2500);
    } catch (error) {
      setDadosErro(error instanceof Error ? error.message : "Não foi possível salvar os dados.");
    } finally {
      setSalvandoDados(false);
    }
  }

  async function trocarSenha() {
    setSenhaSucesso(false);
    if (!senhaAtual) return setSenhaErro("Informe a senha atual.");
    if (novaSenha.length < 8) return setSenhaErro("A nova senha precisa ter pelo menos 8 caracteres.");
    if (novaSenha !== confirmarSenha) return setSenhaErro("A confirmação não coincide com a nova senha.");
    setSenhaErro(null);
    setTrocandoSenha(true);
    try {
      await alterarMinhaSenha(senhaAtual, novaSenha, confirmarSenha);
      setSenhaSucesso(true);
      setSenhaAtual("");
      setNovaSenha("");
      setConfirmarSenha("");
    } catch (error) {
      setSenhaErro(error instanceof Error ? error.message : "Não foi possível alterar a senha.");
    } finally {
      setTrocandoSenha(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6"
      >
        <div className="flex items-center gap-4">
          <Avatar nome={usuario.nome} corIdentificacao={corIdentificacao} fotoUrl={usuario.fotoUrl} className="h-14 w-14 shrink-0 rounded-full text-lg" />
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold tracking-tight text-fg">{usuario.nome}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <Badge tone="blue">{perfilUsuarioLabels[usuario.perfil]}</Badge>
              <span className="truncate text-xs text-fg-muted">{usuario.email}</span>
            </div>
          </div>
        </div>
      </motion.div>

      <section aria-labelledby="perfil-foto" className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6">
        <h2 id="perfil-foto" className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
          Foto
        </h2>
        <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center">
          <Avatar
            nome={usuario.nome}
            corIdentificacao={corIdentificacao}
            fotoUrl={fotoPrevia ?? usuario.fotoUrl}
            className="h-24 w-24 shrink-0 rounded-full text-2xl"
          />
          <div className="min-w-0">
            <p className="text-xs text-fg-muted">PNG ou JPG · máximo 5 MB · recomendado: imagem quadrada, 512 × 512 px.</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <input
                ref={fotoInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                className="sr-only"
                aria-label="Arquivo da foto de perfil"
                onChange={escolherFoto}
              />
              {fotoNova ? (
                <>
                  <Button type="button" onClick={() => void salvarFoto()} disabled={fotoOcupada}>
                    {fotoOcupada && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Salvar foto
                  </Button>
                  <Button type="button" variant="ghost" onClick={cancelarFoto} disabled={fotoOcupada}>
                    Cancelar
                  </Button>
                </>
              ) : (
                <>
                  <Button type="button" variant="secondary" onClick={() => fotoInputRef.current?.click()} disabled={fotoOcupada}>
                    <ImageUp className="h-3.5 w-3.5" /> Alterar foto
                  </Button>
                  {temFotoPropria && (
                    <Button type="button" variant="ghost" onClick={() => void removerFoto()} disabled={fotoOcupada}>
                      {fotoOcupada ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />} Remover foto
                    </Button>
                  )}
                </>
              )}
            </div>
            {fotoNova && <p className="mt-1.5 truncate text-xs text-fg-muted">Pré-visualização de {fotoNova.name} — ainda não salva.</p>}
            {fotoErro && (
              <p role="alert" className="mt-1.5 text-xs font-medium text-danger">
                {fotoErro}
              </p>
            )}
          </div>
        </div>
      </section>

      <section aria-labelledby="perfil-dados" className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6">
        <h2 id="perfil-dados" className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
          Dados pessoais
        </h2>
        <p className="mt-1 flex items-center gap-1.5 text-xs text-fg-muted">
          <Lock className="h-3 w-3 shrink-0" />
          Nome, e-mail, cargo, departamento e perfil só podem ser alterados pela administração.
        </p>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Input label="Nome completo" value={usuario.nome} disabled readOnly />
          <Input label="E-mail" value={usuario.email} disabled readOnly />
          <Input label="Cargo" value={usuario.cargo ?? "—"} disabled readOnly />
          <Input label="Departamento" value={departamento?.nome ?? "—"} disabled readOnly />
          <Input label="Perfil" value={perfilUsuarioLabels[usuario.perfil]} disabled readOnly />
          <Input
            label="Telefone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="(11) 91234-5678"
            value={telefone}
            onChange={(event) => setTelefone(mascararTelefoneDigitando(event.target.value))}
          />
        </div>

        <div className="mt-5">
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Cor de identificação</span>
          <div className="flex flex-wrap gap-2">
            {coresIdentificacaoDisponiveis.map((cor) => (
              <button
                key={cor.id}
                type="button"
                aria-label={cor.id}
                aria-pressed={corIdentificacao === cor.id}
                onClick={() => setCorIdentificacao(cor.id)}
                className={
                  corIdentificacao === cor.id
                    ? "h-7 w-7 rounded-full ring-2 ring-fg ring-offset-2 ring-offset-surface"
                    : "h-7 w-7 rounded-full"
                }
                style={{ backgroundColor: cor.hex }}
              />
            ))}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-line pt-4">
          <Button type="button" onClick={() => void salvarDados()} disabled={salvandoDados}>
            {salvandoDados && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Salvar dados
          </Button>
          {dadosSalvos && (
            <span role="status" className="text-xs font-medium text-success">
              Dados atualizados.
            </span>
          )}
          {dadosErro && (
            <span role="alert" className="text-xs font-medium text-danger">
              {dadosErro}
            </span>
          )}
        </div>
      </section>

      <section id="seguranca" aria-labelledby="perfil-seguranca" className="scroll-mt-20 rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6">
        <div className="flex items-center gap-2.5">
          <KeyRound className="h-4 w-4 text-fg-subtle" />
          <h2 id="perfil-seguranca" className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
            Segurança · Alterar senha
          </h2>
        </div>
        <p className="mt-1 text-xs text-fg-muted">Informe a senha atual e escolha uma nova (mínimo 8 caracteres).</p>

        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Input label="Senha atual" type="password" autoComplete="current-password" value={senhaAtual} onChange={(event) => setSenhaAtual(event.target.value)} />
          <Input label="Nova senha" type="password" autoComplete="new-password" value={novaSenha} onChange={(event) => setNovaSenha(event.target.value)} />
          <Input label="Confirmar" type="password" autoComplete="new-password" value={confirmarSenha} onChange={(event) => setConfirmarSenha(event.target.value)} />
        </div>

        {senhaErro && (
          <p role="alert" className="mt-3 text-xs font-medium text-danger">
            {senhaErro}
          </p>
        )}
        {senhaSucesso && (
          <p role="status" className="mt-3 text-xs font-medium text-success">
            Senha alterada.
          </p>
        )}

        <div className="mt-5 border-t border-line pt-4">
          <Button type="button" variant="secondary" onClick={() => void trocarSenha()} disabled={trocandoSenha}>
            {trocandoSenha && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Alterar senha
          </Button>
        </div>
      </section>
    </div>
  );
}
