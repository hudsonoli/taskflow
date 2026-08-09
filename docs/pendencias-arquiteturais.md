# Pendências arquiteturais

> Divergências **conhecidas e aceitas** entre domínios já migrados. Cada uma foi identificada
> durante uma fase, avaliada, e deixada de fora dela de propósito — porque corrigir no lugar
> onde apareceu significaria mexer em domínios que a fase não tinha mandato para tocar.
>
> Este arquivo existe para que uma divergência deliberada não seja lida depois como descuido,
> e para que a padronização aconteça de uma vez, com decisão explícita, em vez de por
> imitação acidental do domínio que alguém abriu primeiro.

Regra geral: **padronização é decisão global.** Nenhum item abaixo deve ser resolvido só no
domínio em que foi notado.

---

## 1. Motivo de arquivamento composto apenas por espaços

**Origem:** Fase 2C (Fornecedor).

O padrão de arquivamento exige motivo obrigatório
([padrao-arquivamento.md](padrao-arquivamento.md)), e todos os schemas o declaram com
`min_length=1`. Só que `min_length` conta **caracteres**, e `"   "` tem três — passa. O efeito
é que a obrigatoriedade pode ser contornada sem que ninguém perceba, gravando um motivo vazio
num registro cujo arquivamento é permanente.

Estado atual:

| Domínio | `"   "` como motivo | Desde |
|---|---|---|
| **Fornecedor** | **rejeitado (422)** — validador com `strip()` em `FornecedorArquivar` | Fase 2C |
| **Projeto** | **rejeitado (422)** — validador com `strip()` em `ProjetoArquivar` | Fase 2D |
| Cliente | aceito | — |
| Usuário | aceito | — |
| Departamento | aceito | — |
| Equipe | aceito | — |

Placar atual: **2 rejeitam, 4 aceitam.**

Os dois divergentes não são desvio de rota: cada fase exigia explicitamente motivo
obrigatório, e entregar o contrário do pedido seria pior que a inconsistência. Projeto seguiu
Fornecedor por ser o padrão mais recente e mais correto — copiar o comportamento permissivo
de Cliente só para "manter simetria" teria propagado o problema em vez de contê-lo.

Os quatro restantes **continuam intocados de propósito**: alterá-los dentro de uma fase de
domínio seria ampliar escopo sem mandato. A cada nova fase o desequilíbrio cresce, e é isso
que torna a padronização cada vez mais urgente.

**A resolver numa microfase de padronização:** aplicar a mesma validação a Cliente, Usuário,
Departamento e Equipe — ou, se a decisão for outra, remover a de Fornecedor e Projeto. O que
não pode permanecer é a diferença silenciosa.

Referências:
`backend/app/schemas/fornecedor.py` → `FornecedorArquivar.motivo_nao_pode_ser_so_espaco`
`backend/app/schemas/projeto.py` → `ProjetoArquivar.motivo_nao_pode_ser_so_espaco`

---

## 2. Montagem do rótulo de referência no frontend

**Origem:** Fase 2C (Fornecedor).

`frontend/src/lib/formatarReferencia.ts` estabelece que nenhum componente deve montar o
rótulo à mão nem **fazer substring de `codigoReferencia`**. O número exibido tem de vir
pronto da API, em `sequencialReferencia`.

O aviso de possível duplicidade de Cliente contraria a própria regra:

```tsx
// frontend/src/components/clientes/PossiveisDuplicidadesAviso.tsx
sequencialReferencia: Number(item.codigoReferencia.slice(3))
```

A causa não é o componente: é o schema. `PossivelDuplicidadeCliente` não carrega
`sequencialReferencia`, então o frontend não tinha de onde tirar o número. Em Fornecedor isso
foi corrigido **na origem** — `PossivelDuplicidadeFornecedor` traz o campo, e o componente
apenas o repassa.

**A resolver numa microfase de padronização:** acrescentar `sequencialReferencia` a
`PossivelDuplicidadeCliente` e eliminar o `slice(3)`, deixando todos os domínios com o mesmo
caminho — backend emite o número, frontend só formata. Vale revisar, na mesma passada, se
existe outro ponto recortando código de referência.

---

## 3. Comprimento mínimo da busca textual

**Origem:** Fase 2C (Fornecedor), observado em validação manual.

Buscar `"2"` devolve praticamente toda a base. **Não é o incidente da Fase 2B** — não há
extração de dígitos nem filtro de documento envolvido. É casamento textual legítimo: todo
`codigoReferencia` contém os dígitos do ano (`C26…`, `F26…`), e a busca textual cobre o
código de propósito, para que `C26000025` seja pesquisável.

A regra que protege contra o incidente continua íntegra e é a de
`backend/app/core/busca.py`: só o **filtro de documento** tem mínimo (`MIN_DIGITOS_DOCUMENTO
= 4`). A busca **textual** não tem mínimo nenhum.

Comportamento mantido conscientemente. As duas saídas possíveis:

- **manter como está** — assumindo que um termo de um caractere varre a base, o que é
  previsível e não silencioso; ou
- **estabelecer mínimo para a busca textual** (2 ou 3 caracteres), aplicado a **todos** os
  domínios de uma vez, dentro de `app/core/busca.py`.

**Não decidir isso por domínio.** A regra mora num módulo único justamente para não voltar a
divergir entre repositories — foi a divergência que causou o incidente.

---

## Referências

- [padrao-arquivamento.md](padrao-arquivamento.md) — soft-delete, motivo obrigatório, conflito-arquivado
- [padrao-entidades-externas.md](padrao-entidades-externas.md) — identidade em entidade externa e alerta de duplicidade
- `backend/app/core/busca.py` — regra única de interpretação do termo de busca
- `frontend/src/lib/formatarReferencia.ts` — regra única de apresentação das entidades numeradas
