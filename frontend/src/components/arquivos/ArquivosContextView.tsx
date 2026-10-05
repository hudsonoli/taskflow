"use client";

import { useEffect, useRef, useState } from "react";
import { FolderOpen, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  atualizarStatusLayoutArquivo,
  excluirArquivoDemanda,
  listArquivosCentral,
  listDiretorioClientes,
  listDiretorioDemandas,
  listDiretorioProjetos,
} from "@/lib/api-backend";
import type { ArquivoCentral, ArquivosCentralFiltros } from "@/types/arquivo";
import type { ClienteDiretorioItem, ProjetoDiretorioItem } from "@/lib/api-backend";
import type { DemandaArquivoStatusLayout, DemandaDiretorio } from "@/types/demanda";
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

/**
 * Visão de Arquivos reutilizada pelo Gerenciador central (`/arquivos`) e pelas abas Arquivos
 * de Projeto e Cliente. Mesma listagem (`GET /arquivos`), mesmo preview, mesmo upload — a
 * diferença é só o recorte fixo: `clienteId`/`projetoId` vão sempre na query do servidor
 * (nunca um filtro local sobre um dataset global) e o servidor continua aplicando o escopo da
 * Demanda. Passar um id aqui NUNCA amplia visibilidade; o frontend não é autoridade de
 * segurança.
 */
export function ArquivosContextView({
  clienteId,
  projetoId,
  compacto = false,
}: {
  clienteId?: string;
  projetoId?: string;
  compacto?: boolean;
}) {
  const [clientes, setClientes] = useState<ClienteDiretorioItem[]>([]);
  const [projetos, setProjetos] = useState<ProjetoDiretorioItem[]>([]);
  const [demandasDiretorio, setDemandasDiretorio] = useState<DemandaDiretorio[]>([]);

  const [filtrosUsuario, setFiltros] = useState<ArquivosCentralFiltros>({});
  const [itens, setItens] = useState<ArquivoCentral[]>([]);
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [temMais, setTemMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [uploadAberto, setUploadAberto] = useState(false);
  const [indicePreview, setIndicePreview] = useState<number | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);

  // O recorte fixo sempre prevalece sobre o que estiver no estado dos filtros — assim uma
  // troca de Projeto/Cliente pelo chamador nunca deixa o id antigo vazar para a consulta.
  const filtros: ArquivosCentralFiltros = {
    ...filtrosUsuario,
    clienteId: clienteId ?? filtrosUsuario.clienteId,
    projetoId: projetoId ?? filtrosUsuario.projetoId,
  };

  // Diretórios completos (não capados) carregados uma vez — alimentam os filtros e o modal
  // de upload. Só carrega o que o recorte ainda não resolve (Projeto fixo não precisa da lista
  // de Clientes/Projetos). Mesmo padrão de TrafegoView/RelatoriosView.
  useEffect(() => {
    if (!clienteId && !projetoId) listDiretorioClientes().then(setClientes).catch(() => {});
    if (!projetoId) listDiretorioProjetos().then(setProjetos).catch(() => {});
    listDiretorioDemandas().then(setDemandasDiretorio).catch(() => {});
  }, [clienteId, projetoId]);

  const projetosDoRecorte = clienteId ? projetos.filter((projeto) => projeto.clienteId === clienteId) : projetos;
  const demandasDoRecorte = demandasDiretorio.filter(
    (demanda) => (!clienteId || demanda.clienteId === clienteId) && (!projetoId || demanda.projetoId === projetoId),
  );

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
  });

  useEffect(() => {
    let cancelado = false;
    const timeout = setTimeout(() => {
      listArquivosCentral({ ...filtrosAtualRef.current, limit: TAMANHO_PAGINA, offset: 0 })
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
    // chaveAtual já resume todo o conteúdo relevante de `filtros`; refreshNonce força nova busca sem mudar filtros
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

  // Refaz a consulta atual (mesmos filtros) — o servidor volta a ser a fonte da lista.
  function recarregar() {
    setItens([]);
    setTemMais(false);
    setErro(null);
    setCarregandoInicial(true);
    setRefreshNonce((atual) => atual + 1); // força nova busca mesmo com os mesmos filtros
  }

  // O PATCH devolve o registro persistido: o status do servidor é a fonte da verdade (não o
  // que foi enviado). O mesmo `itens` alimenta o card e o preview — um único estado.
  async function alterarStatus(arquivo: ArquivoCentral, status: DemandaArquivoStatusLayout) {
    const atualizado = await atualizarStatusLayoutArquivo(arquivo.demandaId, arquivo.id, status);
    if (filtros.status && atualizado.statusLayout !== filtros.status) {
      // Com filtro de status ativo, o item deixou de pertencer à lista: reconcilia com o servidor
      // em vez de manter na tela algo que a própria consulta não devolveria mais.
      setIndicePreview(null);
      recarregar();
      return;
    }
    setItens((atual) =>
      atual.map((existente) =>
        existente.id === atualizado.id ? { ...existente, statusLayout: atualizado.statusLayout } : existente,
      ),
    );
  }

  async function excluir(arquivo: ArquivoCentral) {
    await excluirArquivoDemanda(arquivo.demandaId, arquivo.id);
    setItens((atual) => atual.filter((existente) => existente.id !== arquivo.id));
    setIndicePreview(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-zinc-400">
          {carregandoInicial
            ? "Carregando…"
            : `${itens.length} arquivo(s) carregado(s)${temMais ? " · há mais — use “Carregar mais”" : ""}`}
        </p>
        <Button type="button" onClick={() => setUploadAberto(true)}>
          <Plus className="h-3.5 w-3.5" />
          Novo arquivo
        </Button>
      </div>

      <ArquivosFiltros
        filtros={filtros}
        onChange={setFiltros}
        clientes={clientes}
        projetos={projetosDoRecorte}
        demandas={demandasDoRecorte}
        ocultarCliente={Boolean(clienteId || projetoId)}
        ocultarProjeto={Boolean(projetoId)}
        compacto={compacto}
      />

      {erro && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erro}
        </div>
      )}

      {carregandoInicial ? (
        <p className="text-sm text-zinc-400">Carregando…</p>
      ) : itens.length === 0 ? (
        <EmptyState title="Nenhum arquivo encontrado." description="Ajuste os filtros ou envie o primeiro arquivo." icon={<FolderOpen size={18} />} />
      ) : (
        <>
          <div
            className={
              compacto
                ? "grid grid-cols-2 gap-3 sm:grid-cols-3"
                : "grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6"
            }
          >
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
        onAlterarStatus={alterarStatus}
        podeExcluir
      />

      <ArquivoUploadModal
        open={uploadAberto}
        onClose={() => setUploadAberto(false)}
        clientes={clientes}
        projetos={projetosDoRecorte}
        demandas={demandasDoRecorte}
        clienteFixoId={clienteId}
        projetoFixoId={projetoId}
        onCreated={() => {
          setUploadAberto(false);
          recarregar();
        }}
      />
    </div>
  );
}
