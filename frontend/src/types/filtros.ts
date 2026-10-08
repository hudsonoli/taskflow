import type { LucideIcon } from "lucide-react";

/**
 * Filtros avançados (Arquivos, Tráfego e futuras listagens). O modelo é independente de domínio: o que identifica um filtro
 * é o par estável `campo` + `operador` + `valores` (ids/códigos) — o texto em português existe só na apresentação.
 *
 * - `is` / `is_not`: um valor ("é" / "não é");
 * - `in` / `not_in`: vários valores ("é um de" / "não é um de"; entre os valores vale OR);
 * - `before` / `after`: datas ("antes de" / "depois de"). "é" numa data usa `is`.
 *
 * Entre filtros DIFERENTES vale AND. Cada campo aparece no máximo uma vez.
 */
export type OperadorFiltro = "is" | "is_not" | "in" | "not_in" | "before" | "after";

export type FiltroAtivo = {
  campo: string;
  operador: OperadorFiltro;
  valores: string[];
};

export type OpcaoFiltro = {
  value: string;
  label: string;
  descricao?: string;
  /** Usuários: avatar (foto ou iniciais) ao lado do nome. */
  avatar?: { nome: string; corIdentificacao?: string; fotoUrl?: string };
};

/** Atalho de data resolvido em relação a "agora" no momento da consulta (ex.: "hoje", "atrasado"). */
export type PresetData = { value: string; label: string };

/** Busca de opções no servidor (campos com muitas opções: usuários, clientes…). `busca` vazia = primeira página. */
export type BuscarOpcoesFiltro = (params: { busca: string; limit: number; offset: number }) => Promise<OpcaoFiltro[]>;
/** Rótulos de valores que vieram da URL e nunca passaram pelo dropdown. Devolve só os que encontrou. */
export type ResolverOpcoesFiltro = (valores: string[]) => Promise<OpcaoFiltro[]>;

export type DefinicaoFiltro = {
  /** chave estável: também é o nome do parâmetro na URL */
  id: string;
  label: string;
  icone?: LucideIcon;
  tipo: "enum" | "data";
  /** enum: opções conhecidas (lista local, pesquisável no cliente) */
  opcoes?: OpcaoFiltro[];
  /** enum: opções no servidor (substitui `opcoes`) */
  buscarOpcoes?: BuscarOpcoesFiltro;
  resolverOpcoes?: ResolverOpcoesFiltro;
  /**
   * enum: o valor é um id de registro (cliente, projeto, usuário…) — na URL só o FORMATO é validado, porque a lista de
   * opções pode ainda não ter chegado (ou o registro pode estar arquivado). Sem isso, valores fora de `opcoes` são descartados.
   */
  valoresAbertos?: boolean;
  /** enum com `opcoes` locais: `false` enquanto a lista ainda carrega (valores sem rótulo mostram "Carregando…", não "Indisponível") */
  opcoesCarregadas?: boolean;
  /** enum: aceita "é um de" (padrão: sim). Com `false` só há um valor por filtro. */
  multiplo?: boolean;
  /** enum: oferece "não é" / "não é um de" (padrão: sim) — só quando o servidor sabe executar a exclusão. */
  permiteExcluir?: boolean;
  /** enum: campo de busca dentro das opções (padrão: sim se há mais de 7 opções ou se a fonte é o servidor) */
  buscavel?: boolean;
  /** data: atalhos relativos a hoje */
  presets?: PresetData[];
  /** texto do campo de busca de opções */
  placeholderBusca?: string;
  mensagemVazio?: string;
};
