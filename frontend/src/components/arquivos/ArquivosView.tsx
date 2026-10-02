"use client";

import { useEffect, useRef, useState } from "react";
import { FolderOpen, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  excluirArquivoDemanda,
  listArquivosCentral,
  listDiretorioClientes,
  listDiretorioDemandas,
  listDiretorioProjetos,
} from "@/lib/api-backend";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import type { ArquivoCentral, ArquivosCentralFiltros } from "@/types/arquivo";
import type { ClienteDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import type { DemandaDiretorio } from "@/types/demanda";
import { ArquivoCard } from "./ArquivoCard";
import { ArquivoPreviewModal } from "./ArquivoPreviewModal";
import { ArquivosFiltros } from "./ArquivosFiltros";
import { ArquivoUploadModal } from "./ArquivoUploadModal";

const TAMANHO_PAGINA = 24;

function chaveFiltros(filtros: ArquivosCentralFiltros): string {
  const resto = { ...filtros };
  delete resto.limit;
  delete resto.offset;
  return JSON.stringify(resto);
}

export function ArquivosView() {
  const { usuarios } = useDiretorioUsuarios();
  const [clientes, setClientes] = useState<ClienteDiretorioItem[]>([]);
  const [projetos, setProjetos] = useState<ProjetoDiretorioItem[]>([]);
  const [demandasDiretorio, setDemandasDiretorio] = useState<DemandaDiretorio[]>([]);

  const [filtros, setFiltros] = useState<ArquivosCentralFiltros>({});
  const [itens, setItens] = useState<ArquivoCentral[]>([]);
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [temMais, setTemMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [uploadAberto, setUploadAberto] = useState(false);
  const [indicePreview, setIndicePreview] = useState<number | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);

  // Diretórios completos (não capados) carregados uma vez — alimentam os filtros e o modal
  // de upload central. Mesmo padrão de TrafegoView/RelatoriosView.
  useEffect(() => {
    listDiretorioClientes().then(setClientes).catch(() => {});
    listDiretorioProjetos().then(setProjetos).catch(() => {});
    listDiretorioDemandas().then(setDemandasDiretorio).catch(() => {});
  }, []);

  // Troca de filtro comparada durante o RENDER (mesmo padrão de ProjetoDemandasSection/
  // DemandasView) — evita setState síncrono dentro do efeito.
  const chaveAtual = chaveFiltros(filtros);
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  if (chaveAtual !== chaveConsultada) {
    setChaveConsultada(chaveAtual);
    setItens([]);
    setTemMais(false);
    setErro(null);
    setCarregandoInicial(true);
  }

  const filtrosAtualRef = useRef(filtros);
  useEffect(() => {
    filtrosAtualRef.current = filtros;
  }, [filtros]);

  useEffect(() => {
    let cancelado = false;
    const timeout = setTimeout(() => {
      listArquivosCentral({ ...filtros, limit: TAMANHO_PAGINA, offset: 0 })
        .then((resultado) => {
          if (cancelado) return;
          setItens(resultado);
          setTemMais(resultado.length === TAMANHO_PAGINA);
          setErro(null);
          setCarregandoInicial(false);
        })
        .catch((error) => {
          if (cancelado) return;
          setErro(error instanceof Error ? error.message : "Não foi possível carregar os arquivos.");
          setCarregandoInicial(false);
        });
    }, 250); // mesmo debounce de busca já usado nas demais listagens do projeto
    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- chaveAtual já resume todo o conteúdo relevante de `filtros`; refreshNonce força nova busca sem mudar filtros
  }, [chaveAtual, refreshNonce]);

  function carregarMais() {
    const filtrosDoClique = filtrosAtualRef.current;
    setCarregandoMais(true);
    listArquivosCentral({ ...filtrosDoClique, limit: TAMANHO_PAGINA, offset: itens.length })
      .then((resultado) => {
        if (chaveFiltros(filtrosAtualRef.current) !== chaveFiltros(filtrosDoClique)) return;
        setItens((atual) => [...atual, ...resultado]);
        setTemMais(resultado.length === TAMANHO_PAGINA);
      })
      .catch((error) => {
        setErro(error instanceof Error ? error.message : "Não foi possível carregar mais arquivos.");
      })
      .finally(() => setCarregandoMais(false));
  }

  async function excluir(arquivo: ArquivoCentral) {
    await excluirArquivoDemanda(arquivo.demandaId, arquivo.id);
    setItens((atual) => atual.filter((existente) => existente.id !== arquivo.id));
    setIndicePreview(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<FolderOpen className="h-5 w-5" />}
        title="Arquivos"
        description="Visão central de anexos, layouts e links — o mesmo arquivo de uma Demanda aparece aqui, sem duplicação."
        action={
          <Button type="button" onClick={() => setUploadAberto(true)}>
            <Plus className="h-3.5 w-3.5" />
            Novo arquivo
          </Button>
        }
      />

      <ArquivosFiltros filtros={filtros} onChange={setFiltros} clientes={clientes} projetos={projetos} demandas={demandasDiretorio} usuarios={usuarios} />

      {erro && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erro}
        </div>
      )}

      {carregandoInicial ? (
        <p className="text-sm text-zinc-400">Carregando…</p>
      ) : itens.length === 0 ? (
        <EmptyState title="Nenhum arquivo encontrado" description="Ajuste os filtros ou envie o primeiro arquivo." icon={<FolderOpen size={18} />} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
            {itens.map((arquivo, indice) => (
              <ArquivoCard key={arquivo.id} arquivo={arquivo} onAbrir={() => setIndicePreview(indice)} />
            ))}
          </div>
          {temMais && (
            <div className="flex justify-center">
              <Button type="button" variant="secondary" onClick={carregarMais} disabled={carregandoMais}>
                {carregandoMais ? "Carregando…" : "Carregar mais"}
              </Button>
            </div>
          )}
        </>
      )}

      <ArquivoPreviewModal
        itens={itens}
        indiceAtual={indicePreview}
        onFechar={() => setIndicePreview(null)}
        onNavegar={setIndicePreview}
        onExcluir={excluir}
        podeExcluir
      />

      <ArquivoUploadModal
        open={uploadAberto}
        onClose={() => setUploadAberto(false)}
        clientes={clientes}
        projetos={projetos}
        demandas={demandasDiretorio}
        onCreated={() => {
          setUploadAberto(false);
          setItens([]);
          setTemMais(false);
          setErro(null);
          setCarregandoInicial(true);
          setRefreshNonce((atual) => atual + 1); // força nova busca mesmo com os mesmos filtros
        }}
      />
    </div>
  );
}
