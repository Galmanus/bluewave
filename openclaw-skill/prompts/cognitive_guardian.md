## Protocolo de Análise de Compliance (OBRIGATÓRIO)

Para CADA análise de compliance, execute nesta ordem:

### PASSO 1: COLETA
- Carregar guidelines do tenant (cores, fontes, tom, dos/don'ts)
- Se imagem: analisar via vision antes de qualquer julgamento
- Se texto: extrair tom, vocabulário, estrutura

### PASSO 2: ANÁLISE DIMENSIONAL (8 dimensões)
Para cada dimensão, produzir:
- **Observação factual** (o que existe no asset)
- **Referência** (o que a guideline especifica)
- **Delta** (diferença mensurável: Delta-E para cor, match % para fonte)
- **Severidade** (crítico/alerta/info — com justificativa)

Dimensões obrigatórias:
1. Cores (Delta-E, contraste WCAG)
2. Tipografia (fonte, peso, caso, hierarquia)
3. Logo (presença, versão, proteção visual)
4. Tom & Voz (análise semântica vs. guideline)
5. Composição (regra dos terços, equilíbrio, whitespace)
6. Fotografia/Visual (estilo, saturação, iluminação)
7. Coerência Estratégica (arquétipos, promessa de marca)
8. Adequação de Canal (formato, proporção, plataforma)

### PASSO 3: SCORING
- Cada dimensão: 0-100 com peso definido
- Score final: média ponderada
- Threshold de aprovação: 70 (configurável)

### PASSO 4: ADVERSÁRIO INTERNO
Antes de entregar, pergunte-se:
- "Se eu fosse o designer que criou isso, como eu contestaria essa análise?"
- "Há alguma justificativa criativa legítima para os desvios encontrados?"
- "Estou sendo justo ou excessivamente rígido?"
Se alguma contestação for válida, ajuste a análise.

### PASSO 5: RECOMENDAÇÕES
Para cada violação crítica:
- Ação específica (não genérica)
- Valor exato (hex code, nome da fonte, dimensão)
- Prioridade (Tier 1: imediato, Tier 2: próximo ciclo, Tier 3: backlog)
