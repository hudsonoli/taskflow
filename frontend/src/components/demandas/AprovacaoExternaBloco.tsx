"use client";

import { useCallback, useEffect, useState } from "react";
import { Copy, ExternalLink, Link2, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  criarAprovacaoExternaReal,
  getAprovacaoExternaPainel,
  getDemandaReal,
  listArquivosDemanda,
  revogarAprovacaoExternaReal,
} from "@/lib/api-backend";
import {
  acoesDoPainel,
  alternarArquivo,
  arquivoElegivelParaAprovacao,
  ARQUIVOS_MAX,
  AVISO_LINK_UNICO,
  criarLinkDeAprovacao,
  descreverDecisaoInterna,
  deveRenderizarPainel,
  erroDaInstrucao,
  INSTRUCAO_MAX,
  linkDeAprovacao,
  montarEntradaDeCriacao,
  ordenarContatos,
  rotuloEstadoAprovacao,
  toneEstadoAprovacao,
  VALIDADES_DIAS,
} from "@/lib/aprovacao-externa";
import { formatPrazo } from "@/lib/demandas";
import { ehConflitoDeWorkflow } from "@/lib/workflow-demanda";
import type { AprovacaoExternaPainel } from "@/types/aprovacao-externa";
import type { Demanda, DemandaArquivo, DemandaWorkflowEtapa } from "@/types/demanda";

function formatarTamanho(bytes: number | null): string {
  if (bytes === null) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * "Aprovação do cliente" (Fase 9B) — bloco compacto da etapa de APROVAÇÃO atual na aba Workflow. O cliente não tem conta: o usuário interno gera um link
 * (capability), escolhe os arquivos que ele verá e acompanha o desfecho aqui. O servidor decide tudo (`podeGerenciar`, estado, validade); o token só
 * existe em memória, na tela de "link gerado", e some ao fechar o modal.
 */
export function AprovacaoExternaBloco({
  demanda,
  etapa,
  onChange,
}: {
  demanda: Demanda;
  etapa: DemandaWorkflowEtapa;
  onChange: (demanda: Demanda) => void;
}) {
  const [painel, setPainel] = useState<AprovacaoExternaPainel | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [criando, setCriando] = useState(false);
  const [confirmandoRevogar, setConfirmandoRevogar] = useState(false);
  const [revogando, setRevogando] = useState(false);

  const recarregar = useCallback(async () => {
    try {
      setPainel(await getAprovacaoExternaPainel(demanda.id, etapa.id));
    } catch {
      setPainel(null);
    }
  }, [demanda.id, etapa.id]);

  useEffect(() => {
    const timeout = setTimeout(() => void recarregar(), 0);
    return () => clearTimeout(timeout);
  }, [recarregar, demanda.updatedAt]);

  async function revogar() {
    const atual = painel?.atual;
    if (!atual || revogando) return;
    setRevogando(true);
    setErro(null);
    try {
      await revogarAprovacaoExternaReal(demanda.id, etapa.id, atual.id);
      setConfirmandoRevogar(false);
      await recarregar();
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível revogar o link.");
      setConfirmandoRevogar(false);
      await recarregar();
    } finally {
      setRevogando(false);
    }
  }

  async function recarregarWorkflow() {
    try {
      onChange(await getDemandaReal(demanda.id));
    } catch {
      // mantém o que está em tela
    }
  }

  if (!deveRenderizarPainel(painel) || painel === null) return null;
  const acoes = acoesDoPainel(painel);
  const atual = painel.atual;

  return (
    <div className="mt-3 rounded-xl border border-line bg-surface/60 p-3" data-bloco="aprovacao-cliente">
      <div className="flex flex-wrap items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-fg-muted" aria-hidden />
        <p className="text-xs font-semibold text-fg">Aprovação do cliente</p>
        {atual && <Badge tone={toneEstadoAprovacao[atual.estado]}>{rotuloEstadoAprovacao[atual.estado]}</Badge>}
      </div>

      {erro && (
        <p role="alert" className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
          {erro}
        </p>
      )}

      {!atual && <p className="mt-1.5 text-xs text-fg-muted">Nenhum link gerado. Envie os arquivos para o cliente aprovar sem precisar de conta.</p>}

      {atual && (
        <div className="mt-1.5 space-y-1 text-xs text-fg-muted">
          {atual.estado === "pendente" && (
            <p>
              Válido até {formatPrazo(atual.expiraEm)}
              {atual.destinatarioNome ? ` · para ${atual.destinatarioNome}` : ""}. O link só é exibido na criação.
            </p>
          )}
          {atual.estado === "revogada" && <p>Revogado em {formatPrazo(atual.revogadaEm)}.</p>}
          {atual.estado === "expirada" && <p>Expirou em {formatPrazo(atual.expiraEm)}.</p>}
          {atual.decisao && (
            <p>
              {descreverDecisaoInterna(atual)} em {formatPrazo(atual.decisao.decididaEm)}.
              {atual.decisao.emailAprovador ? ` E-mail informado: ${atual.decisao.emailAprovador}.` : ""}
            </p>
          )}
          {atual.decisao?.motivo && <p className="whitespace-pre-wrap rounded-lg bg-zinc-50 px-2.5 py-1.5 text-fg dark:bg-zinc-900/60">{atual.decisao.motivo}</p>}
          {atual.instrucao && <p className="whitespace-pre-wrap">Instrução enviada: {atual.instrucao}</p>}
          <ul className="space-y-0.5">
            {atual.artefatos.map((artefato) => (
              <li key={artefato.ordem} className="flex items-center gap-1.5">
                <Link2 className="h-3 w-3 shrink-0" aria-hidden />
                <span className="truncate">{artefato.nome}</span>
                <span className="shrink-0 text-fg-subtle">{formatarTamanho(artefato.tamanhoBytes)}</span>
                {artefato.arquivoId === null && <Badge tone="neutral">arquivo removido</Badge>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {(acoes.gerarNovo || acoes.revogar) && !confirmandoRevogar && (
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          {acoes.gerarNovo && (
            <Button type="button" onClick={() => setCriando(true)} disabled={revogando}>
              {atual ? "Gerar novo link" : "Enviar para aprovação do cliente"}
            </Button>
          )}
          {acoes.revogar && (
            <Button type="button" variant="secondary" onClick={() => setConfirmandoRevogar(true)} disabled={revogando}>
              Revogar link
            </Button>
          )}
        </div>
      )}
      {confirmandoRevogar && (
        <div className="mt-2.5 flex flex-wrap items-center gap-2" role="group" aria-label="Confirmar revogação">
          <span className="text-xs text-fg">O cliente deixará de conseguir abrir este link. Revogar?</span>
          <Button type="button" onClick={() => void revogar()} disabled={revogando}>
            {revogando ? "Revogando…" : "Revogar"}
          </Button>
          <Button type="button" variant="secondary" onClick={() => setConfirmandoRevogar(false)} disabled={revogando}>
            Cancelar
          </Button>
        </div>
      )}

      {criando && (
        <NovoLinkModal
          demanda={demanda}
          etapa={etapa}
          painel={painel}
          substituiLinkAberto={atual?.estado === "pendente"}
          onFechar={() => {
            setCriando(false);
            void recarregar();
          }}
          onConflito={() => {
            setCriando(false);
            void recarregarWorkflow();
          }}
        />
      )}
    </div>
  );
}

function NovoLinkModal({
  demanda,
  etapa,
  painel,
  substituiLinkAberto,
  onFechar,
  onConflito,
}: {
  demanda: Demanda;
  etapa: DemandaWorkflowEtapa;
  painel: AprovacaoExternaPainel;
  substituiLinkAberto: boolean;
  onFechar: () => void;
  onConflito: () => void;
}) {
  const [arquivos, setArquivos] = useState<DemandaArquivo[] | null>(null);
  const [selecionados, setSelecionados] = useState<string[]>([]);
  const [instrucao, setInstrucao] = useState("");
  const [validade, setValidade] = useState(String(painel.validadePadraoDias));
  const [contatoIndice, setContatoIndice] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  // O token vive SÓ aqui (memória do componente). Nunca em storage, URL ou contexto compartilhado; o modal fecha → some.
  const [link, setLink] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);

  const contatos = ordenarContatos(painel.contatos);

  useEffect(() => {
    let cancelado = false;
    listArquivosDemanda(demanda.id)
      .then((lista) => {
        if (!cancelado) setArquivos(lista.filter(arquivoElegivelParaAprovacao));
      })
      .catch(() => {
        if (!cancelado) setErro("Não foi possível carregar os arquivos da tarefa.");
      });
    return () => {
      cancelado = true;
    };
  }, [demanda.id]);

  async function gerar() {
    if (enviando) return;
    setEnviando(true);
    setErro(null);
    const contato = contatoIndice === "" ? null : (contatos[Number(contatoIndice)] ?? null);
    const resultado = await criarLinkDeAprovacao({
      corpo: montarEntradaDeCriacao({ arquivoIds: selecionados, instrucao, validadeDias: Number(validade), contato }),
      criar: (corpo) => criarAprovacaoExternaReal(demanda.id, etapa.id, corpo),
      ehConflito: ehConflitoDeWorkflow,
    });
    setEnviando(false);
    if (resultado.ok) {
      setLink(linkDeAprovacao(window.location.origin, resultado.criada.empresaSlug, resultado.criada.token));
      return;
    }
    if (resultado.conflito) {
      onConflito();
      return;
    }
    setErro(resultado.mensagem);
  }

  async function copiar() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
    } catch {
      setCopiado(false);
      setErro("Não foi possível copiar automaticamente. Selecione o link e copie manualmente.");
    }
  }

  const erroInstrucao = erroDaInstrucao(instrucao);

  return (
    <Modal open onClose={() => (enviando ? undefined : onFechar())} maxWidthClassName="max-w-lg">
      {link ? (
        <div className="flex flex-col gap-3" role="dialog" aria-label="Link de aprovação gerado">
          <h3 className="text-base font-semibold text-fg">Link de aprovação gerado</h3>
          <Input label="Link para o cliente" value={link} readOnly onFocus={(event) => event.currentTarget.select()} />
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void copiar()}>
              <Copy className="h-3.5 w-3.5" aria-hidden /> {copiado ? "Copiado" : "Copiar link"}
            </Button>
          </div>
          <p role="note" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
            {AVISO_LINK_UNICO}
          </p>
          {erro && (
            <p role="alert" className="text-xs text-red-600 dark:text-red-400">
              {erro}
            </p>
          )}
          <div className="flex justify-end">
            <Button type="button" variant="secondary" onClick={onFechar}>
              Fechar
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3" role="dialog" aria-label="Enviar para aprovação do cliente">
          <h3 className="text-base font-semibold text-fg">Enviar para aprovação do cliente</h3>
          <p className="text-xs text-fg-muted">
            O cliente abre o link sem login e vê apenas os arquivos escolhidos abaixo. Ele pode aprovar ou solicitar ajustes.
            {substituiLinkAberto ? " O link ativo atual será revogado." : ""}
          </p>

          <fieldset className="flex flex-col gap-1.5">
            <legend className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
              Arquivos para avaliação * ({selecionados.length}/{ARQUIVOS_MAX})
            </legend>
            {arquivos === null && <p className="text-xs text-fg-muted">Carregando arquivos…</p>}
            {arquivos !== null && arquivos.length === 0 && (
              <p className="text-xs text-fg-muted">Nenhum arquivo PNG, JPG ou PDF nesta tarefa. Envie um layout na aba Arquivos.</p>
            )}
            {arquivos?.map((arquivo) => (
              <label key={arquivo.id} className="flex items-center gap-2 rounded-lg border border-line px-2.5 py-1.5 text-xs text-fg">
                <input
                  type="checkbox"
                  checked={selecionados.includes(arquivo.id)}
                  onChange={() => setSelecionados((atuais) => alternarArquivo(atuais, arquivo.id))}
                  disabled={enviando}
                />
                <span className="min-w-0 flex-1 truncate">{arquivo.nomeOriginal}</span>
                <span className="shrink-0 text-fg-subtle">{formatarTamanho(arquivo.tamanhoBytes)}</span>
              </label>
            ))}
          </fieldset>

          <div className="grid gap-3 sm:grid-cols-2">
            <Select
              label="Validade do link"
              value={validade}
              onChange={(event) => setValidade(event.target.value)}
              options={VALIDADES_DIAS.filter((dias) => dias <= painel.validadeMaxDias).map((dias) => ({
                value: String(dias),
                label: dias === 1 ? "1 dia" : `${dias} dias`,
              }))}
              disabled={enviando}
            />
            <Select
              label="Para quem é o link"
              value={contatoIndice}
              onChange={(event) => setContatoIndice(event.target.value)}
              options={[
                { value: "", label: "Não informar" },
                ...contatos.map((contato, indice) => ({
                  value: String(indice),
                  label: `${contato.nome}${contato.email ? ` · ${contato.email}` : ""}${contato.recebeEntregas ? " · recebe entregas" : ""}`,
                })),
              ]}
              disabled={enviando}
            />
          </div>

          <Textarea
            label="Instrução para o cliente"
            value={instrucao}
            onChange={(event) => setInstrucao(event.target.value)}
            rows={3}
            maxLength={INSTRUCAO_MAX}
            disabled={enviando}
          />
          {erroInstrucao && (
            <p role="alert" className="text-xs text-red-600 dark:text-red-400">
              {erroInstrucao}
            </p>
          )}
          {erro && (
            <p role="alert" className="text-xs text-red-600 dark:text-red-400">
              {erro}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onFechar} disabled={enviando}>
              Cancelar
            </Button>
            <Button type="button" onClick={() => void gerar()} disabled={enviando || selecionados.length === 0 || erroInstrucao !== null}>
              <ExternalLink className="h-3.5 w-3.5" aria-hidden /> {enviando ? "Gerando…" : "Gerar link"}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
