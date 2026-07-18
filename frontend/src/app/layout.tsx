import type { Metadata } from "next";
import { Geist_Mono, Roboto } from "next/font/google";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { Shell } from "@/components/layout/Shell";
import "./globals.css";

// Fonte oficial do TaskFloww — substitui Arial/Helvetica (ver globals.css).
// Pesos alinhados ao uso real de texto na aplicação: 300/400 (corpo e
// campos), 500 (destaques leves) e 700 (títulos/badges com font-bold).
const roboto = Roboto({
  variable: "--font-roboto",
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TaskFloww v2",
  description: "Gestão operacional para agências",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className={`${roboto.variable} ${geistMono.variable}`}>
      <body>
        <AuthProvider>
          <Shell>{children}</Shell>
        </AuthProvider>
      </body>
    </html>
  );
}
