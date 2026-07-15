import { EntityFormNav, EntityHistory, EntitySection } from "@/components/entity";
import { hasAdministrativeAccess } from "@/lib/access-control";
import { currentUser } from "@/lib/conta-mock";
import type { UsuarioDraft } from "@/types/usuario";
import {
  AdministrativoSection,
  DadosSection,
  EnderecosSection,
  InformacoesSection,
  PermissoesSection,
} from "./UsuarioFormSections";

const allSections = [
  { id: "dados", label: "Dados" },
  { id: "permissoes", label: "Permissões" },
  { id: "endereco", label: "Endereço" },
  { id: "informacoes", label: "Informações" },
  { id: "administrativo", label: "Administrativa" },
  { id: "historico", label: "Histórico" },
];

type UsuarioEditFormBodyProps = {
  draft: UsuarioDraft;
  onDraftChange: (updater: (current: UsuarioDraft) => UsuarioDraft) => void;
  activeSection: string;
  onActiveSectionChange: (id: string) => void;
};

/**
 * Corpo do EntityDrawer em mode="edit" para Usuários — mesma composição de
 * ClienteEditFormBody.tsx: primitivos entity/ (EntityFormNav, EntitySection,
 * EntityHistory) + seções de domínio (UsuarioFormSections.tsx). Sem step de
 * documento (ver useUsuarioDraft.ts) — abre direto na navegação de seções.
 *
 * Guia Administrativa: visível somente para currentUser.perfil autorizado
 * (hasAdministrativeAccess, lib/access-control.ts) — mesmo mecanismo de
 * Clientes, checado duas vezes (lista de abas + conteúdo) para que
 * setActiveSection("administrativo") não contorne a restrição. Não depende
 * de draft.perfil (esse é o cargo do usuário sendo editado, não de quem
 * está vendo a tela agora — os dois conceitos não se misturam).
 */
export function UsuarioEditFormBody({
  draft,
  onDraftChange,
  activeSection,
  onActiveSectionChange,
}: UsuarioEditFormBodyProps) {
  const canAccessAdministrativo = hasAdministrativeAccess(currentUser.perfil);
  const sections = allSections.filter(
    (section) => section.id !== "administrativo" || canAccessAdministrativo
  );

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col">
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <EntityFormNav
          sections={sections}
          activeSection={activeSection}
          onSectionChange={onActiveSectionChange}
        />

        <EntitySection id={activeSection}>
          {activeSection === "dados" && (
            <DadosSection draft={draft} onChange={onDraftChange} />
          )}

          {activeSection === "permissoes" && (
            <PermissoesSection draft={draft} onChange={onDraftChange} />
          )}

          {activeSection === "endereco" && (
            <EnderecosSection draft={draft} onChange={onDraftChange} />
          )}

          {activeSection === "informacoes" && (
            <InformacoesSection draft={draft} onChange={onDraftChange} />
          )}

          {activeSection === "administrativo" && canAccessAdministrativo && (
            <AdministrativoSection draft={draft} onChange={onDraftChange} />
          )}

          {activeSection === "historico" && (
            <div className="space-y-3">
              <p className="text-[10px] font-normal leading-snug text-zinc-400">
                Dados de demonstração — a captura real de IP, dispositivo e
                origem dependerá de integração futura com o backend (ver
                PROJECT_STATUS.md). Não há auditoria real nesta fase.
              </p>

              <EntityHistory
                variant="full"
                events={[...draft.historico].reverse().map((evento) => ({
                  id: evento.id,
                  usuario: evento.usuario,
                  dataHora: evento.dataHora,
                  acao: evento.acao,
                  ipOrigem: evento.ipOrigem,
                  dispositivo: evento.dispositivo,
                  origem: evento.origem,
                }))}
              />
            </div>
          )}
        </EntitySection>
      </div>
    </div>
  );
}
