# MISSAO: Construir o Frontend do Braainner

Absolute loyalty to Manuel. FULL POWER MODE.

Wave, voce vai construir a interface frontend completa do Braainner -- o cerebro da plataforma Ialum. O projeto base ja existe em `/opt/ialum/braaineer/frontend/` (copiado do teu proprio frontend BlueWave). Voce tem acesso total a todos os arquivos.

---

## O QUE E O BRAAINNER

Braainner e o painel administrativo INTERNO da Ialum (so pra equipe, nao pra clientes). E onde a equipe:
- Transcreve reunioes, audios, videos e documentos
- Organiza conhecimento em pastas (como VSCode)
- Cruza informacoes pra criar "sinapses" (novos insights)
- Cria e gerencia agentes de IA

Tem TRES paginas. So tres. Nada mais.

---

## PAGINA 1: TRANSCRIPTOR (`/transcriptor`)

### O que faz
Recebe arquivos (audio, video, PDF, imagem), transcreve e permite interagir com a transcricao via IA.

### Layout
```
+--------------------------------------------------+
| [Audio] [Video] [Meet] [PDF] [Imagem]  <- tabs   |
+----------------------------+---------------------+
|                            |                     |
|   AREA DE UPLOAD           |   CHAT IA           |
|   (drag & drop)            |                     |
|                            |   Assistente que    |
|   Apos upload:             |   processa a        |
|   TRANSCRICAO              |   transcricao       |
|   - Orador 1 (azul)       |                     |
|   - Orador 2 (verde)      |   "transforma em    |
|   - Orador 3 (amarelo)    |    ata de reuniao"  |
|   com timestamps           |                     |
|                            |   Quick actions:    |
|   60% largura             |   [Criar ata]       |
|                            |   [Resumir]         |
|                            |   [Extrair decisoes]|
|                            |   [Salvar no        |
|                            |    Synapser]        |
|                            |                     |
|                            |   40% largura       |
+----------------------------+---------------------+
```

### Tabs de upload
- **Audio**: aceita mp3, wav, m4a, ogg
- **Video**: aceita mp4, webm, mov
- **Meet**: dados de uma reuniao Google Meet (abre modal pedindo link/dados)
- **PDF**: aceita .pdf
- **Imagem**: aceita jpg, png (pra OCR)

### Transcricao
- Identifica oradores (Orador 1, 2, 3...) com cores diferentes
- Mostra timestamp de cada segmento
- Scroll vertical quando a transcricao e longa

### Chat IA (lado direito)
- Streaming SSE (texto aparece em tempo real)
- O usuario manda instrucoes sobre a transcricao
- Exemplos: "transforma em ata", "resume os pontos", "extrai decisoes"
- Botao de salvar que abre modal pra escolher pasta do Synapser

### API endpoints
- `POST /api/v1/transcriptor/upload` -- upload do arquivo
- `POST /api/v1/transcriptor/chat` -- conversa sobre a transcricao
- `GET /api/v1/synapser/folders` -- lista pastas pra salvar

---

## PAGINA 2: SYNAPSER (`/synapser`)

### O que faz
File explorer tipo VSCode. Organiza todo o conhecimento da empresa em pastas. A IA cruza documentos selecionados pra criar "sinapses" (novos insights a partir de dados existentes).

### Layout
```
+----------------+------------------------+--------------------+
| ARVORE DE      | CONTEUDO               | CHAT IA            |
| PASTAS         |                        |                    |
|                | Quando seleciona um    | Assistente que     |
| > Marca        | arquivo, mostra aqui   | cruza informacoes  |
|   > DNA        | o conteudo renderizado |                    |
|   > Diretrizes | (markdown)             | "cruze esses 3     |
| > Comunicacao  |                        |  documentos"       |
|   > Editoriais | Toggle: [Ver] [Editar] |                    |
|   > Scripts    |                        | Mostra:            |
| > Produto      | Metadados:             | "3 arquivos        |
|   > Catalogo   | - Titulo               |  selecionados"     |
|   > Fichas     | - Tags                 |                    |
| > Atas         | - Fonte                | Quick actions:     |
| > Sinapses     | - Data                 | [Criar Sinapse]    |
| > Pesquisas    |                        | [Resumir]          |
|                |                        | [Encontrar         |
| [+ Pasta]      |                        |  conexoes]         |
| [+ Documento]  |                        |                    |
|                |                        |                    |
| 25% largura    | 45% largura            | 30% largura        |
+----------------+------------------------+--------------------+
```

### Arvore de pastas (esquerda)
- Pastas expansiveis com chevron que rotaciona
- Icones por tipo: pasta (folder), documento (file-text), ata (clipboard), sinapse (git-branch), pesquisa (search)
- **Checkboxes** em cada arquivo pra selecao multipla
- Busca/filtro no topo
- Botoes "+ Nova Pasta" e "+ Novo Documento"
- A estrutura padrao de pastas e:
  - Marca > DNA, Diretrizes
  - Comunicacao > Editoriais, Scripts
  - Produto > Catalogo, Fichas Tecnicas
  - Atas
  - Sinapses
  - Pesquisas

### Viewer/Editor (centro)
- Quando clica em um arquivo, mostra o conteudo
- Markdown renderizado no modo "Ver"
- Textarea no modo "Editar"
- Metadados no topo: titulo, tags (chips), fonte, data de criacao
- Botao salvar quando em modo edicao

### Chat IA (direita)
- Streaming SSE
- Quando tem arquivos selecionados (checkboxes), mostra badge "N arquivos selecionados"
- O chat ENVIA os IDs dos arquivos selecionados junto com a mensagem
- Quick actions: "Criar Sinapse", "Resumir selecionados", "Encontrar conexoes"
- Resultado pode ser salvo como novo documento em qualquer pasta

### API endpoints
- `GET /api/v1/synapser/tree` -- arvore de pastas e arquivos
- `GET /api/v1/synapser/files/{id}` -- conteudo de um arquivo
- `POST /api/v1/synapser/files` -- criar arquivo
- `PUT /api/v1/synapser/files/{id}` -- atualizar arquivo
- `POST /api/v1/synapser/folders` -- criar pasta
- `DELETE /api/v1/synapser/files/{id}` -- deletar arquivo
- `POST /api/v1/synapser/chat` -- chat IA com contexto dos arquivos selecionados

---

## PAGINA 3: AGENT CREATOR (`/agents`)

### O que faz
Tela dividida: conhecimento do Synapser de um lado, arvore de agentes SSL do outro. A IA cria e edita agentes com base no conhecimento selecionado.

### Layout
```
+----------------------+---------------------------+
| CONHECIMENTO         | AGENTES                   |
| (mini Synapser)      |                           |
|                      | > Seelleer                |
| > Marca              |   > busca_produtos        |
|   [x] DNA            |   > cotacao_frete         |
|   [ ] Diretrizes     |   > funil_vendas          |
| > Comunicacao        |   > faq_geral             |
|   [x] Editorial 1    |   > troca_devolucao       |
| > Produto            |   > escalacao_humana      |
|   [ ] Catalogo       | > Braainner               |
|                      |   > transcriptor          |
| "2 docs selecionados"|   > seekeer               |
|                      |   > synapser              |
| 35% largura          |   > agent_creator         |
|                      | > Publisheer              |
|                      |   > planner               |
|                      |   > coonteent             |
|                      |   > imaageer              |
|                      |   > scheduler             |
|                      | > Markeetteer             |
|                      |   > traakeer              |
|                      |   > anaalizeer            |
|                      |   > campaign_manager      |
|                      |                           |
|                      | Cada agente mostra:       |
|                      | - Nome                    |
|                      | - Badge modelo (Haiku/    |
|                      |   Sonnet/Opus)            |
|                      | - Qtd tools               |
|                      | - Checkbox pra selecionar |
|                      |                           |
|                      | 35% largura               |
+----------------------+---------------------------+
|                                                   |
|  CHAT IA (embaixo, 30% altura)                   |
|                                                   |
|  Context pills: [DNA da Marca] [Editorial 1]     |
|                 [busca_produtos] [funil_vendas]   |
|                                                   |
|  "Cria um agente de nutricao pet pro Seelleer    |
|   com base no DNA da marca e no editorial 1"     |
|                                                   |
|  Quick actions:                                   |
|  [Criar Agente] [Validar SSL] [Deploy]           |
|  [Listar Templates]                               |
|                                                   |
+---------------------------------------------------+
```

### Painel de conhecimento (esquerda)
- Mini file tree do Synapser (mesmo componente, compacto)
- Checkboxes pra selecionar documentos de contexto
- Badge mostrando quantos docs selecionados

### Painel de agentes (direita)
- Arvore por plataforma (Seelleer, Braainner, Publisheer, Markeetteer)
- Cada agente mostra: nome, badge do modelo (cor por tipo), quantidade de tools
- Clicar no agente abre modal com:
  - Conteudo SSL completo (syntax highlighted se possivel)
  - Metadados: modelo, temperature, max_tokens, lista de tools
  - Botao "Editar" (abre editor)
  - Botao "Deploy" (sincroniza com banco)
- Checkboxes pra selecionar agentes como contexto

### Chat IA (embaixo)
- Streaming SSE
- Mostra "context pills" -- chips com nomes dos docs e agentes selecionados
- Envia: `{ message, knowledge_ids: [...], agent_ids: [...] }`
- Quick actions: "Criar Agente", "Validar SSL", "Deploy", "Listar Templates"

### API endpoints
- `GET /api/v1/agents/tree` -- arvore de agentes por plataforma
- `GET /api/v1/agents/{agent_id}/ssl` -- conteudo SSL do agente
- `POST /api/v1/agents/create` -- criar agente via IA
- `POST /api/v1/agents/{agent_id}/deploy` -- deploy no banco
- `POST /api/v1/agents/chat` -- chat IA pra criacao/edicao de agentes
- `GET /api/v1/synapser/tree` -- reutiliza do Synapser

---

## STACK TECNICA

- **React 18** + TypeScript
- **Vite** (build tool)
- **Tailwind CSS** com theme customizado (dark/light)
- **lucide-react** pra icones
- **framer-motion** pra animacoes
- **react-router-dom** pra rotas
- **@tanstack/react-query** pra data fetching
- **react-dropzone** pra upload
- **react-markdown** pra renderizar markdown
- **sonner** pra toasts
- **Radix UI** pra componentes base (Dialog, Tabs, Select, Tooltip)

### Theme classes (Tailwind custom)
- Texto: `text-text-primary`, `text-text-secondary`, `text-text-tertiary`
- Background: `bg-background`, `bg-surface`, `bg-surface-raised`, `bg-accent-subtle`
- Border: `border-border`, `border-border-subtle`
- Accent: `text-accent`, `bg-accent`
- Tipografia: `text-display`, `text-heading`, `text-subheading`, `text-body`, `text-body-medium`, `text-caption`

### Projeto base
O frontend em `/opt/ialum/braaineer/frontend/` ja tem:
- Todos os componentes UI (Button, Card, Dialog, Tabs, Input, Select, Tooltip, DropZone, etc.)
- Contextos (ThemeContext, AuthContext)
- Lib helpers (api.ts, cn.ts)
- Hooks existentes
- Tailwind config com o theme completo
- Vite config

### O que voce precisa criar/modificar:
1. `src/App.tsx` -- rotas pro Braainner (3 paginas)
2. `src/components/AppLayout.tsx` -- sidebar com navegacao Braainner
3. `src/pages/TranscriptorPage.tsx` -- pagina 1 completa
4. `src/pages/SynapserPage.tsx` -- pagina 2 completa
5. `src/pages/AgentCreatorPage.tsx` -- pagina 3 completa
6. Componentes compartilhados que precisar (FileTree, ChatPanel, etc.)

---

## REGRAS

1. Escreva codigo COMPLETO, nao pseudocodigo
2. Cada arquivo deve funcionar -- sem placeholders "TODO"
3. Use os componentes UI existentes em `src/components/ui/`
4. Mantenha o padrao visual do BlueWave (dark theme, gradientes sutis, animacoes suaves)
5. Chat IA deve ter streaming SSE (igual WaveAgentPage.tsx existente)
6. Responsivo (mobile friendly com sidebar colapsavel)
7. TypeScript strict -- tipos pra tudo
8. O Synapser e o coracao do sistema -- capriche nele

---

## ORDEM DE EXECUCAO

1. Primeiro: `AppLayout.tsx` e `App.tsx` (navegacao e rotas)
2. Segundo: `SynapserPage.tsx` (a pagina mais importante)
3. Terceiro: `TranscriptorPage.tsx`
4. Quarto: `AgentCreatorPage.tsx`
5. Extraia componentes compartilhados (FileTree, ChatPanel) se fizer sentido

Comece agora. Escreva o codigo completo de cada arquivo.
