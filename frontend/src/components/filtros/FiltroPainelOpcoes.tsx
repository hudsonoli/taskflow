"use client";

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Check, Search } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { campoBuscavel } from "@/lib/filtros-avancados";
import type { DefinicaoFiltro, OpcaoFiltro } from "@/types/filtros";

const TAMANHO_PAGINA = 30;
const DEBOUNCE_MS = 300;

function semAcento(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/**
 * Lista de opções de um campo (valores do filtro): busca dentro das opções, seleção múltipla e navegação por teclado
 * (setas, Enter, Home/End). Opções locais são filtradas no cliente; opções no servidor (`buscarOpcoes`) são buscadas com
 * debounce, paginadas ("Carregar mais") e a resposta de uma busca antiga é descartada.
 */
export function FiltroPainelOpcoes({
  definicao,
  selecionados,
  onAlternar,
}: {
  definicao: DefinicaoFiltro;
  selecionados: readonly string[];
  onAlternar: (opcao: OpcaoFiltro) => void;
}) {
  const idLista = useId();
  const remoto = Boolean(definicao.buscarOpcoes);
  const buscavel = campoBuscavel(definicao);
  const [consulta, setConsulta] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [ativo, setAtivo] = useState(0);
  const [resultados, setResultados] = useState<OpcaoFiltro[]>([]);
  const [carregando, setCarregando] = useState(remoto);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [temMais, setTemMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const buscarRef = useRef(definicao.buscarOpcoes);
  const chaveRef = useRef<string>("");
  const entradaRef = useRef<HTMLInputElement>(null);
  const listaRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    buscarRef.current = definicao.buscarOpcoes;
  });

  useEffect(() => {
    // abre com o foco na busca (ou na lista, se não há campo de busca)
    (entradaRef.current ?? listaRef.current)?.focus();
  }, []);

  // Debounce da digitação (só no modo servidor; no local o filtro é imediato).
  useEffect(() => {
    if (!remoto) return;
    const timeout = setTimeout(() => setBuscaAplicada(consulta.trim()), DEBOUNCE_MS);
    return () => clearTimeout(timeout);
  }, [consulta, remoto]);

  useEffect(() => {
    if (!remoto || !buscarRef.current) return;
    let cancelado = false;
    chaveRef.current = buscaAplicada;
    buscarRef
      .current({ busca: buscaAplicada, limit: TAMANHO_PAGINA, offset: 0 })
      .then((pagina) => {
        if (cancelado) return; // busca antiga: outra veio depois
        setResultados(pagina);
        setTemMais(pagina.length === TAMANHO_PAGINA);
        setErro(null);
      })
      .catch((falha) => {
        if (cancelado) return;
        setResultados([]);
        setTemMais(false);
        setErro(falha instanceof Error ? falha.message : "Não foi possível buscar as opções.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [remoto, buscaAplicada]);

  function carregarMais() {
    if (!buscarRef.current) return;
    const chave = chaveRef.current;
    setCarregandoMais(true);
    buscarRef
      .current({ busca: chave, limit: TAMANHO_PAGINA, offset: resultados.length })
      .then((pagina) => {
        if (chaveRef.current !== chave) return;
        setResultados((atual) => {
          const vistos = new Set(atual.map((opcao) => opcao.value));
          return [...atual, ...pagina.filter((opcao) => !vistos.has(opcao.value))];
        });
        setTemMais(pagina.length === TAMANHO_PAGINA);
      })
      .catch(() => setTemMais(false))
      .finally(() => setCarregandoMais(false));
  }

  const opcoes = useMemo(() => {
    if (remoto) return resultados;
    const todas = definicao.opcoes ?? [];
    const termo = semAcento(consulta.trim());
    return termo ? todas.filter((opcao) => semAcento(opcao.label).includes(termo)) : todas;
  }, [remoto, resultados, definicao.opcoes, consulta]);

  const indiceAtivo = Math.min(ativo, Math.max(0, opcoes.length - 1));

  function aoTeclar(evento: KeyboardEvent) {
    if (opcoes.length === 0) return;
    if (evento.key === "ArrowDown") {
      evento.preventDefault();
      setAtivo((indiceAtivo + 1) % opcoes.length);
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      setAtivo((indiceAtivo - 1 + opcoes.length) % opcoes.length);
    } else if (evento.key === "Home") {
      evento.preventDefault();
      setAtivo(0);
    } else if (evento.key === "End") {
      evento.preventDefault();
      setAtivo(opcoes.length - 1);
    } else if (evento.key === "Enter") {
      evento.preventDefault();
      onAlternar(opcoes[indiceAtivo]);
    }
  }

  useEffect(() => {
    // mantém a opção ativa visível ao navegar pelo teclado
    document.getElementById(`${idLista}-${indiceAtivo}`)?.scrollIntoView?.({ block: "nearest" });
  }, [idLista, indiceAtivo]);

  const vazio = remoto ? (carregando ? "Carregando…" : (erro ?? (definicao.mensagemVazio ?? "Nenhuma opção encontrada"))) : (definicao.mensagemVazio ?? "Nenhuma opção encontrada");

  return (
    <div onKeyDown={aoTeclar}>
      {buscavel && (
        <div className="relative border-b border-line p-2">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-fg-subtle" aria-hidden />
          <input
            ref={entradaRef}
            value={consulta}
            onChange={(evento) => {
              setConsulta(evento.target.value);
              setAtivo(0);
            }}
            placeholder={definicao.placeholderBusca ?? `Buscar ${definicao.label.toLowerCase()}…`}
            aria-label={`Buscar em ${definicao.label}`}
            aria-controls={idLista}
            aria-activedescendant={opcoes.length > 0 ? `${idLista}-${indiceAtivo}` : undefined}
            className="field w-full rounded-lg py-1.5 pl-8 pr-2 text-xs"
          />
        </div>
      )}
      <ul
        ref={listaRef}
        id={idLista}
        role="listbox"
        aria-label={definicao.label}
        aria-multiselectable={definicao.multiplo !== false}
        tabIndex={buscavel ? -1 : 0}
        className="max-h-64 overflow-y-auto p-1 focus:outline-none"
      >
        {opcoes.length === 0 ? (
          <li role="presentation" className={`px-3 py-4 text-center text-xs ${erro ? "text-danger" : "text-fg-subtle"}`}>
            {vazio}
          </li>
        ) : (
          opcoes.map((opcao, indice) => {
            const marcada = selecionados.includes(opcao.value);
            return (
              <li
                key={opcao.value}
                id={`${idLista}-${indice}`}
                role="option"
                aria-selected={marcada}
                onMouseEnter={() => setAtivo(indice)}
                onClick={() => onAlternar(opcao)}
                className={`flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs ${
                  indice === indiceAtivo ? "bg-surface-hover" : ""
                } ${marcada ? "font-semibold text-fg" : "text-fg-muted"}`}
              >
                <span
                  aria-hidden
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                    marcada ? "border-transparent bg-brand-gradient" : "border-line-strong"
                  }`}
                >
                  {marcada && <Check className="h-3 w-3" />}
                </span>
                {opcao.avatar && (
                  <Avatar
                    nome={opcao.avatar.nome}
                    corIdentificacao={opcao.avatar.corIdentificacao ?? "blue"}
                    fotoUrl={opcao.avatar.fotoUrl}
                    className="h-5 w-5 shrink-0 rounded-full text-[9px]"
                  />
                )}
                <span className="min-w-0 flex-1 truncate">{opcao.label}</span>
                {opcao.descricao && <span className="shrink-0 text-[10px] text-fg-subtle">{opcao.descricao}</span>}
              </li>
            );
          })
        )}
        {remoto && temMais && (
          <li role="presentation" className="p-1">
            <button
              type="button"
              onClick={carregarMais}
              disabled={carregandoMais}
              className="w-full rounded-lg px-2 py-1.5 text-center text-xs font-medium text-fg-muted hover:bg-surface-hover disabled:opacity-50"
            >
              {carregandoMais ? "Carregando…" : "Carregar mais"}
            </button>
          </li>
        )}
      </ul>
    </div>
  );
}
