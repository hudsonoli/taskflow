"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type MouseEvent } from "react";
import { Check, ChevronDown, ChevronsUpDown, Plus, Search, X } from "lucide-react";
import clsx from "clsx";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import {
  dividirVisiveis,
  filtrarPessoas,
  podeEscolher,
  posicionarPopover,
  primeiroNome,
  proximaSelecao,
  selecionadosPrimeiro,
} from "@/lib/member-selector";

/**
 * Só um modelo de UI (NUNCA uma entidade de domínio): o seletor continua entregando `string[]` de ids ao consumidor. `email` aparece (e entra na busca local) só
 * quando a fonte o fornece — o diretório de usuários do backend não o expõe. `inativo` = usuário que não está `ativo` (histórico): aparece marcado e não pode ser
 * escolhido de novo (a menos que o campo declare `permitirInativos`).
 */
export interface MemberOption {
  id: string;
  nome: string;
  subtitulo?: string;
  email?: string;
  inativo?: boolean;
  corIdentificacao?: string;
  fotoUrl?: string;
}

/**
 * Busca de opções no servidor (modo opcional do `MemberSelector`). `busca` já vem aparada
 * (vazia = primeira página sem filtro); `limit`/`offset` paginam. Devolve só a página pedida.
 */
export type BuscarOpcoesMembros = (params: { busca: string; limit: number; offset: number }) => Promise<MemberOption[]>;

/**
 * Resolve id -> nome de quem JÁ está em `values` mas nunca passou pelo dropdown (ex.: os
 * responsáveis de uma Demanda aberta para edição, que podem estar fora da primeira página de
 * qualquer busca). Devolve só os que encontrou; um id ausente do resultado vira "indisponível".
 */
export type ResolverSelecionadosMembros = (ids: string[]) => Promise<MemberOption[]>;

const TAMANHO_PAGINA_PADRAO = 30;
const DEBOUNCE_PADRAO_MS = 300;

/**
 * Seletor de membros com dois modos:
 *
 * - **estático** (padrão, todos os usos antigos): recebe `options` já carregadas e filtra no
 *   cliente. Comportamento inalterado.
 * - **servidor**: com `buscarOpcoes`, NÃO recebe a lista toda — carrega a primeira página ao abrir,
 *   busca no servidor conforme o usuário digita (debounce) e pagina com "Carregar mais". Os
 *   selecionados ficam guardados localmente (id + nome), então uma nova busca nunca os faz sumir
 *   dos chips. `buscarOpcoes` pode ser uma função inline: a versão mais recente é lida por ref.
 */
export function MemberSelector({
  label,
  options = [],
  values,
  onChange,
  multiple = true,
  placeholder = "Selecionar membros…",
  emptyLabel = "Nenhum membro encontrado",
  buscarOpcoes,
  resolverSelecionados,
  ordenarSelecionados = "selecao",
  tamanhoPagina = TAMANHO_PAGINA_PADRAO,
  debounceMs = DEBOUNCE_PADRAO_MS,
  variant = "default",
  max,
  maxVisible,
  disabled = false,
  permitirInativos = false,
  className,
}: {
  label: string;
  options?: MemberOption[];
  values: string[];
  /** `selecionados` (id + nome de quem ficou selecionado) é útil a quem grava o nome junto do id. */
  onChange: (values: string[], selecionados?: MemberOption[]) => void;
  multiple?: boolean;
  placeholder?: string;
  emptyLabel?: string;
  buscarOpcoes?: BuscarOpcoesMembros;
  /** Só no modo servidor: nomes dos `values` que não vieram de uma busca (ver `ResolverSelecionadosMembros`). */
  resolverSelecionados?: ResolverSelecionadosMembros;
  /** Só no modo servidor: ordem dos chips — a da seleção (padrão) ou alfabética por nome. */
  ordenarSelecionados?: "selecao" | "nome";
  tamanhoPagina?: number;
  debounceMs?: number;
  /** `default`: avatares com o primeiro nome embaixo + "+" (formulários, workflow). `compact`: campo enxuto de uma linha (Tráfego, barras de filtro, relatórios). */
  variant?: "default" | "compact";
  /** Limite de pessoas no modo múltiplo (ignorado no `multiple={false}`). */
  max?: number;
  /** Quantos aparecem antes de virar "+N" (padrão: 6 no default, 4 no compact). */
  maxVisible?: number;
  /** Somente leitura: avatares visíveis, sem abrir nem alterar. */
  disabled?: boolean;
  /** Campos históricos/administrativos que podem escolher usuário não-ativo (ex.: permissões de quem já saiu). Padrão: inativo não é escolhido de novo. */
  permitirInativos?: boolean;
  className?: string;
}) {
  const remoto = buscarOpcoes !== undefined;
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [posicao, setPosicao] = useState<{ largura: number; deslocamentoX: number; vertical: "baixo" | "cima" }>({ largura: 352, deslocamentoX: 0, vertical: "baixo" });
  const containerRef = useRef<HTMLDivElement>(null);
  const gatilhoRef = useRef<HTMLButtonElement>(null);
  const buscaRef = useRef<HTMLInputElement>(null);
  const idLista = useId();
  const compacto = variant === "compact";

  // --- modo servidor -----------------------------------------------------------------
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [resultados, setResultados] = useState<MemberOption[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [temMais, setTemMais] = useState(false);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [erroMais, setErroMais] = useState<string | null>(null);
  // Id + nome de quem já foi escolhido: o resultado de uma busca nova não os contém.
  const [escolhidos, setEscolhidos] = useState<Record<string, MemberOption>>({});
  // Ids já resolvidos por `resolverSelecionados` (com ou sem sucesso): enquanto um id sem nome não
  // está aqui, o chip diz "Carregando…"; depois, "Usuário indisponível" — nunca o UUID cru.
  const [resolvidos, setResolvidos] = useState<Record<string, true>>({});
  const buscarRef = useRef(buscarOpcoes);
  const resolverRef = useRef(resolverSelecionados);
  const chaveVigenteRef = useRef<string | null>(null);
  const tentadosRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    buscarRef.current = buscarOpcoes;
    resolverRef.current = resolverSelecionados;
  });

  // Nome dos selecionados que nunca passaram pelo dropdown (edição de um registro existente):
  // pedido uma vez por id; falha libera nova tentativa na próxima mudança de `values`.
  useEffect(() => {
    if (!remoto || !resolverRef.current) return;
    const faltando = values.filter((id) => !escolhidos[id] && !tentadosRef.current.has(id));
    if (faltando.length === 0) return;
    faltando.forEach((id) => tentadosRef.current.add(id));
    resolverRef
      .current(faltando)
      .then((opcoes) => {
        setEscolhidos((atual) => ({ ...atual, ...Object.fromEntries(opcoes.map((opcao) => [opcao.id, opcao])) }));
        setResolvidos((atual) => ({ ...atual, ...Object.fromEntries(faltando.map((id) => [id, true as const])) }));
      })
      .catch(() => {
        faltando.forEach((id) => tentadosRef.current.delete(id));
      });
  }, [remoto, values, escolhidos]);

  useEffect(() => {
    function handleClickOutside(event: globalThis.MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
        setQuery("");
        setBuscaAplicada("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounce da digitação: só o texto "assentado" vira busca no servidor.
  useEffect(() => {
    if (!remoto) return;
    const timeout = setTimeout(() => setBuscaAplicada(query.trim()), debounceMs);
    return () => clearTimeout(timeout);
  }, [query, remoto, debounceMs]);

  // Chave da consulta vigente: só existe com o dropdown aberto. Comparada durante o RENDER (não
  // dentro do efeito) — mesmo padrão de DemandasView/useAjustesProjeto, por causa da regra
  // react-hooks/set-state-in-effect deste projeto.
  const chaveBusca = remoto && open ? buscaAplicada : null;
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  if (chaveBusca !== chaveConsultada) {
    setChaveConsultada(chaveBusca);
    setCarregandoMais(false);
    setErroMais(null);
    if (chaveBusca !== null) {
      setCarregando(true);
      setErro(null);
    }
  }

  useEffect(() => {
    chaveVigenteRef.current = chaveBusca;
    if (chaveBusca === null || !buscarRef.current) return;
    let cancelado = false;
    buscarRef.current({ busca: chaveBusca, limit: tamanhoPagina, offset: 0 })
      .then((pagina) => {
        if (cancelado) return; // resposta obsoleta: outra busca (ou fechar o dropdown) veio depois
        setResultados(pagina);
        setTemMais(pagina.length === tamanhoPagina);
        setErro(null);
        setCarregando(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setResultados([]);
        setTemMais(false);
        setErro(error instanceof Error ? error.message : "Não foi possível buscar usuários.");
        setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [chaveBusca, tamanhoPagina]);

  function carregarMais() {
    const chave = chaveVigenteRef.current;
    if (chave === null || !buscarRef.current) return;
    setCarregandoMais(true);
    setErroMais(null);
    buscarRef.current({ busca: chave, limit: tamanhoPagina, offset: resultados.length })
      .then((pagina) => {
        if (chaveVigenteRef.current !== chave) return; // a busca mudou enquanto esta página vinha
        setResultados((atual) => {
          const jaNaTela = new Set(atual.map((opcao) => opcao.id));
          return [...atual, ...pagina.filter((opcao) => !jaNaTela.has(opcao.id))];
        });
        setTemMais(pagina.length === tamanhoPagina);
      })
      .catch((error) => {
        if (chaveVigenteRef.current !== chave) return;
        setErroMais(error instanceof Error ? error.message : "Não foi possível carregar mais usuários.");
      })
      .finally(() => {
        if (chaveVigenteRef.current === chave) setCarregandoMais(false);
      });
  }

  // --- seleção -----------------------------------------------------------------------
  const selecionados = remoto ? selecionadosDoServidor() : options.filter((option) => values.includes(option.id));
  const termo = query.trim();
  // Local: busca por nome/e-mail/subtítulo, sem acento. Servidor: a lista já vem filtrada. Sem busca, quem já está selecionado vem PRIMEIRO.
  const baseLista = remoto ? resultados : filtrarPessoas(options, termo);
  const filtrados = termo
    ? baseLista
    : remoto
      ? [...selecionados.filter((opcao) => opcao.nome !== "Carregando…" && opcao.nome !== "Usuário indisponível"), ...baseLista.filter((opcao) => !values.includes(opcao.id))]
      : selecionadosPrimeiro(baseLista, values);

  /** Chips do modo servidor: os já conhecidos (id + nome) e, para quem ainda não tem nome, um chip
   * provisório removível — sem ele o usuário não conseguiria tirar um responsável que não carregou. */
  function selecionadosDoServidor(): MemberOption[] {
    const conhecidos = values.filter((id) => escolhidos[id]).map((id) => escolhidos[id]);
    if (ordenarSelecionados === "nome") conhecidos.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
    const semNome = values
      .filter((id) => !escolhidos[id])
      .map((id) => ({ id, nome: !resolverSelecionados || resolvidos[id] ? "Usuário indisponível" : "Carregando…" }));
    return [...conhecidos, ...semNome];
  }

  /** Id + nome de quem fica selecionado após uma mudança (cache do servidor ou `options`). */
  function selecionadosDe(proximos: string[], escolhida?: MemberOption): MemberOption[] {
    const conhecidos: Record<string, MemberOption> = remoto
      ? { ...escolhidos, ...(escolhida ? { [escolhida.id]: escolhida } : {}) }
      : Object.fromEntries(options.map((opcao) => [opcao.id, opcao]));
    return proximos.flatMap((id) => (conhecidos[id] ? [conhecidos[id]] : []));
  }

  function fechar(devolverFoco = false) {
    setOpen(false);
    setQuery("");
    setBuscaAplicada("");
    if (devolverFoco) gatilhoRef.current?.focus();
  }

  /** Abre medindo a tela ANTES (handler de evento, não efeito): alinha à direita / abre para cima se o popover estouraria a viewport. */
  function abrir() {
    if (disabled) return;
    const caixa = containerRef.current?.getBoundingClientRect();
    if (caixa) {
      setPosicao(
        posicionarPopover({
          caixa,
          larguraPopover: Math.min(352, window.innerWidth - 32),
          alturaPopover: 320,
          viewport: { largura: window.innerWidth, altura: window.innerHeight },
        }),
      );
    }
    setOpen(true);
  }

  function alternar() {
    if (open) fechar();
    else abrir();
  }

  function toggle(option: MemberOption) {
    const id = option.id;
    const escolha = proximaSelecao({ values, id, multiple, max });
    if (escolha.bloqueadoPorLimite) return;
    if (remoto && !values.includes(id)) {
      setEscolhidos((atual) => ({ ...atual, [id]: option }));
    }
    onChange(escolha.values, selecionadosDe(escolha.values, option));
    if (escolha.fechar) fechar(true);
  }

  function remove(id: string, event: MouseEvent) {
    event.stopPropagation();
    if (disabled) return;
    const proximos = values.filter((value) => value !== id);
    onChange(proximos, selecionadosDe(proximos));
  }

  /** Esc em qualquer ponto do campo (inclusive no gatilho, com o popover aberto) fecha e devolve o foco ao gatilho. */
  function aoTeclarNoContainer(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (open && event.key === "Escape") {
      event.stopPropagation();
      fechar(true);
    }
  }

  /** Teclado no popover: ↓ da busca vai à primeira opção; ↑/↓ entre opções; ↑ na primeira volta à busca; Esc fecha e devolve o foco ao gatilho. */
  function aoTeclarNoPopover(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.stopPropagation();
      fechar(true);
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    const itens = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('[role="option"]:not([aria-disabled="true"])'));
    if (itens.length === 0) return;
    event.preventDefault();
    const atual = itens.indexOf(document.activeElement as HTMLElement);
    if (event.key === "ArrowDown") itens[Math.min(itens.length - 1, atual + 1)]?.focus();
    else if (atual <= 0) buscaRef.current?.focus();
    else itens[atual - 1]?.focus();
  }

  const carregandoPrimeiraPagina = remoto && carregando && resultados.length === 0;
  const { visiveis, restantes } = dividirVisiveis(selecionados, maxVisible ?? (compacto ? 4 : 6));
  const limiteAtingido = multiple && max !== undefined && max >= 1 && values.length >= max;
  const podeAdicionar = !disabled && (!multiple || !limiteAtingido);
  const nomeCampo = label.toLowerCase();

  const popover = open && (
    <div
      onKeyDown={aoTeclarNoPopover}
      data-superficie="menu"
      style={{ width: posicao.largura, left: posicao.deslocamentoX }}
      className={clsx(
        "absolute z-30 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-line bg-surface shadow-lg",
        posicao.vertical === "cima" ? "bottom-full mb-1" : "top-full mt-1",
      )}
    >
      <div className="border-b border-line p-2">
        <span className="relative block">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-fg-subtle" aria-hidden />
          <input
            ref={buscaRef}
            autoFocus
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar usuário…"
            aria-label={`Buscar ${nomeCampo}`}
            aria-controls={idLista}
            className="field w-full rounded-lg py-1.5 pl-8 pr-2 text-sm"
          />
        </span>
      </div>
      <div
        id={idLista}
        role="listbox"
        aria-label={label}
        aria-multiselectable={multiple}
        className={clsx("max-h-60 overflow-y-auto p-1.5", remoto && carregando && resultados.length > 0 && "opacity-60 transition-opacity")}
      >
        {carregandoPrimeiraPagina ? (
          <p className="px-3 py-2 text-sm text-fg-subtle">Carregando…</p>
        ) : remoto && erro ? (
          <p className="px-3 py-2 text-sm text-red-600 dark:text-red-400">{erro}</p>
        ) : filtrados.length === 0 ? (
          <p className="px-3 py-2 text-sm text-fg-subtle">{emptyLabel}</p>
        ) : (
          filtrados.map((option) => {
            const isSelected = values.includes(option.id);
            const escolhivel = podeEscolher({ selecionado: isSelected, inativo: option.inativo, permitirInativos, totalSelecionados: values.length, max, multiple });
            const secundario = option.email ?? option.subtitulo;
            return (
              <button
                key={option.id}
                type="button"
                role="option"
                aria-selected={isSelected}
                aria-disabled={!escolhivel}
                onClick={() => escolhivel && toggle(option)}
                className={clsx(
                  "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400",
                  isSelected ? "bg-indigo-50/60 dark:bg-indigo-500/10" : escolhivel ? "hover:bg-zinc-50 dark:hover:bg-zinc-800" : "cursor-not-allowed opacity-50",
                )}
              >
                <Avatar nome={option.nome} corIdentificacao={option.corIdentificacao ?? "zinc"} fotoUrl={option.fotoUrl} className="h-8 w-8 shrink-0 rounded-full text-xs" />
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-1.5 font-medium text-fg">
                    <span className="truncate">{option.nome}</span>
                    {option.inativo && <span className="shrink-0 rounded-full bg-zinc-100 px-1.5 py-px text-[10px] font-semibold text-fg-muted dark:bg-zinc-800">Inativo</span>}
                  </p>
                  {secundario && <p className="truncate text-xs text-fg-subtle">{secundario}</p>}
                </div>
                {isSelected ? (
                  <>
                    <Check className="h-4 w-4 shrink-0 text-indigo-600 dark:text-indigo-400" aria-hidden />
                    <span className="sr-only">Selecionado</span>
                  </>
                ) : (
                  <span className="h-4 w-4 shrink-0 rounded-full border border-line" aria-hidden />
                )}
              </button>
            );
          })
        )}
        {remoto && !erro && temMais && (
          <div className="flex flex-col items-center gap-1 p-1.5">
            <Button type="button" variant="secondary" className="px-3 py-1.5 text-xs" onClick={carregarMais} disabled={carregandoMais}>
              {carregandoMais ? "Carregando…" : "Carregar mais"}
            </Button>
            {erroMais && <p className="text-xs text-red-600 dark:text-red-400">{erroMais}</p>}
          </div>
        )}
      </div>
      {multiple && limiteAtingido && <p className="border-t border-line px-3 py-1.5 text-xs text-fg-muted">Limite de {max} atingido</p>}
    </div>
  );

  const aria = {
    "aria-haspopup": "listbox" as const,
    "aria-expanded": open,
    "aria-controls": open ? idLista : undefined,
  };

  // ─── compacto: um campo de uma linha (avatar + nome | pilha de avatares) ───────────────────────────────────────────
  if (compacto) {
    return (
      <div className={clsx("relative", className)} ref={containerRef} onKeyDown={aoTeclarNoContainer}>
        <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{label}</span>
        <button
          ref={gatilhoRef}
          type="button"
          onClick={alternar}
          disabled={disabled}
          aria-label={selecionados.length === 0 ? `${label}: ${placeholder}` : `${label}: ${selecionados.map((pessoa) => pessoa.nome).join(", ")}`}
          {...aria}
          className="field flex min-h-[42px] w-full items-center gap-2 rounded-xl px-2.5 py-1.5 text-left text-sm disabled:cursor-default disabled:opacity-80"
        >
          {selecionados.length === 0 ? (
            <>
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-dashed border-fg-subtle text-fg-subtle" aria-hidden>
                <Plus className="h-3.5 w-3.5" />
              </span>
              <span className="min-w-0 flex-1 truncate text-fg-subtle">{placeholder}</span>
            </>
          ) : multiple ? (
            <>
              <span className="flex shrink-0 items-center">
                {visiveis.map((pessoa, indice) => (
                  <span key={pessoa.id} title={pessoa.nome} className={clsx("rounded-full ring-2 ring-surface", indice > 0 && "-ml-2")}>
                    <Avatar nome={pessoa.nome} corIdentificacao={pessoa.corIdentificacao ?? "zinc"} fotoUrl={pessoa.fotoUrl} className="h-7 w-7 rounded-full text-[10px]" />
                  </span>
                ))}
                {restantes.length > 0 && (
                  <span title={restantes.map((pessoa) => pessoa.nome).join(", ")} className="-ml-2 flex h-7 min-w-7 items-center justify-center rounded-full bg-zinc-100 px-1.5 text-[11px] font-semibold text-fg-muted ring-2 ring-surface dark:bg-zinc-800">
                    +{restantes.length}
                  </span>
                )}
              </span>
              <span className="min-w-0 flex-1 truncate text-xs text-fg-muted">{selecionados.length === 1 ? selecionados[0].nome : `${selecionados.length} selecionados`}</span>
            </>
          ) : (
            <>
              <Avatar nome={selecionados[0].nome} corIdentificacao={selecionados[0].corIdentificacao ?? "zinc"} fotoUrl={selecionados[0].fotoUrl} className="h-7 w-7 shrink-0 rounded-full text-[10px]" />
              <span className="min-w-0 flex-1 truncate font-medium text-fg">{selecionados[0].nome}</span>
              {selecionados[0].inativo && <span className="shrink-0 rounded-full bg-zinc-100 px-1.5 py-px text-[10px] font-semibold text-fg-muted dark:bg-zinc-800">Inativo</span>}
            </>
          )}
          {!disabled && <ChevronDown className={clsx("h-4 w-4 shrink-0 text-fg-subtle transition", open && "rotate-180")} aria-hidden />}
        </button>
        {popover}
      </div>
    );
  }

  // ─── padrão: avatares com o primeiro nome embaixo + botão "+" ─────────────────────────────────────────────────────
  return (
    <div className={clsx("relative", className)} ref={containerRef} onKeyDown={aoTeclarNoContainer}>
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{label}</span>
      <div className={clsx("flex flex-wrap items-start gap-3", disabled && "opacity-80")}>
        {visiveis.map((pessoa) => (
          <div key={pessoa.id} title={pessoa.nome} className="group relative flex w-14 flex-col items-center gap-1">
            <Avatar nome={pessoa.nome} corIdentificacao={pessoa.corIdentificacao ?? "zinc"} fotoUrl={pessoa.fotoUrl} className="h-10 w-10 rounded-full text-sm ring-2 ring-surface transition group-hover:scale-105" />
            <span className="w-full truncate text-center text-[11px] font-medium text-fg-muted">{primeiroNome(pessoa.nome)}</span>
            {pessoa.inativo && <span className="-mt-0.5 rounded-full bg-zinc-100 px-1.5 py-px text-[9px] font-semibold text-fg-muted dark:bg-zinc-800">Inativo</span>}
            {!disabled && (
              <button
                type="button"
                onClick={(event) => remove(pessoa.id, event)}
                aria-label={`Remover ${pessoa.nome}`}
                className="absolute -right-0.5 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-surface text-fg-muted opacity-0 shadow ring-1 ring-line transition hover:text-fg focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 group-focus-within:opacity-100 group-hover:opacity-100"
              >
                <X className="h-2.5 w-2.5" aria-hidden />
              </button>
            )}
          </div>
        ))}
        {restantes.length > 0 && (
          <button
            type="button"
            onClick={alternar}
            disabled={disabled}
            title={restantes.map((pessoa) => pessoa.nome).join(", ")}
            aria-label={`Mais ${restantes.length} selecionados: ${restantes.map((pessoa) => pessoa.nome).join(", ")}`}
            className="flex h-10 min-w-10 items-center justify-center rounded-full bg-zinc-100 px-2 text-xs font-semibold text-fg-muted transition hover:bg-zinc-200 disabled:cursor-default dark:bg-zinc-800 dark:hover:bg-zinc-700"
          >
            +{restantes.length}
          </button>
        )}
        {(podeAdicionar || (multiple === false && !disabled)) && (
          <button
            ref={gatilhoRef}
            type="button"
            onClick={alternar}
            aria-label={multiple === false && selecionados.length > 0 ? `Trocar ${nomeCampo}` : `Adicionar ${nomeCampo}`}
            {...aria}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-dashed border-fg-subtle text-fg-subtle transition hover:scale-105 hover:border-fg hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            {multiple === false && selecionados.length > 0 ? <ChevronsUpDown className="h-4 w-4" aria-hidden /> : <Plus className="h-4 w-4" aria-hidden />}
          </button>
        )}
        {selecionados.length === 0 && <span className="self-center text-sm text-fg-subtle">{placeholder}</span>}
        {disabled && selecionados.length > 0 && <span className="sr-only">Somente leitura</span>}
      </div>
      {popover}
    </div>
  );
}
