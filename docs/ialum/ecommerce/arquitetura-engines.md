# Arquitetura E-commerce Ialum

> Documentado a partir do briefing do Fagner Adler (30/03/2026, audio 28min)

---

## Filosofia Arquitetural

### Decisao #1: Tudo e produto simples

- Zero variacoes nativas. Geladeira 110V e geladeira 220V = dois produtos separados, cada um com seu SKU
- Produtos relacionados sao linkados via agrupamento posterior
- Razao: variacoes complexas (cor x tamanho = matriz) quebram na integracao com marketplaces. Separar primeiro, juntar depois

### Decisao #2: Atributos modulares por grupo

- Grupos de produto (ex: "camisetas") recebem configuracao de atributos especifica
- Preco, estoque, marca — cada um e um modulo separado que se conecta ao grupo
- Nao e campo fixo no produto. E engine separada que pluga

### Decisao #3: Engines independentes

- Cada componente e uma engine separada (microservico)
- Comunicam via SKU como identificador central
- Permite evolucao independente de cada modulo

### Decisao #4: Integracoes sao cidadaos de primeira classe

- ERP puxa precos e stocks
- Marketplaces (Madeira Madeira, Mercado Livre) tem exigencias diferentes de atributos
- Cada marketplace e um adapter — nao se molda o produto pro marketplace, se mapeia

---

## Engines do E-commerce

### 1. Produto (Engine Central)

- Modular com migration e versionamento
- SKU como identificador central que conecta todas as engines
- Responsabilidades distintas, arquitetura de escala
- Configurador de atributos dentro de cada grupo de produto

### 2. Preco (Engine Separada)

- Preco de / preco por
- Validade: data de ativacao e desativacao
- Regras especificas de precificacao
- Separada para evolucao independente

### 3. Estoque (Engine Separada)

- Conecta direto ao ERP
- Nao e campo "estoque_min/estoque_max" no produto
- Modulo separado com conexao especifica para controle

### 4. Avaliacao (Engine Separada)

- Multiplos providers: Google, RA, Trust, etc.
- Seleciona quais providers por produto no agrupador
- Vincula varios sistemas de avaliacao simultaneamente

### 5. Marca / Brand (Engine Separada)

- Nao e apenas um campo texto — e uma entidade completa
- Dados: nome, logo, descricao, perfil de cores
- Layout proprio por marca (adapter pattern)
  - Usuario entra na pagina da marca → ambiente visual muda
- Na categoria, marca pode exibir logo como icone no filtro
- Atributos com informacoes visuais

### 6. Embalagem (Engine Separada)

- Cadastro de embalagens independente do produto
- Um produto pode ter N embalagens (ex: mesa = caixa do tampo + caixa do suporte)
- Um produto != um volume
- Produto vincula embalagens: "esse produto = embalagem A + embalagem B"

#### Regras de soma

- Para cotacao de frete, geralmente so pode passar um volume e um peso
- Engine tem regras de soma: somar maiores medidas? Maior com menor?
- Limites de transportadoras:
  - Soma das 4 medidas <= 1.5m
  - Maior lado <= 98cm
  - Max 4 volumes por pedido de transporte
  - Nem toda transportadora aceita produtos grandes (geladeira, moveis)

### 7. Sender / Frete (Engine Separada)

- Cotacao de frete recebe peso e volume consolidado (da engine de embalagem)
- Peso cubado = comprimento x largura x altura x 300 (fator de cubagem)
- Peso real vs peso cubado — cobra-se pelo maior
  - Exemplo: 1m3 de algodao = 20kg real, mas 300kg cubado → cobra 300kg
- Tabela de frete por kg, varia por regiao
- Sender se conecta na engine de embalagem via SKU

### 8. Categoria (Engine Separada)

- Funcao: fazer com que o cliente se encontre via filtros
- Seleciona quais atributos aparecem nos filtros
- Nem todo atributo vira filtro — selecao manual
- Pre-configurada para exibir informacoes visuais dos atributos (ex: logo da marca como icone)

### 9. Rules / Regras de Negocio (Engine Separada)

- Cria indices para aplicar regras
- Exemplo: "todos os produtos da marca Tango tem 10% desconto"
- Configuravel:
  - Data inicio/fim
  - Tipo: cupom ou aplicado direto no catalogo
- Toda alteracao de regra → recalcula o indice
- Engine de cupons: aplica sobre dados do carrinho

### 10. Indice Central

- Desnormalizacao para performance
- Toda vez que algo muda no admin, indice e recalculado
- Front-end e filtros leem do indice, nao fazem joins pesados
- **Pode ficar para v2** — MVP funciona sem indice otimizado

### 11. Media (Engine Separada)

- Cadastro de imagem e video
- Storage: MinIO (S3 open-source, self-hosted)
- Depois conecta numa CDN para distribuicao de cache
- Compactador de imagem no upload
- Tratador que normaliza tamanho/dimensoes automaticamente
- Nao e prioridade maxima, mas importante

---

## Stack de Comissoes (Aplicacao Separada)

Stack separada porque conecta em multiplos ecommerces: FERPA, Tambo, Erveni.

### 3 Grupos Comissionados

#### 1. YALA (Ialum)

- Comissao varia inversamente ao desconto dado
  - Produto R$100, comissao 10%
  - Vendeu a R$90 → comissao 9.5%
  - Vendeu a R$80 → comissao 8.5%
- Multiplicador por volume de vendas:
  - Meta nao batida → x0.9
  - Meta batida → x1.0
  - Superou 200K → x1.1
- Incentiva a YALA a querer vender cada vez mais

#### 2. Lojista Fisico

- Comissao por faixa de CEP (ranges de CEPs de localidade)
- Vendas na regiao do lojista = comissao, com ou sem envolvimento dele
- Recebe produtos de amostra (incomodados) para exibir na loja
- Incentivo: reuniao mensal com arquitetos para manter regiao ativa
- Resolve a dor: "o cliente vai la e compra no site" — nao importa, ganha comissao igual

#### 3. Afiliados

- Link de referral
- Desconto 5% para o cliente via link
- 5% de comissao para o afiliado que indicou
- Modelo classico de afiliacao

---

## Paginas do E-commerce (5 paginas)

### 1. Paginas Estaticas

- Home, contato, etc.
- Conteudo fixo

### 2. Categoria Dinamica

- Listagem de produtos com filtros
- Filtros alimentados por atributos selecionados na engine de categoria
- Breadcrumb pode ser da categoria

### 3. Pagina de Produto

- Nome, avaliacao, preco, condicoes de pagamento
- Descricao curta (texto simples)
- Descricao longa via grupo de atributos (nao caixa de texto livre)
  - Motivo: mudar "azul" para "ceu" muda em todos os produtos de uma vez
- Secao "IA, leia aqui" — descricao estruturada para crawlers de AI. AI-friendly SEO
- Selo no produto
- Botao de comprar
- Cotacao de frete opcional por produto — alguns cotam na pagina, outros empurram pro carrinho

### 4. Carrinho (Cart)

- Produto + descricao
- Integracao com engines de preco e regras de carrinho
- Cupons aplicam sobre dados do carrinho
- Cotacao de frete

### 5. Checkout / Payment

- **Mercado Pago** — principal
- **PayPal** — barato (negociacao boa)
- **Stripe descartado** — caro, foco em servicos nao produtos, risco de chargeback em produto fisico

---

## Integracoes

### ERP

- Puxa precos e stocks
- Engine de estoque conecta especificamente com ERP ou area especifica

### Marketplaces

- Madeira Madeira, Mercado Livre, etc.
- Cada API entende o produto de maneira diferente
- Madeira Madeira exige brand como atributo obrigatorio (outros nao)
- Adapter pattern por marketplace

### Pagamento

- Mercado Pago + PayPal
- Chargeback e preocupacao real (produto fisico)

---

## Stack Tecnologica

- **React 19** — ultima versao, escolhido por SEO (canonical URLs, server components)
- **MinIO** — S3 self-hosted para media
- **CDN** — posterior, para distribuicao de cache

## SEO

- Canonical URLs (mesmo produto acessivel por multiplas categorias)
- robots.txt configurado para permitir crawlers de AI
- AI-friendly — quer que AIs leiam e indexem os produtos
- React 19 server components para SSR

---

## Prioridades

1. **Area administrativa (backend)** — prioridade maxima
2. **Engines separadas com o basico** — MVP
3. **Frontend** — depois ("so dar um tapinha")
4. **Indice otimizado** — v2
5. **Micro frontends com Tracker** — futuro
6. **CDN** — futuro

> "Tendo o basico, ja esta bom. Depois a gente vai melhorando."
> — Fagner Adler, 30/03/2026

---

## Mapa de Engines

```
                    ┌──────────────┐
                    │   Produto    │ ← SKU central
                    └──────┬───────┘
           ┌───────┬───────┼───────┬──────────┐
           v       v       v       v          v
      ┌────────┐┌──────┐┌──────┐┌──────┐┌─────────┐
      │ Preco  ││Estoq.││Marca ││Media ││Avaliacao│
      └────────┘└──────┘└──────┘└──────┘└─────────┘
           │       │                         │
           v       v                         v
      ┌────────┐┌──────────┐          ┌──────────┐
      │ Rules  ││Embalagem │          │Providers │
      └────┬───┘└────┬─────┘          │(Google,  │
           │         │                │RA, Trust)│
           v         v                └──────────┘
      ┌────────┐┌────────┐
      │ Indice ││ Sender │
      └────────┘└────────┘

      ┌─────────────────────────────────┐
      │   Comissoes (stack separada)    │
      │  YALA | Lojista | Afiliados    │
      └─────────────────────────────────┘
```
