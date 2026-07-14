"use client";

import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  type ReactNode,
} from "react";

export type EntityDrawerMode = "peek" | "edit";

/**
 * Único preset oficial hoje (entity-component-api.md, seção 2). Novos presets
 * (ex. "workspace", cogitado para Projetos/Demandas na Fase 6 de
 * entity-architecture-plan.md) são extensões aditivas desta união — nunca uma
 * largura arbitrária vinda da View. A prop é mantida mesmo com um único valor
 * possível porque já é parte do contrato aprovado; a resolução interna de
 * largura, abaixo, ainda não precisa ser preset-aware enquanto só existir
 * "standard".
 */
export type EntityDrawerPreset = "standard";

export type EntityDrawerProps = {
  open: boolean;
  mode: EntityDrawerMode;
  preset?: EntityDrawerPreset;
  isDirty?: boolean;
  loading?: boolean;
  canGoBack?: boolean;
  onClose: () => void;
  onRequestClose?: () => void;
  onBack?: () => void;
  header: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
};

// isSaving e onRequestModeChange foram removidos desta prop list: nada em
// EntityDrawer os lê (EntityActions é construído pela página, que já wireia
// primaryAction.onClick/loading diretamente — EntityDrawer não tem como
// injetar nada em header/children/footer, que são ReactNode opaco). Manter
// como prop aceita-mas-ignorada seria exatamente o tipo de callback prematuro
// que esta fase de simplificação elimina. Se um caso de uso real precisar que
// o EntityDrawer participe desse fluxo, isso volta como adição futura.
//
// Só os campos com leitor real hoje (EntityHeader) entram no Context.
type EntityDrawerContextValue = {
  canGoBack: boolean;
  back: () => void;
  titleId: string;
  descriptionId: string;
};

// Contexto estritamente interno ao pacote entity/: nunca reexportado por
// index.ts nem consumido por Views de domínio (entity-component-api.md, seção 2).
const EntityDrawerContext = createContext<EntityDrawerContextValue | null>(null);

export function useEntityDrawerContext() {
  return useContext(EntityDrawerContext);
}

// Peek: ancorado à borda direita, largura fixa e compacta (não cresce com o
// viewport além de sm). Largura reduzida em ~15% sobre a anterior
// (300px/320px → 255px/272px, largura fixa com max-width, sem porcentagem)
// para diminuir ainda mais a área ocupada pelo modo somente-leitura.
//
// Edit: painel flutuante, centralizado horizontalmente no desktop
// (top-4/bottom-4 + inset-x-0 + margin-inline:auto — nunca combinado com
// right-4). Largura inalterada (720px/800px/840px). Centralização via
// inset-x-0+mx-auto em vez de left-1/2+-translate-x-1/2: mesmo resultado
// matemático (margens automáticas absorvem o espaço excedente de forma
// simétrica em torno da largura fixa), mas sem depender de transform —
// mais robusto a qualquer composição futura de transição/animação.
// Continua centralizado relativo à janela do navegador inteira (o backdrop
// já cobre a tela toda, inclusive a Sidebar) — não conhece a largura da
// Sidebar, propositalmente (entity/ nunca importa de layout/Shell).
const drawerShellClassNamesByMode: Record<EntityDrawerMode, string> = {
  peek: "inset-y-0 right-0 h-dvh w-full sm:w-[255px] sm:max-w-[272px] border-l border-zinc-200 shadow-xl sm:rounded-l-3xl",
  edit: "inset-0 sm:inset-x-0 sm:top-4 sm:bottom-4 sm:mx-auto w-full sm:w-[720px] lg:w-[800px] sm:max-w-[840px] border border-zinc-200 shadow-2xl rounded-none sm:rounded-3xl",
};

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Casca única de overlay de detalhe/edição de entidade — substitui, para o
 * novo padrão, o par EntitySidePanel+Modal usado hoje (ver entity-ux-pattern.md
 * e entity-architecture-plan.md). Nunca conhece a entidade, nunca busca dados,
 * nunca decide o que salvar/persistir — apenas monta/anima/gerencia foco do
 * card e delega todo o conteúdo aos slots header/children/footer.
 */
export function EntityDrawer({
  open,
  mode,
  isDirty = false,
  loading = false,
  canGoBack = false,
  onClose,
  onRequestClose,
  onBack,
  header,
  children,
  footer,
}: EntityDrawerProps) {
  const titleId = useId();
  const descriptionId = useId();
  const drawerRef = useRef<HTMLElement>(null);

  function requestClose() {
    if (isDirty && onRequestClose) {
      onRequestClose();
      return;
    }
    onClose();
  }

  // --- Comportamento genérico de overlay (foco inicial, focus trap,
  // bloqueio de scroll, restauração de foco) --------------------------------
  // Nada aqui é específico de "entidade": é candidato a extração futura para
  // um hook useOverlayBehavior compartilhável com ConfirmDialog e afins.
  // Mantido inline por ora, por decisão explícita de não criar hooks novos
  // nesta fase.
  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    const previouslyFocusedElement = document.activeElement as HTMLElement | null;
    const focusFrame = window.requestAnimationFrame(() => {
      const focusable = drawerRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      focusable?.focus();
    });

    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        requestClose();
        return;
      }

      if (event.key !== "Tab") return;

      const container = drawerRef.current;
      if (!container) return;

      const focusable = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocusedElement?.focus();
    };
    // requestClose depende só de isDirty/onRequestClose/onClose, já listados abaixo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, isDirty, onRequestClose, onClose]);
  // --- fim do bloco candidato a useOverlayBehavior --------------------------

  if (!open) return null;

  const contextValue: EntityDrawerContextValue = {
    canGoBack,
    back: () => onBack?.(),
    titleId,
    descriptionId,
  };

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/25 backdrop-blur-[2px]"
        onClick={requestClose}
        aria-hidden="true"
      />

      <EntityDrawerContext.Provider value={contextValue}>
        <section
          ref={drawerRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          aria-busy={loading || undefined}
          className={`fixed z-50 flex flex-col bg-white transition-all duration-200 ease-out ${drawerShellClassNamesByMode[mode]}`}
        >
          {header}

          <div className="flex min-h-0 flex-1 flex-col md:flex-row">{children}</div>

          {footer}
        </section>
      </EntityDrawerContext.Provider>
    </div>
  );
}
