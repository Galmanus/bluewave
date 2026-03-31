# ADR-02 — Autenticação Stateless com JWT

> Status: Aceita
> Data: 2026-03-18

## Contexto

Precisamos de autenticação que funcione em ambiente Docker sem sticky sessions, escale horizontalmente e carregue contexto do tenant sem queries extras.

## Decisão

Adotamos **JWT (JSON Web Tokens)** com HS256 para autenticação stateless, com refresh token em httpOnly cookie e suporte dual JWT + API Key.

### Implementação
- Access token (30min): `{ sub: user_id, tenant_id, role, exp }`
- Refresh token (7 dias): httpOnly, Secure, SameSite=Strict cookie, rotação no uso
- HS256 (single-issuer MVP) — migrável para RS256 se verificação por terceiros for necessária
- Dual auth: `Authorization: Bearer <jwt>` OU `X-API-Key: <key>`
- `get_current_user` FastAPI dependency aceita ambos

## Alternativas Consideradas

| Estratégia | Prós | Contras | Veredicto |
|------------|------|---------|-----------|
| Sessions (server-side) | Simples, revogável | Precisa Redis/sticky sessions | Rejeitada — complexidade Docker |
| OAuth2 externo (Auth0) | Delegado, seguro | Custo, latência extra, vendor lock | Rejeitada — overhead para MVP |
| **JWT stateless** | Sem estado, escalável, Docker-friendly | Revogação limitada ao TTL | **Aceita** |

## Consequências

**Positivas:**
- Sem session store — escala horizontal trivial
- tenant_id + role no payload — zero DB lookups por request
- Docker-friendly — sem Redis necessário para auth
- API Key dual auth habilita integrações programáticas

**Negativas:**
- Revogação imediata impossível (mitigado por TTL curto de 30min)
- Token leaked tem janela de 30min (mitigado por HTTPS + httpOnly refresh)
- HS256 single-key — se comprometida, todos os tokens são inválidos (rotação de secret planejada)
