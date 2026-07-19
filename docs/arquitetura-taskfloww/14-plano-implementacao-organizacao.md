# 1. Objetivo

Este documento organiza a execução incremental do épico **TF-ORG-002 —
Implementação do Domínio Organizacional**.

Ele estabelece a ordem das entregas, suas dependências e as condições gerais
de execução. Não altera decisões arquiteturais, não cria requisitos, não
autoriza implementações e não determina soluções físicas.

O
`docs/arquitetura-taskfloww/13-dominio-organizacional-oficial.md`
permanece como referência conceitual oficial e deve ser consultado antes de
cada subtarefa. Este plano não o substitui.

# 2. Escopo

## Dentro do escopo

O TF-ORG-002 abrange:

- convergência da implementação atual com a arquitetura organizacional
  oficial;
- Departamentos;
- Equipes e sua relação organizacional aprovada;
- Cargos;
- vínculos de Usuários com Departamentos;
- vínculos de Usuários com Equipes;
- vínculos de Usuários com Cargos;
- principalidade independente dos vínculos;
- vigência e preservação de histórico organizacional;
- responsabilidades organizacionais definidas no documento 13;
- contexto organizacional necessário aos módulos consumidores;
- integração gradual entre domínio, backend e frontend;
- isolamento por Empresa;
- separação entre organização e autorização RBAC;
- convergência ou retirada controlada de estruturas legadas incompatíveis.

## Fora do escopo

- Squads;
- gestor direto;
- organograma;
- aprovações;
- férias;
- ausências;
- substituições;
- funcionalidades experimentais;
- novos conceitos organizacionais não aprovados no documento 13;
- folha de pagamento;
- remuneração;
- benefícios;
- ponto eletrônico;
- recrutamento;
- admissão ou desligamento trabalhista;
- mudanças na arquitetura oficial;
- ampliação de RBAC não exigida pela integração organizacional;
- reformulações gerais de módulos não necessárias à etapa em execução.

# 3. Dependências

- Usuários;
- Departamentos;
- Equipes;
- Cargos;
- autenticação;
- RBAC;
- Workflow;
- Projetos;
- Dashboard;
- Agenda;
- Kanban;
- Central de Tráfego;
- Relatórios;
- auditoria e histórico;
- documentação técnica e operacional.

A lista identifica impactos potenciais, não autoriza alterações. Cada
subtarefa deve confirmar suas dependências efetivas e interromper a execução
se uma descoberta exigir ampliação de escopo.

# 4. Princípios de Implementação

- Implementar incrementalmente.
- Não misturar etapas.
- Alterações pequenas e revisáveis.
- Compatibilidade antes da remoção.
- Arquitetura antes do código.

# 5. Ordem oficial de implementação

As etapas devem ser executadas na sequência abaixo.

## TF-ORG-002.1 — Convergência do modelo existente

### Objetivo

Identificar e preparar a convergência entre a implementação existente e a
arquitetura oficial, sem alterar silenciosamente contratos ou comportamentos.

### Dependências

Usuários, Departamentos, Equipes, Cargos, RBAC e documentação existente.

### Resultado esperado

Implementação e divergências conhecidas, com a convergência organizada e sem
decisões implícitas.

## TF-ORG-002.2 — Departamentos

### Objetivo

Consolidar Departamentos como estrutura organizacional da Empresa e preparar
seu uso consistente pelas etapas seguintes.

### Dependências

TF-ORG-002.1, Empresa, Usuários, Equipes, RBAC e histórico organizacional.

### Resultado esperado

Departamentos alinhados ao documento 13, com isolamento preservado e aptos à
consolidação de Equipes.

## TF-ORG-002.3 — Equipes

### Objetivo

Consolidar Equipes e promover sua convergência para a direção arquitetural
oficial, preservando os usos operacionais existentes durante a transição.

### Dependências

TF-ORG-002.2, Empresa, Departamentos, Usuários, Workflow, Projetos, Kanban,
Agenda e Central de Tráfego.

### Resultado esperado

Equipes e sua relação organizacional alinhadas ao documento 13, com
compatibilidade operacional preservada.

## TF-ORG-002.4 — Cargos

### Objetivo

Consolidar Cargos como conceito organizacional separado de Perfil RBAC e de
responsabilidades.

### Dependências

TF-ORG-002.1, Empresa, Usuários, RBAC e relatórios organizacionais.

### Resultado esperado

Cargos separados de Perfil e autorização, prontos para a consolidação dos
vínculos.

## TF-ORG-002.5 — Vínculos

### Objetivo

Consolidar a participação de Usuários na organização por vínculos, incluindo
principalidade, vigência e preservação de histórico conforme o documento 13.

### Dependências

TF-ORG-002.2, TF-ORG-002.3, TF-ORG-002.4, Usuários, Departamentos, Equipes,
Cargos, Empresa, auditoria, histórico e RBAC.

### Resultado esperado

Vínculos e principalidades alinhados ao documento 13, com vigência, histórico
e isolamento preservados.

## TF-ORG-002.6 — Contexto organizacional

### Objetivo

Disponibilizar uma interpretação consistente do contexto organizacional para
os fluxos que dependem de Usuário, Departamento, Equipe, Cargo e
responsabilidade.

### Dependências

TF-ORG-002.5, Usuários, Departamentos, Equipes, Cargos, RBAC e módulos
operacionais consumidores.

### Resultado esperado

Contexto organizacional consistente, com isolamento e separação de RBAC
preservados, apto à integração de backend.

## TF-ORG-002.7 — Integração Backend

### Objetivo

Integrar as capacidades organizacionais aprovadas aos fluxos de backend,
preservando contratos, isolamento, validações e comportamento esperado.

### Dependências

TF-ORG-002.6, capacidades organizacionais das etapas anteriores,
autenticação, RBAC, consumidores existentes, auditoria e tratamento de erros.

### Resultado esperado

Capacidades disponíveis aos consumidores previstos, com compatibilidade
preservada e prontas para integração de frontend.

## TF-ORG-002.8 — Integração Frontend

### Objetivo

Integrar o contexto organizacional real às interfaces aprovadas, removendo
dependências de dados simulados somente quando houver fonte oficial
disponível.

### Dependências

TF-ORG-002.7, Usuários, Departamentos, Equipes, Cargos, RBAC, módulos
operacionais com interface e contratos disponibilizados pelo backend.

### Resultado esperado

Interfaces consumindo fontes oficiais, sem relações inventadas e com os
legados aptos à retirada controlada.

## TF-ORG-002.9 — Legados

### Objetivo

Concluir a convergência por meio da retirada controlada de estruturas,
contratos, dados simulados e interpretações legadas que tenham substitutos
oficiais validados.

### Dependências

TF-ORG-002.8, todas as etapas anteriores, documentação, testes de regressão,
módulos consumidores, histórico e auditoria.

### Resultado esperado

Legados do escopo sem consumidores ativos e substitutos validados, com
compatibilidade e histórico preservados.

# 6. Estratégia de migração

A convergência deve ocorrer de forma incremental:

```text
arquitetura oficial
        ↓
diagnóstico da implementação atual
        ↓
classificação das divergências
        ↓
entregas compatíveis e verificáveis
        ↓
adoção pelos consumidores
        ↓
retirada controlada dos legados
```

Cada etapa deve consultar a arquitetura, confirmar o estado atual, separar
divergência conceitual de dívida técnica, identificar consumidores, definir
uma entrega pequena e reversível, preservar dados e histórico e registrar
diferenças ainda não resolvidas.

A transição não deve substituir todo o domínio de uma única vez. Estruturas
existentes devem permanecer disponíveis enquanto forem necessárias para
compatibilidade e somente podem ser retiradas após a adoção comprovada do
comportamento oficial.

Uma descoberta que contradiga o documento 13 deve ser submetida a revisão
formal, nunca resolvida por alteração silenciosa ou adaptação local.

Este plano define a sequência da convergência, não sua implementação física.

# 7. Estratégia de compatibilidade

A compatibilidade deve ser tratada como requisito de cada etapa.

Para preservar contratos e comportamento:

- contratos devem ser inventariados antes da alteração;
- contratos devem permanecer estáveis durante a transição aprovada;
- semânticas novas não devem ser introduzidas implicitamente;
- fluxos fora do escopo devem permanecer inalterados;
- cada entrega deve funcionar com o estado das etapas anteriores;
- consumidores devem migrar em unidades verificáveis;
- períodos de convivência devem ser explícitos;
- legados somente devem ser retirados após a convergência dos consumidores;
- autenticação, isolamento por Empresa e RBAC devem permanecer válidos;
- nenhuma camada deve inventar campos ou relacionamentos ausentes.

Antes de implementar uma etapa, deve existir uma forma aprovada de restaurar
o comportamento funcional anterior caso a entrega não seja validada.

O rollback funcional deve preservar contratos ainda utilizados, integridade,
histórico, isolamento e autorização. Ele não autoriza apagar histórico nem
restaurar uma interpretação incompatível com a arquitetura como solução
definitiva.

# 8. Critérios de aceite

Uma etapa do TF-ORG-002 somente pode ser considerada concluída quando:

- objetivo e domínio oficial estiverem atendidos;
- decisões e regras do documento 13 estiverem preservadas;
- isolamento por Empresa estiver preservado;
- RBAC não tiver sofrido regressão;
- contratos e comportamentos fora do escopo permanecerem compatíveis;
- não houver regressões conhecidas;
- testes e validações aplicáveis estiverem aprovados;
- rollback funcional tiver sido avaliado;
- divergências remanescentes estiverem registradas;
- documentação e status relevantes estiverem atualizados;
- alterações estiverem limitadas ao escopo aprovado;
- a etapa tiver sido revisada e homologada pelo fluxo oficial.

A conclusão técnica não substitui a homologação. Da mesma forma, a
homologação visual não substitui validações de domínio, isolamento,
autorização e compatibilidade.

# 9. Riscos

## Regressões de RBAC

Relações organizacionais podem ser confundidas com autorização.

Mitigação: revisar autenticação e RBAC em toda etapa que exponha ou altere
contexto organizacional.

## Compatibilidade

Camadas podem divergir, contratos podem mudar prematuramente e legados podem
ser removidos antes da convergência de seus consumidores.

Mitigação: inventariar contratos, consumidores, identidades e comportamentos;
validar cada transição e manter rollback funcional.

## Dependências ocultas

Módulos operacionais podem depender de campos, mocks ou comportamentos não
documentados.

Mitigação: pesquisar consumidores e interromper a implementação se uma
dependência exigir ampliação não aprovada.

## Perda de histórico

A convergência pode tratar encerramento como exclusão ou ignorar vigência.

Mitigação: validar histórico e ciclo de vida em toda etapa aplicável.

## Escopo excessivo

Uma etapa pode acumular domínio, integração e interface em uma única entrega
difícil de validar.

Mitigação: dividir o trabalho em alterações pequenas e interromper quando uma
descoberta exigir novo escopo.

# 10. Checklist obrigatório antes de cada implementação

Antes de iniciar qualquer tarefa do TF-ORG-002, confirmar:

- [ ] arquitetura oficial consultada;
- [ ] escopo aprovado;
- [ ] dependências analisadas;
- [ ] impacto conhecido;
- [ ] critérios de aceite definidos;
- [ ] rollback funcional previsto;
- [ ] branch correta;
- [ ] revisão obrigatória prevista.

Se qualquer item obrigatório não puder ser confirmado, a implementação não
deve iniciar até que a lacuna seja resolvida ou formalmente tratada no escopo.

# 11. Fluxo oficial de execução

O fluxo oficial do projeto é:

```text
Hudson
   ↓
ChatGPT
(arquitetura e revisão)
   ↓
Claude
(análise técnica)
   ↓
Codex
(implementação)
   ↓
ChatGPT
(revisão)
   ↓
Hudson
(homologação)
```

As responsabilidades do fluxo são:

- **Hudson — direcionamento:** define prioridade, contexto e aprovação final;
- **ChatGPT — arquitetura:** consolida a decisão arquitetural e o escopo
  conceitual;
- **Claude — análise técnica:** avalia a implementação existente, impactos,
  lacunas, dependências e plano técnico;
- **Codex — implementação:** altera somente o escopo aprovado, valida a
  entrega e apresenta o resultado para revisão;
- **ChatGPT — revisão:** verifica aderência à arquitetura, ao escopo e aos
  critérios de aceite;
- **Hudson — homologação:** decide pela aceitação da entrega e pelos próximos
  passos.

Regras obrigatórias:

- nunca desenvolver diretamente na branch `main`;
- nenhuma implementação deve iniciar sem arquitetura aprovada;
- nenhuma implementação deve iniciar sem escopo técnico aprovado;
- uma tarefa não deve modificar arquivos fora do escopo;
- descobertas que ampliem o escopo devem interromper a implementação e
  retornar para análise;
- documentação e implementação devem evoluir juntas;
- validação e revisão devem ocorrer antes de commit;
- commit e push dependem de autorização explícita;
- uma etapa somente deve avançar quando seus critérios de conclusão forem
  atendidos.
