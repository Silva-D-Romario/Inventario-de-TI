# Política de segurança

## Versões suportadas

A versão mais recente da branch `main` recebe correções de segurança.

## Como relatar uma vulnerabilidade

Não publique credenciais, dados pessoais, procedimentos de exploração ou outras informações sensíveis em uma issue pública.

Prefira abrir uma Security Advisory privada na aba **Security** do repositório. Inclua:

- componente e versão afetados;
- passos mínimos para reproduzir;
- impacto observado;
- sugestão de correção, se houver.

## Controles implementados

- autenticação JWT com rotação e revogação de refresh tokens;
- tokens de acesso com 15 minutos e refresh tokens com 7 dias;
- papéis de usuário, técnico e administrador;
- limitação de requisições anônimas e autenticadas;
- cookies seguros, HTTPS, HSTS e cabeçalhos defensivos em produção;
- chave secreta e hosts obrigatórios fora do modo de desenvolvimento;
- validação de extensão, tamanho e assinatura dos anexos;
- download de anexos somente por rota autenticada;
- trilha de auditoria imutável;
- análise estática, testes, verificação de deploy e auditoria de dependências na CI.

Segredos devem existir somente em variáveis de ambiente ou no gerenciador de segredos da plataforma.
