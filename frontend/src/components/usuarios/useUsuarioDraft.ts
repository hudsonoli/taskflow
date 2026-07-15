"use client";

import { useState } from "react";
import {
  EMPRESA_PADRAO_ID,
  createPermissoesCatalogo,
  generateCodigoInterno,
  generateId,
} from "@/lib/usuario-mock";
import type { UsuarioDraft } from "@/types/usuario";

function cloneUsuario(usuario: UsuarioDraft): UsuarioDraft {
  return {
    ...usuario,
    permissoes: usuario.permissoes.map((item) => ({ ...item })),
    enderecos: usuario.enderecos.map((endereco) => ({ ...endereco })),
    informacoes: { ...usuario.informacoes },
    administrativo: {
      salario: { ...usuario.administrativo.salario },
      dadosBancarios: { ...usuario.administrativo.dadosBancarios },
    },
    historico: usuario.historico.map((evento) => ({ ...evento })),
  };
}

function createEmptyDraft(): UsuarioDraft {
  return {
    id: generateId("usuario"),
    codigoInterno: generateCodigoInterno(),
    empresaId: EMPRESA_PADRAO_ID,
    nome: "",
    email: "",
    departamentoId: "",
    squad: "",
    paginaPrincipal: "Dashboard",
    perfil: "Operador",
    acessoSistema: true,
    emAtividade: true,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      rg: "",
      cpf: "",
    },
    administrativo: {
      salario: {
        valor: null,
        moeda: "BRL",
        dataInicio: "",
        observacao: "",
      },
      dadosBancarios: {
        chavePix: "",
        banco: "",
        agencia: "",
        conta: "",
        tipoConta: "Corrente",
      },
    },
    historico: [],
  };
}

/**
 * Estado de edição/criação de um Usuário — mesma estrutura de
 * useClienteDraft.ts. Sem step de documento (Usuário não tem um
 * equivalente a CNPJ/CPF com lookup): a criação abre direto no formulário
 * completo, com o botão Salvar desabilitado até nome/e-mail/departamento
 * estarem preenchidos (canSubmit), em vez de um passo de gate separado —
 * mesmo requisito do NovoUsuarioModal.tsx anterior, sem inventar um fluxo
 * novo.
 *
 * resetToken força reinicialização completa a cada nova sessão de edição
 * (usuário diferente, nova criação, ou reabertura após cancelar) — ajuste
 * de estado durante o render (não em useEffect), mesmo padrão de
 * useClienteDraft.ts.
 */
export function useUsuarioDraft(usuario: UsuarioDraft | undefined, resetToken: number) {
  const editing = usuario !== undefined;

  const [activeSection, setActiveSection] = useState("dados");
  const [draft, setDraft] = useState<UsuarioDraft>(() =>
    usuario ? cloneUsuario(usuario) : createEmptyDraft()
  );

  const [lastResetToken, setLastResetToken] = useState(resetToken);

  if (resetToken !== lastResetToken) {
    setLastResetToken(resetToken);
    setActiveSection("dados");
    setDraft(usuario ? cloneUsuario(usuario) : createEmptyDraft());
  }

  const canSubmit =
    draft.nome.trim() !== "" &&
    draft.email.trim() !== "" &&
    draft.departamentoId !== "";

  return {
    editing,
    activeSection,
    setActiveSection,
    draft,
    setDraft,
    canSubmit,
  };
}
