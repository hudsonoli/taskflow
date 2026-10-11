"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { CheckCircle2, Download, FileText, MessageSquareWarning, ShieldAlert } from "lucide-react";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { normalizarBranding } from "@/lib/branding";
import { useBranding } from "@/lib/BrandingContext";
import { slugDaRota } from "@/lib/tenant";
import {
  baixarArtefato,
  baixarLogo,
  consultarAprovacao,
  DecisaoJaRegistradaError,
  decidirAprovacao,
  erroDaDecisao,
  extrairTokenDoFragmento,
  formatarTamanhoPublico,
  LinkIndisponivelError,
  MENSAGEM_LINK_INDISPONIVEL,
  montarDecisao,
  MOTIVO_MAX,
  NOME_MAX,
  rotuloEstadoPublico,
} from "@/lib/aprovacao-externa-publica";
import type { AprovacaoPublica, ArtefatoPublicoAprovacao, DecisaoPublica } from "@/types/aprovacao-externa";

type Fase =
  | { tipo: "lendo" }
  | { tipo: "indisponivel" }
  | { tipo: "erro"; mensagem: string }
  | { tipo: "pronto"; dados: AprovacaoPublica };

function formatarDataHora(iso: string): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(data);
}

/**
 * Portal Externo de Aprovação (Fase 9B) — a tela do CLIENTE. Sem conta, sem sessão do tenant, sem menu: o link (`/e/<slug>/aprovacao#token=…`) é a única credencial (o slug só é conferido contra a empresa do token).
 *
 * O token é lido do FRAGMENTO (nunca vai ao servidor web), fica só em memória e viaja só no corpo dos POSTs do BFF dedicado. O fragmento permanece na barra
 * de endereço para o cliente poder recarregar/reabrir o link. Todo texto vindo do servidor/cliente é renderizado como TEXTO (nenhum HTML injetado). Nada
 * do que é registrado (token, e-mail, nome, motivo) vai para console ou analytics.
 */
export function AprovacaoPublicaView() {
  const { aplicarBranding } = useBranding();
  const slug = slugDaRota(usePathname());
  const aplicarBrandingRef = useRef(aplicarBranding);
  useEffect(() => {
    aplicarBrandingRef.current = aplicarBranding;
  }, [aplicarBranding]);

  // O token vive só em estado (memória): nunca em storage, cookie ou URL do servidor.
  const [token, setToken] = useState<string | null>(null);
  const [fase, setFase] = useState<Fase>({ tipo: "lendo" });
  const [logo, setLogo] = useState<string | null>(null);

  async function carregar(token: string) {
    try {
      const dados = await consultarAprovacao(slug ?? "", token);
      aplicarBrandingRef.current(normalizarBranding(dados.empresa));
      setFase({ tipo: "pronto", dados });
      return dados;
    } catch (falha) {
      setFase(falha instanceof LinkIndisponivelError ? { tipo: "indisponivel" } : { tipo: "erro", mensagem: falha instanceof Error ? falha.message : "Não foi possível carregar." });
      return null;
    }
  }

  useEffect(() => {
    let cancelado = false;
    const timeout = setTimeout(() => {
      const doFragmento = extrairTokenDoFragmento(window.location.hash);
      setToken(doFragmento);
      if (!doFragmento || !slug) {
        setFase({ tipo: "indisponivel" });
        return;
      }
      void carregar(doFragmento).then(async (dados) => {
        if (cancelado || !dados || !normalizarBranding(dados.empresa).logoDisponivel) return;
        const blob = await baixarLogo(slug, doFragmento);
        if (!cancelado && blob) setLogo(URL.createObjectURL(blob));
      });
    }, 0);
    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      if (logo) URL.revokeObjectURL(logo);
    };
  }, [logo]);

  return (
    <div className="min-h-screen bg-app px-4 py-6 sm:py-10">
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
        <div className="flex justify-center">
          <BrandLogo variant="auth" srcOverride={logo} />
        </div>
        {fase.tipo === "lendo" && <p className="text-center text-sm text-fg-muted">Carregando…</p>}
        {fase.tipo === "indisponivel" && <Indisponivel />}
        {fase.tipo === "erro" && (
          <Cartao>
            <p role="alert" className="text-sm text-fg">
              {fase.mensagem}
            </p>
            <Button type="button" variant="secondary" className="mt-3" onClick={() => token && void carregar(token)}>
              Tentar novamente
            </Button>
          </Cartao>
        )}
        {fase.tipo === "pronto" && token && (
          <Aprovacao slug={slug ?? ""} token={token} dados={fase.dados} onAtualizar={() => carregar(token)} />
        )}
        <p className="text-center text-[11px] text-fg-subtle">Link de acesso individual. Não o compartilhe com quem não deva avaliar este material.</p>
      </div>
    </div>
  );
}

function Cartao({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm sm:p-6">{children}</div>;
}

function Indisponivel() {
  return (
    <Cartao>
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
          <ShieldAlert size={20} aria-hidden />
        </div>
        <h1 className="text-lg font-semibold tracking-tight text-fg">{MENSAGEM_LINK_INDISPONIVEL}</h1>
        <p className="text-sm text-fg-muted">Se você precisa avaliar este material, peça um novo link a quem o enviou.</p>
      </div>
    </Cartao>
  );
}

function Aprovacao({
  slug,
  token,
  dados,
  onAtualizar,
}: {
  slug: string;
  token: string;
  dados: AprovacaoPublica;
  onAtualizar: () => Promise<AprovacaoPublica | null>;
}) {
  const decidido = dados.estado !== "pendente";
  const [nome, setNome] = useState(dados.destinatarioNome ?? "");
  const [email, setEmail] = useState("");
  const [modo, setModo] = useState<DecisaoPublica | null>(null);
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(decisao: DecisaoPublica) {
    if (enviando) return;
    const entrada = { decisao, nome, email, motivo };
    const problema = erroDaDecisao(entrada);
    if (problema) {
      setErro(problema);
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await decidirAprovacao(slug, token, montarDecisao(entrada));
      await onAtualizar();
    } catch (falha) {
      if (falha instanceof DecisaoJaRegistradaError || falha instanceof LinkIndisponivelError) {
        await onAtualizar(); // mostra o estado final (já respondida) ou o "indisponível" neutro
      } else {
        setErro(falha instanceof Error ? falha.message : "Não foi possível enviar sua resposta.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Cartao>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="neutral">{dados.demandaIdentificador}</Badge>
        <Badge tone={dados.estado === "aprovada" ? "green" : dados.estado === "ajustes_solicitados" ? "amber" : "blue"}>
          {rotuloEstadoPublico(dados.estado)}
        </Badge>
      </div>
      <h1 className="mt-2 text-lg font-semibold tracking-tight text-fg">{dados.demandaNome}</h1>
      {dados.destinatarioNome && <p className="mt-0.5 text-sm text-fg-muted">Enviado para {dados.destinatarioNome}</p>}
      {dados.instrucao && <p className="mt-3 whitespace-pre-wrap rounded-xl bg-zinc-50 px-3 py-2.5 text-sm text-fg dark:bg-zinc-900/60">{dados.instrucao}</p>}

      <ul className="mt-4 flex flex-col gap-4">
        {dados.artefatos.map((artefato) => (
          <li key={artefato.ordem}>
            <Artefato slug={slug} token={token} artefato={artefato} />
          </li>
        ))}
      </ul>

      {decidido && dados.decisao ? (
        <div
          role="status"
          className={`mt-5 flex items-start gap-3 rounded-xl border px-3 py-3 text-sm ${
            dados.estado === "aprovada"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
              : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300"
          }`}
        >
          {dados.estado === "aprovada" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> : <MessageSquareWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />}
          <p>
            {dados.estado === "aprovada" ? "Aprovado em" : "Ajustes solicitados em"} {formatarDataHora(dados.decisao.decididaEm)}. Obrigado! Esta resposta
            não pode mais ser alterada.
          </p>
        </div>
      ) : (
        <form
          className="mt-5 flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void enviar(modo ?? "aprovar");
          }}
        >
          <Input label="Seu nome *" value={nome} onChange={(event) => setNome(event.target.value)} maxLength={NOME_MAX} autoComplete="name" disabled={enviando} required />
          <Input
            label="Seu e-mail (opcional)"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            disabled={enviando}
          />
          {modo === "solicitar_ajustes" && (
            <Textarea
              label="Quais ajustes são necessários? *"
              value={motivo}
              onChange={(event) => setMotivo(event.target.value)}
              rows={4}
              maxLength={MOTIVO_MAX}
              disabled={enviando}
              autoFocus
            />
          )}
          {erro && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {erro}
            </p>
          )}
          <div className="flex flex-col gap-2 sm:flex-row">
            {modo !== "solicitar_ajustes" && (
              <Button type="button" className="min-h-11 flex-1 justify-center text-sm" onClick={() => void enviar("aprovar")} disabled={enviando}>
                {enviando ? "Enviando…" : "Aprovar"}
              </Button>
            )}
            {dados.podeSolicitarAjustes && modo !== "solicitar_ajustes" && (
              <Button type="button" variant="secondary" className="min-h-11 flex-1 justify-center text-sm" onClick={() => setModo("solicitar_ajustes")} disabled={enviando}>
                Solicitar ajustes
              </Button>
            )}
            {modo === "solicitar_ajustes" && (
              <>
                <Button type="button" className="min-h-11 flex-1 justify-center text-sm" onClick={() => void enviar("solicitar_ajustes")} disabled={enviando}>
                  {enviando ? "Enviando…" : "Enviar solicitação de ajustes"}
                </Button>
                <Button type="button" variant="secondary" className="min-h-11 justify-center text-sm" onClick={() => setModo(null)} disabled={enviando}>
                  Voltar
                </Button>
              </>
            )}
          </div>
          <p className="text-[11px] text-fg-subtle">Link válido até {formatarDataHora(dados.expiraEm)}. Seu nome e e-mail são registrados como informados por você.</p>
        </form>
      )}
    </Cartao>
  );
}

function Artefato({ slug, token, artefato }: { slug: string; token: string; artefato: ArtefatoPublicoAprovacao }) {
  const [url, setUrl] = useState<string | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [baixando, setBaixando] = useState(false);

  useEffect(() => {
    if (artefato.tipo !== "imagem") return;
    let cancelado = false;
    let criada: string | null = null;
    baixarArtefato(slug, token, artefato.ordem)
      .then((blob) => {
        if (cancelado) return;
        criada = URL.createObjectURL(blob);
        setUrl(criada);
      })
      .catch(() => {
        if (!cancelado) setFalhou(true);
      });
    return () => {
      cancelado = true;
      if (criada) URL.revokeObjectURL(criada);
    };
  }, [slug, token, artefato.ordem, artefato.tipo]);

  async function baixarPdf() {
    if (baixando) return;
    setBaixando(true);
    setFalhou(false);
    try {
      const blob = await baixarArtefato(slug, token, artefato.ordem);
      const temporaria = URL.createObjectURL(blob);
      const ancora = document.createElement("a");
      ancora.href = temporaria;
      ancora.download = artefato.nome;
      document.body.appendChild(ancora);
      ancora.click();
      ancora.remove();
      setTimeout(() => URL.revokeObjectURL(temporaria), 10_000);
    } catch {
      setFalhou(true);
    } finally {
      setBaixando(false);
    }
  }

  return (
    <div className="rounded-xl border border-line p-3">
      <div className="mb-2 flex items-center justify-between gap-2 text-xs text-fg-muted">
        <span className="min-w-0 truncate font-medium text-fg">{artefato.nome}</span>
        <span className="shrink-0">{formatarTamanhoPublico(artefato.tamanhoBytes)}</span>
      </div>
      {artefato.tipo === "imagem" ? (
        url ? (
          // eslint-disable-next-line @next/next/no-img-element -- blob: URL de um arquivo já conferido pelo servidor (SHA-256); next/image não se aplica
          <img src={url} alt={artefato.nome} className="mx-auto max-h-[70vh] w-full rounded-lg bg-zinc-50 object-contain dark:bg-zinc-900/60" />
        ) : (
          <p className="py-6 text-center text-xs text-fg-muted">{falhou ? "Não foi possível carregar a imagem." : "Carregando imagem…"}</p>
        )
      ) : (
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 shrink-0 text-fg-muted" aria-hidden />
          <Button type="button" variant="secondary" onClick={() => void baixarPdf()} disabled={baixando}>
            <Download className="h-3.5 w-3.5" aria-hidden /> {baixando ? "Baixando…" : "Baixar PDF"}
          </Button>
        </div>
      )}
      {artefato.tipo === "pdf" && falhou && <p className="mt-2 text-xs text-red-600 dark:text-red-400">Não foi possível baixar o arquivo.</p>}
    </div>
  );
}
