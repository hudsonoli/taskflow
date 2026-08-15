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

## 4. `codigo_interno` — quais domínios ainda precisam dele

**Origem:** microfase 2D.1.

`codigo_interno` nasceu como "chave estável de importação": permite a um importador localizar
um registro sem depender do UUID, que muda a cada ambiente. Isso só faz sentido **onde há
importação**.

A decisão de arquitetura de 2026-08-09 fixou que as únicas importações por XLSX serão
Departamentos, Usuários, Clientes, Fornecedores, Grupos de Cliente, Categorias, Peças e
Modelos de Workflow. **Projetos e Demandas nascem vazios.**

| Domínio | `codigo_interno` | Situação |
|---|---|---|
| Departamento, Equipe, GrupoCliente, Cliente, Fornecedor | **mantido** | serão importados — a chave tem função |
| **Projeto** | **removido em 2D.1** | sem importação, era cópia literal do `codigo_referencia` |
| **Demanda** | **nunca terá** | mesma razão |

Não há pendência aberta aqui — o registro existe para que ninguém reintroduza o campo por
simetria ao criar um domínio novo. **Antes de acrescentar `codigo_interno`, pergunte se
aquele domínio será importado.** Se não for, o campo é peso morto com UNIQUE e índice.

---

## 5. Pausa automática por fim de expediente

**Aberta.** Precisa de um job no backend.

Até a Fase 2E.1, `AppDataContext.tsx` mantinha um `setInterval` de 20 segundos que, fora do
expediente, mudava toda demanda `em_execucao` para `pausada` e escrevia uma linha em
`demanda.historico[]` assinada como "Sistema".

Isso foi **removido**, por dois motivos independentes:

1. `historico[]` não tem tabela nesta fase — a linha não teria onde ser gravada;
2. a regra só rodava com alguém logado e a aba aberta. Ninguém trabalhando às 19h significava
   nenhuma pausa registrada; duas abas abertas, duas execuções concorrentes.

O que **entrou no lugar**: `app/core/expediente.py` recusa a *entrada* em `em_execucao` fora
do horário, com 409 `FORA_DE_EXPEDIENTE` — validação no servidor, que nenhum `curl` contorna.

O que **falta**: pausar trabalho **já em curso** quando o expediente termina. É trabalho
periódico de servidor (job agendado), não de navegador. Enquanto não existir, uma tarefa
iniciada às 18h55 permanece `em_execucao` durante a noite.

Relacionado: `RegraExpediente` ainda é constante em `app/core/expediente.py`, não tabela — a
janela não é editável pela interface. A assinatura já recebe a regra como argumento, então
quando houver tabela muda quem produz `REGRA_PADRAO`, não quem a consome.

---

## 6. `criado_por` fora do escopo-base do operador

**Aberta.** Decisão de produto, não defeito de implementação.

A tabela de escopo aprovada define `operador` como *responsável **ou** departamento*;
`criado_por` entra apenas no escopo de Atendimento. A consequência observável:

> Um operador **sem departamento** que cria uma demanda **sem se atribuir** recebe 201 e, no
> instante seguinte, 404 no mesmo id.

Está fixado em
`backend/tests/test_demanda.py::test_operador_criador_sem_vinculo_perde_a_demanda_de_vista`
para que qualquer mudança de comportamento seja deliberada.

Duas saídas possíveis, ambas para a Fase 2E.5: incluir `criado_por` no escopo-base de todo
mundo, ou fazer a interface atribuir o criador como responsável por padrão. A primeira muda a
regra; a segunda muda o formulário. Não foi decidido.

---

## 9. `/uploads/**` é servido como estático, sem autenticação

**Aberta.** Exposição conhecida, deixada deliberadamente para uma decisão sua.

`app/main.py` monta `StaticFiles(directory="uploads")` em `/uploads`. Os **endpoints** de
arquivo (`/demandas/{codigo}/uploads`) passaram a exigir autenticação e escopo da própria
Demanda, mas o **conteúdo** continua acessível por URL direta: quem souber
`/uploads/T26000001/arquivo.pdf` baixa o arquivo sem token.

Não foi corrigido junto porque muda como a interface carrega imagem e download —
`resolveArquivoUrl` em `frontend/src/lib/api.ts` monta `<img src>` apontando para esse
caminho. A correção real é servir o arquivo por um endpoint autenticado (streaming com
checagem de escopo) e abandonar o mount estático.

Baixo risco **hoje**, porque `arquivos` não tem persistência na Fase 2E.1 e a interface não
oferece upload — a pasta nasce vazia. Vira risco real em 2E.3, quando o upload voltar.

---

## 10. `GET /sessoes-trabalho/horas` reclassifica sessões antigas quando um usuário muda de departamento

**Aberta.** Limitação conhecida e aceita nesta fase — documentada, não corrigida.

Uma sessão conta para o agregado de horas de um departamento (`SessaoTrabalhoRepository.horas_departamento`)
quando `sessao.departamento_id` aponta pra ele **OU** quando o usuário responsável pela sessão
pertence **atualmente** a ele (`usuarios.departamento_id`, lido no momento da consulta — não
uma foto do departamento de quando a sessão aconteceu).

Consequência: se um usuário muda de departamento, as sessões antigas dele que não têm
`departamento_id` próprio (a maioria — esse campo só é preenchido quando a sessão nasce sem
usuário) migram de classificação junto. O agregado do departamento novo passa a contar horas
que, na época, foram de outro departamento; o antigo deixa de contar.

Não há tabela de histórico de lotação por período nesta fase — não é possível reconstruir "de
qual departamento este usuário era, na data desta sessão" sem criar esse histórico. A regra
usa o vínculo atual porque é o único dado disponível, e é a mesma regra já aprovada para
"colaborador estrutural do departamento" (`usuarios.departamento_id`) usada em
`app/core/escopo.py::pode_consultar_horas_departamento` e em
`MeuDepartamentoView.tsx::colaboradoresOptions`.

**Não resolver isso agora.** Se um histórico de lotação por período for criado no futuro (para
outro motivo), revisitar `horas_departamento` para usar o departamento vigente na data da
sessão, não o atual.

Referências:
`backend/app/repositories/sessao_trabalho_repository.py::horas_departamento`
`backend/app/schemas/sessao_trabalho.py::SessaoTrabalhoHorasRead` (docstring com a mesma nota)

---

## Referências

- [padrao-arquivamento.md](padrao-arquivamento.md) — soft-delete, motivo obrigatório, conflito-arquivado
- [padrao-entidades-externas.md](padrao-entidades-externas.md) — identidade em entidade externa e alerta de duplicidade
- `backend/app/core/busca.py` — regra única de interpretação do termo de busca
- `frontend/src/lib/formatarReferencia.ts` — regra única de apresentação das entidades numeradas
