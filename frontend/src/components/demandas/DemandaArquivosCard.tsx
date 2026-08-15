import { RecursoIndisponivel } from "./RecursoIndisponivel";

/**
 * Arquivos de Demanda — **sem tabela na Fase 2E.1**.
 *
 * O componente anterior lia e escrevia `demanda.arquivos`, que agora chega sempre vazio da
 * API. Manter os controles de escrita criaria a pior falha possível: o usuário preencheria,
 * a tela mostraria salvo, e nada existiria no banco.
 *
 * As props continuam na assinatura porque o chamador não muda quando arquivos voltar em
 * Fase 2E.3 — só o corpo deste arquivo.
 */
export function DemandaArquivosCard() {
  return <RecursoIndisponivel recurso="Arquivos" fase="Fase 2E.3" />;
}
