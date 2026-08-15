"use client";

import type { ReactNode } from "react";
import { useAppData } from "@/lib/AppDataContext";
import { podeAcessarAreaAdministrativa } from "@/lib/escopo-operacional";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";

/**
 * Proteção de **URL direta** para as áreas administrativas (Configurações, Projetos,
 * Relatórios).
 *
 * Não é a barreira de segurança — essa é a API, que responde 403 a operador em `/projetos`,
 * `/clientes`, `/usuarios` e nos demais cadastros. Este guard existe para os casos em que a
 * navegação não teve como esconder o caminho:
 *
 * - alguém digitou ou salvou a URL;
 * - a sessão mudou de perfil com a aba aberta;
 * - link externo apontando para dentro do app.
 *
 * Fora desses casos o item nem aparece no menu (ver `TopNav`), então "Acesso negado" deixa de
 * ser navegação normal e volta a ser o que deveria: exceção.
 *
 * Enquanto a sessão carrega não decide nada — mostrar "sem acesso" para quem ainda não foi
 * identificado seria uma acusação falsa de meio segundo a cada carregamento.
 */
export function AreaAdministrativaGuard({ children }: { children: ReactNode }) {
  const { usuarioAtual, sessaoCarregando } = useAppData();

  if (sessaoCarregando || !usuarioAtual) return null;

  if (!podeAcessarAreaAdministrativa(usuarioAtual)) {
    return (
      <AcessoNegado
        titulo="Área restrita à administração"
        descricao="Cadastros, configurações e relatórios são acessíveis a administradores e gestores. Se você precisa desta área, fale com quem administra o workspace."
      />
    );
  }

  return <>{children}</>;
}
