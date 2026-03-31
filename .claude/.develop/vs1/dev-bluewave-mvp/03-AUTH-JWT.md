# Fase 03 — Autenticação JWT & Multi-Tenant Isolation 🟢

## Objetivo

Implementar autenticação stateless via JWT com suporte a multi-tenant, refresh token seguro, password reset, SSO framework e autenticação dual (JWT + API Key).

## Componentes

### Security (`core/security.py`)
- JWT encode/decode (HS256)
- bcrypt password hash/verify
- Token payload: `{ sub: user_id, tenant_id, role, exp }`
- Access token TTL: 30 minutos
- Refresh token TTL: 7 dias (httpOnly cookie, rotação no uso)

### Config (`core/config.py`)
- Pydantic `Settings` class com 30+ variáveis de ambiente
- Categorias: DB, JWT, AI, LangSmith, Email, Social, Storage, Billing, Redis, Sentry

### Dependencies (`core/deps.py`)
- `get_current_user(token)` — decode JWT → verify exp → retorna `UserContext`
- `require_role("admin")` — dependency secundária para controle de acesso
- Suporte dual: JWT Bearer header + `X-API-Key` header
- Injetado via `Depends()` em todas as rotas protegidas

### Tenant Isolation (`core/tenant.py`)
- `ContextVar` para `tenant_id` do request atual
- SQLAlchemy session event injeta `WHERE tenant_id = :tid` em todo SELECT, UPDATE, DELETE
- Nenhum desenvolvedor pode esquecer o filtro

### Auth Router (`routers/auth.py`)
- `POST /auth/register` — cria tenant + admin user
- `POST /auth/login` — retorna access token + set-cookie refresh
- `POST /auth/refresh` — rotaciona refresh token
- `POST /auth/logout` — invalida refresh token
- `POST /auth/password-reset` — email com link de reset (Resend)

### SSO (`routers/sso.py`)
- Framework SAML/SSO (Okta, Azure AD, Google Workspace)
- Callback endpoint para integração enterprise

### API Key Auth (`core/api_key_auth.py`)
- Validação de `X-API-Key` header
- Hash comparison (key_hash stored, not plaintext)

## Entregáveis

- [x] Register cria tenant + user admin
- [x] Login retorna JWT válido com tenant_id e role
- [x] Refresh token em httpOnly cookie com rotação
- [x] Rotas protegidas rejeitam requests sem token (401)
- [x] Tenant isolation automático (tenant A nunca vê dados de B)
- [x] Dual auth: JWT Bearer + X-API-Key
- [x] Password reset via email
- [x] SSO framework funcional

## Critérios de Conclusão

- Register → Login → hit rota protegida → sucesso
- Token expirado → 401
- Tenant A → query dados → nunca retorna dados de tenant B
- API Key válida → acesso equivalente ao JWT
- Refresh com cookie expirado → 401
