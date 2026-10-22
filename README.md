# Inventário de TI

Sistema para controlar ativos de tecnologia, responsáveis, empréstimos, movimentações e manutenções.

[![Qualidade Python](https://github.com/Silva-D-Romario/Inventario-de-TI/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Silva-D-Romario/Inventario-de-TI/actions/workflows/ci.yml)

**Versão 1.0.0** — API pronta para execução local com Docker e preparação de deploy no Render.

## Objetivo

Demonstrar desenvolvimento backend com Django, regras de negócio, autenticação, auditoria, tarefas assíncronas, testes e execução com Docker.

## Recursos disponíveis

- Cadastro e autenticação com JWT.
- Perfis de usuário, técnico e administrador.
- Edição do próprio perfil.
- Gestão de papéis e ativação de contas restrita a administradores.
- CRUD de ativos, categorias, setores e status.
- Pesquisa, filtros, ordenação e paginação do inventário.
- Proteção contra exclusão de cadastros vinculados a ativos.
- Gestão de responsáveis, empréstimos, devoluções e transferências.
- Histórico imutável de movimentações com usuário executor.
- Manutenções transacionais com custos e restauração automática do status do ativo.
- Gestão de garantias, custos e documentos com download autenticado.
- Identificação dos ativos por QR Code e UUID público.
- Trilha de auditoria imutável para alterações e ações operacionais.
- Dashboard com indicadores, distribuições e séries prontas para gráficos.
- Relatórios CSV filtráveis de ativos, custos e manutenções.
- Alertas assíncronos e deduplicados para empréstimos vencidos e garantias.
- Notificações isoladas por usuário com controle de leitura.
- Health check e documentação OpenAPI/Swagger.
- Proteções de produção, throttling, validação de conteúdo e auditoria de dependências.

## Stack

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
    Beat[Celery Beat] --> Redis
    Redis --> Worker[Celery Worker]
    Worker --> PostgreSQL
    Worker --> Email[E-mail]
```

O Compose executa a API, PostgreSQL, Redis, Celery Worker e Celery Beat. O Beat agenda a verificação diária, o Redis entrega a tarefa e o Worker cria notificações persistentes e envia os e-mails configurados.

## Deploy

O repositório inclui um Blueprint do Render com API, PostgreSQL, Redis, Worker e agendamento diário. A ativação não é automática porque Worker e Cron Job geram cobrança. O passo a passo, limitações e variáveis necessárias estão em [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

A política e os controles aplicados estão em [SECURITY.md](SECURITY.md).

## Executar com Docker

```bash
cp .env.example .env
docker compose up --build
```

Serviços disponíveis:

- API: `http://localhost:18000/api/v1/health/`
- Swagger: `http://localhost:18000/api/docs/`
- Administração Django: `http://localhost:18000/admin/`

## Autenticação

Principais endpoints:

| Método | Endpoint | Acesso |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register/` | Público |
| `POST` | `/api/v1/auth/token/` | Público |
| `POST` | `/api/v1/auth/token/refresh/` | Público |
| `GET/PATCH` | `/api/v1/auth/me/` | Autenticado |
| `GET` | `/api/v1/auth/users/` | Administrador |
| `PATCH` | `/api/v1/auth/users/{id}/access/` | Administrador |

Criar uma conta:

```bash
curl -X POST http://localhost:18000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "romario",
    "email": "romario@example.com",
    "first_name": "Romário",
    "last_name": "Silva",
    "password": "SenhaSegura@2026",
    "password_confirmation": "SenhaSegura@2026"
  }'
```

Obter o token:

```bash
curl -X POST http://localhost:18000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"romario","password":"SenhaSegura@2026"}'
```

Use o token de acesso nas rotas protegidas:

```text
Authorization: Bearer SEU_ACCESS_TOKEN
```

O cadastro público sempre cria o perfil `USER`. Apenas um administrador pode promover outra conta para `TECHNICIAN` ou `ADMIN`. Para criar o primeiro administrador local:

```bash
docker compose exec web python manage.py createsuperuser
```

Em hospedagem, o comando `bootstrap_admin` cria a primeira conta somente quando `APP_ADMIN_USERNAME`, `APP_ADMIN_EMAIL` e `APP_ADMIN_PASSWORD` são fornecidos. Ele nunca redefine a senha de uma conta existente.

## Inventário

| Recurso | Endpoint | Usuário | Técnico | Administrador |
| --- | --- | --- | --- | --- |
| Categorias | `/api/v1/inventory/categories/` | Consultar | Consultar | CRUD |
| Setores | `/api/v1/inventory/sectors/` | Consultar | Consultar | CRUD |
| Status | `/api/v1/inventory/statuses/` | Consultar | Consultar | CRUD |
| Ativos | `/api/v1/inventory/assets/` | Consultar | Criar e atualizar | CRUD |

O sistema cria automaticamente os status `Disponível`, `Em uso`, `Em manutenção` e `Baixado`.

Exemplo de cadastro de ativo por técnico ou administrador:

```bash
curl -X POST http://localhost:18000/api/v1/inventory/assets/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_tag": "PAT-001",
    "name": "Notebook Dell Latitude",
    "category": 1,
    "sector": 1,
    "status": 1,
    "serial_number": "SN-001",
    "manufacturer": "Dell",
    "model": "Latitude 5440",
    "acquisition_date": "2026-10-18",
    "purchase_value": "4500.00"
  }'
```

Filtros disponíveis para ativos:

```text
?category=1
?sector=1
?status=1
?search=Dell
?ordering=-updated_at
?acquisition_date__gte=2026-01-01&acquisition_date__lte=2026-12-31
```

## Empréstimos e movimentações

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET/POST` | `/api/v1/inventory/responsible-people/` | Consultar e cadastrar responsáveis |
| `GET/POST` | `/api/v1/inventory/loans/` | Consultar e registrar empréstimos |
| `POST` | `/api/v1/inventory/loans/{id}/return/` | Registrar devolução |
| `POST` | `/api/v1/inventory/assets/{id}/transfer/` | Transferir ou atribuir um ativo |
| `GET` | `/api/v1/inventory/movements/` | Consultar o histórico imutável |

Exemplo de empréstimo:

```bash
curl -X POST http://localhost:18000/api/v1/inventory/loans/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset": 1,
    "borrower": 1,
    "expected_return_date": "2026-10-30",
    "notes": "Uso temporário em projeto"
  }'
```

O empréstimo move o ativo para o setor do responsável e altera seu status para `Em uso`. A devolução restaura o setor de origem e o status `Disponível`. Essas operações usam transações e bloqueio de linha no banco para impedir empréstimos simultâneos do mesmo ativo.

## Manutenções, garantias, custos e anexos

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET/POST` | `/api/v1/inventory/maintenances/` | Consultar e iniciar manutenções |
| `POST` | `/api/v1/inventory/maintenances/{id}/complete/` | Concluir e registrar o custo |
| `POST` | `/api/v1/inventory/maintenances/{id}/cancel/` | Cancelar uma manutenção |
| `GET/POST` | `/api/v1/inventory/warranties/` | Gerenciar garantias |
| `GET/POST` | `/api/v1/inventory/costs/` | Gerenciar custos dos ativos |
| `GET/POST` | `/api/v1/inventory/attachments/` | Listar e enviar documentos |
| `GET` | `/api/v1/inventory/attachments/{id}/download/` | Baixar um documento autenticado |

Exemplo de início e conclusão de manutenção:

```bash
curl -X POST http://localhost:18000/api/v1/inventory/maintenances/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset": 1,
    "maintenance_type": "CORRECTIVE",
    "description": "Substituição da fonte",
    "provider": "Assistência Técnica"
  }'

curl -X POST http://localhost:18000/api/v1/inventory/maintenances/1/complete/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"resolution_notes":"Fonte substituída","cost":"480.50"}'
```

Ao iniciar uma manutenção, o ativo muda para `Em manutenção`. Somente uma manutenção pode ficar aberta por ativo. Na conclusão ou no cancelamento, o status volta para `Disponível` ou `Em uso`, conforme a atribuição atual. O custo da conclusão é registrado automaticamente no histórico financeiro.

Anexos aceitam PDF, PNG, JPG, JPEG e WebP com até 10 MB. A extensão e a assinatura do conteúdo são validadas. Os arquivos ficam em volume persistente no Docker e são entregues somente pela rota autenticada de download. Para produção distribuída, substitua o armazenamento local por um serviço de objetos compatível com S3.

## QR Code e auditoria

Cada ativo recebe um UUID público aleatório. O QR Code contém somente a URL de consulta desse identificador; dados patrimoniais e técnicos continuam protegidos pela autenticação JWT.

| Método | Endpoint | Acesso | Descrição |
| --- | --- | --- | --- |
| `GET` | `/api/v1/inventory/assets/{id}/qr-code/` | Autenticado | Gerar a etiqueta QR em PNG |
| `GET` | `/api/v1/inventory/assets/scan/{public_id}/` | Autenticado | Consultar o ativo ao ler o QR |
| `GET` | `/api/v1/inventory/audit-logs/` | Administrador | Consultar a auditoria imutável |

Baixar a etiqueta:

```bash
curl http://localhost:18000/api/v1/inventory/assets/1/qr-code/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  --output ativo-1-qrcode.png
```

A auditoria registra usuário, ação, recurso, campos alterados, IP, agente do cliente, rota, método e identificador da requisição. Criações, atualizações, exclusões, transferências, devoluções, encerramentos de manutenção e leituras de QR são rastreadas. Os registros não podem ser criados, editados ou excluídos pela API.

Filtros de auditoria disponíveis:

```text
?actor=1
?action=UPDATE
?resource_type=inventory.asset
?object_id=15
?created_at__gte=2026-10-01&created_at__lte=2026-10-31
```

## Dashboard e relatórios

O dashboard consolida os principais indicadores sem exigir processamento no cliente:

| Método | Endpoint | Acesso | Conteúdo |
| --- | --- | --- | --- |
| `GET` | `/api/v1/inventory/dashboard/` | Autenticado | Indicadores, distribuições, custos mensais e últimas movimentações |
| `GET` | `/api/v1/inventory/reports/assets.csv` | Técnico ou administrador | Inventário patrimonial filtrável |
| `GET` | `/api/v1/inventory/reports/costs.csv` | Técnico ou administrador | Histórico financeiro filtrável |
| `GET` | `/api/v1/inventory/reports/maintenances.csv` | Técnico ou administrador | Histórico de manutenções filtrável |

Exemplos:

```bash
curl http://localhost:18000/api/v1/inventory/dashboard/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN"

curl "http://localhost:18000/api/v1/inventory/reports/assets.csv?sector=1&acquisition_from=2026-01-01" \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  --output ativos.csv
```

Os relatórios aceitam filtros por período e atributos do recurso, usam codificação UTF-8 compatível com planilhas e registram cada exportação na auditoria. A documentação completa dos parâmetros está no Swagger.

## Alertas assíncronos

Todos os dias, o Celery procura empréstimos vencidos e garantias que terminarão dentro do período configurado. Técnicos e administradores ativos recebem uma notificação própria e um e-mail. A chave de deduplicação impede alertas repetidos para o mesmo evento.

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/v1/inventory/notifications/` | Listar somente as notificações do usuário autenticado |
| `GET` | `/api/v1/inventory/notifications/{id}/` | Consultar uma notificação própria |
| `POST` | `/api/v1/inventory/notifications/{id}/mark-read/` | Marcar uma notificação como lida |
| `POST` | `/api/v1/inventory/notifications/mark-all-read/` | Marcar todas as próprias notificações como lidas |

Filtros disponíveis:

```text
?alert_type=OVERDUE_LOAN
?alert_type=WARRANTY_EXPIRING
?read_at__isnull=true
?search=garantia
```

O horário e o período de garantia são definidos no `.env`:

```env
INVENTORY_ALERT_HOUR=8
INVENTORY_ALERT_MINUTE=0
INVENTORY_WARRANTY_ALERT_DAYS=30
```

O backend de e-mail padrão escreve as mensagens nos logs, adequado ao desenvolvimento. Em produção, configure o backend SMTP e as credenciais somente por variáveis de ambiente. Para disparar uma verificação de teste pela fila:

```bash
docker compose exec web python manage.py shell -c \
  "from apps.inventory.tasks import generate_inventory_alerts; generate_inventory_alerts.delay()"
```

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
DJANGO_DEBUG=false \
DJANGO_SECRET_KEY=uma-chave-segura-com-mais-de-cinquenta-caracteres \
DJANGO_ALLOWED_HOSTS=example.com \
python manage.py check --deploy
pip-audit --skip-editable
```

## Etapas

1. ✅ Fundação Django, banco, containers, testes e CI.
2. ✅ Autenticação JWT e perfis de acesso.
3. ✅ Cadastro de ativos, categorias, setores e status.
4. ✅ Empréstimos, responsáveis e movimentações.
5. ✅ Manutenções, garantias, custos e anexos.
6. ✅ QR Code e auditoria.
7. ✅ Dashboard e relatórios.
8. ✅ Alertas assíncronos.
9. ✅ Segurança, documentação e preparação do deploy.

## Fluxo Git

- `main`: versão estável.
- `develop`: desenvolvimento e validação antes da PR.
