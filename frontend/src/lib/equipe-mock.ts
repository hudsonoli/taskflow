import { departamentos } from "@/lib/usuario-mock";
import type { EquipeAcesso } from "@/types/equipe";

export { departamentos };

export const EMPRESA_PADRAO_ID = "empresa-principal";

export const responsaveisDisponiveis = [
  { id: "user-1", nome: "Hudson Cunha" },
  { id: "user-2", nome: "Ana Costa" },
  { id: "user-3", nome: "Carlos Lima" },
  { id: "user-4", nome: "João Silva" },
  { id: "user-5", nome: "Maria Souza" },
  { id: "user-6", nome: "Pedro Santos" },
];

export const clientesDisponiveis = [
  { id: "cliente-1", nome: "Cliente Exemplo" },
  { id: "cliente-2", nome: "Clínica Clare" },
  { id: "cliente-3", nome: "Loja Boxx" },
  { id: "cliente-4", nome: "Cliente Inativo" },
];

export function generateId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function generateCodigoInterno(): string {
  const numero = Math.floor(Math.random() * 10000);
  return `#${numero.toString().padStart(4, "0")}`;
}

export function generateSigla(nome: string): string {
  const words = nome.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) return "";
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase();

  return words
    .slice(0, 4)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export function createAcessoPadrao(): EquipeAcesso {
  return {
    visualizarTodosProjetos: false,
    aprovarSla: false,
    gerenciarMembros: false,
    visivelParaClientes: false,
  };
}
