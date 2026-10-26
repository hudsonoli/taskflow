"use client";

import type { ReactNode } from "react";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { podeAcessarProjetos } from "@/lib/escopo-operacional";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";

/**
 * Proteção de **URL direta** de Projetos: administração (admin/gestor) e Atendimento — quem demanda as tarefas dos clientes e as organiza em projetos. Os demais recebem o aviso.
 *
 * Não é a barreira de segurança (a API é: `GET/POST /projetos` respondem 403 a quem não é admin/gestor/Atendimento, e o Atendimento só alcança a própria carteira). Enquanto a sessão ou
 * o diretório de departamentos carregam — o Atendimento é reconhecido pelo departamento — não decide nada: negar antes da hora seria acusar quem tem acesso.
 */
export function ProjetosAcessoGuard({ children }: { children: ReactNode }) {
  const { usuarioAtual, sessaoCarregando } = useAppData();
  const { departamentos, carregando } = useDiretorioDepartamentos();

  if (sessaoCarregando || !usuarioAtual) return null;
  if (carregando && !podeAcessarProjetos(usuarioAtual, departamentos)) return null;

  if (!podeAcessarProjetos(usuarioAtual, departamentos)) {
    return (
      <AcessoNegado
        titulo="Área restrita"
        descricao="Projetos são acessíveis à administração e ao Atendimento. Se você precisa desta área, fale com quem administra o workspace."
      />
    );
  }

  return <>{children}</>;
}
