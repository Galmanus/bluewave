# ADR-01 — Isolamento Multi-Tenant por Row-Level (tenant_id)

> Status: Aceita
> Data: 2026-03-18

## Contexto

O Bluewave é SaaS multi-tenant — agência A nunca pode ver dados da agência B. Precisamos de uma estratégia de isolamento que seja segura, simples de implementar e escalável.

## Decisão

Adotamos **row-level isolation** via coluna `tenant_id` UUID non-nullable em todas as tabelas tenant-scoped, com filtro automático via SQLAlchemy session event.

### Implementação
- `TenantMixin` em `models/base.py` — adiciona `tenant_id` FK consistentemente
- `core/tenant.py` — `ContextVar` armazena tenant_id do request atual
- SQLAlchemy session event injeta `WHERE tenant_id = :tid` em todo SELECT, UPDATE, DELETE
- Composite index `(tenant_id, id)` em tabelas de alto tráfego
- JWT payload carrega `tenant_id` — sem DB lookup extra por request

## Alternativas Consideradas

| Estratégia | Prós | Contras | Veredicto |
|------------|------|---------|-----------|
| DB por tenant | Isolamento máximo | Caro, migrations complexas | Rejeitada — overkill para MVP |
| Schema por tenant | Bom isolamento | Nightmare de migrations com N tenants | Rejeitada — não escala |
| **Row-level (tenant_id)** | Simples, escalável, um migration path | Requer disciplina em queries | **Aceita** |

## Consequências

**Positivas:**
- Adicionar tenant = um INSERT, não provisionar infra
- Um pipeline de migrations para todos os tenants
- Um connection pool compartilhado
- Performance com composite indexes

**Negativas:**
- Se o filtro falhar, tenant A vê dados de B (mitigado pelo session event automático)
- Noisy neighbor potencial em queries pesadas (mitigável com connection pooling)
- Testes de tenant isolation são críticos (implementados em `test_tenant_isolation.py`)
