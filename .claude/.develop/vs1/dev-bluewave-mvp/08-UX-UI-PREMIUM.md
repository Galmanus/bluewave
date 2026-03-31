# Fase 08 — UX/UI Premium Redesign 🟢

## Objetivo

Elevar a interface ao padrão de SaaS premium internacional (Linear, Vercel, Notion, Stripe Dashboard), com design system completo, dark mode, animações e acessibilidade.

## Componentes

### Design System
- **Color tokens**: CSS variables semânticas para light/dark mode (background, surface, border, text-primary/secondary/tertiary, accent, success, warning, danger)
- **Typography**: Inter font family. Scale: display (28px), heading (20px), subheading (16px), body (14px), caption (12px), mono (13px)
- **Spacing**: grid base 4px. Tokens de `space-xs` (4px) a `space-3xl` (48px)
- **Elevation**: 4 níveis de shadow (`shadow-xs` a `shadow-lg`) + `shadow-focus`
- **Border radius**: 5 níveis de `radius-sm` (6px) a `radius-full` (pill)

### 12 Componentes UI (`components/ui/`)

| Componente | Base | Descrição |
|------------|------|-----------|
| `Avatar` | — | Avatares com fallback iniciais |
| `Badge` | — | Status badges com variantes de cor |
| `Button` | — | Primary, secondary, ghost, loading state |
| `Card` | — | Container com elevation |
| `CommandPalette` | cmdk | ⌘K quick navigation |
| `Dialog` | Radix Dialog | Modais acessíveis |
| `DropZone` | react-dropzone | Upload drag-and-drop |
| `Input` | — | Text inputs com validação |
| `Select` | Radix Select | Dropdowns acessíveis |
| `Table` | — | Data tables com sorting |
| `Tabs` | Radix Tabs | Tab navigation animada |
| `Tooltip` | Radix Tooltip | Hover tooltips |

### Dark Mode
- CSS variables + atributo `data-theme`
- Persistência em localStorage
- Respeita `prefers-color-scheme` no primeiro load
- Toggle no header da app

### Animações (Framer Motion)
- Page transitions (fade + slide)
- Card hover (scale + shadow)
- Tab slide indicator
- Modal open/close
- Stagger fade-in em listas
- `prefers-reduced-motion` desativa tudo globalmente

### Acessibilidade (WCAG 2.1 AA)
- Contrast ratios adequados em light + dark
- Focus rings visíveis em todos os interativos
- Keyboard navigation completa
- `aria-labels` em todos os componentes
- Sem `confirm()` nativo — Radix Dialog customizado

### Redesign de Páginas
- Login/Register: gradient background, logo, password strength bar
- AppLayout: sidebar colapsável 240→64px, Lucide icons, theme toggle, user avatar
- AssetList: display typography, count badges, animated tab indicator
- AssetDetail: 2-panel 60/40, animações Framer Motion, Radix Dialog para delete
- Upload: react-dropzone, 60vh drop zone, animated states, success checkmark
- Team: initials avatars, slide-down invite panel, Radix Dialog para delete

## Entregáveis

- [x] Design system com CSS variables (light + dark)
- [x] 12 componentes UI acessíveis
- [x] Dark mode funcional com persistência
- [x] Framer Motion em todas as interações
- [x] ⌘K command palette
- [x] Todas as páginas redesenhadas
- [x] WCAG 2.1 AA compliance
- [x] `prefers-reduced-motion` respeitado

## Critérios de Conclusão

- UI premium em light + dark mode sem artefatos visuais
- Tab com teclado navega todos os interativos
- Screen reader lê labels corretos
- Animações desativam com reduced-motion
- Command palette abre com ⌘K e navega para qualquer página
