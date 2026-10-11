"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Moon, RotateCcw, Sun } from "lucide-react";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { ColorField } from "@/components/personalizacao/ColorField";
import { LogoField } from "@/components/personalizacao/LogoField";
import { PersonalizacaoPreview } from "@/components/personalizacao/PersonalizacaoPreview";
import { COR_PRIMARIA_PADRAO, COR_SECUNDARIA_PADRAO, hexValido } from "@/lib/branding-tokens";
import {
  atualizarBrandingEmpresa,
  enviarLogoEmpresa,
  obterBrandingEmpresa,
  removerLogoEmpresa,
  restaurarBrandingEmpresa,
  urlLogoEmpresa,
} from "@/lib/plataforma-api";
import type { Branding, TemaVisual } from "@/types/personalizacao";
import type { PlataformaEmpresa } from "@/types/plataforma";

/**
 * Personalização (logo, cores, tema) de UMA empresa, escolhida pela Administração da Plataforma. Mesmos campos e
 * mesmas validações do tenant (o backend reaproveita o mesmo serviço). Diferença importante: salvar aqui NÃO altera a
 * aparência do app de quem está editando — só a da empresa em foco.
 */

const TEMAS: { valor: TemaVisual; rotulo: string; icone: typeof Sun }[] = [
  { valor: "claro", rotulo: "Claro", icone: Sun },
  { valor: "escuro", rotulo: "Escuro", icone: Moon },
];

type Rascunho = { corPrimaria: string; corSecundaria: string; tema: TemaVisual };
const rascunhoDe = (b: Branding): Rascunho => ({ corPrimaria: b.corPrimaria, corSecundaria: b.corSecundaria, tema: b.tema });

export function EmpresaPersonalizacaoSection({ empresa }: { empresa: PlataformaEmpresa }) {
  const [salvo, setSalvo] = useState<Branding | null>(null);
  const [rascunho, setRascunho] = useState<Rascunho | null>(null);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [previaUrl, setPreviaUrl] = useState<string | null>(null);
  const [removendoLogo, setRemovendoLogo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [confirmarRestaurar, setConfirmarRestaurar] = useState(false);

  async function carregar() {
    setErro(null);
    try {
      const dados = await obterBrandingEmpresa(empresa.id);
      setSalvo(dados);
      setRascunho(rascunhoDe(dados));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível carregar a personalização.");
    }
  }

  useEffect(() => {
    const timeout = setTimeout(() => void carregar(), 0);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresa.id]);

  useEffect(() => {
    if (!arquivo) return;
    const url = URL.createObjectURL(arquivo);
    const timeout = setTimeout(() => setPreviaUrl(url), 0);
    return () => {
      clearTimeout(timeout);
      URL.revokeObjectURL(url);
    };
  }, [arquivo]);

  const coresValidas = rascunho ? hexValido(rascunho.corPrimaria) && hexValido(rascunho.corSecundaria) : false;
  const alteracoesPendentes = useMemo(() => {
    if (!salvo || !rascunho) return false;
    return (
      rascunho.corPrimaria !== salvo.corPrimaria ||
      rascunho.corSecundaria !== salvo.corSecundaria ||
      rascunho.tema !== salvo.tema ||
      arquivo !== null ||
      removendoLogo
    );
  }, [salvo, rascunho, arquivo, removendoLogo]);

  function desfazerLogo() {
    setArquivo(null);
    setPreviaUrl(null);
    setRemovendoLogo(false);
  }

  function atualizar(parcial: Partial<Rascunho>) {
    setRascunho((atual) => (atual ? { ...atual, ...parcial } : atual));
    setSucesso(null);
  }

  async function handleSalvar() {
    if (!salvo || !rascunho || !coresValidas) return;
    setSalvando(true);
    setErroSalvar(null);
    setSucesso(null);
    let atual = salvo;
    try {
      if (arquivo) atual = await enviarLogoEmpresa(empresa.id, arquivo);
      else if (removendoLogo) atual = await removerLogoEmpresa(empresa.id);
      if (
        rascunho.corPrimaria !== atual.corPrimaria ||
        rascunho.corSecundaria !== atual.corSecundaria ||
        rascunho.tema !== atual.tema
      ) {
        atual = await atualizarBrandingEmpresa(empresa.id, rascunho);
      }
      setSalvo(atual);
      setRascunho(rascunhoDe(atual));
      desfazerLogo();
      setSucesso(`Personalização salva para ${empresa.nome}.`);
    } catch (error) {
      setSalvo(atual);
      setErroSalvar(error instanceof Error ? error.message : "Não foi possível salvar a personalização.");
      if (arquivo && atual.logoVersao !== salvo.logoVersao) desfazerLogo();
    } finally {
      setSalvando(false);
    }
  }

  async function handleRestaurar() {
    setSalvando(true);
    setErroSalvar(null);
    setSucesso(null);
    try {
      const padrao = await restaurarBrandingEmpresa(empresa.id);
      setSalvo(padrao);
      setRascunho(rascunhoDe(padrao));
      desfazerLogo();
      setConfirmarRestaurar(false);
      setSucesso("Padrão restaurado: logo removido e cores/tema originais do TaskFlow.");
    } catch (error) {
      setConfirmarRestaurar(false);
      setErroSalvar(error instanceof Error ? error.message : "Não foi possível restaurar o padrão.");
    } finally {
      setSalvando(false);
    }
  }

  if (erro) return <EstadoErro mensagem={erro} onRetry={carregar} />;
  if (!salvo || !rascunho) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-sm text-fg-muted shadow-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Carregando personalização…
      </div>
    );
  }

  // Logo SALVO da empresa em foco (nunca o da própria empresa de quem edita): `null` = sem logo.
  const logoSalvoSrc = salvo.logoDisponivel ? urlLogoEmpresa(empresa.id, salvo.logoVersao) : null;
  const srcPrevia = arquivo && previaUrl ? previaUrl : removendoLogo ? null : logoSalvoSrc;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-6 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <LogoField
            arquivo={arquivo}
            previaUrl={previaUrl}
            logoAtual={salvo.logoDisponivel}
            logoAtualSrc={logoSalvoSrc}
            removendo={removendoLogo}
            onEscolher={(novo) => {
              setArquivo(novo);
              setRemovendoLogo(false);
              setSucesso(null);
            }}
            onRemover={() => {
              setArquivo(null);
              setPreviaUrl(null);
              setRemovendoLogo(true);
              setSucesso(null);
            }}
            onDesfazer={desfazerLogo}
          />

          <ColorField
            label="Cor principal"
            descricao="Botões principais, destaques e item ativo do menu."
            valor={rascunho.corPrimaria}
            padrao={COR_PRIMARIA_PADRAO}
            onChange={(valor) => atualizar({ corPrimaria: valor })}
          />
          <ColorField
            label="Cor secundária"
            descricao="Destaques complementares e fim do degradê da marca."
            valor={rascunho.corSecundaria}
            padrao={COR_SECUNDARIA_PADRAO}
            onChange={(valor) => atualizar({ corSecundaria: valor })}
          />

          <fieldset>
            <legend className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Tema padrão da empresa</legend>
            <div className="inline-flex rounded-xl border border-field-line bg-field p-1" role="radiogroup" aria-label="Tema">
              {TEMAS.map(({ valor, rotulo, icone: Icone }) => {
                const ativo = rascunho.tema === valor;
                return (
                  <button
                    key={valor}
                    type="button"
                    role="radio"
                    aria-checked={ativo}
                    onClick={() => atualizar({ tema: valor })}
                    className={clsx(
                      "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                      ativo ? "bg-brand-gradient shadow-sm" : "text-fg-muted hover:bg-surface-hover hover:text-fg",
                    )}
                  >
                    <Icone size={14} /> {rotulo}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </div>

        <div className="flex flex-col gap-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Prévia — {empresa.nome}</p>
          <PersonalizacaoPreview
            primaria={hexValido(rascunho.corPrimaria) ? rascunho.corPrimaria : salvo.corPrimaria}
            secundaria={hexValido(rascunho.corSecundaria) ? rascunho.corSecundaria : salvo.corSecundaria}
            tema={rascunho.tema}
            logoSrc={srcPrevia}
          />
          <p className="text-xs text-fg-muted">
            A identidade vale para os usuários desta empresa. A aparência do seu próprio acesso não muda.
          </p>
        </div>
      </div>

      {erroSalvar && (
        <div role="alert" className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-2.5 text-xs font-medium text-danger">
          {erroSalvar}
        </div>
      )}
      {sucesso && (
        <div role="status" className="rounded-xl border border-success/40 bg-success/10 px-3 py-2.5 text-xs font-medium text-success">
          {sucesso}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button type="button" variant="secondary" disabled={salvando || salvo.padrao} onClick={() => setConfirmarRestaurar(true)}>
          <RotateCcw size={14} /> Restaurar padrão
        </Button>
        <div className="flex items-center gap-3">
          {alteracoesPendentes && <span className="text-xs text-fg-muted">Alterações não salvas</span>}
          <Button type="button" disabled={salvando || !alteracoesPendentes || !coresValidas} onClick={() => void handleSalvar()}>
            {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Salvar alterações
          </Button>
        </div>
      </div>

      <Modal open={confirmarRestaurar} onClose={() => !salvando && setConfirmarRestaurar(false)} maxWidthClassName="max-w-md">
        <h2 className="text-base font-semibold text-fg">Restaurar o padrão do TaskFlow?</h2>
        <p className="mt-2 text-sm text-fg-muted">
          O logo de {empresa.nome} será removido e as cores e o tema voltam ao padrão. Nenhuma outra configuração é alterada.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" disabled={salvando} onClick={() => setConfirmarRestaurar(false)}>
            Cancelar
          </Button>
          <Button type="button" disabled={salvando} onClick={() => void handleRestaurar()}>
            {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Restaurar padrão
          </Button>
        </div>
      </Modal>
    </div>
  );
}
