# 13 — Domínio Organizacional Oficial

> Épico: **TF-ORG-001 — Consolidação do Domínio Organizacional**
>
> Status: **referência conceitual oficial**
>
> Natureza: documento de domínio. Não é DDL, migration, contrato OpenAPI,
> especificação de interface nem autorização para implementação.

## 1. Objetivo

Este documento define o domínio organizacional oficial do TaskFloww V2.

Sua finalidade é oferecer uma única referência para todas as futuras decisões
de banco de dados, backend, API, BFF, frontend, permissões, dashboards,
Kanban, Agenda, Projetos, Central de Tráfego e Relatórios que dependam da
estrutura interna de uma Empresa.

Este documento:

- consolida as decisões válidas presentes na documentação anterior;
- estabelece vocabulário oficial;
- separa identidade, estrutura organizacional, responsabilidade e autorização;
- define entidades, relacionamentos e cardinalidades;
- registra divergências entre o domínio recomendado e a implementação atual;
- explicita assuntos que ainda dependem de decisão;
- organiza um mapa incremental de implementação.

O objetivo não é reproduzir o código existente. O código atual é analisado
somente para identificar compatibilidades, lacunas e divergências.

### 1.1 Como ler este documento

Este documento separa três níveis:

| Nível | Conteúdo |
|---|---|
| Domínio | conceitos, relações, cardinalidades, responsabilidades e regras de negócio |
| Arquitetura | princípios e consequências técnicas necessárias para preservar o domínio |
| Implementação | escolhas físicas, contratos, componentes e estratégia de entrega |

As seções de princípios, vocabulário, entidades, relacionamentos e regras de
negócio são normativas para o domínio.

A seção de impacto técnico registra consequências arquiteturais sem escolher
soluções físicas.

O mapa de implementação organiza a evolução futura, mas cada etapa deve
decidir seus próprios artefatos e contratos antes de alterar o sistema.

## 2. Autoridade e precedência

Este documento passa a ser a referência conceitual oficial do domínio
organizacional do TaskFloww.

Os demais documentos continuam válidos em seus respectivos contextos
históricos, diagnósticos, técnicos ou operacionais. Eles devem convergir para
esta referência ao longo das próximas análises e implementações.

Quando uma divergência conceitual for identificada:

- este documento orienta a decisão de domínio;
- o documento divergente não é automaticamente invalidado;
- a implementação existente não é automaticamente alterada;
- a convergência deve ser planejada, aprovada e validada em tarefa própria;
- incompatibilidades devem permanecer registradas até serem resolvidas.

Uma revisão conceitual futura pode alterar esta referência, desde que seja
explícita, justificada e aprovada.

## 3. Escopo

### 3.1 Dentro do escopo

Fazem parte do domínio organizacional:

- Empresa;
- Departamento;
- Equipe;
- Squad, apenas como conceito transversal ainda pendente de detalhamento;
- Usuário;
- Cargo/Função;
- vínculo de Usuário com Departamento;
- vínculo de Usuário com Equipe;
- vínculo de Usuário com Cargo;
- Departamento principal;
- Equipe principal;
- Cargo principal;
- responsabilidade de Head;
- responsabilidade de Gestor organizacional;
- responsabilidade de Líder de Equipe;
- vigência e histórico dos vínculos;
- isolamento por Empresa;
- relação da organização com RBAC;
- efeitos da organização nos módulos operacionais.

### 3.2 Fora do escopo desta consolidação

Este documento não define:

- folha de pagamento;
- remuneração;
- benefícios;
- ponto eletrônico;
- férias;
- ausências;
- substituições temporárias;
- cadeia completa de aprovações;
- organograma hierárquico;
- avaliação de desempenho;
- recrutamento;
- admissão trabalhista;
- desligamento trabalhista ou obrigações legais;
- usuários externos de portal de Cliente;
- regras completas de Squad;
- gestor direto individual;
- DDL ou detalhes físicos de banco;
- formatos finais de endpoints;
- telas ou componentes.

Os assuntos organizacionais excluídos, mas relacionados, aparecem em
**Pontos pendentes de decisão**.

## 4. Princípios arquiteturais

### 4.1 Empresa é a raiz de isolamento

Empresa é a raiz de tenant do TaskFloww.

Todo cadastro organizacional e todo vínculo organizacional pertencem a uma
única Empresa.

Um relacionamento entre registros de Empresas diferentes é inválido, mesmo
quando os identificadores informados existirem individualmente.

Agência, filial, marca ou unidade operacional não substitui Empresa como raiz
de isolamento.

### 4.2 Organização não é autorização

Departamento, Equipe, Squad, Cargo, Head, Gestor e Líder descrevem posição,
participação ou responsabilidade organizacional.

Eles não concedem permissões automaticamente.

Permissões continuam sendo controladas por RBAC. Uma regra de autorização
pode usar o contexto organizacional para limitar escopo, mas a existência do
vínculo, isoladamente, não autoriza uma ação.

Exemplos:

- possuir o cargo “Diretor de Arte” não concede permissão para editar usuários;
- ser Head de Marketing não concede automaticamente permissão administrativa;
- liderar uma Equipe não concede acesso a dados financeiros;
- participar de um Departamento não permite alterar o cadastro desse
  Departamento sem a permissão RBAC correspondente.

### 4.3 Responsabilidade não é perfil nem cargo

Head, Gestor organizacional, Líder e Responsável são responsabilidades.

Uma responsabilidade:

- é atribuída explicitamente;
- tem escopo conhecido;
- pode possuir vigência;
- deve possuir histórico;
- não deve ser inferida apenas pelo nome do Cargo;
- não deve ser inferida apenas pelo Perfil RBAC;
- não deve ser representada por texto livre no Usuário.

### 4.4 Relacionamentos usam identidade

Relacionamentos organizacionais usam IDs estáveis.

Não devem ser usados:

- nome de Departamento como chave;
- nome de Equipe como chave;
- Cargo digitado livremente no Usuário;
- Squad como string no cadastro do Usuário;
- e-mail do Usuário como chave estrangeira;
- título visual como substituto de vínculo persistido.

Nomes e siglas são atributos de apresentação e busca. IDs são usados para
integridade e relacionamento.

### 4.5 Vínculos preservam história

Participações organizacionais não devem ser apagadas fisicamente em operação
normal.

Quando um vínculo termina:

- o registro histórico permanece;
- a vigência é encerrada;
- o status deixa de ser ativo;
- o motivo pode ser registrado;
- o ator responsável deve ser registrado quando a operação for autenticada;
- eventos de domínio devem representar a mudança.

### 4.6 A estrutura admite múltipla participação

O TaskFloww não presume que um Usuário pertença a uma única unidade.

Um Usuário pode:

- participar de vários Departamentos;
- possuir no máximo um Departamento principal ativo;
- participar de várias Equipes;
- possuir no máximo uma Equipe principal ativa;
- possuir vários Cargos;
- possuir no máximo um Cargo principal ativo.

Participação e principalidade são conceitos distintos.

## 5. Visão conceitual

A arquitetura oficial adotada pelo projeto segue esta direção:

```text
Empresa
├── Departamentos
│   ├── Equipes
│   │   └── vínculos com Usuários
│   ├── vínculos com Usuários
│   ├── Head
│   └── Gestores organizacionais
├── catálogo de Cargos
│   └── vínculos com Usuários
└── Squads transversais
    └── vínculos com Usuários
```

Essa representação não significa que Usuário “pertença” fisicamente a uma
Equipe de forma exclusiva. Usuário é uma entidade da Empresa e participa das
estruturas por meio de vínculos.

Também não significa que Cargo esteja abaixo do Usuário como entidade. Cargo
é um catálogo da Empresa e se relaciona com Usuários por vínculos.

## 6. Vocabulário Oficial

Os termos abaixo são as formas oficiais a serem usadas em requisitos,
documentação, contratos e interfaces. Termos semelhantes não devem ser
tratados como sinônimos sem qualificação.

| Termo oficial | Uso |
|---|---|
| Perfil RBAC | papel de autorização |
| Gestor RBAC | Usuário cujo Perfil RBAC é Gestor |
| Cargo | posição ou função profissional |
| Responsabilidade | atribuição organizacional explícita e contextual |
| Head | responsabilidade principal sobre Departamento |
| Gestor organizacional | responsabilidade adicional sobre Departamento |
| Líder | responsabilidade principal sobre Equipe |
| Equipe | agrupamento operacional com Departamento de referência |
| Departamento | unidade formal da Empresa |
| Squad | estrutura transversal ainda pendente de detalhamento |
| Responsável | Usuário atribuído a objeto ou ação específica |
| Principal | marcação preferencial dentro de uma categoria de vínculo |
| Vínculo | participação explícita entre entidades, com ciclo de vida |
| Usuário | pessoa operacional vinculada à Empresa |
| Empresa | raiz de isolamento organizacional |

“Gestor” sem qualificação deve ser evitado quando houver risco de confundir
Gestor RBAC, Gestor organizacional e gestor direto.

As definições detalhadas aparecem a seguir.

### 6.1 Empresa

Raiz de isolamento organizacional e de dados.

Uma Empresa possui seus próprios Usuários, Departamentos, Equipes, Cargos e,
quando definidos, Squads.

Registros de uma Empresa não podem ser associados a registros de outra.

### 6.2 Departamento

Unidade formal e relativamente estável da estrutura da Empresa.

Representa uma área organizacional, como:

- Marketing;
- Atendimento;
- Criação;
- Mídia;
- Produção;
- Tecnologia.

Departamento não é Equipe e não é Squad.

### 6.3 Equipe

Agrupamento operacional de trabalho.

A arquitetura oficial adotada pelo projeto estabelece que toda Equipe possui
exatamente um Departamento de referência vigente.

Essa regra define o estado arquitetural desejado e não afirma que a
implementação atual já o represente.

Uma Equipe pode reunir:

- membros cujo Departamento principal ou secundário coincide com o
  Departamento da Equipe;
- membros convidados de outros Departamentos, quando essa exceção for
  registrada explicitamente.

Equipe é adequada para distribuição de trabalho, capacidade, liderança
operacional e acompanhamento de execução.

### 6.4 Squad

Estrutura transversal e multidisciplinar que pode reunir Usuários de vários
Departamentos e Equipes.

Squad não pertence obrigatoriamente a um Departamento.

Este documento reconhece Squad como conceito distinto, mas não define seu
ciclo de vida, liderança, cardinalidades operacionais, principalidade ou
regras de gestão. Esses pontos permanecem pendentes.

### 6.5 Cargo

Posição ou função profissional configurável pela Empresa.

Exemplos:

- Diretor de Arte;
- Redator;
- Analista de Mídia;
- Executivo de Atendimento;
- Desenvolvedor;
- Coordenador de Produção.

Cargo:

- não é Perfil RBAC;
- não concede permissão;
- não representa automaticamente liderança;
- pode variar entre Empresas;
- não deve ser enum global;
- não deve ser texto livre no Usuário.

### 6.6 Perfil

Papel de autorização usado pelo RBAC.

Perfis definem uma base de acesso ao sistema. Eles não descrevem integralmente
a posição profissional nem a responsabilidade organizacional do Usuário.

“Gestor” como nome de Perfil e “Gestor organizacional” são conceitos
distintos. O termo deve ser qualificado em contratos e documentação.

### 6.7 Permissão

Autorização para executar uma ação sobre um recurso.

Permissões pertencem ao domínio de segurança e RBAC.

O contexto organizacional pode limitar o escopo de uma permissão, mas não
substitui a permissão.

### 6.8 Head

Responsabilidade principal sobre um Departamento.

Head:

- não é Cargo;
- não é Perfil;
- não é entidade independente;
- é uma atribuição explícita entre Usuário e Departamento;
- possui vigência e histórico;
- existe no máximo uma atribuição principal ativa por Departamento.

Um Usuário pode exercer responsabilidade de Head em mais de um Departamento,
desde que cada atribuição seja explícita.

A forma física de persistir e expor essa responsabilidade deve ser decidida
durante o épico TF-ORG. Este documento define sua semântica, não um model,
tabela ou contrato de API.

### 6.9 Gestor

Termo que precisa ser qualificado.

Pode significar:

1. **Perfil Gestor:** papel RBAC;
2. **Gestor organizacional:** responsabilidade adicional sobre um
   Departamento;
3. **Gestor direto:** relação individual de reporte, ainda não definida.

Este documento define apenas os dois primeiros conceitos. Gestor direto
permanece pendente.

### 6.10 Líder

Responsabilidade operacional principal sobre uma Equipe.

Líder:

- não é Cargo;
- não é Perfil;
- é atribuído explicitamente no escopo de uma Equipe;
- deve possuir vigência e histórico;
- não recebe permissões automaticamente.

Uma Equipe possui no máximo um Líder principal ativo. Outras
responsabilidades de coordenação podem existir separadamente, quando
formalizadas.

### 6.11 Responsável

Usuário designado para responder por um objeto ou ação em contexto específico.

Exemplos:

- responsável por Projeto;
- responsável por Demanda;
- responsável por etapa de Workflow;
- responsável por Cliente;
- responsável por aprovação.

Responsável não é sinônimo de Head, Líder, Gestor ou Cargo.

### 6.12 Usuário

Pessoa interna ou prestador com vínculo operacional com a Empresa, com ou sem
acesso ao sistema.

Usuário possui identidade organizacional própria e participa de
Departamentos, Equipes, Cargos e, futuramente, Squads por meio de vínculos.

Contato comercial de Cliente não se torna automaticamente Usuário.

## 7. Entidades

### 7.1 Empresa

#### Responsabilidade

- isolar os dados organizacionais;
- possuir os catálogos e estruturas;
- definir o contexto de unicidade;
- impedir vínculos entre tenants.

#### Dependências

Empresa não depende de outra entidade organizacional.

Todas as demais entidades organizacionais dependem de Empresa.

#### Regras

- deve possuir identidade estável;
- não é removida fisicamente em operação normal;
- inativação não pode deixar operações organizacionais em estado ambíguo;
- todos os vínculos associados devem preservar `empresa_id`.

### 7.2 Departamento

#### Responsabilidade

- representar estrutura formal;
- agrupar Equipes de referência;
- organizar participação de Usuários;
- possuir Head e Gestores organizacionais quando atribuídos;
- servir de dimensão para carga, pauta e relatórios.

#### Dependências

- pertence a uma Empresa;
- pode possuir várias Equipes;
- pode possuir vários Usuários vinculados;
- possui no máximo um Head principal ativo;
- pode possuir vários Gestores organizacionais ativos.

#### Regras

- nome e código devem ser únicos no escopo definido pela Empresa;
- pode ser ativo, inativo ou arquivado;
- não deve ser excluído fisicamente em operação normal;
- inativação deve tratar Equipes e vínculos ativos de forma explícita;
- um Departamento não contém outro Departamento até que hierarquia e
  organograma sejam formalmente decididos.

### 7.3 Equipe

#### Responsabilidade

- representar unidade operacional de execução;
- organizar membros;
- permitir liderança operacional;
- alimentar distribuição de trabalho e carga.

#### Dependências

- pertence a uma Empresa;
- possui exatamente um Departamento de referência vigente;
- possui vários vínculos com Usuários;
- possui no máximo um Líder principal ativo.

#### Regras

- uma Equipe não é um Departamento;
- uma Equipe não é uma Squad;
- mudança do Departamento de referência deve ser auditada;
- membros de outros Departamentos são exceções explícitas;
- inativação não apaga histórico de membros;
- uma Equipe inativa não aceita novos vínculos ativos.

### 7.4 Cargo

#### Responsabilidade

- representar função profissional configurável;
- oferecer classificação organizacional consistente;
- permitir filtros, relatórios e experiência contextual;
- evitar texto livre divergente.

#### Dependências

- pertence a uma Empresa;
- relaciona-se com Usuários por vínculos;
- não depende de Departamento ou Equipe.

#### Regras

- não concede permissão;
- não concede responsabilidade;
- pode ser compartilhado por vários Usuários;
- pode ser inativado sem apagar vínculos históricos;
- um Cargo inativo não pode receber novo vínculo ativo;
- nomes podem variar entre Empresas.

### 7.5 Usuário

#### Responsabilidade

- representar uma pessoa operacional da Empresa;
- concentrar identidade e dados básicos;
- participar das estruturas por vínculos;
- opcionalmente possuir acesso ao sistema.

#### Dependências

- pertence a uma Empresa;
- pode possuir vínculos com Departamentos;
- pode possuir vínculos com Equipes;
- pode possuir vínculos com Cargos;
- pode receber responsabilidades organizacionais.

#### Regras

- não armazena Departamento por nome;
- não armazena Equipe por nome;
- não armazena Cargo por texto livre;
- não armazena Head ou Líder como booleano;
- não armazena Squad como string;
- inativação preserva identidade e histórico;
- acesso ao sistema e participação organizacional são conceitos distintos.

### 7.6 Squad

Squad é reconhecida como entidade potencial da Empresa e estrutura
transversal.

Sua modelagem detalhada não é fechada por este documento.

Antes de implementação, devem ser decididos:

- objetivo operacional;
- ciclo de vida;
- liderança;
- tipos de membro;
- vigência;
- possibilidade de Squad principal;
- relação com Projeto, Cliente e Workflow;
- permissões e visibilidade.

## 8. Relacionamentos e cardinalidades

### 8.1 Empresa e Departamento

```text
Empresa 1 ─── 0..N Departamentos
Departamento 1 ─── 1 Empresa
```

Todo Departamento pertence exatamente a uma Empresa.

### 8.2 Departamento e Equipe

```text
Departamento 1 ─── 0..N Equipes
Equipe 1 ─── 1 Departamento de referência
```

Como arquitetura oficial adotada pelo projeto, toda Equipe ativa deve possuir
um Departamento de referência.

Essa relação ainda precisa convergir com a implementação atual.

Mudanças de Departamento devem ser explícitas e auditáveis.

### 8.3 Usuário e Departamento

```text
Usuário 1 ─── 0..N vínculos ─── 1 Departamento
Departamento 1 ─── 0..N vínculos ─── 1 Usuário
```

É uma relação N:N com entidade de vínculo.

O vínculo deve representar:

- Empresa;
- Usuário;
- Departamento;
- principalidade;
- status;
- início;
- fim;
- motivo de encerramento;
- ator de criação;
- ator de encerramento;
- timestamps técnicos.

Para cada Usuário:

- podem existir vários vínculos ativos com Departamentos diferentes;
- não pode haver dois vínculos ativos com o mesmo Departamento;
- pode existir no máximo um vínculo principal ativo;
- é permitido não haver Departamento principal durante cadastro,
  transição ou ausência de vínculo;
- consumidores devem tratar explicitamente a ausência de principal.

### 8.4 Usuário e Equipe

```text
Usuário 1 ─── 0..N vínculos ─── 1 Equipe
Equipe 1 ─── 0..N vínculos ─── 1 Usuário
```

É uma relação N:N com entidade de vínculo.

O vínculo deve representar:

- Empresa;
- Usuário;
- Equipe;
- papel operacional;
- principalidade;
- tipo de participação normal ou convidada;
- status;
- vigência;
- motivo e atores;
- timestamps técnicos.

Para cada Usuário:

- podem existir várias Equipes ativas;
- não pode haver dois vínculos ativos com a mesma Equipe;
- pode existir no máximo uma Equipe principal ativa;
- a Equipe principal pode estar ausente;
- pertencer à Equipe não altera automaticamente o Departamento principal.

### 8.5 Usuário e Cargo

```text
Usuário 1 ─── 0..N vínculos ─── 1 Cargo
Cargo 1 ─── 0..N vínculos ─── 1 Usuário
```

É uma relação N:N com entidade de vínculo.

Para cada Usuário:

- podem existir vários Cargos ativos;
- não pode haver dois vínculos ativos com o mesmo Cargo;
- pode existir no máximo um Cargo principal ativo;
- o Cargo principal pode estar ausente;
- Cargo não concede Perfil, Permissão ou responsabilidade.

### 8.6 Departamento e Head

```text
Departamento 1 ─── 0..1 Head principal ativo
Usuário 1 ─── 0..N responsabilidades de Head
```

No domínio, Head é uma responsabilidade com vigência entre Usuário e
Departamento. Não é um atributo derivado do Cargo nem do Perfil.

A escolha de como essa responsabilidade será persistida, consultada e
alterada pertence às etapas de arquitetura técnica e implementação do épico
TF-ORG.

Regras:

- no máximo um Head principal ativo por Departamento;
- um Usuário pode ser Head de vários Departamentos;
- o Usuário deve estar ativo e pertencer à mesma Empresa;
- o Usuário deve possuir vínculo ativo com o Departamento;
- Perfil e Cargo não tornam o Usuário Head automaticamente;
- atribuição e remoção exigem autorização RBAC;
- a troca deve ser auditável e transacional.

### 8.7 Departamento e Gestores organizacionais

```text
Departamento 1 ─── 0..N Gestores organizacionais
Usuário 1 ─── 0..N responsabilidades de gestão departamental
```

Gestor organizacional é responsabilidade adicional no Departamento.

Não deve ser confundido com Perfil Gestor nem com gestor direto.

### 8.8 Equipe e Líder

```text
Equipe 1 ─── 0..1 Líder principal ativo
Usuário 1 ─── 0..N responsabilidades de liderança
```

Regras:

- no máximo um Líder principal ativo por Equipe;
- o Líder deve possuir vínculo ativo com a Equipe;
- o Líder pertence à mesma Empresa;
- Cargo e Perfil não concedem liderança automaticamente;
- troca de Líder preserva histórico;
- liderança não concede permissão sem RBAC.

### 8.9 Squad e demais entidades

Squad é transversal e não pertence obrigatoriamente a um Departamento.

As cardinalidades e regras operacionais de Squad permanecem pendentes.

Nenhuma implementação deve reutilizar Equipe como Squad ou adicionar
`squad` textual ao Usuário enquanto essas regras não forem aprovadas.

## 9. Regras de negócio

### 9.1 Principalidade

Departamento principal, Equipe principal e Cargo principal são marcações
independentes.

Um Usuário pode ter:

- zero ou um Departamento principal ativo;
- zero ou uma Equipe principal ativa;
- zero ou um Cargo principal ativo.

Definir um novo principal deve retirar a principalidade anterior da mesma
categoria na mesma transação.

Principalidade:

- não torna o vínculo exclusivo;
- não concede permissão;
- não encerra vínculos secundários;
- não deve ser inferida pela data de criação;
- deve estar disponível de forma explícita nas consultas.

### 9.2 Vigência

Vínculos e responsabilidades devem permitir:

- data/hora de início;
- data/hora de fim;
- status coerente com a vigência;
- ator responsável;
- motivo de encerramento quando aplicável.

Um vínculo ativo não possui fim efetivo.

Um vínculo encerrado não volta a ser o mesmo vínculo ativo. Um retorno futuro
gera nova vigência, preservando o período anterior.

A data de fim não pode ser anterior à data de início.

### 9.3 Histórico

Histórico organizacional é imutável em seu significado.

Correções técnicas excepcionais devem ser auditadas; não devem apagar a
existência anterior de um vínculo.

Eventos mínimos esperados:

- vínculo criado;
- vínculo alterado;
- principal alterado;
- vínculo encerrado;
- Head atribuído;
- Head substituído;
- Gestor incluído ou removido;
- Líder atribuído ou substituído;
- Equipe movida de Departamento;
- entidade inativada ou reativada.

### 9.4 Quem pode ser Head

Pode receber a responsabilidade de Head um Usuário que:

- esteja ativo;
- pertença à mesma Empresa do Departamento;
- possua vínculo ativo com o Departamento;
- seja escolhido explicitamente por ator com permissão RBAC.

Não é requisito conceitual possuir um Cargo chamado “Head”.

Não é suficiente possuir Perfil Gestor.

Políticas adicionais de elegibilidade, caso desejadas, devem ser formalizadas
como regra de negócio própria e não inferidas silenciosamente.

### 9.5 Quem pode ser Líder

Pode receber a responsabilidade de Líder um Usuário que:

- esteja ativo;
- pertença à mesma Empresa da Equipe;
- possua vínculo ativo com a Equipe;
- seja escolhido explicitamente por ator com permissão RBAC.

Cargo e Perfil não são critérios automáticos de liderança.

### 9.6 Troca de Head

A troca de Head deve:

1. validar novo Usuário, Empresa, Departamento e vínculo ativo;
2. validar autorização RBAC do ator;
3. encerrar a responsabilidade anterior;
4. iniciar a nova responsabilidade;
5. manter no máximo um Head principal ativo;
6. registrar ator, data e motivo;
7. emitir eventos;
8. ocorrer de forma transacional.

O histórico do Head anterior não é sobrescrito.

### 9.7 Troca de Líder

A troca de Líder segue os mesmos princípios:

- validação de vínculo;
- encerramento da liderança anterior;
- criação da nova vigência;
- unicidade do Líder principal;
- auditoria;
- atomicidade.

### 9.8 Desligamento organizacional do Usuário

Desligamento organizacional não significa remoção física.

Ao inativar um Usuário:

- novos vínculos e responsabilidades ficam proibidos;
- vínculos ativos precisam ser encerrados;
- responsabilidades de Head, Gestor e Líder precisam ser encerradas;
- principalidades deixam de estar ativas;
- histórico permanece;
- tarefas, projetos e eventos históricos continuam referenciando o Usuário;
- pendências operacionais devem ser apresentadas ao ator responsável.

A estratégia para substituições e aprovações pendentes não é definida aqui.

### 9.9 Inativação de Departamento

Um Departamento não deve ser inativado silenciosamente quando possuir:

- Equipes ativas;
- vínculos ativos de Usuários;
- Head ativo;
- Gestores organizacionais ativos;
- objetos operacionais que dependam dele.

A inativação deve exigir resolução explícita dessas dependências. A forma de
conduzir essa resolução pertence à implementação futura.

### 9.10 Inativação de Equipe

Uma Equipe inativa:

- não aceita novos membros;
- não aceita nova liderança;
- preserva vínculos históricos;
- não deve receber novas atribuições operacionais;
- exige tratamento explícito de trabalho ainda em andamento.

### 9.11 Inativação de Cargo

Cargo inativo:

- permanece em históricos;
- não pode receber novos vínculos ativos;
- não altera automaticamente permissões;
- não deve apagar vínculos anteriores.

### 9.12 Participação fora do Departamento da Equipe

Um Usuário pode participar de Equipe cujo Departamento de referência não seja
um de seus Departamentos ativos somente como exceção explícita.

Essa participação deve ser identificável como convite ou vínculo transversal.

Ela não altera automaticamente:

- Departamento principal;
- demais vínculos departamentais;
- Cargo;
- Perfil;
- Permissões.

### 9.13 Consistência multiempresa

Em qualquer vínculo:

```text
empresa do vínculo
= empresa do Usuário
= empresa da entidade relacionada
```

Essa regra deve ser garantida pela arquitetura, independentemente de
validação da interface.

## 10. Exemplos em uma agência de publicidade

### 10.1 Empresa e estrutura formal

Considere a Empresa:

```text
Agência Horizonte Comunicação
```

Sua estrutura inclui:

```text
Agência Horizonte Comunicação
├── Marketing
│   ├── Equipe Design
│   ├── Equipe Social
│   └── Equipe Vídeo
└── Atendimento
    ├── Equipe Atendimento Goiânia
    └── Equipe Atendimento Palmas
```

Marketing e Atendimento são Departamentos.

Design, Social, Vídeo, Atendimento Goiânia e Atendimento Palmas são Equipes.

Cada Equipe possui um Departamento de referência:

| Equipe | Departamento de referência |
|---|---|
| Design | Marketing |
| Social | Marketing |
| Vídeo | Marketing |
| Atendimento Goiânia | Atendimento |
| Atendimento Palmas | Atendimento |

### 10.2 Usuária com várias Equipes

Ana Ribeiro:

- Departamento principal: Marketing;
- Equipe principal: Social;
- Equipes secundárias: Design e Vídeo;
- Cargo principal: Estrategista de Conteúdo;
- Cargo secundário: Redatora;
- responsabilidade: Líder da Equipe Social.

Ser Líder da Equipe Social não muda seu Cargo e não concede permissões
administrativas automaticamente.

### 10.3 Usuário com vários Departamentos

Bruno Almeida:

- Departamento principal: Marketing;
- Departamento secundário: Atendimento;
- Equipe principal: Design;
- Equipe secundária: Atendimento Goiânia;
- Cargo principal: Diretor de Arte;
- Cargo secundário: Facilitador de Workshop.

O vínculo com Atendimento é explícito. Ele não é deduzido apenas porque Bruno
participa da Equipe Atendimento Goiânia.

### 10.4 Head de Departamento

Mariana Costa:

- Departamento principal: Marketing;
- Cargo principal: Gerente de Operações Criativas;
- responsabilidade: Head de Marketing;
- Equipe principal: Vídeo.

“Head de Marketing” é responsabilidade explícita.

Se o Cargo de Mariana mudar, ela continua Head até que a responsabilidade
seja encerrada.

Se Mariana perder a responsabilidade de Head, seu Cargo não é alterado
automaticamente.

### 10.5 Líder sem ser Head

Carlos Nunes:

- Departamento principal: Atendimento;
- Equipe principal: Atendimento Palmas;
- Cargo principal: Executivo de Atendimento;
- responsabilidade: Líder de Atendimento Palmas;
- não é Head do Departamento Atendimento.

Liderança de Equipe e responsabilidade de Head são escopos diferentes.

### 10.6 Head com várias Equipes sob o Departamento

Mariana, como Head de Marketing, possui responsabilidade sobre o
Departamento, mas não se torna automaticamente membro ou Líder de Design,
Social e Vídeo.

Consultas gerenciais podem mostrar essas Equipes no contexto do Departamento,
desde que Mariana possua a permissão RBAC necessária.

### 10.7 Membro convidado

Bruno possui Atendimento como Departamento secundário e participa da Equipe
Atendimento Goiânia normalmente.

Se ele não possuísse vínculo ativo com Atendimento, sua participação nessa
Equipe precisaria ser marcada como convidada.

O convite não criaria silenciosamente um vínculo com o Departamento.

### 10.8 Troca de Head

Mariana deixa a responsabilidade de Head de Marketing em 30 de setembro.
Ana assume em 1º de outubro.

O histórico registra:

```text
Mariana Costa
Head de Marketing
início: 01/01
fim: 30/09

Ana Ribeiro
Head de Marketing
início: 01/10
fim: —
```

O vínculo antigo não é editado para parecer que Mariana nunca foi Head.

### 10.9 Squad transversal — exemplo apenas conceitual

Uma futura “Squad Lançamento Nacional” poderia reunir:

- Ana, de Marketing;
- Bruno, de Marketing e Atendimento;
- Carlos, de Atendimento;
- uma pessoa de Tecnologia.

Esse exemplo demonstra transversalidade. Ele não decide liderança,
principalidade, duração, permissões ou contrato de Squad.

## 11. Organização e RBAC

### 11.1 Separação obrigatória

O domínio deve preservar quatro conceitos:

| Conceito | Pergunta respondida |
|---|---|
| Perfil RBAC | Que base de acesso o Usuário possui? |
| Permissão | Que ação pode executar? |
| Vínculo organizacional | Onde participa? |
| Responsabilidade | Por qual estrutura responde? |

Nenhum desses conceitos substitui os demais.

### 11.2 Escopo organizacional

Uma permissão pode ser limitada a:

- toda a Empresa;
- Departamentos relacionados;
- Equipes relacionadas;
- Projetos ou Clientes relacionados;
- o próprio Usuário.

Esse escopo só produz autorização quando associado a uma regra RBAC
explícita.

### 11.3 Gates visuais

Ocultar botão ou seção no frontend não representa segurança.

Toda mutação e toda leitura sensível precisam ser autorizadas no backend.

## 12. Impacto técnico

Esta seção pertence ao nível de arquitetura. Ela registra propriedades que as
futuras soluções técnicas devem preservar, sem determinar tabelas, classes,
rotas, formatos de payload ou componentes.

### 12.1 Banco de dados

A arquitetura de dados deve preservar:

- isolamento por Empresa;
- relações N:N de Usuário com Departamento;
- relações N:N de Usuário com Equipe;
- relações N:N de Usuário com Cargo;
- Departamento de referência da Equipe;
- responsabilidades de Head e Gestor;
- responsabilidades de liderança;
- vigência;
- principalidade;
- auditoria;
- unicidade parcial de vínculos ativos;
- integridade entre tenant dos registros.

A evolução dos dados deve preservar informações atuais e tratar
explicitamente as divergências, especialmente os papéis de Head e Gestor já
registrados na implementação.

### 12.2 Backend

A arquitetura de aplicação deve:

- centralizar regras de domínio;
- validar tenant;
- impedir duplicidade ativa;
- garantir atomicidade em mudanças correlacionadas;
- impedir vínculos com entidades inativas;
- preservar histórico;
- emitir eventos;
- aplicar RBAC;
- não depender de validação da interface.

### 12.3 Integração entre camadas

Os contratos entre camadas devem diferenciar:

- catálogos;
- vínculos;
- responsabilidades;
- contexto organizacional;
- alterações organizacionais.

O contexto organizacional de um Usuário deve possuir uma interpretação
consistente. Cada consumidor não deve reconstruir o domínio com regras
próprias.

Alterações correlacionadas devem possuir estratégia explícita de
consistência. Uma interface não deve aparentar sucesso quando apenas parte da
operação válida foi concluída.

O contexto de Empresa deve vir da identidade autenticada quando o Usuário não
estiver operando uma escolha explícita de tenant.

### 12.4 Frontend

A experiência de usuário deve:

- consumir identidades organizacionais consistentes;
- representar múltiplos vínculos e principalidades;
- não representar Squad como texto livre;
- separar dados básicos de contexto organizacional;
- exibir ausência de principal;
- preservar formulário após erro;
- não inferir permissão por Cargo ou responsabilidade.

### 12.5 Permissões

RBAC permanece responsável por autorização.

O domínio organizacional poderá fornecer escopo, mas não poderá conceder
ações por conta própria.

### 12.6 Dashboard

O Dashboard poderá usar:

- Departamento principal;
- Equipe principal;
- responsabilidades de Head e Líder;
- vínculos ativos;
- permissões RBAC.

Esses dados podem orientar conteúdo e filtros, mas não devem gerar acesso
indevido.

### 12.7 Kanban

O Kanban poderá:

- filtrar por Departamento;
- filtrar por Equipe;
- mostrar responsáveis disponíveis;
- calcular capacidade por vínculo ativo;
- aplicar escopo RBAC.

Equipe e Departamento não devem ser tratados como sinônimos.

### 12.8 Agenda

A Agenda poderá combinar:

- compromissos pessoais;
- compromissos de Equipe;
- compromissos de Departamento;
- compromissos de Projeto.

Participação organizacional não implica inscrição automática sem regra
explícita.

### 12.9 Projetos

Projetos poderão referenciar:

- Departamento responsável;
- Equipe responsável;
- Usuários responsáveis;
- Clientes;
- Workflows.

Essas relações devem usar IDs reais e não nomes provenientes de mocks.

### 12.10 Central de Tráfego

A Central de Tráfego depende fortemente deste domínio para:

- carga por Usuário;
- carga por Equipe;
- carga por Departamento;
- gargalos;
- redistribuição;
- capacidade;
- visão de Head;
- visão de Líder.

Dados organizacionais históricos devem ser considerados para relatórios de
períodos passados.

### 12.11 Relatórios

Relatórios devem distinguir:

- vínculo atual;
- vínculo vigente no período consultado;
- Departamento principal atual;
- Departamento principal no período;
- Equipe atual;
- Cargo atual;
- responsabilidade histórica.

Usar somente o estado atual para períodos passados produz resultados
incorretos.

## 13. Divergências encontradas

### 13.1 Documentos de diagnóstico estão desatualizados

**Implementação atual:** Empresa, Usuário, Departamento, Cargo, Equipe e
vários vínculos já existem no backend.

**Documentação anterior:** `00`, `09` e `PROJECT_STATUS.md` ainda descrevem
parte dessas entidades como inexistentes, mockadas ou futuras.

**Direção oficial:** tratar esses documentos como registros históricos. Este
documento define o domínio; um trabalho separado pode atualizar o status do
projeto.

**Justificativa:** diagnóstico temporal não deve competir com modelo
normativo.

### 13.2 Head e Gestor estão no vínculo usuário-departamento

**Implementação atual:** `usuario_departamentos.papel` aceita `membro`,
`gestor` e `head`.

**Direção oficial:** participação departamental e responsabilidade de
liderança são conceitos distintos. Head e Gestores organizacionais possuem
responsabilidade com vigência, sem antecipar sua representação física.

**Justificativa:** uma pessoa pode participar do Departamento sem liderá-lo;
trocas de responsabilidade precisam de semântica e histórico próprios.

### 13.3 Equipe não possui Departamento de referência no backend

**Implementação atual:** a entidade persistida Equipe possui Empresa, código,
nome, descrição e status, mas não `departamento_id`.

**Frontend mock:** `EquipeDraft` possui `departamentoId`.

**Direção oficial:** toda Equipe deve possuir exatamente um Departamento de
referência vigente. Essa é a arquitetura adotada pelo projeto, ainda não
refletida pela implementação atual.

**Justificativa:** carga, pauta, contexto de liderança e convidados dependem
dessa relação.

### 13.4 Vínculo de Equipe não identifica convidado

**Implementação atual:** o vínculo registra papel e principalidade, mas não
distingue membro do Departamento e convidado externo ao Departamento.

**Direção oficial:** a exceção deve ser explícita no domínio.

**Justificativa:** sem essa informação, não é possível validar nem explicar
por que o Usuário participa de Equipe de outro Departamento.

### 13.5 Squad existe somente como texto legado

**Implementação atual:** não há model, migration, schema, repository, service
ou rota de Squad. O frontend legado possui `UsuarioDraft.squad: string`.

**Direção oficial:** não devem surgir novos usos desse campo. Squad deve
aguardar decisão própria e, quando aprovada, possuir identidade e relações
explícitas.

**Justificativa:** texto livre impede integridade, histórico e consultas.

### 13.6 Frontend remoto de Usuários não possui contexto organizacional

**Implementação atual:** o tipo remoto `Usuario` contém somente dados básicos,
e o BFF expõe apenas rotas de Usuários.

**Direção oficial:** o contexto organizacional deve ser fornecido de forma
consistente pelas camadas responsáveis e não ser inventado no frontend.

**Justificativa:** o frontend não deve reconstruir relações a partir de mocks
ou converter `Usuario` em `UsuarioDraft`.

### 13.7 Draft legado suporta apenas um Departamento

**Implementação atual:** `UsuarioDraft.departamentoId` é singular.

**Direção oficial:** Usuário participa de vários Departamentos, com
principalidade explícita.

**Justificativa:** o campo singular não representa a cardinalidade oficial.

### 13.8 Status de vínculos não são uniformes

**Implementação atual:** vínculos de Departamento e Cargo usam
`ativo/inativo`; vínculo de Equipe usa `ativo/encerrado`.

**Direção oficial:** o vocabulário de status deve ser consolidado antes de
novos contratos públicos.

**Justificativa:** semântica divergente aumenta complexidade de API,
frontend, filtros e relatórios.

### 13.9 Endpoints atuais são genéricos

**Implementação atual:** vínculos usam rotas como
`/vinculos/departamentos`, `/vinculos/cargos` e `/vinculos/equipes`.

**Documentação anterior:** propõe também recursos aninhados por Usuário ou
Departamento.

**Direção oficial:** os contratos técnicos devem ser definidos em tarefa
própria e preservar contexto consistente e alterações correlacionadas.

**Justificativa:** esta consolidação define domínio, não deve escolher
silenciosamente a forma final da API.

### 13.10 IDs organizacionais de mocks divergem

**Implementação atual:** módulos frontend usam universos diferentes de IDs
para Departamentos, Equipes e responsáveis.

**Direção oficial:** uma única fonte de identidade organizacional deve
substituir os universos divergentes.

**Justificativa:** IDs divergentes inviabilizam joins, carga e relatórios
confiáveis.

### 13.11 Perfil, Cargo e responsabilidade ainda aparecem misturados

**Implementação atual:** mocks e componentes antigos usam listas de perfil e
textos de Cargo com significados diferentes; `gestor` também aparece como
Perfil e papel de vínculo.

**Direção oficial:** nomes e conceitos distintos devem ser usados para Perfil
RBAC, Cargo e responsabilidade organizacional.

**Justificativa:** sem separação, uma mudança visual pode acidentalmente
alterar autorização ou estrutura.

### 13.12 Roadmaps anteriores reutilizam identificadores TF-ORG

**Implementação documental atual:** `11-plano-implementacao-organizacao.md`
já usa identificadores como TF-ORG-002 e TF-ORG-003.

**Direção oficial:** as entregas deste novo épico devem usar subtarefas
`TF-ORG-001.x` até que uma renumeração formal seja aprovada.

**Justificativa:** evita colisão e mantém rastreabilidade histórica.

## 14. Pontos pendentes de decisão

Nenhum item desta seção está autorizado para implementação por este
documento.

### 14.1 Gestor direto

Decidir:

- se existe relação individual de reporte;
- se ela é derivada do Head do Departamento principal;
- se pode haver múltiplos gestores;
- se possui vigência;
- como tratar matriz organizacional;
- como se relaciona com Perfil Gestor.

### 14.2 Squads

Decidir:

- finalidade;
- ciclo de vida;
- catálogo;
- liderança;
- papéis;
- vigência;
- possibilidade de Squad principal;
- vínculo com Cliente, Projeto e Workflow;
- escopo de visibilidade;
- regras de inativação.

### 14.3 Organograma

Decidir:

- se Departamentos podem possuir Departamento pai;
- se Equipes aparecem como nós;
- se o organograma representa estrutura formal ou linha de reporte;
- como representar estruturas matriciais;
- como versionar mudanças.

### 14.4 Aprovações

Decidir:

- quais objetos exigem aprovação;
- se aprovação depende de Head, Líder, Perfil ou permissão;
- cadeia e alçadas;
- delegação;
- prazos;
- auditoria.

Nenhuma aprovação deve ser inferida somente pela responsabilidade
organizacional.

### 14.5 Férias e ausências

Decidir:

- entidade responsável;
- períodos;
- impacto em capacidade;
- visibilidade;
- integração com Agenda;
- efeito sobre atribuições;
- relação com dados pessoais.

### 14.6 Substituições

Decidir:

- substituição de Head;
- substituição de Líder;
- substituição de responsável;
- vigência;
- permissões temporárias;
- notificações;
- encerramento automático;
- auditoria.

### 14.7 Gestores organizacionais adicionais

Decidir:

- escopo exato;
- cardinalidade;
- diferenças em relação ao Head;
- poderes operacionais;
- representação em consultas e relatórios.

### 14.8 Obrigatoriedade de principal

Este documento define no máximo um principal ativo e admite ausência
temporária.

Antes de tornar principalidade obrigatória, decidir:

- em que momento do ciclo de vida;
- para quais tipos de Usuário;
- comportamento durante onboarding;
- comportamento durante transição;
- tratamento de prestadores.

### 14.9 Mudança de Departamento da Equipe

Decidir:

- se o histórico será somente por eventos;
- se haverá vínculo temporal Equipe–Departamento;
- impacto em relatórios passados;
- tratamento de membros convidados após a mudança.

## 15. Critérios de qualidade do domínio

Uma futura implementação estará alinhada a este documento quando:

- Empresa for a raiz de isolamento;
- não houver vínculo cross-tenant;
- Equipe possuir Departamento de referência;
- Usuários puderem ter múltiplos Departamentos, Equipes e Cargos;
- principalidades forem independentes e únicas por categoria;
- Head e Líder forem responsabilidades explícitas;
- Cargo e responsabilidade não concederem permissão;
- RBAC continuar sendo a fonte de autorização;
- vínculos possuírem vigência e histórico;
- encerramentos não apagarem registros;
- Squad não for representada por texto livre;
- frontend não inventar relações ausentes na API;
- relatórios históricos considerarem vigência;
- divergências existentes possuírem plano explícito de convergência, sem
  adaptação silenciosa.

## 16. Decisões Arquiteturais Congeladas

### 16.1 Significado do congelamento

Este documento passa a representar a referência conceitual oficial do domínio
organizacional do TaskFloww.

As futuras implementações devem respeitar as decisões registradas nesta
seção. Divergências entre essas decisões e qualquer implementação ou
documento devem ser registradas explicitamente.

Uma alteração arquitetural futura deve ocorrer por revisão formal deste
documento. A atualização desta referência não modifica automaticamente as
implementações existentes; a convergência técnica deve ocorrer em subtarefas
específicas, com escopo e validação próprios.

O congelamento não resolve os pontos que permanecem pendentes na seção 14 e
não determina escolhas físicas de persistência, API ou interface.

### 16.2 Decisões congeladas

Ficam congeladas as seguintes decisões:

- Empresa é a raiz de isolamento;
- Usuário participa da organização por vínculos;
- Usuário pode possuir múltiplos Departamentos;
- Usuário pode possuir múltiplas Equipes;
- Usuário pode possuir múltiplos Cargos;
- principalidade é independente para:
  - Departamento;
  - Equipe;
  - Cargo;
- Cargo não representa Perfil;
- Perfil não representa Cargo;
- RBAC continua sendo o único responsável por autorização;
- Head é responsabilidade organizacional;
- Head não é Cargo;
- Head não é Perfil;
- Líder é responsabilidade organizacional;
- Equipe possui Departamento de referência como direção arquitetural oficial;
- Squad permanece conceito independente da Equipe;
- histórico organizacional deve ser preservado;
- vigência faz parte do domínio;
- relacionamentos usam IDs estáveis;
- o domínio organizacional não define implementação física.

## 17. Mapa de implementação

As etapas abaixo organizam resultados esperados. Elas não determinam
artefatos físicos, formatos de API ou componentes. Cada etapa exige análise e
aprovação próprias antes de qualquer implementação.

### TF-ORG-001.1 — Decisões pendentes mínimas e contratos

Objetivo:

- resolver apenas decisões que bloqueiam a arquitetura;
- congelar vocabulário;
- definir princípios de compatibilidade;
- definir necessidades de leitura e alteração;
- decidir tratamento dos papéis atuais de Head/Gestor.

Não inclui alteração de sistema.

### TF-ORG-001.2 — Convergência de Departamentos e vínculos

Objetivo:

- alinhar participação do Usuário em Departamentos;
- preservar múltiplos vínculos;
- preservar principalidade;
- consolidar status e vigência;
- preparar separação de responsabilidades.

### TF-ORG-001.3 — Equipes com Departamento de referência

Objetivo:

- vincular toda Equipe a um Departamento;
- planejar a convergência dos dados existentes;
- registrar mudança;
- tratar membros convidados;
- preservar vínculos atuais.

### TF-ORG-001.4 — Cargos e vínculos

Objetivo:

- confirmar o catálogo real;
- consolidar múltiplos Cargos;
- consolidar Cargo principal;
- garantir separação de RBAC;
- definir necessidades de consulta organizacional.

### TF-ORG-001.5 — Responsabilidade de Head

Objetivo:

- separar Head da participação departamental;
- formalizar seu ciclo de vida;
- planejar a convergência dos Heads atuais;
- garantir unicidade;
- definir a semântica de troca e histórico.

### TF-ORG-001.6 — Gestores organizacionais

Objetivo:

- avançar somente após decisão do escopo;
- separar Perfil Gestor, Gestor organizacional e gestor direto;
- preservar auditoria.

### TF-ORG-001.7 — Contexto organizacional

Objetivo:

- definir uma visão consistente por Usuário;
- definir os catálogos necessários;
- preservar tenant e RBAC;
- definir consistência para alterações correlacionadas;
- evitar interpretações divergentes entre consumidores.

### TF-ORG-001.8 — Integração entre camadas

Objetivo:

- traduzir o contexto organizacional entre as camadas;
- preservar Empresa e identidade autenticada;
- impedir exposição indevida de dados;
- consolidar tratamento de validação e erros.

### TF-ORG-001.9 — Exibição no frontend

Objetivo:

- mostrar contexto organizacional real;
- remover placeholders somente onde houver fonte oficial;
- representar carregamento, erro e nova tentativa;
- não usar mocks como fonte de domínio.

### TF-ORG-001.10 — Edição de vínculos

Objetivo:

- editar Departamentos, Equipes e Cargos por IDs;
- preservar formulário após erro;
- refletir o estado confirmado após sucesso;
- tratar alterações correlacionadas de forma consistente.

### TF-ORG-001.11 — Integração com criação de Usuário

Objetivo:

- decidir fluxo entre criação da identidade e criação dos vínculos;
- evitar Usuário criado parcialmente sem feedback;
- manter compatibilidade da criação básica;
- não ampliar contratos sem aprovação.

### TF-ORG-001.12 — Squads

Objetivo:

- iniciar somente após as decisões da seção 14;
- não reutilizar Equipe;
- não reaproveitar `squad` textual;
- representar a estrutura transversal conforme as decisões aprovadas.

### TF-ORG-001.13 — Consultas operacionais e relatórios

Objetivo:

- integrar Dashboard, Kanban, Agenda, Projetos, Central de Tráfego e
  Relatórios;
- respeitar vigência;
- aplicar RBAC;
- eliminar universos de mock por fluxo controlado.

### TF-ORG-001.14 — Desativação de legados

Objetivo:

- remover campos e mocks somente após todos os consumidores migrarem;
- desativar contratos incompatíveis com janela de compatibilidade;
- atualizar documentação de status;
- preservar histórico Git e dados persistidos.

## 18. Dependências entre etapas

```text
TF-ORG-001.1  Decisões e contratos
        │
        ├── TF-ORG-001.2  Departamentos
        ├── TF-ORG-001.3  Equipes
        ├── TF-ORG-001.4  Cargos
        ├── TF-ORG-001.5  Head
        └── TF-ORG-001.6  Gestores
                    │
                    ▼
           TF-ORG-001.7  Contexto organizacional
                    │
                    ▼
           TF-ORG-001.8  Integração entre camadas
                    │
              ┌─────┴─────┐
              ▼           ▼
       TF-ORG-001.9   TF-ORG-001.10
       Exibição       Edição
                          │
                          ▼
                 TF-ORG-001.11
                 Criação integrada

TF-ORG-001.12 Squads depende de decisão própria.
TF-ORG-001.13 Integrações operacionais depende dos contratos reais.
TF-ORG-001.14 Legados é a última etapa.
```

## 19. Fontes analisadas

### 19.1 Documentação

- `AGENTS.md`
- `PROJECT_STATUS.md`
- `docs/arquitetura-taskfloww/00-estado-atual.md`
- `docs/arquitetura-taskfloww/02-modelo-dados-futuro.md`
- `docs/arquitetura-taskfloww/03-roadmap-implementacao.md`
- `docs/arquitetura-taskfloww/06-diagnostico-entidade-tarefa-atual.md`
- `docs/arquitetura-taskfloww/07-modelo-dominio-tarefa-proposto.md`
- `docs/arquitetura-taskfloww/08-plano-migracao-entidade-tarefa.md`
- `docs/arquitetura-taskfloww/09-diagnostico-estrutura-organizacional.md`
- `docs/arquitetura-taskfloww/10-modelo-dominio-organizacao.md`
- `docs/arquitetura-taskfloww/11-plano-implementacao-organizacao.md`
- `docs/arquitetura-taskfloww/usuarios-bff.md`
- `docs/database-model.md`
- documentos de requisitos, integrações, design system e referências com
  impacto em Usuários, Equipes, Departamentos e responsáveis.

### 19.2 Backend

Foram analisados:

- models de Empresa, Usuário, Departamento, Cargo, Equipe e vínculos;
- migrations existentes;
- schemas Pydantic;
- repositories;
- services;
- eventos;
- autorização;
- rotas;
- testes de entidades, tenant, conflitos, principalidade, vigência,
  encerramento e regressão de autenticação.

### 19.3 Frontend

Foram analisados:

- tipos remotos e legados de Usuário;
- tipos de Equipe;
- mocks de Usuário, Equipe, Projeto e Tráfego;
- listagem, Peek, criação e edição remota de Usuários;
- formulários legados;
- BFF de Usuários;
- browser client;
- testes de Usuários;
- consumidores de Departamento, Equipe e responsável.

## 20. Declaração final

O domínio organizacional do TaskFloww deve ser construído sobre vínculos
explícitos, históricos e isolados por Empresa.

Departamento, Equipe, Cargo, participação e responsabilidade são conceitos
distintos.

Head não é Cargo.

Head não é Perfil.

Líder não é Cargo.

Permissão não vem do Cargo, do Departamento, da Equipe, de Head ou de Líder.

RBAC permanece responsável por autorização.

Usuários podem participar de múltiplas estruturas, com principalidades
independentes.

Equipe possui Departamento de referência.

Squad é transversal, mas permanece pendente de decisão detalhada.

Nenhuma implementação futura deve preencher lacunas deste documento por
suposição silenciosa. Questões pendentes devem ser decididas e registradas
antes de qualquer implementação.

## 21. Histórico desta revisão

### Melhorias conceituais realizadas

- a autoridade do documento foi reformulada como referência conceitual, sem
  invalidar documentos históricos ou técnicos;
- domínio, arquitetura e implementação foram separados explicitamente;
- o Vocabulário Oficial foi consolidado para evitar ambiguidades entre
  Perfil, Cargo, responsabilidade, Head, Gestor e Líder;
- a linguagem normativa foi padronizada;
- prescrições de tabelas, models, migrations, endpoints e componentes foram
  removidas das direções oficiais;
- Head permaneceu definido por sua semântica, sem antecipar persistência;
- Equipe com Departamento de referência foi reafirmada como arquitetura
  oficial ainda pendente de convergência técnica;
- divergências passaram a distinguir estado atual e direção oficial;
- o roadmap passou a descrever resultados, não artefatos físicos.

### Decisões preservadas

- Empresa é a raiz de isolamento;
- Usuário pode participar de múltiplos Departamentos, Equipes e Cargos;
- principalidades são independentes e limitadas a uma por categoria;
- Equipe possui Departamento de referência;
- Head e Líder são responsabilidades, não Cargos ou Perfis;
- Cargo não concede permissão;
- RBAC permanece responsável pela autorização;
- vínculos possuem ciclo de vida e histórico;
- Squad é uma estrutura transversal.

### Pontos deliberadamente mantidos em aberto

- gestor direto;
- regras detalhadas de Squad;
- organograma;
- aprovações;
- férias e ausências;
- substituições;
- detalhes de Gestores organizacionais adicionais;
- obrigatoriedade futura de principal;
- representação histórica da mudança de Departamento de uma Equipe;
- escolhas físicas de persistência, contratos e interface.

## 22. Encerramento do épico

TF-ORG-001 é considerado concluído.

As próximas evoluções deverão ocorrer por subtarefas específicas do épico
TF-ORG.
