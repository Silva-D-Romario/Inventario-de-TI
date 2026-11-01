# Arquitetura e organização

O projeto usa um monólito modular: o Django concentra API, regras de negócio e entrega do build React. Essa escolha mantém o deploy simples sem misturar responsabilidades no código.

## Backend

```text
apps/
├── accounts/            # autenticação, perfis e permissões
├── core/                # recursos transversais, como health check
└── inventory/           # domínio de inventário e operações
    ├── models.py        # entidades e invariantes persistidas
    ├── serializers.py   # contrato e validação da API
    ├── services.py      # casos de uso transacionais
    ├── views.py         # endpoints HTTP
    ├── permissions.py   # autorização por perfil
    └── tasks.py         # tarefas assíncronas
```

Regras que alteram mais de uma entidade ficam em `services.py`. As views apenas coordenam HTTP, autorização, serializers e auditoria. Cada operação crítica usa transação no banco e possui testes automatizados.

## Frontend

```text
frontend/src/
├── app/                 # composição da aplicação e navegação
├── components/
│   ├── common/          # estados e cabeçalhos reutilizáveis
│   └── layout/          # estrutura autenticada da aplicação
├── features/
│   ├── auth/            # sessão, login e cadastro
│   ├── dashboard/       # indicadores e movimentações
│   ├── assets/          # consulta e CRUD de ativos
│   ├── operations/      # empréstimos e manutenções
│   └── catalogs/        # categorias, setores e status
├── lib/                 # cliente HTTP, tipos e formatadores
└── styles/              # identidade visual e responsividade
```

O cliente HTTP centraliza JWT, renovação do token, erros e encerramento de sessão. As funcionalidades não conhecem detalhes do armazenamento dos tokens. Permissões também são refletidas na interface, mas a API continua sendo a autoridade final.

## Execução e entrega

- No desenvolvimento, o Vite usa proxy para a API em `localhost:18000`.
- No build, o Docker compila o React antes de montar a imagem Python.
- Em produção, Django e WhiteNoise entregam a SPA e seus arquivos estáticos na mesma origem da API.
- A CI valida Python, TypeScript, lint, testes, contratos, auditorias e build Docker.
