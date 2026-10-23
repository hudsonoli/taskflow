# Cor do modelo de workflow

Identidade visual do **modelo** de workflow (não da Demanda, da etapa, do status nem da prioridade).

- Coluna `workflow_modelos.cor` (VARCHAR(7), nullable) + CHECK `cor IS NULL OR cor ~ '^#[0-9A-F]{6}$'` (migration `0053`, aditiva, sem backfill). `NULL` = "sem cor personalizada": a interface usa o ponto neutro; nada é sorteado nem persistido por padrão.
- API: `cor` opcional em `POST /workflow-modelos` e `PATCH /workflow-modelos/{id}` (omitido = não muda; `null` = remove) e devolvida em leitura, lista e `/diretorio`. Aceita só `#RRGGBB` (qualquer caixa, espaço em volta aparado) e normaliza para
  maiúsculas; nome CSS, `#FFF`, `rgb()`, texto e HTML/CSS viram 422. Clientes antigos que não enviam `cor` seguem válidos.
- Autoridade: a mesma de editar o workflow (admin/gestor); quem só seleciona (`/diretorio`, `GET /{id}`) apenas vê. Alterar a cor publica o evento `workflow_modelo.alterado` existente (`camposAlterados: ["cor"]`); no-op não publica.
- **Não** faz parte do snapshot da Demanda: mudar a cor muda como o modelo é exibido, não as etapas materializadas.
- Interface: `WorkflowCorPonto`/`WorkflowNomeComCor` (único lugar com `style` de cor; o nome continua sempre em texto) e `WorkflowCorField` (paleta de 10 atalhos, seletor nativo, HEX editável, preview, "Remover cor").
  Exibida na listagem de workflows, no cadastro/edição e no seletor de workflow da criação de tarefa. Não toca Kanban, Pauta, prioridade, status, progresso nem Carga.
