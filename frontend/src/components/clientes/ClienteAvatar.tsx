// Paleta fixa de 8 cores — a mesma escolhida sempre para o mesmo clienteId
// (hash estável, não randômico). Tons 600 do Tailwind para manter contraste
// suficiente com o texto branco em todos os casos.
const AVATAR_COLORS = [
  "bg-orange-600",
  "bg-blue-600",
  "bg-emerald-600",
  "bg-violet-600",
  "bg-rose-600",
  "bg-cyan-600",
  "bg-amber-600",
  "bg-indigo-600",
];

function resolveAvatarColor(clienteId: string): string {
  let hash = 0;

  for (let index = 0; index < clienteId.length; index += 1) {
    hash = (hash * 31 + clienteId.charCodeAt(index)) | 0;
  }

  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

type ClienteAvatarProps = {
  clienteId: string;
  sigla: string;
  logoUrl?: string;
};

// logoUrl é apenas preparação para upload futuro (ainda não implementado):
// quando existir, a imagem substitui o avatar colorido abaixo.
export function ClienteAvatar({ clienteId, sigla, logoUrl }: ClienteAvatarProps) {
  if (logoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logoUrl}
        alt=""
        className="h-7 w-7 shrink-0 rounded-full object-cover"
      />
    );
  }

  return (
    <span
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold text-white ${resolveAvatarColor(clienteId)}`}
      aria-hidden="true"
    >
      {sigla}
    </span>
  );
}
