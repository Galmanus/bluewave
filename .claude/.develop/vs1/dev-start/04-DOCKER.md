# Fase 4 — Docker

## Objetivo
Docker Compose orquestrando todos os serviços.

## Componentes
- 3 serviços: postgres, backend, frontend
- Network bridge (bluewave_network)
- Volumes persistentes
- Health checks

## Entregáveis
- [x] docker-compose.yml funcional
- [x] Backend em porta 8300
- [x] Frontend em porta 5174
- [x] PostgreSQL interno

## Critérios de Conclusão
`docker compose up` sobe tudo, frontend acessível via browser.
