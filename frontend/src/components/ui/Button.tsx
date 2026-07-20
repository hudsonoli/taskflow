import { Loader2 } from "lucide-react";

type ButtonColorScheme = "neutral" | "brand";

// ─────────────────────────────────────────────────────────────────────
// Regra arquitetural (decisão (C), Fase 4B.1 — docs/design-system/
// 14-component-hierarchy.md, seção 1): colorScheme é um eixo que só
// existe para variant="primary". Nenhuma outra variante consulta
// colorScheme — cada uma tem exatamente uma aparência fixa. Essa
// separação é estrutural, não só documental: ver
// primaryClassNamesByColorScheme (única tabela indexada por
// colorScheme) vs. secondaryClassName/fixedVariantClassNames (valores
// fixos) e resolveVariantClassName abaixo, que só lê colorScheme no
// ramo de variant === "primary".
// ─────────────────────────────────────────────────────────────────────
type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger" | "success";

// xs formaliza o tamanho hoje reimplementado via className solto em
// DemandasTable.tsx/ProjetosTable.tsx (px-3 py-1.5 text-xs) — mesmos
// valores exatos, para que uma futura migração produza o mesmo resultado
// visual (Fase 4B.1, levantamento de consumidores).
type ButtonSize = "xs" | "sm" | "md";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  // Efeito apenas em variant="primary" — ver regra arquitetural acima.
  // Nas demais variantes a prop continua aceita (compatibilidade), mas
  // não altera a aparência.
  colorScheme?: ButtonColorScheme;
  // Quando true: desabilita o botão automaticamente, preserva a largura
  // (o rótulo continua ocupando espaço, só fica invisível) e substitui o
  // conteúdo por um spinner centralizado — nunca soma largura nova ao
  // botão. Ver Button() abaixo.
  loading?: boolean;
  // Ícones decorativos ao lado do rótulo — Button cuida do
  // posicionamento/espaçamento/aria-hidden; o consumidor só passa o
  // ícone já dimensionado (ex.: <Plus className="h-4 w-4" />), como já
  // faz hoje manualmente. Substitui o padrão hoje repetido em ~8 lugares
  // (<span className="inline-flex items-center gap-2">…</span> em volta
  // dos children).
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
};

const sizeClassNames: Record<ButtonSize, string> = {
  xs: "px-3 py-1.5 text-xs",
  sm: "px-3.5 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
};

// Tamanho do spinner de loading, alinhado à escala de ícone já oficial
// (docs/design-system/14-component-hierarchy.md, seção 6: compacto
// h-3.5/padrão h-4) — nenhum tamanho novo inventado para o spinner.
const spinnerSizeClassNames: Record<ButtonSize, string> = {
  xs: "h-3.5 w-3.5",
  sm: "h-3.5 w-3.5",
  md: "h-4 w-4",
};

// Primary e Secondary — inalterados em relação à API anterior. neutral
// continua sendo o default de Primary (preto/branco); brand (laranja,
// identidade BOX) é usado explicitamente pelos consumidores que já
// adotaram a ação principal em laranja (ex.: Clientes, Usuários, via
// EntityActions). Nenhum dos 62 consumidores atuais de Button muda de
// aparência com esta revisão.
const primaryClassNamesByColorScheme: Record<ButtonColorScheme, string> = {
  neutral: "bg-zinc-900 text-white hover:opacity-90",
  brand: "bg-primary text-white hover:bg-primary-hover",
};

// secondaryClassName não é indexado por colorScheme — é o primeiro caso
// da separação arquitetural acima: Secondary sempre teve exatamente uma
// aparência, independente de colorScheme (nenhum consumidor real usa
// colorScheme="brand" com variant="secondary" hoje).
const secondaryClassName = "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50";

// Outline/Ghost/Danger/Success — variantes novas desta fase (Fase 4B.1),
// sem consumidor real ainda. Mesma regra da linha acima: aparência fixa,
// nenhuma delas lê colorScheme. Já nascem com foco/active padronizados
// conforme 14-component-hierarchy.md, seção 1.3 (anel de foco sempre
// neutro, nunca laranja; active:scale-[0.98] universal) — tratamento
// ainda não estendido a Primary/Secondary nesta etapa, para não alterar
// a aparência dos consumidores existentes.
// `outline` reaproveita exatamente a combinação visual que antes só
// existia como colorScheme="brand" + variant="secondary" (sem consumidor
// real), agora promovida a variante própria e fixa.
// `danger` usa a intensidade "bordada" (não preenchida) porque é a única
// já validada em produção hoje, como override de className em
// entity/EntityActions.tsx — a intensidade preenchida (para um Danger
// que seja a própria ação principal de um bloco, ex. futuro
// ConfirmDialog) fica para quando esse consumidor existir.
// `success` usa emerald-600/emerald-700 — não é uma cor solta escolhida
// aqui: é o mesmo par "verde = sucesso" já registrado como vocabulário
// semântico em docs/design-system/13-tokens-visuais.md, seção "Vocabulário
// semântico de ação (Button)", na mesma família de cor usada pelo tom
// green de StatusPill (emerald), só que na intensidade de botão
// preenchido em vez de badge de fundo claro.
const fixedVariantClassNames: Record<"outline" | "ghost" | "danger" | "success", string> = {
  outline:
    "border border-zinc-200 bg-white text-zinc-900 hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 active:scale-[0.98]",
  ghost:
    "bg-transparent text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 active:scale-[0.98]",
  danger:
    "border border-red-200 bg-white text-red-600 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 active:scale-[0.98]",
  success:
    "bg-emerald-600 text-white hover:bg-emerald-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 active:scale-[0.98]",
};

// Único ponto do componente que decide se colorScheme importa: só o ramo
// de variant === "primary" o consulta. Os demais ramos (secondary e as 4
// variantes fixas) ignoram o parâmetro por construção, não por convenção.
function resolveVariantClassName(variant: ButtonVariant, colorScheme: ButtonColorScheme): string {
  if (variant === "primary") return primaryClassNamesByColorScheme[colorScheme];
  if (variant === "secondary") return secondaryClassName;
  return fixedVariantClassNames[variant];
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  colorScheme = "neutral",
  loading = false,
  leftIcon,
  rightIcon,
  className,
  disabled,
  ...rest
}: ButtonProps) {
  const variantClassName = resolveVariantClassName(variant, colorScheme);
  // loading implica disabled — não é possível clicar duas vezes numa
  // ação em andamento (docs/design-system/14-component-hierarchy.md,
  // seção 1.5). disabled explícito do consumidor continua funcionando
  // independentemente de loading.
  const isDisabled = disabled || loading;

  return (
    <button
      {...rest}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={`relative rounded-2xl ${sizeClassNames[size]} font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${variantClassName} ${className ?? ""}`}
    >
      {/*
        O rótulo/ícones sempre ocupam espaço (mesmo durante loading, só
        ficam "invisible") — é assim que a largura do botão nunca muda ao
        alternar loading, sem precisar calcular/reservar min-width.
      */}
      <span
        className={`inline-flex items-center justify-center gap-2 ${loading ? "invisible" : ""}`}
      >
        {leftIcon ? (
          <span aria-hidden="true" className="inline-flex shrink-0">
            {leftIcon}
          </span>
        ) : null}
        {children}
        {rightIcon ? (
          <span aria-hidden="true" className="inline-flex shrink-0">
            {rightIcon}
          </span>
        ) : null}
      </span>

      {loading ? (
        <span className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <Loader2 className={`animate-spin ${spinnerSizeClassNames[size]}`} />
        </span>
      ) : null}
    </button>
  );
}
