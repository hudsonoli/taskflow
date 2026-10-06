import type { Metadata } from "next";
import { connection } from "next/server";
import { Geist, Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/layout/AppShell";
import { AppDataProvider } from "@/lib/AppDataContext";
import { BrandingProvider } from "@/lib/BrandingContext";
import { variaveisDaMarca } from "@/lib/branding-tokens";
import { obterBranding } from "@/lib/server/branding";
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
  return (
    <html
      lang="pt-BR"
      data-theme={branding.tema}
      style={variaveis}
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <BrandingProvider inicial={branding}>
          <AppDataProvider>
            <AppShell>{children}</AppShell>
          </AppDataProvider>
        </BrandingProvider>
      </body>
    </html>
  );
}
