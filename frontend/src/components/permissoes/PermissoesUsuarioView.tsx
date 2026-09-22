"use client";

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Combobox } from "@/components/ui/Combobox";
import { EmptyState } from "@/components/ui/EmptyState";
import { EstadoCarregando } from "@/components/operacional/EstadoCarregando";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { definirPermissaoUsuario, herdarPermissaoUsuario, listarPermissoesUsuario } from "@/lib/api-backend";
import { podeGerenciarPermissoes } from "@/lib/escopo-operacional";
import type { PermissaoAdminItem, PermissaoEstadoUI } from "@/types/permissao";

function estadoUI(item: PermissaoAdminItem): PermissaoEstadoUI {
  if (item.override === "conceder") return "conceder";
  if (item.override === "negar") return "negar";
  return "herdar";
}

const OPCOES_ESTADO: { value: PermissaoEstadoUI; label: string }[] = [
  { value: "herdar", label: "Herdar" },
  { value: "conceder", label: "Conceder" },
  { value: "negar", label: "Negar" },
];

export function PermissoesUsuarioView() {
  const { usuarioAtual, sessaoCarregando } = useAppData();
  const { usuarios, carregando: diretorioCarregando, erro: diretorioErro } = useDiretorioUsuarios();

  const [usuarioId, setUsuarioId] = useState("");
  const [itens, setItens] = useState<PermissaoAdminItem[] | null>(null);
  const [carregandoItens, setCarregandoItens] = useState(false);
  const [erroCarregamento, setErroCarregamento] = useState<string | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [emAtualizacao, setEmAtualizacao] = useState<Set<string>>(new Set());

  const isSelf = usuarioId !== "" && usuarioId === usuarioAtual?.id;

  async function carregar(id: string) {
    setCarregandoItens(true);
    setErroCarregamento(null);
    setItens(null);
    try {
      const dados = await listarPermissoesUsuario(id);
      setItens(dados);
    } catch (error) {
      setItens(null);
      setErroCarregamento(
        error instanceof Error ? error.message : "Não foi possível carregar as permissões deste usuário.",
      );
    } finally {
      setCarregandoItens(false);
    }
  }

  useEffect(() => {
    if (!usuarioId) return;
    const timeout = setTimeout(() => {
      void carregar(usuarioId);
    }, 0);
    return () => clearTimeout(timeout);
  }, [usuarioId]);

  async function handleMudarEstado(item: PermissaoAdminItem, novoEstado: PermissaoEstadoUI) {
    if (isSelf || emAtualizacao.has(item.permissao)) return;

    setErroAcao(null);
    setEmAtualizacao((atual) => new Set(atual).add(item.permissao));
    try {
      if (novoEstado === "herdar") {
        await herdarPermissaoUsuario(usuarioId, item.permissao);
        // DELETE devolve 204 — refaz o GET completo pra ter herdado/efetivo corretos.
        await carregar(usuarioId);
      } else {
        const atualizado = await definirPermissaoUsuario(usuarioId, item.permissao, novoEstado);
        setItens((atual) => (atual ? atual.map((linha) => (linha.permissao === atualizado.permissao ? atualizado : linha)) : atual));
      }
    } catch (error) {
      setErroAcao(error instanceof Error ? error.message : "Não foi possível atualizar esta permissão.");
    } finally {
      setEmAtualizacao((atual) => {
        const proximo = new Set(atual);
        proximo.delete(item.permissao);
        return proximo;
      });
    }
  }

  if (sessaoCarregando || !usuarioAtual) return null;

  if (!podeGerenciarPermissoes(usuarioAtual)) {
    return (
      <AcessoNegado
        titulo="Área restrita a administradores"
        descricao="A gestão de permissões é restrita a administradores com a permissão permissoes.gerenciar. Se você precisa desta área, fale com quem administra o workspace."
      />
    );
  }

  // Grupos por módulo, na ordem já entregue pela API (montar_visao_administrativa já ordena
  // por módulo/label/permissão) — nunca recalculado aqui.
  const grupos: { modulo: string; itens: PermissaoAdminItem[] }[] = [];
  for (const item of itens ?? []) {
    const grupo = grupos.find((g) => g.modulo === item.modulo);
    if (grupo) grupo.itens.push(item);
    else grupos.push({ modulo: item.modulo, itens: [item] });
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={<ShieldCheck className="h-5 w-5" />}
        title="Permissões por usuário"
        description="Gerencie exceções individuais sobre as permissões herdadas do perfil."
      />

      <div className="max-w-sm">
        <Combobox
          label="Usuário"
          value={usuarioId}
          onChange={setUsuarioId}
          options={usuarios.map((usuario) => ({ value: usuario.id, label: usuario.nome }))}
          placeholder={diretorioCarregando ? "Carregando usuários…" : "Buscar usuário…"}
          emptyLabel={diretorioErro ?? "Nenhum usuário encontrado"}
        />
      </div>

      {!usuarioId && (
        <EmptyState title="Selecione um usuário" description="Selecione um usuário para visualizar as permissões." />
      )}

      {usuarioId && isSelf && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-400">
          Suas próprias permissões podem ser consultadas, mas não alteradas por esta tela.
        </p>
      )}

      {usuarioId && erroAcao && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erroAcao}
        </p>
      )}

      {usuarioId && carregandoItens && <EstadoCarregando cards={0} />}

      {usuarioId && !carregandoItens && erroCarregamento && (
        <EstadoErro mensagem={erroCarregamento} onRetry={() => void carregar(usuarioId)} />
      )}

      {usuarioId && !carregandoItens && !erroCarregamento && itens && (
        <div className="flex flex-col gap-4">
          {grupos.map((grupo) => (
            <section
              key={grupo.modulo}
              className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
            >
              <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
                {grupo.modulo}
              </h2>
              <div className="flex flex-col divide-y divide-zinc-100 dark:divide-zinc-800">
                {grupo.itens.map((item) => (
                  <div
                    key={item.permissao}
                    className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-zinc-800 dark:text-zinc-100">{item.label}</p>
                      <p className="text-xs text-zinc-400 dark:text-zinc-500">{item.permissao}</p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 sm:shrink-0">
                      <Badge tone="neutral">Perfil base: {item.herdado ? "Permitido" : "Negado"}</Badge>
                      <Badge tone={item.efetivo ? "green" : "red"}>Efetivo: {item.efetivo ? "Permitido" : "Negado"}</Badge>
                      <div className="w-36">
                        <Select
                          label=""
                          className="py-1.5"
                          value={estadoUI(item)}
                          disabled={isSelf || emAtualizacao.has(item.permissao)}
                          onChange={(event) => void handleMudarEstado(item, event.target.value as PermissaoEstadoUI)}
                          options={OPCOES_ESTADO}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
