// Barrel público do pacote entity/. Exporta somente a API aprovada em
// docs/design-system/entity-component-api.md — o Context interno do
// EntityDrawer (useEntityDrawerContext) e o helper de ids (entityFormIds.ts)
// são deliberadamente NÃO reexportados aqui: são consumidos apenas por
// outros arquivos deste pacote via import relativo direto.

export { EntityDrawer } from "./EntityDrawer";
export type { EntityDrawerProps, EntityDrawerMode, EntityDrawerPreset } from "./EntityDrawer";

export { EntityHeader } from "./EntityHeader";
export type { EntityHeaderProps } from "./EntityHeader";

export { EntityPeek } from "./EntityPeek";
export type { EntityPeekProps, EntityPeekSummaryItem } from "./EntityPeek";

export { EntityForm } from "./EntityForm";
export type { EntityFormProps } from "./EntityForm";

export { EntityFormNav } from "./EntityFormNav";
export type {
  EntityFormNavProps,
  EntityFormNavSection,
  EntitySectionStatus,
  EntitySectionsStatusMap,
} from "./EntityFormNav";

export { EntitySection } from "./EntitySection";
export type { EntitySectionProps } from "./EntitySection";

export { EntityActions } from "./EntityActions";
export type { EntityActionsProps, EntityActionButton, EntityActionVariant } from "./EntityActions";

export { EntityHistory } from "./EntityHistory";
export type { EntityHistoryProps, EntityHistoryEvent } from "./EntityHistory";

export { AdministrativeSection } from "./AdministrativeSection";

export { FinancialValueField } from "./FinancialValueField";

export { BankingFields } from "./BankingFields";
export type { BankingFieldsValue } from "./BankingFields";
