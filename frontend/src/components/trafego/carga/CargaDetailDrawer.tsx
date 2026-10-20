"use client";

import { useState } from "react";
import { DetailsModal } from "@/components/ui/DetailsModal";
import { EmptyState } from "@/components/ui/EmptyState";
import { linhaDoItem, parametrosDoDetalhe, type AlvoDetalhe } from "@/lib/trafego-carga";
import { TrafegoErroLocal, TrafegoSkeleton } from "../TrafegoEstados";
import { CargaItensTabela } from "./CargaItensTabela";
import { useTrafegoCarga } from "./useTrafegoCarga";

/**
 * Drill-down de UMA pessoa ou UM departamento: etapas que compõem o número da semana. Faz UMA chamada (`detalhe=usuario|departamento`) ao ABRIR — o componente só é montado com um alvo, então nada
 * é carregado antes e fechar/reabrir busca de novo (sem cache: o dado é sempre o do momento). Não há chamada por linha.
 */
export function CargaDetailDrawer({ alvo, semana, onClose, onAbrirTarefa }: { alvo: AlvoDetalhe; semana: string; onClose: () => void; onAbrirTarefa: (demandaId: string) => void }) {
  const [versao, setVersao] = useState(0);
  const estado = useTrafegoCarga(parametrosDoDetalhe(alvo, semana), versao);
  const detalhe = estado.dados?.detalhe ?? null;
  const linhas = detalhe ? detalhe.etapas.map(linhaDoItem) : [];

  return (
    <DetailsModal
      open
      onClose={onClose}
      title={alvo.nome}
      description={alvo.tipo === "usuario" ? "Etapas que compõem a carga desta pessoa na semana" : "Etapas que compõem a carga deste departamento na semana"}
      maxWidthClassName="max-w-5xl"
    >
      {estado.carregando && detalhe === null ? (
        <TrafegoSkeleton kpis={0} linhas={4} />
      ) : detalhe === null ? (
        <TrafegoErroLocal mensagem={estado.erro ?? "Não foi possível carregar o detalhe da carga."} onTentarNovamente={() => setVersao((v) => v + 1)} />
      ) : linhas.length === 0 ? (
        <EmptyState title="Nenhuma etapa aberta para este recorte." description="Etapas abertas de tarefas em andamento aparecem aqui, com a parte que cabe a este recorte." />
      ) : (
        <div className="flex flex-col gap-3">
          <CargaItensTabela linhas={linhas} mostrarParte onAbrir={onAbrirTarefa} />
          <p className="text-xs text-fg-subtle">
            {detalhe.truncado ? `Mostrando ${linhas.length} de ${detalhe.etapasTotal} etapas.` : detalhe.etapasTotal === 1 ? "1 etapa." : `${detalhe.etapasTotal} etapas.`} A coluna “Nesta semana” é a parte deste
            recorte; quando a etapa é dividida, o total da etapa aparece abaixo. A janela é planejamento, não prazo.
          </p>
        </div>
      )}
    </DetailsModal>
  );
}
