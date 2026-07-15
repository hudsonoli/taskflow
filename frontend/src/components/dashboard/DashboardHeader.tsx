type DashboardHeaderProps = {
  nome: string;
};

function getGreeting(hour = new Date().getHours()) {
  if (hour < 12) return "Bom dia";
  if (hour < 18) return "Boa tarde";
  return "Boa noite";
}

// O título "Dashboard" já vem do chrome global (Header.tsx) — aqui só a
// saudação, sem repetir o título nem qualquer elemento decorativo.
export function DashboardHeader({ nome }: DashboardHeaderProps) {
  const primeiroNome = nome.trim().split(/\s+/)[0] ?? nome;

  return (
    <p className="text-sm leading-6 text-zinc-500">
      {getGreeting()}, {primeiroNome}. Aqui está o que precisa da sua atenção hoje.
    </p>
  );
}
