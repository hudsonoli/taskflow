"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2 } from "lucide-react";
import { SecaoAcessoInicial, SecaoDadosEmpresa, SecaoIdentidadeVisual } from "@/components/plataforma/NovaEmpresaSecoes";
import { SenhaTemporariaAviso } from "@/components/plataforma/SenhaTemporariaAviso";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { validarLogoNoNavegador } from "@/lib/personalizacao-logo";
import {
  ONBOARDING_VAZIO,
  brandingDoRascunho,
  payloadDoOnboarding,
  sugerirSlug,
  validarOnboarding,
  type RascunhoOnboarding,
} from "@/lib/plataforma";
import { atualizarBrandingEmpresa, enviarLogoEmpresa, onboardingEmpresaPlataforma } from "@/lib/plataforma-api";
import type { PlataformaOnboarding } from "@/types/plataforma";

type Resultado = { dados: PlataformaOnboarding; avisos: string[] };

/**
 * Nova empresa (Fase 10B/10B.1): Empresa (ATIVA) + identidade visual + primeiro Gestor num único formulário em seções. A criação da Empresa e do Gestor é ATÔMICA no
 * servidor (`POST /plataforma/empresas/onboarding`), sem SMTP: o servidor gera uma senha TEMPORÁRIA (só o hash persiste) que a tela de sucesso mostra UMA vez; a identidade visual (cores/tema e logo) é aplicada logo depois pelo mecanismo existente e, se falhar, NÃO desfaz a
 * empresa — vira um aviso. Ao concluir, o Administrador da Plataforma continua na Gestão (nenhuma sessão tenant, nenhuma impersonação): a tela de sucesso mostra o endereço
 * `/e/<slug>/login` para copiar, o usuário e a senha temporária do Gestor (exibida uma única vez).
 */
export function NovaEmpresaModal({ open, onClose, onCriada }: { open: boolean; onClose: () => void; onCriada: () => void }) {
  const router = useRouter();
  const [rascunho, setRascunho] = useState<RascunhoOnboarding>(ONBOARDING_VAZIO);
  const [slugEditado, setSlugEditado] = useState(false);
  const [codigoEditado, setCodigoEditado] = useState(false);
  const [logo, setLogo] = useState<File | null>(null);
  const [erroLogo, setErroLogo] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tentou, setTentou] = useState(false);
  const [resultado, setResultado] = useState<Resultado | null>(null);

  function atualizar(parcial: Partial<RascunhoOnboarding>) {
    if (parcial.codigoInterno !== undefined) setCodigoEditado(true); // fora do updater: efeito colateral não pertence a ele
    setRascunho((atual) => {
      const novo = { ...atual, ...parcial };
      // Enquanto a pessoa não mexeu, o slug e o código interno acompanham o nome (são só SUGESTÕES; o servidor valida e decide).
      if (parcial.nome !== undefined) {
        const base = sugerirSlug(parcial.nome);
        if (!slugEditado) novo.slug = base;
        if (!codigoEditado) novo.codigoInterno = base.toUpperCase();
      }
      return novo;
    });
  }

  function reiniciar() {
    setRascunho(ONBOARDING_VAZIO);
    setSlugEditado(false);
    setCodigoEditado(false);
    setLogo(null);
    setErroLogo(null);
    setErro(null);
    setTentou(false);
    setResultado(null);
  }

  function fechar() {
    if (salvando) return;
    reiniciar(); // descarta também a senha temporária (memória)
    onClose();
  }

  async function escolherLogo(arquivo: File | null) {
    setLogo(arquivo);
    setErroLogo(arquivo ? await validarLogoNoNavegador(arquivo) : null);
  }

  const erros = validarOnboarding(rascunho);
  const invalido = Object.keys(erros).length > 0 || Boolean(erroLogo);

  async function enviar(event: FormEvent) {
    event.preventDefault();
    setTentou(true);
    if (invalido || salvando) return;
    setSalvando(true);
    setErro(null);
    try {
      const dados = await onboardingEmpresaPlataforma(payloadDoOnboarding(rascunho));
      const avisos: string[] = [];
      const marca = brandingDoRascunho(rascunho);
      if (marca) {
        try {
          await atualizarBrandingEmpresa(dados.empresa.id, marca);
        } catch (falha) {
          avisos.push(`As cores/tema não foram aplicados (${falha instanceof Error ? falha.message : "erro"}). Ajuste na aba Personalização.`);
        }
      }
      if (logo) {
        try {
          await enviarLogoEmpresa(dados.empresa.id, logo);
        } catch (falha) {
          avisos.push(`O logo não foi enviado (${falha instanceof Error ? falha.message : "erro"}). Envie na aba Personalização.`);
        }
      }
      setResultado({ dados, avisos });
      onCriada();
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível criar a empresa.");
    } finally {
      setSalvando(false);
    }
  }

  if (resultado) {
    const { dados, avisos } = resultado;
    return (
      <Modal open={open} onClose={fechar} maxWidthClassName="max-w-xl">
        <div className="flex max-h-[85vh] flex-col gap-4 overflow-y-auto">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-fg">Empresa criada</h2>
              <p className="mt-0.5 text-xs text-fg-muted">
                {dados.empresa.nome} · slug <span className="font-mono">{dados.empresa.slug}</span> · Ativa
              </p>
            </div>
          </div>

          <SenhaTemporariaAviso slug={dados.empresa.slug} urlAcesso={dados.urlAcesso} email={dados.gestor.email} senha={dados.senhaTemporaria} />

          <p className="text-xs text-fg-muted">
            Gestor: <span className="font-semibold text-fg">{dados.gestor.nome}</span>. No primeiro acesso o servidor o obriga a criar a senha pessoal em{" "}
            <span className="font-mono">/e/{dados.empresa.slug}/trocar-senha-inicial</span>.
          </p>

          {avisos.length > 0 && (
            <ul role="alert" className="flex list-disc flex-col gap-1 rounded-xl border border-amber-300/60 bg-amber-50 py-2.5 pl-7 pr-3 text-xs text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
              {avisos.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          )}

          <p className="text-xs text-fg-muted">
            Você continua na Gestão: nenhuma sessão da empresa foi aberta e ninguém foi impersonado. O acesso da empresa é pelo endereço acima, com o usuário e a senha temporária do Gestor.
          </p>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const id = dados.empresa.id;
                reiniciar();
                onClose();
                router.push(`/gestao/empresas/${id}`);
              }}
            >
              Abrir empresa na Gestão
            </Button>
            <Button type="button" onClick={fechar}>
              Concluir
            </Button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={fechar} maxWidthClassName="max-w-2xl">
      <form onSubmit={enviar} noValidate className="flex max-h-[85vh] flex-col gap-4 overflow-y-auto">
        <div>
          <h2 className="text-base font-semibold text-fg">Nova empresa</h2>
          <p className="mt-1 text-xs text-fg-muted">
            Cria a empresa (ativa), a identidade visual e o primeiro Gestor. Ao salvar, o ambiente fica pronto em <span className="font-mono">/e/{rascunho.slug.trim() || "slug"}/login</span>.
          </p>
        </div>

        <SecaoDadosEmpresa
          rascunho={rascunho}
          erros={erros}
          mostrarErros={tentou}
          atualizar={atualizar}
          desabilitado={salvando}
          aoEditarSlug={(valor) => {
            setSlugEditado(true);
            setRascunho((atual) => ({ ...atual, slug: valor }));
          }}
        />
        <SecaoIdentidadeVisual
          rascunho={rascunho}
          erros={erros}
          mostrarErros={tentou}
          atualizar={atualizar}
          desabilitado={salvando}
          logo={logo}
          erroLogo={erroLogo}
          aoEscolherLogo={(arquivo) => void escolherLogo(arquivo)}
        />
        <SecaoAcessoInicial rascunho={rascunho} erros={erros} mostrarErros={tentou} atualizar={atualizar} desabilitado={salvando} />

        {erro && (
          <p role="alert" className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-2.5 text-xs font-medium text-danger">
            {erro}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" disabled={salvando} onClick={fechar}>
            Cancelar
          </Button>
          <Button type="submit" disabled={salvando}>
            {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} {salvando ? "Criando…" : "Criar empresa"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
