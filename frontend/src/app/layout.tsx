import type { Metadata } from "next";
import { cookies } from "next/headers";
import { connection } from "next/server";
import { Geist, Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/layout/AppShell";
import { AppDataProvider } from "@/lib/AppDataContext";
import { BrandingProvider } from "@/lib/BrandingContext";
import { variaveisDaMarca } from "@/lib/branding-tokens";
import { SESSION_COOKIE_NAME } from "@/lib/server/backend";
import { obterBranding } from "@/lib/server/branding";
import { COOKIE_TEMA, SCRIPT_TEMA_SISTEMA, normalizarPreferencia, resolveEffectiveTheme } from "@/lib/tema";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Taskfloww",
  description: "Gestão operacional para agências",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Tema e cores da Empresa são resolvidos NO SERVIDOR a cada request e gravados no <html>: o primeiro HTML já
  // sai com o tema certo (sem flash claro→escuro). `connection()` marca a renderização como dinâmica — o
  // branding muda em runtime, não pode ser congelado no build.
  await connection();
  const branding = await obterBranding();
  const variaveis = variaveisDaMarca(branding.corPrimaria, branding.corSecundaria);

  // Preferência PESSOAL de tema (cookie-espelho; a verdade é o banco): só vale com sessão — sem tf_session o
  // cookie é ignorado, então a tela pública/outro usuário nunca herda o tema de quem saiu. Logo e cores são
  // sempre da empresa. Para "sistema" o servidor não conhece o dispositivo: sai o tema da empresa como base e um
  // script mínimo (abaixo) ajusta o data-theme antes do primeiro paint.
  const cookieStore = await cookies();
  const autenticado = Boolean(cookieStore.get(SESSION_COOKIE_NAME)?.value);
  const preferencia = autenticado ? normalizarPreferencia(cookieStore.get(COOKIE_TEMA)?.value) : null;
  const temaInicial = resolveEffectiveTheme({ temaEmpresa: branding.tema, preferencia, sistemaEscuro: false, autenticado });

  return (
    <html
      lang="pt-BR"
      data-theme={temaInicial}
      suppressHydrationWarning
      style={variaveis}
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      {preferencia === "sistema" && (
        <head>
          <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA_SISTEMA }} />
        </head>
      )}
      <body className="min-h-full">
        <BrandingProvider inicial={branding} preferenciaInicial={preferencia} autenticadoInicial={autenticado}>
          <AppDataProvider>
            <AppShell>{children}</AppShell>
          </AppDataProvider>
        </BrandingProvider>
      </body>
    </html>
  );
}
