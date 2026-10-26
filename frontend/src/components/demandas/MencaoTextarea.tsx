"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import clsx from "clsx";
import { detectarMencaoAtiva, inserirMencao, reconciliarSelecionadas, type MencaoAtiva, type Mencionavel } from "@/lib/mencoes";
import { Avatar } from "@/components/ui/Avatar";

const ATRASO_BUSCA_MS = 160;

/**
 * Caixa de texto com @menção: ao digitar "@" abre a lista de pessoas ELEGÍVEIS (o servidor filtra empresa, status e acesso à tarefa). Escolher grava o rótulo "@Nome" no texto e guarda
 * a identidade (id) à parte — digitar "@Nome" sem escolher não é menção. Teclado: ↑ ↓ navegam, Enter/Tab escolhem, Esc fecha. O texto continua legível (é só texto).
 */
export function MencaoTextarea({
  value,
  onValueChange,
  selecionadas,
  onSelecionadasChange,
  buscar,
  placeholder,
  rows = 2,
  autoFocus,
  disabled,
  ariaLabel,
  className,
  onKeyDownExtra,
  inputClassName,
}: {
  value: string;
  onValueChange: (valor: string) => void;
  selecionadas: Mencionavel[];
  onSelecionadasChange: (pessoas: Mencionavel[]) => void;
  buscar: (consulta: string, sinal: AbortSignal) => Promise<Mencionavel[]>;
  placeholder?: string;
  rows?: number;
  autoFocus?: boolean;
  disabled?: boolean;
  ariaLabel?: string;
  className?: string;
  inputClassName?: string;
  /** Atalhos do chamador (ex.: Ctrl+Enter envia, Esc cancela a edição). Roda DEPOIS do tratamento da lista, só quando a lista não consumiu a tecla. */
  onKeyDownExtra?: (evento: KeyboardEvent<HTMLTextAreaElement>) => void;
}): ReactNode {
  const idBase = useId();
  const idLista = `${idBase}-lista`;
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const [ativa, setAtiva] = useState<MencaoAtiva | null>(null);
  const [cursor, setCursor] = useState(0);
  const [sugestoes, setSugestoes] = useState<Mencionavel[]>([]);
  const [indice, setIndice] = useState(0);
  const [fechadaPorEsc, setFechadaPorEsc] = useState<number | null>(null);

  const aberta = ativa !== null && sugestoes.length > 0 && fechadaPorEsc !== ativa.inicio;

  // Busca no servidor com debounce; cada nova consulta cancela a anterior (resposta velha nunca sobrescreve a nova).
  useEffect(() => {
    if (!ativa) return; // a lista só aparece com uma menção ativa (`aberta`); ao escolher/fechar ela já foi esvaziada no evento
    const controle = new AbortController();
    const temporizador = setTimeout(() => {
      buscar(ativa.consulta, controle.signal)
        .then((pessoas) => {
          if (controle.signal.aborted) return;
          setSugestoes(pessoas);
          setIndice(0);
        })
        .catch(() => {
          if (!controle.signal.aborted) setSugestoes([]);
        });
    }, ATRASO_BUSCA_MS);
    return () => {
      clearTimeout(temporizador);
      controle.abort();
    };
  }, [ativa, buscar]);

  function atualizarAtiva(texto: string, posicao: number) {
    const proxima = detectarMencaoAtiva(texto, posicao);
    setCursor(posicao);
    setAtiva((atual) => {
      if (proxima && atual && atual.inicio === proxima.inicio && atual.consulta === proxima.consulta) return atual;
      return proxima;
    });
    if (!proxima || (fechadaPorEsc !== null && proxima.inicio !== fechadaPorEsc)) setFechadaPorEsc(null);
  }

  function aoDigitar(texto: string, posicao: number) {
    onValueChange(texto);
    onSelecionadasChange(reconciliarSelecionadas(texto, selecionadas));
    atualizarAtiva(texto, posicao);
  }

  function escolher(pessoa: Mencionavel) {
    if (!ativa) return;
    const resultado = inserirMencao(value, ativa, cursor, pessoa);
    onValueChange(resultado.texto);
    onSelecionadasChange(reconciliarSelecionadas(resultado.texto, [...selecionadas.filter((p) => p.id !== pessoa.id), pessoa]));
    setAtiva(null);
    setSugestoes([]);
    requestAnimationFrame(() => {
      const area = areaRef.current;
      if (!area) return;
      area.focus();
      area.setSelectionRange(resultado.cursor, resultado.cursor);
    });
  }

  function aoPressionar(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (aberta) {
      if (evento.key === "ArrowDown") {
        evento.preventDefault();
        setIndice((atual) => (atual + 1) % sugestoes.length);
        return;
      }
      if (evento.key === "ArrowUp") {
        evento.preventDefault();
        setIndice((atual) => (atual - 1 + sugestoes.length) % sugestoes.length);
        return;
      }
      if ((evento.key === "Enter" && !evento.ctrlKey && !evento.metaKey && !evento.shiftKey) || evento.key === "Tab") {
        evento.preventDefault();
        escolher(sugestoes[indice] ?? sugestoes[0]);
        return;
      }
      if (evento.key === "Escape") {
        evento.preventDefault();
        evento.stopPropagation();
        setFechadaPorEsc(ativa?.inicio ?? null);
        return;
      }
    }
    onKeyDownExtra?.(evento);
  }

  return (
    <div className={clsx("relative min-w-0", className)}>
      <textarea
        ref={areaRef}
        value={value}
        autoFocus={autoFocus}
        disabled={disabled}
        rows={rows}
        placeholder={placeholder}
        aria-label={ariaLabel}
        role="combobox"
        aria-autocomplete="list"
        aria-haspopup="listbox"
        aria-expanded={aberta}
        aria-controls={aberta ? idLista : undefined}
        aria-activedescendant={aberta ? `${idBase}-opcao-${indice}` : undefined}
        onChange={(evento) => aoDigitar(evento.target.value, evento.target.selectionStart ?? evento.target.value.length)}
        onKeyDown={aoPressionar}
        onKeyUp={(evento) => {
          if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(evento.key)) atualizarAtiva(evento.currentTarget.value, evento.currentTarget.selectionStart ?? 0);
        }}
        onClick={(evento) => atualizarAtiva(evento.currentTarget.value, evento.currentTarget.selectionStart ?? 0)}
        onBlur={() => setTimeout(() => setAtiva(null), 120)} // deixa o clique/toque numa opção acontecer antes de fechar
        className={inputClassName ?? "field w-full resize-none rounded-xl px-3 py-2.5 text-sm"}
      />
      {aberta && (
        <ul
          id={idLista}
          role="listbox"
          aria-label="Pessoas que podem ser mencionadas"
          data-superficie="menu"
          className="absolute left-0 right-0 top-full z-30 mt-1 max-h-56 overflow-y-auto rounded-xl border border-zinc-200 bg-surface p-1 shadow-lg dark:border-zinc-700"
        >
          {sugestoes.map((pessoa, posicao) => (
            <li
              key={pessoa.id}
              id={`${idBase}-opcao-${posicao}`}
              role="option"
              aria-selected={posicao === indice}
              onMouseDown={(evento) => {
                evento.preventDefault(); // não tira o foco do textarea
                escolher(pessoa);
              }}
              onMouseEnter={() => setIndice(posicao)}
              className={clsx(
                "flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm",
                posicao === indice ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400" : "text-zinc-700 dark:text-zinc-200",
              )}
            >
              <Avatar nome={pessoa.nome} corIdentificacao="" className="h-6 w-6 shrink-0 text-[10px]" />
              <span className="min-w-0 flex-1 truncate">{pessoa.nome}</span>
              {pessoa.cargo && <span className="hidden shrink-0 truncate text-xs text-fg-subtle sm:inline">{pessoa.cargo}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
