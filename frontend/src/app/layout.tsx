import type { Metadata } from "next";
import { cookies, headers } from "next/headers";
import { connection } from "next/server";
import { Geist, Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/layout/AppShell";
import { AppDataProvider } from "@/lib/AppDataContext";
import { BrandingProvider } from "@/lib/BrandingContext";
import { BRANDING_PADRAO } from "@/lib/branding";
import { NotificacoesProvider } from "@/lib/NotificacoesContext";
import { variaveisDaMarca } from "@/lib/branding-tokens";
import { SESSION_COOKIE_NAME } from "@/lib/server/backend";
import { obterBrandingPublico } from "@/lib/server/branding";
import { COOKIE_TEMA, SCRIPT_TEMA_SISTEMA, normalizarPreferencia, resolveEffectiveTheme } from "@/lib/tema";
import { NOME_PRODUTO, tituloDaPagina } from "@/lib/produto";
import { CONTEXTO_APROVACAO, CONTEXTO_GESTAO, HEADER_CONTEXTO, HEADER_TENANT_SLUG, normalizarSlug, slugVisual } from "@/lib/tenant";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Título da aba (Fase 10A): no tenant, `<Empresa> | TaskFlow` (nome vindo do servidor pelo slug da rota, nunca fixo); na Gestão e nas telas neutras, só o
// produto. Páginas que definem o próprio título ("Gestão", "Aprovação") recebem o sufixo ` | TaskFlow` pelo template.
export async function generateMetadata(): Promise<Metadata> {
  const cabecalhos = await headers();
  const contexto = cabecalhos.get(HEADER_CONTEXTO);
  const slug = contexto === CONTEXTO_APROVACAO || contexto === CONTEXTO_GESTAO ? null : normalizarSlug(cabecalhos.get(HEADER_TENANT_SLUG));
  const publico = slug ? await obterBrandingPublico({ tipo: "slug", slug }) : null;
  return {
    title: { default: tituloDaPagina(publico?.disponivel ? publico.nome : null), template: `%s | ${NOME_PRODUTO}` },
    description: "Gestão operacional para agências",
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Tema e cores da Empresa são resolvidos NO SERVIDOR a cada request e gravados no <html>: o primeiro HTML já
  // sai com o tema certo (sem flash claro→escuro). `connection()` marca a renderização como dinâmica — o
  // branding muda em runtime, não pode ser congelado no build.
  await connection();

  // Contexto de EMPRESA da página (só visual): o slug da rota `/e/<slug>/...` (definido pelo proxy.ts). Fase 9D: sem fallback — nem cookie, nem sessão,
  // nem empresa padrão (EMPRESA_CODIGO); fora de `/e/<slug>` a identidade é a neutra do TaskFlow. Nunca decide autorização: a empresa dos dados
  // vem sempre do token no backend.
  const cabecalhos = await headers();
  const cookieStore = await cookies();
  // Portal Externo de Aprovação (Fase 9B): a página ignora qualquer sessão/cookie do tenant. O HTML inicial sai com a marca NEUTRA e sem
  // contexto de empresa — a marca real chega depois da consulta do token (a empresa vem do link, nunca do navegador).
  const contextoAprovacao = cabecalhos.get(HEADER_CONTEXTO) === CONTEXTO_APROVACAO;
  const autenticado = !contextoAprovacao && Boolean(cookieStore.get(SESSION_COOKIE_NAME)?.value);
  const slugRota = normalizarSlug(cabecalhos.get(HEADER_TENANT_SLUG));
  const slug = contextoAprovacao ? null : slugVisual({ slugDaRota: slugRota });

  // A Gestão (`/gestao`) mantém a identidade do PRODUTO (TaskFlow): escolher uma empresa em foco não muda a marca nem vira sessão tenant.
  const contextoPlataforma = cabecalhos.get(HEADER_CONTEXTO) === CONTEXTO_GESTAO;
  const publico = contextoPlataforma
    ? { branding: BRANDING_PADRAO, disponivel: true, nome: null }
    : contextoAprovacao
      ? { branding: BRANDING_PADRAO, disponivel: true, nome: null }
      : slug
        ? await obterBrandingPublico({ tipo: "slug", slug })
        : { branding: BRANDING_PADRAO, disponivel: false, nome: null };
  // O NOME da empresa (público) viaja junto da marca: é a identidade principal do ambiente tenant (cabeçalho sem logo, login).
  const branding = slug && publico.disponivel ? { ...publico.branding, nome: publico.nome } : publico.branding;
  const variaveis = variaveisDaMarca(branding.corPrimaria, branding.corSecundaria);

  // Preferência PESSOAL de tema (cookie-espelho; a verdade é o banco): só vale com sessão — sem tf_session o
  // cookie é ignorado, então a tela pública/outro usuário nunca herda o tema de quem saiu. Logo e cores são
  // sempre da empresa. Para "sistema" o servidor não conhece o dispositivo: sai o tema da empresa como base e um
  // script mínimo (abaixo) ajusta o data-theme antes do primeiro paint.
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
        <BrandingProvider
          inicial={branding}
          preferenciaInicial={preferencia}
          autenticadoInicial={autenticado}
          tenantSlugInicial={contextoAprovacao ? null : slugRota}
        >
          <AppDataProvider>
            <NotificacoesProvider>
              <AppShell>{children}</AppShell>
            </NotificacoesProvider>
          </AppDataProvider>
        </BrandingProvider>
      </body>
    </html>
  );
}
