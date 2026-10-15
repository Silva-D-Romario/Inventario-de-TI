# Inventário de TI

Sistema para controlar ativos de tecnologia, responsáveis, empréstimos, movimentações e manutenções.

## Objetivo

Demonstrar desenvolvimento backend com Django, regras de negócio, autenticação, auditoria, tarefas assíncronas, testes e execução com Docker.

## Stack planejada

- Python e Django
- Django REST Framework
- PostgreSQL
- Celery e Redis
- Docker Compose
- Pytest e Ruff
- GitHub Actions

## Arquitetura inicial

```mermaid
flowchart LR
    Cliente[Cliente HTTP] --> Django[Django + DRF]
    Django --> PostgreSQL[(PostgreSQL)]
    Django --> Redis[(Redis)]
    Redis -. tarefas futuras .-> Celery[Celery Worker]
```

Nesta primeira etapa, o Compose executa somente os três componentes necessários: aplicação, PostgreSQL e Redis. O worker Celery será incluído quando os alertas assíncronos forem implementados.

## Executar com Docker

```bash
cp .env.example .env
docker compose up --build
```

Serviços disponíveis:

- API: `http://localhost:18000/api/v1/health/`
- Swagger: `http://localhost:18000/api/docs/`
- Administração Django: `http://localhost:18000/admin/`

Para encerrar:

```bash
docker compose down
```

## Desenvolvimento local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

Validações:

```bash
ruff format --check .
ruff check .
pytest
python manage.py check
```

## Etapas

1. ✅ Fundação Django, banco, containers, testes e CI.
2. Autenticação e perfis de acesso.
3. Cadastro de ativos, categorias, setores e status.
4. Empréstimos, responsáveis e movimentações.
5. Manutenções, garantias, custos e anexos.
6. QR Code e auditoria.
7. Dashboard e relatórios.
8. Alertas assíncronos.
9. Segurança, documentação e deploy.

## Fluxo Git

- `main`: versão estável.
- `develop`: desenvolvimento e validação antes da PR.
