import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { EntityFormNav, EntityHistory, EntitySection } from "@/components/entity";
import { hasAdministrativeAccess } from "@/lib/access-control";
import { currentUser } from "@/lib/conta-mock";
import type { ClienteDraft, DocumentoTipo } from "@/types/cliente";
import {
  AdministrativoSection,
  ContatosSection,
  DadosSection,
  EnderecoSection,
  EquipeSection,
} from "./ClienteFormSections";
import type { ClienteDraftStep } from "./useClienteDraft";

const allSections = [
  { id: "dados", label: "Dados" },
  { id: "endereco", label: "Endereço" },
  { id: "contatos", label: "Contatos" },
  { id: "equipe", label: "Equipe" },
  { id: "administrativo", label: "Administrativa" },
  { id: "historico", label: "Histórico" },
];

type ClienteEditFormBodyProps = {
  step: ClienteDraftStep;
  documentoInput: string;
  onDocumentoInputChange: (value: string) => void;
  documentType: DocumentoTipo | null;
  draft: ClienteDraft;
  onDraftChange: (updater: (current: ClienteDraft) => ClienteDraft) => void;
  onNomeFantasiaChange: (value: string) => void;
  onSiglaChange: (value: string) => void;
  activeSection: string;
  onActiveSectionChange: (id: string) => void;
};

/**
 * Corpo do EntityDrawer em mode="edit" para Clientes. Não é um componente
 * genérico de entity/ — é conteúdo específico do domínio Cliente, composto
 * a partir dos primitivos entity/ (EntityFormNav, EntitySection,
 * EntityHistory) e das seções de formulário já existentes
 * (ClienteFormSections.tsx).
 *
 * Nota: DadosSection/EnderecoSection/EquipeSection já trazem sua própria
 * grade interna (md:grid-cols-2) — não são envolvidas por EntityForm aqui,
 * pois isso duplicaria a grade. A conversão dessas seções para o grid de 12
 * colunas fica para uma fase futura, fora do escopo desta migração.
 * AdministrativoSection, por ser seção nova sem grade legada, já usa
 * EntityForm.
 *
 * Guia Administrativa: visível somente para currentUser.perfil autorizado
 * (hasAdministrativeAccess, lib/access-control.ts). A checagem é aplicada
 * duas vezes — ao montar a lista de abas (nav) e de novo ao renderizar o
 * conteúdo — para que setActiveSection("administrativo") não consiga expor
 * o conteúdo caso alguém contorne a navegação. Ocultar aqui é só UI: o
 * backend deverá aplicar a mesma autorização ao servir estes campos.
 */
export function ClienteEditFormBody({
  step,
  documentoInput,
  onDocumentoInputChange,
  documentType,
  draft,
  onDraftChange,
  onNomeFantasiaChange,
  onSiglaChange,
  activeSection,
  onActiveSectionChange,
}: ClienteEditFormBodyProps) {
  if (step === "documento") {
    return (
      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto px-4 py-3">
        <div className="space-y-4">
          <Input
            label="CNPJ ou CPF"
            placeholder="Digite o CNPJ ou CPF"
            value={documentoInput}
            density="compact"
            className="focus:!border-primary"
            onChange={(event) => onDocumentoInputChange(event.target.value)}
          />

          {documentoInput.length > 0 && (
            <p className="text-xs text-zinc-400">
              {documentType === "cnpj" && "Documento identificado como CNPJ."}
              {documentType === "cpf" && "Documento identificado como CPF."}
              {documentType === null &&
                "Informe um CNPJ (14 dígitos) ou CPF (11 dígitos) válido."}
            </p>
          )}
        </div>
      </div>
    );
  }

  const canAccessAdministrativo = hasAdministrativeAccess(currentUser.perfil);
  const sections = allSections.filter(
    (section) => section.id !== "administrativo" || canAccessAdministrativo
  );

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col">
      <div className="shrink-0 px-4 pt-2.5">
        <Badge>{draft.tipoDocumento === "cnpj" ? "CNPJ" : "CPF"}</Badge>
      </div>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <EntityFormNav
          sections={sections}
          activeSection={activeSection}
          onSectionChange={onActiveSectionChange}
        />

        <EntitySection id={activeSection}>
          {activeSection === "dados" && (
            <DadosSection
              draft={draft}
              onChange={onDraftChange}
              onNomeFantasiaChange={onNomeFantasiaChange}
              onSiglaChange={onSiglaChange}
            />
          )}

          {activeSection === "endereco" && (
            <EnderecoSection draft={draft} onChange={onDraftChange} />
          )}

          {activeSection === "contatos" && (
            <ContatosSection draft={draft} onChange={onDraftChange} />
          )}

          {activeSection === "equipe" && (
            <EquipeSection draft={draft} onChange={onDraftChange} />
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
