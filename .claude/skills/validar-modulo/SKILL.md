---
name: validar-modulo
description: "Use antes de declarar qualquer módulo (frontend ou backend) do TaskFloww como concluído. Encodes o 'Checklist obrigatório' e o 'Processo de Validação' do CLAUDE.md com os comandos reais de AGENTS.md/frontend-AGENTS.md."
---

# /validar-modulo

Delegue a execução para o agente `qa-validator` sempre que possível — ele só valida, não corrige, o que evita a tentação de "consertar rapidinho" sem revisão.

## Comandos (frontend, dentro do container — `frontend/AGENTS.md`)

```bash
docker compose exec taskfloww_front npm run typecheck
docker compose exec taskfloww_front npm run lint
docker compose exec taskfloww_front npm run build
```

## Comandos (backend)

Confirme o nome do serviço em `docker-compose.yml` antes de assumir — não hardcode um nome que pode ter mudado:
```bash
docker compose exec <servico_backend> pytest
docker compose exec <servico_backend> ruff check .
```

## Sempre ao final

```bash
git status
git diff --stat
```

## Checklist obrigatório (verbatim do CLAUDE.md — "Checklist obrigatório")

- [ ] Rota `page.tsx` criada
- [ ] View criada
- [ ] Componentes criados
- [ ] Tipos criados
- [ ] Mocks/hooks de dados criados
- [ ] Adicionado ao menu correspondente
- [ ] Adicionado ao hub de Configurações (quando aplicável)
- [ ] Acesso direto à URL validado
- [ ] `npm run lint`
- [ ] `npm run build`
- [ ] `git status` mostrado
- [ ] `git diff --stat` mostrado

## Regra de honestidade (CLAUDE.md é explícito nisso)

"Nunca considerar um módulo concluído apenas porque os componentes foram criados." Só declare sucesso se **todos** os itens acima passarem. Se algo falhar, mostre o erro real (não resuma) e devolva para o builder responsável corrigir — não tente múltiplas correções automáticas em sequência (regra do `AGENTS.md`: "Não tentar várias correções automáticas em sequência").

Nunca rode `git commit` a partir desta skill.
