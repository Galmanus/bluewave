
# Bluewave — Brief de Design UX/UI para Frontend de Classe Mundial

> **Público:** Designer UX/UI Sênior / Engenheiro Frontend
> **Objetivo:** Elevar o frontend do MVP SaaS Bluewave para atingir os mais altos padrões estéticos do mercado internacional — no nível de Linear, Vercel, Notion, Stripe Dashboard e Figma.

---

## 1. Contexto do Produto

Bluewave é uma **plataforma SaaS multi-tenant** para agências de marketing, equipes audiovisuais e produtoras. Usuários fazem upload de media assets (imagens/vídeos), a IA gera automaticamente captions e hashtags, e um workflow interno de aprovação (draft → pending → approved) governa a publicação de conteúdo.

**Usuários primários:** Diretores criativos, gestores de conteúdo, editores e executivos de conta — pessoas que vivem em ferramentas visuais diariamente e têm zero tolerância para interfaces desajeitadas.

**Fluxos principais do usuário:**
1. Registrar uma nova equipe → convidar membros com roles (admin/editor/viewer)
2. Upload de media assets → IA gera captions + hashtags → editar metadados
3. Submeter asset para aprovação → admin aprova ou rejeita com comentário
4. Navegar/filtrar/buscar na biblioteca de assets por status

---

## 2. Filosofia & Princípios de Design

### 2.1 Identidade Visual

| Atributo | Direção |
|----------|---------|
| **Personalidade** | Profissional porém acessível. Confiante, limpo, sem pressa. Como uma ferramenta criativa premium — não um dashboard corporativo. |
| **Estética** | Minimalismo escandinavo encontra polimento do Vale do Silício. Espaço em branco é uma feature. Cada elemento justifica sua presença. |
| **Sistema de cores** | Paleta primária suave com accent vibrante usado com moderação para CTAs e status. Suporte a dark mode desde o primeiro dia. |
| **Tipografia** | Inter ou Geist Sans como fonte do sistema. Hierarquia tipográfica clara: display, heading, body, caption, mono. Nenhuma fonte abaixo de 12px. |
| **Iconografia** | Lucide React ou Phosphor Icons — stroke weight consistente (1.5px), opticamente alinhados, monocromáticos. Nunca decorativos, sempre funcionais. |
| **Ilustrações** | Nenhuma no MVP. Empty states usam micro-copy + um único ícone sutil. Sem imagens de banco, sem ilustrações cartoon. |

### 2.2 Princípios Fundamentais

1. **Densidade sem desordem** — Mostre informação eficientemente (como Linear) mas deixe cada elemento respirar. Sem aperto.
2. **Revelação progressiva** — Mostre o mínimo por padrão. Revele complexidade no hover, click ou expand. Rejeite vício em modais — use expansão inline, slide-overs e command palettes.
3. **Movimento com propósito** — Cada animação deve servir uma função: orientar o usuário, confirmar uma ação ou mostrar mudança de estado. Duração: 150–250ms. Easing: `cubic-bezier(0.4, 0, 0.2, 1)`. Sem bouncing, sem movimento gratuito.
4. **Feedback instantâneo** — Atualizações otimistas de UI para mutações (aprovar, rejeitar, salvar). Skeleton loaders para fetches iniciais. Nunca mostre uma tela branca em branco.
5. **Acessível por padrão** — WCAG 2.1 AA no mínimo. Focus rings na navegação por teclado. Ratios de contraste ≥ 4.5:1 para texto. Labels para screen-reader em cada elemento interativo.

---

## 3. Especificação do Design System

### 3.1 Tokens de Cor

```
/* Light mode */
--background:        #FAFAFA     /* fundo da página */
--surface:           #FFFFFF     /* cards, sidebar, modais */
--surface-elevated:  #FFFFFF     /* popovers, dropdowns — com shadow */
--border:            #E5E7EB     /* bordas padrão */
--border-subtle:     #F3F4F6     /* divisores, linhas separadoras */

--text-primary:      #111827     /* headings, ênfase */
--text-secondary:    #6B7280     /* texto body, descrições */
--text-tertiary:     #9CA3AF     /* placeholders, meta, timestamps */
--text-inverse:      #FFFFFF     /* texto em fundos coloridos */

--accent:            #2563EB     /* CTA primário, links, estados ativos */
--accent-hover:      #1D4ED8     /* estado hover do accent */
--accent-subtle:     #EFF6FF     /* fundos tintados para itens ativos */

--success:           #059669     /* aprovado, confirmado */
--success-subtle:    #ECFDF5     /* tint de fundo success */
--warning:           #D97706     /* pendente, atenção */
--warning-subtle:    #FFFBEB     /* tint de fundo warning */
--danger:            #DC2626     /* rejeitado, destrutivo */
--danger-subtle:     #FEF2F2     /* tint de fundo danger */

/* Dark mode */
--background:        #09090B
--surface:           #18181B
--surface-elevated:  #27272A
--border:            #27272A
--border-subtle:     #1F1F23
--text-primary:      #FAFAFA
--text-secondary:    #A1A1AA
--text-tertiary:     #71717A
--accent:            #3B82F6
--accent-hover:      #60A5FA
--accent-subtle:     #172554
```

### 3.2 Escala Tipográfica

| Token | Tamanho | Peso | Line Height | Uso |
|-------|---------|------|-------------|-----|
| `display` | 28px | 700 | 1.2 | Títulos de página (Assets, Team) |
| `heading` | 20px | 600 | 1.3 | Headers de seção, títulos de card |
| `subheading` | 16px | 600 | 1.4 | Subseções, títulos de dialog |
| `body` | 14px | 400 | 1.5 | Texto padrão, descrições |
| `body-medium` | 14px | 500 | 1.5 | Labels, itens de navegação |
| `caption` | 12px | 400 | 1.4 | Info meta, timestamps, badges |
| `mono` | 13px | 400 | 1.5 | Código, tamanhos de arquivo, IDs |

**Stack de fontes:** `'Inter', 'system-ui', '-apple-system', 'Segoe UI', sans-serif`

### 3.3 Sistema de Espaçamento

Use um grid base de 4px: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96`

| Token | Valor | Uso |
|-------|-------|-----|
| `space-xs` | 4px | Gaps de ícones inline |
| `space-sm` | 8px | Padding de badges, espaçamento compacto |
| `space-md` | 12px | Padding de inputs, gaps de listas |
| `space-lg` | 16px | Padding de cards, gaps de seções |
| `space-xl` | 24px | Entre seções |
| `space-2xl` | 32px | Padding de página |
| `space-3xl` | 48px | Quebras de seções maiores |

### 3.4 Elevação & Shadows

| Nível | Shadow | Uso |
|-------|--------|-----|
| `shadow-xs` | `0 1px 2px rgba(0,0,0,0.05)` | Inputs, cards sutis |
| `shadow-sm` | `0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)` | Cards, sidebar |
| `shadow-md` | `0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)` | Dropdowns, popovers |
| `shadow-lg` | `0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)` | Modais, command palette |
| `shadow-focus` | `0 0 0 2px var(--accent), 0 0 0 4px rgba(37,99,235,0.2)` | Focus ring para acessibilidade |

### 3.5 Border Radius

| Token | Valor | Uso |
|-------|-------|-----|
| `radius-sm` | 6px | Badges, elementos pequenos |
| `radius-md` | 8px | Botões, inputs, cards |
| `radius-lg` | 12px | Modais, painéis, cards grandes |
| `radius-xl` | 16px | Cards de feature, elementos hero |
| `radius-full` | 9999px | Avatares, pills, toggles |

---

## 4. Especificação da Biblioteca de Componentes

### 4.1 Botões

| Variante | Aparência | Uso |
|----------|-----------|-----|
| **Primary** | Fundo accent sólido, texto branco, shadow sutil | CTAs principais: Upload, Save, Approve |
| **Secondary** | Borda sutil, bg transparente, texto escuro | Cancel, Back, ações secundárias |
| **Ghost** | Sem borda, sem bg, apenas texto com hover bg | Ações inline, botões de ícone |
| **Danger** | Fundo vermelho sólido ou borda vermelha outlined | Delete, Reject (confirmação obrigatória) |

Todos os botões: `radius-md`, altura 36px (padrão) / 32px (pequeno) / 40px (grande). Transição 150ms. Desabilitado: 40% opacidade + sem eventos de ponteiro. Loading: spinner substitui o label, largura preservada.

### 4.2 Inputs & Formulários

- **Inputs de texto**: 40px de altura, borda de 1px, `radius-md`. No focus: borda muda para accent + brilho externo sutil (`shadow-focus`). Placeholder em `text-tertiary`.
- **Textareas**: Mesmo estilo, auto-resize até max-height.
- **Select dropdowns**: Estilizados custom (não `<select>` nativo). Usar Radix UI ou Headless UI para acessibilidade. Abertura/fechamento animados.
- **Layout de formulário**: Label acima do input, gap de 4px. Agrupar campos relacionados. Mensagens de erro aparecem abaixo do input em cor `danger` com ícone.

### 4.3 Cards & Containers

- **Card de asset**: Surface branco, borda de 1px, `radius-lg`. Área de thumbnail com container aspect-ratio. No hover: translate-y -1px + `shadow-md`. Transição suave de 200ms.
- **Cards de estatísticas**: Tint de fundo sutil, sem borda, `radius-lg`.
- **Painel de detalhes**: Largura total, dividido em seções lógicas com divisores sutis.

### 4.4 Badges de Status

| Status | Light Mode | Dark Mode |
|--------|------------|-----------|
| Draft | Bg cinza, texto cinza | Bg zinc-800, texto zinc-300 |
| Pending Approval | Bg amber-50, texto amber-700 | Bg amber-900/50, texto amber-300 |
| Approved | Bg green-50, texto green-700 | Bg green-900/50, texto green-300 |

Estilo: `radius-full`, fonte `caption`, 6px padding horizontal, 2px vertical. Indicador de ponto (círculo de 4px) antes do texto.

### 4.5 Navegação (Sidebar)

- **Largura**: 240px (recolhível para modo somente ícones de 64px por preferência do usuário)
- **Área do logo**: 56px de altura, marca + wordmark. No modo recolhido: apenas marca.
- **Itens de nav**: 36px de altura, `radius-md`, 12px de padding. Item ativo: bg accent-subtle + texto accent + barra lateral accent de 2px.
- **Área do usuário (inferior)**: Avatar (círculo de 32px) + nome + badge de role. Dropdown para settings/logout.
- **Divisores**: 1px `border-subtle`, 8px de margem vertical.
- **Transição**: Recolher/expandir com 200ms ease. Conteúdo na área principal ajusta fluidamente.

### 4.6 Barra de Header

- **Altura**: 56px
- **Conteúdo**: Trilha de breadcrumb (contexto da página), gatilho de busca (⌘K), sino de notificação (futuro), avatar do usuário.
- **Busca**: Abre um overlay de command palette (como ⌘K do Linear/Notion) para navegação rápida e busca de assets.
- **Fixo**: Fixado no topo da área de conteúdo, borda inferior sutil.

### 4.7 Tabelas (Página de Equipe)

- **Estilo**: Sem bordas visíveis entre linhas. `border-subtle` sutil entre header e body.
- **Hover de linha**: Fundo tintado (`gray-50` / `zinc-800`).
- **Altura da linha**: Mínimo 48px para alvos de clique confortáveis.
- **Alinhamento**: Texto à esquerda, números à direita, ações à direita.
- **Empty state**: Mensagem centralizada com ícone sutil e botão CTA.

### 4.8 Notificações Toast

- **Posição**: Inferior-direita (não superior-direita — evita conflito com ações do header)
- **Estilo**: Bg surface-elevated, `shadow-lg`, `radius-lg`. Borda esquerda accent (4px) codificada por cor conforme tipo.
- **Duração**: Success 3s, Error 5s, com barra de progresso na parte inferior.
- **Animação**: Desliza da direita, fade out.

### 4.9 Empty States

- **Padrão**: Centralizado verticalmente na área de conteúdo. Ícone monocromático único (48px), heading, descrição (máximo 2 linhas), botão CTA único.
- **Tom**: Encorajador e orientado à ação. "No assets yet" → "Faça upload do seu primeiro asset para começar."

### 4.10 Diálogos de Confirmação

- **Substituir `confirm()` nativo** com componente de diálogo customizado.
- **Estrutura**: Overlay + painel centralizado. Ícone (warning/danger), título, descrição, dois botões (cancel + confirm).
- **Ações destrutivas**: Botão de confirmação em cor danger. Exigir digitação do nome do item para exclusões irreversíveis (opcional para MVP).

---

## 5. Especificação de Design Página por Página

### 5.1 Página de Login

**Referência:** Vercel login, Linear login

- Card centralizado em tela cheia sobre fundo com gradiente sutil (gradiente `background → surface` ou mesh sutil).
- Logo no topo do card (marca + wordmark, 32px de altura).
- Input de email → Input de senha → Botão Sign in (primary largura total).
- Link "Forgot password?" abaixo do formulário (mesmo se não estiver conectado — mostrar polimento).
- Linha divisória com "or" → Link "Create a team account".
- Footer: linha de copyright sutil.
- **Dark mode**: Card recebe `surface-elevated` com brilho de borda sutil.

### 5.2 Página de Registro

Mesmo layout do login mas com 4 campos: Team Name, Full Name, Email, Password. Indicador de força da senha (barra segmentada green/yellow/red). Texto de passo: "Você será o admin da sua nova equipe."

### 5.3 Biblioteca de Assets (Página de Lista)

**Referência:** Notion gallery view, Figma file browser, Frame.io

- **Seção de header**: Título da página "Assets" (tamanho display) + badge de contagem de assets + botão Upload (primary).
- **Barra de filtros**: Tabs horizontais (All | Draft | Pending | Approved) com badges de contagem por status. Lado direito: toggle grid/list view, dropdown de ordenação.
- **Grid de assets**:
  - Responsivo: 4 colunas (xl), 3 (lg), 2 (md), 1 (sm).
  - Cada card: Área de thumbnail 16:10 (object-cover para imagens reais, ícone de tipo centralizado para placeholder) + overlay no hover mostrando ações rápidas (ícone de olho para preview, ícone de edição).
  - Abaixo do thumbnail: caption (truncado 1 linha), badge de status, ícone de tipo de arquivo, timestamp.
  - Animação de entrada sutil (stagger fade-in no carregamento inicial).
- **Paginação**: "Load more" com infinite scroll OU paginação numerada com contagem total.
- **Empty state**: Prompt com ilustração de upload.

### 5.4 Página de Detalhe do Asset

**Referência:** Frame.io asset detail, Dropbox file preview

- **Layout**: Duas colunas no desktop. Esquerda 60%: área de preview grande. Direita 40%: painel de metadados.
- **Área de preview**:
  - Container de fundo escuro com mídia centralizada.
  - Para imagens: preview real da imagem (servir do backend `/uploads/` ou gerar thumbnails).
  - Para vídeos: placeholder com ícone de play.
  - Botão de toggle fullscreen no canto.
- **Painel de metadados**:
  - Badge de status (proeminente, topo do painel).
  - Alerta de comentário de rejeição (se rejeitado — banner yellow/red).
  - **Campo de caption**: Textarea editável com contagem de caracteres. Auto-save no blur com confirmação sutil "Saved".
  - **Campo de hashtags**: Componente tag-input (chips que podem ser removidos individualmente, digite para adicionar). Não um input de texto raw.
  - **Seção de info do arquivo**: Recolhível, mostra tipo, tamanho, dimensões, enviado por, data de envio.
  - **Timeline de atividade** (preparado para o futuro): Placeholder de seção para histórico de aprovação.
- **Barra de ações** (fixada na parte inferior do painel ou flutuante):
  - Botões Submit / Approve / Reject — dependentes do contexto por status + role.
  - Menu mais (⋯) para delete, re-gerar IA, download.

### 5.5 Página de Upload

**Referência:** Dropbox upload, WeTransfer

- **Drop zone**: Grande, centralizada, ocupa 70% da altura do viewport. Borda tracejada com ícone. Borda animada no drag-over (borda se torna accent sólida, fundo pulsa sutilmente).
- **Suporte multi-arquivo** (UI preparada para o futuro): Mostrar lista de arquivos abaixo da drop zone com barras de progresso individuais.
- **Progresso**: Barra de progresso circular ou horizontal com porcentagem. Nome e tamanho do arquivo exibidos.
- **Estado de sucesso**: Animação de checkmark → botão "View asset" → auto-redirect após 2s.
- **Estado de erro**: Banner vermelho com botão de retry por arquivo.

### 5.6 Página de Equipe

**Referência:** Linear team settings, Notion workspace members

- **Header**: Título "Team" + contagem de membros + botão "Invite".
- **Formulário de convite**: Painel slide-down (não um modal) com nome, email, senha, seletor de role. Seletor de role mostra descrição de cada role no hover/focus.
- **Lista de membros**: Tabela limpa com:
  - Avatar (baseado em iniciais, colorido por role — azul para admin, verde para editor, cinza para viewer).
  - Nome + email.
  - Dropdown de role (edição inline).
  - Data de entrada.
  - Menu de ações (⋯) → Mudar role, Remover.
- **Linha do usuário atual**: Destaque sutil, label "(you)", não pode mudar próprio role.

---

## 6. Especificação de Micro-Interações & Animações

| Interação | Animação | Duração | Easing |
|-----------|----------|---------|--------|
| Transição de página | Fade in + 8px translate-y | 200ms | ease-out |
| Hover de card | Translate-y -2px + elevação de shadow | 200ms | ease |
| Pressionar botão | Scale 0.98 | 100ms | ease |
| Troca de tab | Underline desliza para nova tab | 250ms | spring |
| Recolher sidebar | Transição de largura + rotação de ícone | 200ms | ease-in-out |
| Toast entrar | Desliza da direita | 300ms | spring |
| Toast sair | Fade out + translate-y 8px | 200ms | ease-in |
| Pulso do skeleton | Opacidade 0.4 → 0.7 loop | 1.5s | ease-in-out |
| Mudança de status | Cross-fade de cor do badge | 300ms | ease |
| Drag over zone | Animação de borda tracejada + pulso de bg | contínuo | linear |
| Checkmark de sucesso | Desenho de path SVG | 400ms | ease-out |
| Modal abrir | Opacidade 0→1 + scale 0.95→1 | 200ms | spring |
| Modal fechar | Opacidade 1→0 + scale 1→0.95 | 150ms | ease-in |

---

## 7. Breakpoints Responsivos

| Breakpoint | Largura | Mudanças de Layout |
|------------|---------|-------------------|
| `sm` | ≥640px | Coluna única → grid 2-col |
| `md` | ≥768px | Sidebar aparece (estava oculta). 2-col → grid 3-col. |
| `lg` | ≥1024px | Detalhe do asset vira 2 painéis. |
| `xl` | ≥1280px | Grid de assets 4-col. Sidebar mais larga. |
| `2xl` | ≥1536px | Container max-width centralizado. Mais espaço para respirar. |

**Mobile (< 768px):** Sidebar se torna overlay fullscreen acionado pelo hamburger. Header simplifica para logo + hamburger + avatar. Barra de ações inferior para detalhe do asset.

---

## 8. Estratégia de Dark Mode

- Implementar via CSS variables alternadas por atributo `data-theme="dark"` no `<html>`.
- Controle de toggle: na área do usuário da sidebar ou header. Respeitar `prefers-color-scheme` na primeira visita.
- **Não** simplesmente inverter as cores. Dark mode usa proporções diferentes de tint/shade:
  - Fundos são zinc/neutral escuros, não preto puro.
  - Contraste de texto é mais suave (não branco puro — usar `#FAFAFA`).
  - Cores accent mudam levemente para mais brilhante para legibilidade.
  - Bordas se tornam mais sutis (contraste menor).
  - Shadows são substituídos por brilhos de borda sutis ou removidos inteiramente.

---

## 9. Bibliotecas de Componentes Recomendadas

Para velocidade de implementação sem sacrificar qualidade:

| Biblioteca | Uso |
|------------|-----|
| **Radix UI Primitives** | Componentes base acessíveis e sem estilo (Dialog, Dropdown, Tooltip, Tabs, Select) |
| **Tailwind CSS** | Estilização utility-first (já instalado) |
| **tailwind-merge + clsx** | Utilitários de merge de classes para gerenciamento de variantes |
| **Framer Motion** | Animações de nível produção (transições de página, animações de layout, drag) |
| **Lucide React** | Conjunto de ícones consistente e limpo (já tree-shakeable) |
| **cmdk** | Componente de command palette (⌘K) |
| **react-dropzone** | Handling robusto de drag-and-drop de arquivos |
| **sonner** | Notificações toast melhores (substituir react-hot-toast — animações melhores) |

---

## 10. Checklist de Qualidade

Antes de considerar o redesign completo, validar:

- [ ] Cada página carrega em < 100ms percebido (skeleton + UI otimista)
- [ ] Dark mode funciona em cada página sem glitches visuais
- [ ] Navegação por Tab/teclado funciona em cada elemento interativo
- [ ] Nenhum texto abaixo do ratio de contraste WCAG AA (4.5:1)
- [ ] Cada botão tem estado de loading + desabilitado
- [ ] Cada formulário mostra erros de validação inline
- [ ] Empty states existem para cada view de lista/grid
- [ ] Layout responsivo testado em 375px, 768px, 1024px, 1440px
- [ ] Animações respeitam `prefers-reduced-motion` (desabilitadas quando configurado)
- [ ] Sem scroll horizontal em nenhuma largura de viewport
- [ ] Todos os ícones são consistentemente dimensionados e opticamente alinhados
- [ ] Cores dos badges de status são consistentes entre views de lista e detalhe
- [ ] Notificações toast não empilham além de 3 visíveis
- [ ] `confirm()` nativo é totalmente substituído por diálogos customizados

---

## 11. Restrições Técnicas

O designer/implementador deve trabalhar dentro destas limitações:

- **React 18 + TypeScript** — Todos os componentes devem ser tipados.
- **Tailwind CSS** — Método principal de estilização. Estender `tailwind.config.js` com os design tokens acima.
- **Vite** — Bundler. HMR rápido. Sem Webpack.
- **React Router DOM v6** — Routing já está configurado. Preservar estrutura de rotas.
- **TanStack React Query** — Todo data fetching usa hooks existentes em `src/hooks/`. Não substituir.
- **Cliente de API existente** — `src/lib/api.ts` com Axios + retry + interceptors. Não substituir.
- **AuthContext** — Estado de auth é gerenciado em `src/contexts/AuthContext.tsx`. Estender, não reescrever.
- **Docker Compose** — Frontend roda dentro de um container com volume mounts. `npm run dev` via Vite.

---

## 12. Entregáveis Esperados

1. **Config Tailwind estendida** com sistema completo de design tokens (cores, tipografia, espaçamento, shadows, radii).
2. **Biblioteca de componentes reutilizáveis** em `src/components/ui/` — Button, Input, Select, Badge, Card, Dialog, Toast, Avatar, Tabs, DropZone, Table, Tooltip, CommandPalette.
3. **Páginas redesenhadas** — Todas as 7 páginas reconstruídas usando a nova biblioteca de componentes.
4. **Toggle de dark mode** — Implementação funcional com persistência (localStorage).
5. **Camada de animação** — Integração do Framer Motion para transições de página, interações de cards e micro-interações.
6. **Auditoria de acessibilidade** — Navegação por teclado e suporte a screen reader verificados.
