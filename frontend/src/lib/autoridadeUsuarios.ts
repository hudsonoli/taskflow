// Autoridade tenant sobre Usuários, do ponto de vista da UI (Fase 1A). ESPELHA o backend
// (backend/app/core/autoridade_usuarios.py) — só decide o que MOSTRAR; a barreira real é a API, que recusa
// com 403 de qualquer forma. Funções puras, testáveis com `node --test` (`npm run test:perfil`).
//
// Modelo: o Gestor administra SOMENTE Usuário (perfil técnico `operador`). O admin LEGADO administra Gestor e
// Usuário, nunca atribui `admin`. Quem não é nenhum dos dois (um Usuário com permissão concedida) age como o
// Gestor. Ninguém suspende/exclui a si mesmo. A decisão usa perfil e permissões da SESSÃO — nunca e-mail.
import { PERFIL_PARA_PERFIL_BASE, perfilUsuarioLabels } from "../types/usuario.ts";
import type { PerfilUsuario, UsuarioPerfilBaseApi } from "../types/usuario.ts";

type Ator = { id: string; perfil: PerfilUsuario; permissoes?: string[] };
type Alvo = { id: string; perfil: PerfilUsuario };

/** Perfil técnico (o que a API grava) de um perfil da UI. */
export function perfilTecnico(perfil: PerfilUsuario): UsuarioPerfilBaseApi {
  return PERFIL_PARA_PERFIL_BASE[perfil];
}

/** Perfis que o ator pode ATRIBUIR ao criar/editar alguém. Nunca `admin`. */
export function perfisAtribuiveis(ator: Pick<Ator, "perfil">): UsuarioPerfilBaseApi[] {
  return perfilTecnico(ator.perfil) === "admin" ? ["gestor", "operador"] : ["operador"];
}

/** Opções do seletor de perfil do formulário (valor = perfil da UI que o mapeamento leva ao técnico certo). */
export function opcoesDePerfil(ator: Pick<Ator, "perfil">): { value: PerfilUsuario; label: string }[] {
  return perfisAtribuiveis(ator).map((tecnico) => ({ value: tecnico, label: perfilUsuarioLabels[tecnico] }));
}

/** O ator pode operar sobre alguém com este perfil? Admin legado: todos; os demais: só Usuário. */
export function podeAdministrarAlvo(ator: Pick<Ator, "perfil">, alvo: Pick<Alvo, "perfil">): boolean {
  if (perfilTecnico(ator.perfil) === "admin") return true;
  return perfilTecnico(alvo.perfil) === "operador";
}

function temPermissao(ator: Pick<Ator, "permissoes">, chave: string): boolean {
  return ator.permissoes?.includes(chave) ?? false;
}

/** Botão "Nova pessoa": exige `usuarios.criar` (fail-closed enquanto a sessão não trouxe as permissões). */
export function podeCriarUsuario(ator: Pick<Ator, "permissoes">): boolean {
  return temPermissao(ator, "usuarios.criar");
}

export function podeEditarUsuario(ator: Ator, alvo: Alvo): boolean {
  return temPermissao(ator, "usuarios.editar") && podeAdministrarAlvo(ator, alvo);
}

/** Excluir/inativar/bloquear: além da hierarquia, ninguém age sobre si mesmo. */
export function podeSuspenderUsuario(ator: Ator, alvo: Alvo): boolean {
  return temPermissao(ator, "usuarios.suspender") && podeAdministrarAlvo(ator, alvo) && ator.id !== alvo.id;
}

/** Overrides individuais: `permissoes.gerenciar` + hierarquia + nunca em si mesmo (alterar). */
export function podeGerenciarPermissoesDe(ator: Ator, alvo: Alvo): boolean {
  return temPermissao(ator, "permissoes.gerenciar") && podeAdministrarAlvo(ator, alvo) && ator.id !== alvo.id;
}

/** O ator pode alterar o perfil/situação "ativo" do alvo no formulário (editar o alvo e o alvo não ser ele mesmo). */
export function podeAlterarPerfilDe(ator: Ator, alvo: Alvo): boolean {
  return podeEditarUsuario(ator, alvo) && ator.id !== alvo.id && perfisAtribuiveis(ator).length > 0;
}
