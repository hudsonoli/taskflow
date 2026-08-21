"use client";

import { createContext, useContext, useEffect, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { pecasMock } from "@/lib/pecas-mock";
import { configuracaoEmailMock } from "@/lib/configuracao-email-mock";
import { configuracaoNumeracaoTarefaMock } from "@/lib/configuracao-numeracao-tarefa-mock";
import { slaRegrasMock } from "@/lib/sla-mock";
import { fetchSessao, fetchUsuarioAtualCompleto, logout as logoutRequest } from "@/lib/auth";
import { listDemandasReais } from "@/lib/api-backend";
import type { Demanda } from "@/types/demanda";
import type { SlaRegra } from "@/types/sla";
import type { Peca } from "@/types/peca";
import type { PerfilUsuario, Usuario } from "@/types/usuario";
import type { ConfiguracaoEmail } from "@/types/configuracao-email";
import type { ConfiguracaoNumeracaoTarefa } from "@/types/configuracao-numeracao-tarefa";

interface AppDataContextValue {
  /**
   * Demandas REAIS, vindas da API e **já escopadas pelo servidor** (Fase 2E.1).
   *
   * Não há mais fallback para `demandasMock`, e nenhuma demanda é meio-API meio-mock: as
   * cinco coleções sem tabela (`workflowEtapas`, `checklist`, `arquivos`, `comentarios`,
   * `historico`) chegam vazias e assim ficam até 2E.2–2E.4.
   *
   * Com a base nova nascendo vazia, as telas operacionais mostram estado vazio real até que
   * demandas sejam criadas — o mesmo que aconteceu quando Projeto migrou.
   */
  demandas: Demanda[];
  /** Atualização otimista local. Quem escreve de verdade é a API — ver lib/api-backend.ts. */
  setDemandas: Dispatch<SetStateAction<Demanda[]>>;
  demandasCarregando: boolean;
  recarregarDemandas: () => Promise<void>;
  pecas: Peca[];
  setPecas: Dispatch<SetStateAction<Peca[]>>;
  slaRegras: SlaRegra[];
  setSlaRegras: Dispatch<SetStateAction<SlaRegra[]>>;
  configuracaoEmail: ConfiguracaoEmail;
  setConfiguracaoEmail: Dispatch<SetStateAction<ConfiguracaoEmail>>;
  configuracaoNumeracaoTarefa: ConfiguracaoNumeracaoTarefa;
  setConfiguracaoNumeracaoTarefa: Dispatch<SetStateAction<ConfiguracaoNumeracaoTarefa>>;
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
  const [demandas, setDemandas] = useState<Demanda[]>([]);
  const [demandasCarregando, setDemandasCarregando] = useState(true);
  const [pecas, setPecas] = useState<Peca[]>(pecasMock);
  const [slaRegras, setSlaRegras] = useState<SlaRegra[]>(slaRegrasMock);
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

  // A pausa automática por expediente saiu daqui na Fase 2E.1.
  //
  // Ela rodava num setInterval do navegador, mudava `status` para "pausada" e escrevia em
  // `historico[]`. As duas coisas deixaram de existir: `historico` não tem tabela, e o
  // expediente passou a ser validado no servidor — que recusa a ENTRADA em `em_execucao`
  // fora do horário com 409 `FORA_DE_EXPEDIENTE`.
  //
  // Pausar trabalho JÁ EM CURSO é outra coisa, e não pode viver no cliente: só rodaria com
  // alguém logado e a aba aberta. Vira job de backend — ver docs/pendencias-arquiteturais.md.

  useEffect(() => {
    // Demanda é escopada por usuário: só faz sentido carregar depois da sessão resolvida, e
    // recarregar quando ela muda. O setTimeout(0) segue o mesmo padrão do efeito de sessão
    // acima — tira o setState do corpo do efeito e evita a cascata de renders.
    const timeout = setTimeout(() => {
      if (!autenticado || mustChangePassword) {
        setDemandas([]);
        setDemandasCarregando(false);
        return;
      }
      void recarregarDemandas();
    }, 0);
    return () => clearTimeout(timeout);
  }, [autenticado, mustChangePassword]);

  async function recarregarDemandas() {
    setDemandasCarregando(true);
    try {
      setDemandas(await listDemandasReais());
    } catch {
      // Falha de rede não pode virar "não há demandas": mantém o que já estava em tela.
    } finally {
      setDemandasCarregando(false);
    }
  }

  return (
    <AppDataContext.Provider
      value={{
        demandas,
        setDemandas,
        demandasCarregando,
        recarregarDemandas,
        pecas,
        setPecas,
        slaRegras,
        setSlaRegras,
        configuracaoEmail,
        setConfiguracaoEmail,
        configuracaoNumeracaoTarefa,
        setConfiguracaoNumeracaoTarefa,
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
