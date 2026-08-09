"use client";

import { createContext, useContext, useEffect, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { demandasMock } from "@/lib/demandas-mock";
import { projetosLegado, type ProjetoLegado } from "@/lib/legacy-referencias-mock";
import { pecasMock } from "@/lib/pecas-mock";
import { regraExpedienteMock, isDentroExpediente } from "@/lib/regra-expediente-mock";
import { configuracaoEmailMock } from "@/lib/configuracao-email-mock";
import { configuracaoNumeracaoTarefaMock } from "@/lib/configuracao-numeracao-tarefa-mock";
import { workflowModelosMock } from "@/lib/workflow-modelos-mock";
import { slaRegrasMock } from "@/lib/sla-mock";
import { fetchSessao, fetchUsuarioAtualCompleto, logout as logoutRequest } from "@/lib/auth";
import { generateId, formatCodigoTarefa } from "@/lib/ids";
import type { Demanda } from "@/types/demanda";
import type { WorkflowModelo } from "@/types/workflow-modelo";
import type { SlaRegra } from "@/types/sla";
import type { Peca } from "@/types/peca";
import type { PerfilUsuario, Usuario } from "@/types/usuario";
import type { RegraExpediente } from "@/types/regra-expediente";
import type { ConfiguracaoEmail } from "@/types/configuracao-email";
import type { ConfiguracaoNumeracaoTarefa } from "@/types/configuracao-numeracao-tarefa";

interface AppDataContextValue {
  demandas: Demanda[];
  setDemandas: Dispatch<SetStateAction<Demanda[]>>;
  /**
   * Projeção LEGADA, não Projeto real. Projeto migrou na Fase 2D e `ProjetosView` fala
   * direto com a API. Isto existe só para Demandas, Relatórios e Meu Departamento, que
   * ainda são mock e referenciam `projeto-1/2/3` — ver lib/legacy-referencias-mock.ts.
   * Somente leitura: não há `setProjetos`.
   */
  projetos: ProjetoLegado[];
  pecas: Peca[];
  setPecas: Dispatch<SetStateAction<Peca[]>>;
  workflowModelos: WorkflowModelo[];
  setWorkflowModelos: Dispatch<SetStateAction<WorkflowModelo[]>>;
  slaRegras: SlaRegra[];
  setSlaRegras: Dispatch<SetStateAction<SlaRegra[]>>;
  regraExpediente: RegraExpediente;
  setRegraExpediente: Dispatch<SetStateAction<RegraExpediente>>;
  configuracaoEmail: ConfiguracaoEmail;
  setConfiguracaoEmail: Dispatch<SetStateAction<ConfiguracaoEmail>>;
  configuracaoNumeracaoTarefa: ConfiguracaoNumeracaoTarefa;
  setConfiguracaoNumeracaoTarefa: Dispatch<SetStateAction<ConfiguracaoNumeracaoTarefa>>;
  // Gera o próximo código de tarefa (#AA0000) e avança o contador configurado.
  gerarProximoCodigoTarefa: () => string;
  // Intenção de abrir uma tarefa específica (ex.: clique em notificação) — consumida pela tela de Tarefas.
  demandaParaAbrir: { demandaId: string; aba?: string } | null;
  setDemandaParaAbrir: Dispatch<SetStateAction<{ demandaId: string; aba?: string } | null>>;
  // Sessão real (backend) — ver lib/auth.ts. Diretório de usuários (seletores de
  // responsável/membro) agora vem de lib/diretorioUsuarios.ts (cache remoto), não deste
  // contexto — ver docs/padrao-arquivamento.md.
  sessaoCarregando: boolean;
  autenticado: boolean;
  mustChangePassword: boolean;
  usuarioAtual?: Usuario;
  perfilAtual: PerfilUsuario;
  logout: () => Promise<void>;
  recarregarSessao: () => Promise<void>;
}

const AppDataContext = createContext<AppDataContextValue | null>(null);

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [demandas, setDemandas] = useState<Demanda[]>(demandasMock);
  const projetos = projetosLegado;
  const [pecas, setPecas] = useState<Peca[]>(pecasMock);
  const [workflowModelos, setWorkflowModelos] = useState<WorkflowModelo[]>(workflowModelosMock);
  const [slaRegras, setSlaRegras] = useState<SlaRegra[]>(slaRegrasMock);
  const [regraExpediente, setRegraExpediente] = useState<RegraExpediente>(regraExpedienteMock);
  const [configuracaoEmail, setConfiguracaoEmail] = useState<ConfiguracaoEmail>(configuracaoEmailMock);
  const [configuracaoNumeracaoTarefa, setConfiguracaoNumeracaoTarefa] = useState<ConfiguracaoNumeracaoTarefa>(
    configuracaoNumeracaoTarefaMock,
  );
  const [demandaParaAbrir, setDemandaParaAbrir] = useState<{ demandaId: string; aba?: string } | null>(null);

  const [sessaoCarregando, setSessaoCarregando] = useState(true);
  const [autenticado, setAutenticado] = useState(false);
  const [mustChangePassword, setMustChangePassword] = useState(false);
  const [usuarioAtual, setUsuarioAtual] = useState<Usuario | undefined>(undefined);
  const perfilAtual: PerfilUsuario = usuarioAtual?.perfil ?? "operador";

  async function recarregarSessao() {
    const sessao = await fetchSessao();
    if (!sessao) {
      setAutenticado(false);
      setMustChangePassword(false);
      setUsuarioAtual(undefined);
      setSessaoCarregando(false);
      return;
    }

    setAutenticado(true);
    setMustChangePassword(sessao.mustChangePassword);

    if (sessao.mustChangePassword) {
      // Perfil completo só é buscado depois da troca obrigatória — /usuarios/me também
      // fica bloqueado enquanto a senha estiver pendente (ver dependency no backend).
      setUsuarioAtual(undefined);
    } else {
      const completo = await fetchUsuarioAtualCompleto();
      setUsuarioAtual(completo ?? undefined);
    }

    setSessaoCarregando(false);
  }

  async function logout() {
    await logoutRequest();
    setAutenticado(false);
    setMustChangePassword(false);
    setUsuarioAtual(undefined);
  }

  useEffect(() => {
    const timeout = setTimeout(() => {
      void recarregarSessao();
    }, 0);
    return () => clearTimeout(timeout);
  }, []);

  // Regra de expediente: fora do horário configurado, demandas "em execução" são pausadas automaticamente.
  useEffect(() => {
    function aplicarRegraExpediente() {
      const agora = new Date();
      if (isDentroExpediente(agora, regraExpediente)) return;

      setDemandas((current) => {
        let alterou = false;
        const proximo = current.map((demanda) => {
          if (demanda.status !== "em_execucao") return demanda;
          alterou = true;
          return {
            ...demanda,
            status: "pausada" as const,
            updatedAt: agora.toISOString(),
            historico: [
              {
                id: generateId("hist-demanda-auto"),
                usuarioId: "sistema",
                usuario: "Sistema",
                acao: "Pausada automaticamente — fora do horário de expediente",
                dataHora: agora.toLocaleString("pt-BR"),
                ip: "—",
                dispositivo: "Regra automática",
              },
              ...demanda.historico,
            ],
          };
        });
        return alterou ? proximo : current;
      });
    }

    aplicarRegraExpediente();
    const intervalId = setInterval(aplicarRegraExpediente, 20000);
    return () => clearInterval(intervalId);
  }, [regraExpediente]);

  function gerarProximoCodigoTarefa(): string {
    const anoAtual = new Date().getFullYear();
    // Vira o ano automaticamente reiniciando em 1, a menos que o número já esteja configurado para o ano corrente.
    const numero = configuracaoNumeracaoTarefa.ano === anoAtual ? configuracaoNumeracaoTarefa.proximoNumero : 1;

    setConfiguracaoNumeracaoTarefa((current) => ({
      ...current,
      ano: anoAtual,
      proximoNumero: numero + 1,
      updatedAt: new Date().toISOString(),
    }));

    return formatCodigoTarefa(anoAtual, numero);
  }

  return (
    <AppDataContext.Provider
      value={{
        demandas,
        setDemandas,
        projetos,
        pecas,
        setPecas,
        workflowModelos,
        setWorkflowModelos,
        slaRegras,
        setSlaRegras,
        regraExpediente,
        setRegraExpediente,
        configuracaoEmail,
        setConfiguracaoEmail,
        configuracaoNumeracaoTarefa,
        setConfiguracaoNumeracaoTarefa,
        gerarProximoCodigoTarefa,
        demandaParaAbrir,
        setDemandaParaAbrir,
        sessaoCarregando,
        autenticado,
        mustChangePassword,
        usuarioAtual,
        perfilAtual,
        logout,
        recarregarSessao,
      }}
    >
      {children}
    </AppDataContext.Provider>
  );
}

export function useAppData(): AppDataContextValue {
  const context = useContext(AppDataContext);
  if (!context) {
    throw new Error("useAppData precisa ser usado dentro de <AppDataProvider>");
  }
  return context;
}
