# Deploy no Render

O `render.yaml` cria a API, PostgreSQL, Redis, um Celery Worker e um agendamento diário. O Celery Beat continua disponível no Docker Compose para desenvolvimento local; no Render, o Cron Job envia a tarefa diária ao Worker às 11:00 UTC, equivalente a 08:00 em Maceió.

## Antes de confirmar

O Blueprint usa os planos gratuitos para a API, PostgreSQL e Key Value, mas o Background Worker e o Cron Job usam o menor plano pago porque esses tipos de serviço não possuem plano gratuito. Confira os valores exibidos pelo Render antes de clicar em **Deploy Blueprint**.

Os planos gratuitos também possuem limitações e podem mudar. Consulte:

- [Planos gratuitos](https://render.com/docs/free)
- [Planos de computação](https://render.com/docs/compute-plans)
- [Especificação de Blueprints](https://render.com/docs/blueprint-spec)

## Passo a passo

1. No Render, selecione **New > Blueprint**.
2. Conecte `Silva-D-Romario/Inventario-de-TI`.
3. Use a branch `main` e o caminho `render.yaml`.
4. Preencha os três segredos solicitados:
   - `APP_ADMIN_USERNAME`;
   - `APP_ADMIN_EMAIL`;
   - `APP_ADMIN_PASSWORD` com uma senha forte.
5. Revise os recursos e custos apresentados.
6. Confirme o deploy e aguarde todos os serviços ficarem disponíveis.
7. Abra `/api/v1/health/`, `/api/docs/` e `/admin/` na URL criada.

O primeiro início executa as migrações, coleta os arquivos estáticos e cria o administrador. Reinícios posteriores não alteram a senha de uma conta existente. Depois de confirmar o acesso, os três valores `APP_ADMIN_*` podem ser removidos do serviço web.

## E-mail

O Blueprint usa o backend `dummy` para não registrar mensagens nem exigir credenciais no deploy de demonstração. Para envio real, configure no grupo de ambiente:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario
EMAIL_HOST_PASSWORD=segredo
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=inventario@example.com
```

## Anexos

O armazenamento local do serviço web é efêmero no plano gratuito. Os anexos funcionam, mas podem desaparecer após reinícios ou novos deploys. Para produção, use um disco persistente pago ou armazenamento de objetos compatível com S3.

## Atualizações

Depois do primeiro deploy, mudanças aprovadas em `main` disparam uma nova implantação. Antes de promover uma versão, confirme a CI e mantenha `develop` sincronizada com `main`.
