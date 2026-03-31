# Fase 05 — Frontend Setup & Auth UI 🟢

## Objetivo

Configurar o projeto frontend (React + TypeScript + Vite + Tailwind) e implementar toda a camada de autenticação: login, registro, guards de rota e gerenciamento de token.

## Componentes

### Scaffold
- Vite 5.4 + React 18 + TypeScript 5.5
- Tailwind CSS 3.4 configurado
- `tsconfig.json` com strict mode

### HTTP Client (`lib/api.ts`)
- Instância Axios centralizada com base URL
- JWT interceptor: injeta `Authorization: Bearer` em cada request
- Auto-refresh: ao receber 401, chama `/auth/refresh` e retenta o request original
- Retry com exponential backoff: 3 tentativas, 500ms base, ±20% jitter
- Status retentáveis: 408, 429, 500, 502, 503, 504 + erros de rede

### Utilities
- `lib/cn.ts` — classname helper (clsx + tailwind-merge)
- `lib/sentry.ts` — Sentry error tracking frontend

### Auth Context (`contexts/AuthContext.tsx`)
- Armazena token em memória (não localStorage)
- Expõe: `login()`, `logout()`, `user`, `isAuthenticated`
- Refresh automático no mount da app

### Theme Context (`contexts/ThemeContext.tsx`)
- Toggle light/dark mode
- Persistência em localStorage
- Respeita `prefers-color-scheme` no primeiro load

### Páginas de Auth
- `LoginPage.tsx` — formulário email + password, gradient background, logo
- `RegisterPage.tsx` — tenant name + admin user, password strength bar

### Guards
- `AuthGuard.tsx` — redireciona para `/login` se não autenticado
- `RoleGuard.tsx` — redireciona para `/` se role insuficiente

### Routing (`App.tsx`)
- React Router com lazy-loaded pages (Suspense)
- Rotas públicas: `/`, `/login`, `/register`
- Rotas protegidas dentro de `AuthGuard` → `AppLayout`
- Rotas admin dentro de `RoleGuard`

### Entry Points
- `main.tsx` — React entry + Sentry init
- `index.css` — Tailwind directives + global styles

## Entregáveis

- [x] Projeto Vite + React + TS + Tailwind configurado
- [x] Axios com JWT interceptor + retry + auto-refresh
- [x] AuthContext funcional (login, logout, user state)
- [x] ThemeContext com dark mode
- [x] LoginPage + RegisterPage
- [x] AuthGuard + RoleGuard
- [x] Lazy loading de todas as pages
- [x] Sentry integrado no frontend

## Critérios de Conclusão

- Register → Login → ver shell do dashboard → Logout → redirect para /login
- Token expirado → auto-refresh transparente
- Usuário viewer tentando acessar /team → redirect para /
- Dark mode toggle persiste entre reloads
