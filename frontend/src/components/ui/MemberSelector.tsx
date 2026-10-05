"use client";

import { useEffect, useRef, useState, type MouseEvent } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";

export interface MemberOption {
  id: string;
  nome: string;
  subtitulo?: string;
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
}) {
  const remoto = buscarOpcoes !== undefined;
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

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
  const filtrados = remoto
    ? resultados
    : query.trim()
      ? options.filter((option) => option.nome.toLowerCase().includes(query.trim().toLowerCase()))
      : options;

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

  function toggle(option: MemberOption) {
    const id = option.id;
    if (remoto && !values.includes(id)) {
      setEscolhidos((atual) => ({ ...atual, [id]: option }));
    }
    if (multiple) {
      const proximos = values.includes(id) ? values.filter((value) => value !== id) : [...values, id];
      onChange(proximos, selecionadosDe(proximos, option));
    } else {
      const proximos = values.includes(id) ? [] : [id];
      onChange(proximos, selecionadosDe(proximos, option));
      setOpen(false);
      setQuery("");
      setBuscaAplicada("");
    }
  }

  function remove(id: string, event: MouseEvent) {
    event.stopPropagation();
    const proximos = values.filter((value) => value !== id);
    onChange(proximos, selecionadosDe(proximos));
  }

  const carregandoPrimeiraPagina = remoto && carregando && resultados.length === 0;

  return (
    <div className="relative" ref={containerRef}>
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">{label}</span>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setOpen((current) => !current);
          }
        }}
        className="flex min-h-[42px] w-full cursor-pointer items-center justify-between gap-2 rounded-xl border border-zinc-200/80 bg-zinc-50/70 px-3 py-1.5 text-left text-sm outline-none transition focus:border-indigo-300 focus:bg-white dark:border-zinc-800 dark:bg-zinc-900/60 dark:focus:bg-zinc-900"
      >
        {selecionados.length === 0 ? (
          <span className="text-zinc-400">{placeholder}</span>
        ) : (
          <div className="flex flex-1 flex-wrap items-center gap-1.5 py-0.5">
            {selecionados.map((option) => (
              <span
                key={option.id}
                className="inline-flex items-center gap-1.5 rounded-full bg-white py-0.5 pl-0.5 pr-2 ring-1 ring-zinc-200 dark:bg-zinc-800 dark:ring-zinc-700"
              >
                <Avatar
                  nome={option.nome}
                  corIdentificacao={option.corIdentificacao ?? "zinc"}
                  fotoUrl={option.fotoUrl}
                  className="h-5 w-5 rounded-full text-[10px]"
                />
                <span className="text-xs font-medium text-zinc-700 dark:text-zinc-200">{option.nome}</span>
                {multiple && (
                  <button
                    type="button"
                    onClick={(event) => remove(option.id, event)}
                    aria-label={`Remover ${option.nome}`}
                    className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            ))}
          </div>
        )}
        <ChevronDown className={`h-4 w-4 shrink-0 text-zinc-400 transition ${open ? "rotate-180" : ""}`} />
      </div>

      {open && (
        <div className="absolute z-20 mt-1 w-full min-w-[260px] overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
          <div className="border-b border-zinc-100 p-2 dark:border-zinc-800">
            <span className="relative block">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
              <input
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar…"
                className="w-full rounded-lg border border-transparent bg-zinc-50 py-1.5 pl-8 pr-2 text-sm text-zinc-900 outline-none focus:border-indigo-300 dark:bg-zinc-800 dark:text-zinc-100"
              />
            </span>
          </div>
          <div className={`max-h-60 overflow-y-auto p-1.5 ${remoto && carregando && resultados.length > 0 ? "opacity-60 transition-opacity" : ""}`}>
            {carregandoPrimeiraPagina ? (
              <p className="px-3 py-2 text-sm text-zinc-400">Carregando…</p>
            ) : remoto && erro ? (
              <p className="px-3 py-2 text-sm text-red-600 dark:text-red-400">{erro}</p>
            ) : filtrados.length === 0 ? (
              <p className="px-3 py-2 text-sm text-zinc-400">{emptyLabel}</p>
            ) : (
              filtrados.map((option) => {
                const isSelected = values.includes(option.id);
                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => toggle(option)}
                    className={
                      isSelected
                        ? "flex w-full items-center gap-2.5 rounded-lg bg-indigo-50/60 px-2.5 py-2 text-left text-sm transition dark:bg-indigo-500/10"
                        : "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition hover:bg-zinc-50 dark:hover:bg-zinc-800"
                    }
                  >
                    <Avatar
                      nome={option.nome}
                      corIdentificacao={option.corIdentificacao ?? "zinc"}
                      fotoUrl={option.fotoUrl}
                      className="h-7 w-7 shrink-0 rounded-full text-xs"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-zinc-800 dark:text-zinc-100">{option.nome}</p>
                      {option.subtitulo && <p className="truncate text-xs text-zinc-400">{option.subtitulo}</p>}
                    </div>
                    {isSelected && <Check className="h-4 w-4 shrink-0 text-indigo-600 dark:text-indigo-400" />}
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
        </div>
      )}
    </div>
  );
}
