// Helper estritamente interno ao pacote entity/ — nunca exportado por
// index.ts. Gera ids determinísticos compartilhados entre EntityFormNav
// (rail) e EntitySection (painel), para que os dois arquivos não precisem
// importar um do outro diretamente para se conectarem via ARIA
// (aria-controls/aria-labelledby, role="tab"/role="tabpanel").

export function entityFormNavTabId(sectionId: string) {
  return `entity-formnav-tab-${sectionId}`;
}

export function entitySectionPanelId(sectionId: string) {
  return `entity-section-panel-${sectionId}`;
}
