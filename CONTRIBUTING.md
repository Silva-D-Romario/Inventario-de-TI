# Padrão de desenvolvimento

Este repositório usa um fluxo simples e repetível para os projetos do portfólio.

## Branches

- `main`: produção e versões estáveis.
- `develop`: implementação e validação das próximas etapas.
- Não criar branches adicionais no fluxo normal do projeto.

## Etapas de entrega

1. Definir objetivo, escopo e critérios de conclusão da etapa.
2. Implementar em `develop`, mantendo responsabilidades separadas no código.
3. Criar commits pequenos e separados por mudança.
4. Executar as validações locais proporcionais ao risco.
5. Publicar `develop` e abrir pull request para `main`.
6. Aguardar todos os checks do GitHub Actions.
7. Fazer o merge somente com os checks aprovados.
8. Sincronizar `develop` com o merge de `main`.
9. Criar uma release quando houver uma versão funcional relevante.

## Validações obrigatórias

```bash
ruff format --check .
ruff check .
python manage.py makemigrations --check --dry-run
python manage.py check
pytest
```

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

```bash
docker compose build
```

## Commits

Use mensagens no imperativo e separe código, testes, documentação e infraestrutura quando forem responsabilidades independentes.

Exemplos:

- `Adiciona gerador de dados demonstrativos`
- `Testa cenários demonstrativos do inventário`
- `Documenta fluxo de contribuição`

## Pull request

A descrição deve informar o que mudou, como foi validado, riscos conhecidos e passos manuais necessários. Não integrar uma PR com checks pendentes ou falhando.
