"use client";

import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent, type ReactNode } from "react";
import { ArrowLeft, Check, ListFilter, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import {
  ROTULO_OPERADOR,
  alternarValor,
  aplicarFiltro,
  filtroDeData,
  limparFiltros,
  operadoresEscolhiveis,
  permiteMultiplos,
  removerFiltro,
  resumirValores,
  rotuloDeData,
  trocarOperador,
} from "@/lib/filtros-avancados";
import type { DefinicaoFiltro, FiltroAtivo, OpcaoFiltro, OperadorFiltro } from "@/types/filtros";
import { FiltroPainelData } from "./FiltroPainelData";
import { FiltroPainelOpcoes } from "./FiltroPainelOpcoes";
import { PainelFlutuante } from "./PainelFlutuante";

type Painel =
  | { tipo: "campos"; ancora: HTMLElement }
  | { tipo: "valores"; campo: string; ancora: HTMLElement; viaCampos: boolean }
  | { tipo: "operador"; campo: string; ancora: HTMLElement };

type Conhecidas = Record<string, Record<string, OpcaoFiltro | null>>;

/**
 * Filtros avançados compartilhados (estilo "Filtrar"): escolhe o CAMPO, depois o VALOR; cada filtro vira um chip
 * `[campo] [operador] [valor] [x]` editável. Genérico: tudo vem das `definicoes` (campos, operadores, opções locais ou no
 * servidor, atalhos de data). Não busca dados nem conhece o domínio: devolve a lista de `FiltroAtivo` em `onChange`.
 *
 * Entre campos diferentes vale AND; dentro de um campo, "é um de" é OR. Em telas estreitas os chips rolam na horizontal e o
 * botão "Filtrar" continua visível.
 */
export function FiltrosAvancados({
  definicoes,
  filtros,
  onChange,
  className,
}: {
  definicoes: readonly DefinicaoFiltro[];
  filtros: readonly FiltroAtivo[];
  onChange: (filtros: FiltroAtivo[]) => void;
  className?: string;
}) {
  const [painel, setPainel] = useState<Painel | null>(null);
  const [conhecidas, setConhecidas] = useState<Conhecidas>({});
  const tentadosRef = useRef<Set<string>>(new Set());
  const resolverRef = useRef<Record<string, DefinicaoFiltro["resolverOpcoes"]>>({});

  useEffect(() => {
    resolverRef.current = Object.fromEntries(definicoes.map((definicao) => [definicao.id, definicao.resolverOpcoes]));
  });

  const porId = new Map(definicoes.map((definicao) => [definicao.id, definicao]));
  const ativos = filtros.filter((filtro) => porId.has(filtro.campo));

  // Rótulos de valores que vieram de fora (URL) e não estão nas opções locais: resolvidos uma vez por valor.
  const faltando = ativos.flatMap((filtro) => {
    const definicao = porId.get(filtro.campo)!;
    if (definicao.tipo !== "enum" || !definicao.resolverOpcoes) return [];
    return filtro.valores
      .filter((valor) => !definicao.opcoes?.some((opcao) => opcao.value === valor) && conhecidas[definicao.id]?.[valor] === undefined)
      .map((valor) => `${definicao.id}\u0000${valor}`);
  });
  const chaveFaltando = faltando.join("\u0001");
  useEffect(() => {
    if (!chaveFaltando) return;
    const porCampo = new Map<string, string[]>();
    for (const item of chaveFaltando.split("\u0001")) {
      if (tentadosRef.current.has(item)) continue;
      tentadosRef.current.add(item);
      const [campo, valor] = item.split("\u0000");
      porCampo.set(campo, [...(porCampo.get(campo) ?? []), valor]);
    }
    for (const [campo, valores] of porCampo) {
      const resolver = resolverRef.current[campo];
      if (!resolver) continue;
      resolver(valores)
        .then((opcoes) => {
          setConhecidas((atual) => {
            const doCampo = { ...atual[campo] };
            for (const valor of valores) doCampo[valor] = opcoes.find((opcao) => opcao.value === valor) ?? null; // null = indisponível
            return { ...atual, [campo]: doCampo };
          });
        })
        .catch(() => {
          valores.forEach((valor) => tentadosRef.current.delete(`${campo}\u0000${valor}`)); // permite nova tentativa
        });
    }
  }, [chaveFaltando]);

  function rotuloDoValor(definicao: DefinicaoFiltro, valor: string): string | undefined {
    if (definicao.tipo === "data") return rotuloDeData(valor, definicao.presets);
    const local = definicao.opcoes?.find((opcao) => opcao.value === valor);
    if (local) return local.label;
    const resolvida = conhecidas[definicao.id]?.[valor];
    if (resolvida === null) return "Indisponível";
    if (resolvida) return resolvida.label;
    // lista local já carregada e sem esse valor (registro arquivado/removido): não fica "Carregando…" para sempre
    return definicao.opcoes && definicao.opcoesCarregadas !== false && !definicao.resolverOpcoes ? "Indisponível" : undefined;
  }

  function fechar() {
    setPainel(null);
  }

  function alternar(definicao: DefinicaoFiltro, opcao: OpcaoFiltro) {
    setConhecidas((atual) => ({ ...atual, [definicao.id]: { ...atual[definicao.id], [opcao.value]: opcao } }));
    const atual = filtros.find((filtro) => filtro.campo === definicao.id);
    const novo = alternarValor(atual, definicao, opcao.value);
    onChange(novo ? aplicarFiltro(filtros, novo) : removerFiltro(filtros, definicao.id));
    if (!permiteMultiplos(definicao)) fechar();
  }

  function aplicarData(definicao: DefinicaoFiltro, operador: OperadorFiltro, valor: string, fecharDepois: boolean) {
    onChange(aplicarFiltro(filtros, filtroDeData(definicao.id, operador, valor)));
    if (fecharDepois) fechar();
  }

  function abrir(tipo: "campos" | "valores" | "operador", evento: MouseEvent<HTMLElement>, campo?: string) {
    const ancora = evento.currentTarget;
    if (painel && painel.ancora === ancora && painel.tipo === tipo) {
      fechar();
      return;
    }
    if (tipo === "campos") setPainel({ tipo, ancora });
    else if (tipo === "valores") setPainel({ tipo, campo: campo!, ancora, viaCampos: false });
    else setPainel({ tipo, campo: campo!, ancora });
  }

  const disponiveis = definicoes.filter((definicao) => !ativos.some((filtro) => filtro.campo === definicao.id));
  const definicaoDoPainel = painel && painel.tipo !== "campos" ? porId.get(painel.campo) : undefined;
  const filtroDoPainel = painel && painel.tipo !== "campos" ? ativos.find((filtro) => filtro.campo === painel.campo) : undefined;

  return (
    <div className={className}>
      <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible sm:pb-0" role="group" aria-label="Filtros">
        {ativos.map((filtro) => {
          const definicao = porId.get(filtro.campo)!;
          const Icone = definicao.icone;
          const operadores = operadoresEscolhiveis(definicao, filtro);
          const resumo = resumirValores(filtro.valores, (valor) => rotuloDoValor(definicao, valor), "Carregando…");
          return (
            <div
              key={filtro.campo}
              role="group"
              aria-label={`Filtro ${definicao.label}`}
              className="inline-flex shrink-0 items-stretch overflow-hidden rounded-lg border border-line-strong bg-surface text-xs shadow-sm"
            >
              <span className="flex items-center gap-1.5 border-r border-line px-2 py-1.5 font-medium text-fg-muted">
                {Icone && <Icone className="h-3.5 w-3.5" aria-hidden />}
                {definicao.label}
              </span>
              {operadores.length > 1 ? (
                <button
                  type="button"
                  aria-haspopup="menu"
                  aria-expanded={painel?.tipo === "operador" && painel.campo === filtro.campo}
                  aria-label={`Operador de ${definicao.label}: ${ROTULO_OPERADOR[filtro.operador]}`}
                  onClick={(evento) => abrir("operador", evento, filtro.campo)}
                  className="border-r border-line px-2 py-1.5 text-fg-subtle hover:bg-surface-hover hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
                >
                  {ROTULO_OPERADOR[filtro.operador]}
                </button>
              ) : (
                <span className="border-r border-line px-2 py-1.5 text-fg-subtle">{ROTULO_OPERADOR[filtro.operador]}</span>
              )}
              <button
                type="button"
                aria-haspopup="dialog"
                aria-expanded={painel?.tipo === "valores" && painel.campo === filtro.campo}
                aria-label={`Valores de ${definicao.label}: ${resumo}`}
                onClick={(evento) => abrir("valores", evento, filtro.campo)}
                className="max-w-[14rem] truncate px-2 py-1.5 font-semibold text-fg hover:bg-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
              >
                {resumo}
              </button>
              <button
                type="button"
                aria-label={`Remover filtro ${definicao.label}`}
                onClick={() => {
                  if (painel && painel.tipo !== "campos" && painel.campo === filtro.campo) fechar();
                  onChange(removerFiltro(filtros, filtro.campo));
                }}
                className="border-l border-line px-1.5 text-fg-subtle hover:bg-surface-hover hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
              >
                <X className="h-3.5 w-3.5" aria-hidden />
              </button>
            </div>
          );
        })}

        {/* Um só botão: no mobile vai para ANTES dos chips (que rolam na horizontal) e continua visível; no desktop fica depois deles. */}
        <Button
          type="button"
          variant="secondary"
          className="order-first shrink-0 sm:order-none"
          aria-haspopup="dialog"
          aria-expanded={painel?.tipo === "campos"}
          onClick={(evento) => abrir("campos", evento)}
        >
          <ListFilter className="h-3.5 w-3.5" aria-hidden />
          Filtrar
        </Button>

        {ativos.length > 0 && (
          <Button type="button" variant="ghost" className="shrink-0" onClick={() => onChange(limparFiltros())}>
            Limpar
          </Button>
        )}
      </div>

      {painel?.tipo === "campos" && (
        <PainelFlutuante ancora={painel.ancora} onFechar={fechar} rotulo="Filtrar por">
          {disponiveis.length === 0 ? (
            <p className="px-3 py-4 text-center text-xs text-fg-subtle">Todos os filtros já foram adicionados.</p>
          ) : (
            <MenuLista
              titulo="Filtrar por"
              itens={disponiveis.map((definicao) => ({
                id: definicao.id,
                rotulo: definicao.label,
                icone: definicao.icone ? <definicao.icone className="h-3.5 w-3.5" aria-hidden /> : undefined,
              }))}
              onEscolher={(id, evento) => {
                // o painel de valores reaproveita a mesma âncora (o botão "Filtrar")
                setPainel({ tipo: "valores", campo: id, ancora: painel.ancora, viaCampos: true });
                evento?.stopPropagation();
              }}
            />
          )}
        </PainelFlutuante>
      )}

      {painel?.tipo === "operador" && definicaoDoPainel && filtroDoPainel && (
        <PainelFlutuante ancora={painel.ancora} onFechar={fechar} rotulo={`Operador de ${definicaoDoPainel.label}`} largura={200}>
          <MenuLista
            itens={operadoresEscolhiveis(definicaoDoPainel, filtroDoPainel).map((operador) => ({
              id: operador,
              rotulo: ROTULO_OPERADOR[operador],
              marcado: operador === filtroDoPainel.operador,
            }))}
            onEscolher={(id) => {
              onChange(aplicarFiltro(filtros, trocarOperador(filtroDoPainel, definicaoDoPainel, id as OperadorFiltro)));
              fechar();
            }}
          />
        </PainelFlutuante>
      )}

      {painel?.tipo === "valores" && definicaoDoPainel && (
        <PainelFlutuante ancora={painel.ancora} onFechar={fechar} rotulo={`Valores de ${definicaoDoPainel.label}`}>
          <div className="flex items-center gap-1.5 border-b border-line px-2 py-1.5">
            {painel.viaCampos && (
              <button
                type="button"
                aria-label="Voltar para os campos"
                onClick={() => setPainel({ tipo: "campos", ancora: painel.ancora })}
                className="rounded-md p-1 text-fg-subtle hover:bg-surface-hover hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
              </button>
            )}
            <span className="px-1 text-xs font-semibold text-fg">{definicaoDoPainel.label}</span>
          </div>
          {definicaoDoPainel.tipo === "data" ? (
            <FiltroPainelData
              definicao={definicaoDoPainel}
              filtro={filtroDoPainel}
              onAplicar={(operador, valor) => {
                const dePreset = definicaoDoPainel.presets?.some((preset) => preset.value === valor) ?? false;
                aplicarData(definicaoDoPainel, operador, valor, dePreset || operador === filtroDoPainel?.operador);
              }}
            />
          ) : (
            <FiltroPainelOpcoes
              definicao={definicaoDoPainel}
              selecionados={filtroDoPainel?.valores ?? []}
              onAlternar={(opcao) => alternar(definicaoDoPainel, opcao)}
            />
          )}
        </PainelFlutuante>
      )}
    </div>
  );
}

type ItemMenu = { id: string; rotulo: string; icone?: ReactNode; marcado?: boolean };

/** Lista de ações com foco rotativo: setas, Home/End e Enter; o primeiro item recebe o foco ao abrir. */
function MenuLista({
  itens,
  onEscolher,
  titulo,
}: {
  itens: ItemMenu[];
  onEscolher: (id: string, evento?: { stopPropagation: () => void }) => void;
  titulo?: string;
}) {
  const listaRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    listaRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }, []);

  function aoTeclar(evento: KeyboardEvent<HTMLUListElement>) {
    const botoes = Array.from(listaRef.current?.querySelectorAll<HTMLButtonElement>("button") ?? []);
    const atual = botoes.indexOf(document.activeElement as HTMLButtonElement);
    let proximo = -1;
    if (evento.key === "ArrowDown") proximo = (atual + 1) % botoes.length;
    else if (evento.key === "ArrowUp") proximo = (atual - 1 + botoes.length) % botoes.length;
    else if (evento.key === "Home") proximo = 0;
    else if (evento.key === "End") proximo = botoes.length - 1;
    if (proximo >= 0) {
      evento.preventDefault();
      botoes[proximo]?.focus();
    }
  }

  return (
    <div>
      {titulo && <p className="border-b border-line px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{titulo}</p>}
      <ul ref={listaRef} role="menu" onKeyDown={aoTeclar} className="max-h-72 overflow-y-auto p-1">
        {itens.map((item) => (
          <li key={item.id} role="none">
            <button
              type="button"
              role={item.marcado === undefined ? "menuitem" : "menuitemradio"}
              aria-checked={item.marcado}
              onClick={(evento) => onEscolher(item.id, evento)}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs text-fg-muted hover:bg-surface-hover hover:text-fg focus:bg-surface-hover focus:text-fg focus:outline-none"
            >
              {item.icone}
              <span className="min-w-0 flex-1 truncate">{item.rotulo}</span>
              {item.marcado && <Check className="h-3.5 w-3.5 shrink-0" aria-hidden />}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
