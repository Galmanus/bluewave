# Ialum — Documento de Tecnologia

**Versao:** 4.0
**Data:** Fevereiro 2026

---

## Visao Geral

Ialum e uma plataforma de inteligencia artificial composta por quatro plataformas interconectadas — **Braainner**, **Seelleer**, **Publisheer** e **Markeetteer** — que cobrem gestao de conhecimento, atendimento e vendas, criacao de conteudo e inteligencia de marketing.

A arquitetura e construida sobre plataformas open source orientadas a IA, interconectadas por sistemas proprietarios e unificadas por um banco de dados unico. Cada modulo funciona de forma independente ou integrada, adaptando-se a qualquer segmento de negocio.

O diferencial central e transformar dados brutos — conversas, documentos, audios, imagens, metricas — em **inteligencia estruturada e acionavel**, alimentando continuamente todas as operacoes comerciais da empresa.

---

## Principios da Plataforma

### ID Unico Cross-Plataforma

Todas as aplicacoes compartilham um **ID unico de visitante/lead** que acompanha o contato em toda a sua jornada — da descoberta a pos-venda. Quando um visitante interage com qualquer ponto de contato (uma landing page no Paagees, uma conversa no Taalkeer, um conteudo no Publisheer), ele e identificado e rastreado como uma unica pessoa.

Na pratica:

- Um lead capturado no **Paagees** e cadastrado instantaneamente no **Taalkeer** como contato, pronto para atendimento
- O **Traakeer** rastreia esse ID por eventos mapeados para cada fase da jornada: descoberta, consideracao, compra e pos-venda
- Qualquer aplicacao pode acionar acoes sobre esse lead: o **Seelleer** envia mensagens, o **Publisheer** segmenta conteudo, o **Markeetteer** ativa ou desativa campanhas
- O **Coonteext** compila tudo que se sabe sobre esse lead a partir de todas as fontes, e o **Braainner** armazena os padroes identificados
- Rotas automatizadas direcionam o lead conforme sua qualificacao: desde nurturing por conteudo ate acionamento direto de um especialista de vendas

O ID unificado elimina silos entre marketing, vendas e atendimento. O lead nao "recomeca" ao mudar de canal — todo o historico, contexto e qualificacao o acompanham.

### Modelo de Entrega

A entrega segue sempre duas etapas, independente do modelo de infraestrutura:

1. **Miniconsultoria** — Entendimento dos requisitos do cliente, mapeamento de necessidades e planejamento da implantacao
2. **Implantacao** — Time de TI (casos simples) ou time de desenvolvimento configura e coloca tudo em funcionamento, utilizando IA nos servidores para maximizar produtividade

Apos o setup, o **time Ialum continua acompanhando ativamente** a operacao do cliente.

### Modelo de Infraestrutura

O modelo padrao e **servidor dedicado (VPS) por cliente** — com banco de dados isolado, storage proprio e acesso tecnico exclusivo pela Ialum. Este modelo e obrigatorio para plataformas que lidam com dados sensiveis (Braainner, Ecommerceer) por questoes de LGPD e privacidade.

Para aplicacoes com entregas mais pontuais — como o **Seendeer** (agregador de frete), o **Taalkeer** e o **Paagees** — existe uma versao **multi-tenant SaaS** voltada a pequenas empresas que precisam de modulos especificos sem a necessidade de um servidor dedicado. Mesmo nestes casos, a configuracao inicial (tabelas de frete, setup de canais etc.) e realizada pelo time Ialum, com uma taxa de setup.

---

## As 4 Plataformas

---

### 1. Braainner — Gestao de Conhecimento

O cerebro da operacao. Captura, estrutura, pesquisa e disponibiliza todo o conhecimento da empresa para as demais plataformas.

**Dor que resolve:** Dados desorganizados, reunioes perdidas, conhecimento disperso entre pessoas e sistemas.

#### Modulos:

**Transcriptor** `Ialum.Braainner.Transcriptor`
| | |
|---|---|
| **Funcao** | Captura e converte dados nao estruturados em texto estruturado. Processa reunioes (Google Meet), videos (YouTube), PDFs, imagens e posts de redes sociais. Suporta audio longo, OCR e analise visual por IA. |
| **Stack base** | Whisper |
| **Diferenciais** | Suporte a multiplos formatos de entrada em um unico fluxo. Processamento automatico sem intervencao manual. |
| **Integracoes** | Alimenta o Reminder com transcricoes estruturadas. Dados capturados ficam disponiveis para o Seekeer, o Synapser e qualquer modulo que consulte o Braainner. |

**Reminder** `Ialum.Braainner.Reminder`
| | |
|---|---|
| **Funcao** | Repositorio de conhecimento compilado com busca semantica. Armazena resumos, notas, descricoes de produtos, estudos de caso e analises — todos com embeddings vetoriais para recuperacao inteligente. |
| **Stack base** | pgvector |
| **Diferenciais** | Armazena apenas conhecimento compilado, nunca dados brutos — garantindo qualidade e relevancia. Busca semantica unificada por vetores em toda a base. |
| **Integracoes** | Recebe transcricoes do Transcriptor, pesquisas externas do Seekeer, insights do Coonteext, dados de performance do Publisheer e tendencias do Markeetteer. E a fonte central que o Orchestraatoor, o Plaanner, o Coonteent e o Analiizeer consultam para contextualizar suas operacoes. |

**Seekeer** `Ialum.Braainner.Seekeer`
| | |
|---|---|
| **Funcao** | Motor de pesquisa externa que busca informacoes na web, em bases de dados publicas e em fontes especializadas para enriquecer a base de conhecimento. Compila referencias, tendencias de mercado e dados complementares que nao existem internamente. |
| **Stack base** | LLM + APIs de busca |
| **Diferenciais** | Fonte de dados externa integrada nativamente ao Braainner — pesquisa, compila e armazena automaticamente sem que o usuario precise sair da plataforma. |
| **Integracoes** | Resultados sao armazenados no Reminder e ficam disponiveis para todos os modulos. O Plaanner do Publisheer utiliza pesquisas do Seekeer para embasar editoriais com dados de mercado atualizados. O Orchestraatoor pode acionar pesquisas para responder perguntas complexas durante atendimentos. |

**Synapser** `Ialum.Braainner.Synapser`
| | |
|---|---|
| **Funcao** | Interface conversacional (RAG) onde o usuario dialoga com sua base de conhecimento. Cruza informacoes, identifica padroes e gera insights sob demanda. |
| **Stack base** | pgvector + LLM |
| **Diferenciais** | Permite cruzar dados de todas as fontes (transcricoes, pesquisas, conversas, metricas) em uma unica conversa. O usuario constroi conexoes entre conhecimentos de forma interativa. |
| **Integracoes** | Acessa todo o repositorio do Reminder, incluindo dados vindos do Coonteext, do Seekeer e das metricas do Markeetteer. Insights gerados podem ser salvos de volta no Reminder para uso por outros modulos. |

**Agent Creator** `Ialum.Braainner.AgentCreator`
| | |
|---|---|
| **Funcao** | Construtor de agentes especializados sem codigo. Um meta-agente guia o usuario na criacao de agentes para qualquer funcao da plataforma. |
| **Stack base** | Claude / GPT |
| **Diferenciais** | Acessivel a usuarios nao tecnicos. Criacao conversacional guiada por IA. Agentes criados podem operar em qualquer modulo (Seelleer, Publisheer, Markeetteer). |
| **Integracoes** | Os agentes criados aqui sao usados pelo Orchestraatoor do Seelleer, pelos editores do Publisheer e pelos analistas do Markeetteer. Carrega automaticamente schemas Pydantic do sistema para garantir compatibilidade. |

---

### 2. Seelleer — Atendimento e Vendas

Central inteligente de atendimento ao cliente com IA aplicada em todas as camadas — da comunicacao multicanal a cotacao de frete, passando por orquestracao de multiplas IAs e inteligencia de contexto.

**Dor que resolve:** Atendimento fragmentado, perda de contexto entre canais, processos de venda manuais e lentos.

#### Modulos:

**Taalkeer** `Ialum.Seelleer.Taalkeer`
| | |
|---|---|
| **Funcao** | Infraestrutura de comunicacao omnichannel. Centraliza WhatsApp (com gestao completa de instancias, envio de mensagens em massa, chatbots e webhooks via Evolution API), Instagram, Facebook Messenger, e-mail, chat do site e demais canais em uma unica interface. Gerencia historico de contatos, equipes e filas de atendimento. |
| **Stack base** | Chatwoot + Evolution API |
| **Diferenciais** | Base omnichannel robusta com camadas de IA proprietarias por cima. Gestao completa de WhatsApp via Evolution (instancias, massa, chatbots, webhooks). |
| **Integracoes** | Recebe automaticamente leads capturados pelo Paagees ja vinculados ao ID unico do ecossistema — o contato chega com todo o historico de navegacao e qualificacao rastreados pelo Traakeer. E a base sobre a qual o Orchestraatoor, o Coonteext e os agentes especializados operam. |

> **Paaneels** `Ialum.Seelleer.Taalkeer.Paaneels`
> Sub-modulo do Taalkeer. Paineis de orcamento com integracao direta a ERPs e ao Seendeer. Permite criar e gerenciar propostas comerciais completas com valores de produtos, impostos e frete calculados automaticamente — sem sair do ambiente de atendimento. Orcamento completo dentro do chat com calculo automatico de frete em tempo real via Seendeer. O orcamento gerado fica vinculado ao ID unico do lead, rastreavel pelo Traakeer como evento de conversao.

**Orchestraatoor** `Ialum.Seelleer.Orchestraatoor`
| | |
|---|---|
| **Funcao** | Orquestra multiplas IAs especializadas. Decide autonomamente qual agente deve atender cada conversa com base em deteccao de objecoes, classificacao de urgencia, identificacao de produtos e reconhecimento de intencoes. Gerencia o ciclo de vida dos agentes: criacao, configuracao, monitoramento de performance e transferencias entre especialistas — tudo em tempo real. |
| **Stack base** | LLM local / API |
| **Diferenciais** | Roteamento inteligente por LLM com cache de decisoes — evita reprocessamento. Metricas por agente: taxa de resolucao, tempo de resposta, confianca, satisfacao. |
| **Integracoes** | Consulta o Braainner para contextualizar atendimentos com conhecimento da empresa. Utiliza agentes criados pelo AgentCreator. Aciona o Seendeer via MCP para cotar fretes durante conversas. Dados de performance dos agentes alimentam o Traakeer e o Analiizeer. |

**Coonteext** `Ialum.Seelleer.Coonteext`
| | |
|---|---|
| **Funcao** | Le, organiza e compila os contextos das conversas. Extrai preferencias, qualificacoes e dados do cliente de forma dinamica durante o atendimento, sem interromper o fluxo natural. Compila essas informacoes para analise futura e para que as IAs entreguem respostas cada vez mais assertivas. |
| **Stack base** | LLM + PostgreSQL |
| **Diferenciais** | Extracao nao-invasiva — opera em paralelo a conversa. Nunca sobrescreve dados, apenas adiciona. Perfil do lead enriquecido progressivamente a cada interacao. |
| **Integracoes** | Retroalimenta o Braainner (Reminder) com insights extraidos das interacoes — padroes de objecoes, preferencias recorrentes, lacunas de informacao. Dados compilados ficam disponiveis para o Orchestraatoor tomar decisoes mais precisas, para o Publisheer segmentar conteudo por perfil, e para o Markeetteer ajustar campanhas por qualificacao. |

**Seendeer** `Ialum.Seelleer.Seendeer`
| | |
|---|---|
| **Funcao** | Agregador inteligente de transportadoras para cotacao de frete. Ao inves de depender de APIs externas lentas e instaveis, utiliza uma arquitetura propria de cadastramento de tabelas de frete processadas por IA, funcionando como uma calculadora ultra-rapida com altissima precisao. |
| **Stack base** | Custom + IA |
| **Diferenciais** | Independencia total de APIs externas — elimina indisponibilidade e lentidao. Cotacao massiva com medias ponderadas por percentual de vendas em multiplas regioes do Brasil — precisao real para estrategias de frete gratis e precificacao competitiva. Calculos customizados para operacoes de fulfillment. |
| **Integracoes** | Fornece fretes ao Paaneels para orcamentos em tempo real. Conecta com os principais e-commerces (VTEX, Shopify, Mercado Livre, entre outros) e transportadoras do mercado. Nativamente AI-friendly com MCP avancado — qualquer agente da plataforma (Orchestraatoor, Synapser, AgentCreator) pode cotar fretes de forma autonoma dentro de fluxos inteligentes. |

---

### 3. Publisheer — Criacao e Publicacao de Conteudo

Pipeline de producao de conteudo com IA — do planejamento editorial a publicacao e rastreamento, com validacao humana em cada etapa. Trabalha inteiramente sobre os dados do Braainner como base de conhecimento.

**Dor que resolve:** Dificuldade em planejar, criar e publicar conteudo visual consistente e estrategico para multiplas redes sociais.

#### Modulos:

**Plaanner** `Ialum.Publisheer.Plaanner`
| | |
|---|---|
| **Funcao** | Planejamento estrategico e mapeamento completo de editoriais. Une as informacoes estruturadas do Braainner para criar editoriais detalhados para cada canal — Instagram, Meta Ads, Google Ads, TikTok, LinkedIn, entre outros. Cada editorial define objetivo, duracao, publico-alvo, mix de conteudo, frequencia, lista completa de topicos, estrategia visual, abordagem por peca, prompts de geracao de imagens, referencias e textos base. |
| **Stack base** | LLM |
| **Diferenciais** | Editoriais completos por canal com prompts de geracao de imagens, referencias visuais e textos ja incluidos. Planejamento e mapeamento de topicos em uma unica ferramenta — da estrategia ao briefing de cada peca. Validacao humana antes de prosseguir para a criacao. |
| **Integracoes** | Consulta o Braainner (Reminder + Seekeer) para embasar editoriais com dados reais da empresa. Utiliza dados de qualificacao do Coonteext para segmentar conteudo por perfil de lead. Acessa metricas do Traakeer e Analiizeer para ajustar a estrategia com base em performance historica. |

**Coonteent** `Ialum.Publisheer.Coonteent`
| | |
|---|---|
| **Funcao** | Controla e estrutura os conteudos textuais para cada tipo de publicacao. Gerencia copys, legendas, roteiros, CTAs e textos adaptados ao formato de cada rede social e tipo de campanha (organico, pago). Garante consistencia de tom de voz e mensagem entre todas as pecas. |
| **Stack base** | PostgreSQL + LLM |
| **Diferenciais** | Conteudo estruturado por tipo de publicacao e canal de destino. Consistencia de tom de voz e mensagem mantida automaticamente pela IA. |
| **Integracoes** | Trabalha sobre os editoriais e briefings definidos no Plaanner. Acessa descricoes e ativos armazenados no Braainner (Reminder). Os conteudos finalizados sao combinados com as midias do Imaageer para compor publicacoes completas no Launcheer. |

**Imaageer** `Ialum.Publisheer.Imaageer`
| | |
|---|---|
| **Funcao** | Sistema de criacao de imagens e videos para publicacoes. Editor completo com geracao por IA, templates com a identidade visual da marca (tipografia, cores, logo), upload de midias proprias e composicao final. Cada peca e criada no formato nativo da plataforma de destino (carrossel Instagram, video TikTok, anuncio Meta Ads etc.). |
| **Stack base** | Midjourney / DALL-E |
| **Diferenciais** | Ialum Template — aplica automaticamente a identidade visual da marca a imagens e videos gerados por IA. Editor avancado que combina IA generativa com upload de midias do usuario. Criacao nativa por plataforma — cada rede recebe conteudo no formato ideal. |
| **Integracoes** | Utiliza prompts de geracao de imagens e referencias visuais definidos no Plaanner. Acessa ativos visuais armazenados no Braainner (Reminder). Midias finalizadas sao combinadas com os conteudos do Coonteent e seguem para o Launcheer. |

**Launcheer** `Ialum.Publisheer.Launcheer`
| | |
|---|---|
| **Funcao** | Agendamento, planejamento e publicacao de conteudo. Para conteudo organico: agendamento inteligente com otimizacao de horarios e publicacao automatica via APIs oficiais das plataformas (Instagram, LinkedIn, TikTok, Facebook, Twitter). Para conteudo pago: planejamento de campanhas e rastreamento de performance integrado ao Traakeer. |
| **Stack base** | Conectores proprios + APIs oficiais |
| **Diferenciais** | Gestao unificada de organico e pago em um unico lugar. Otimizacao automatica de horarios de publicacao. Processamento em lote com persistencia de estado — jobs longos podem ser retomados do ponto exato de falha. |
| **Integracoes** | Recebe conteudos do Coonteent e midias do Imaageer para compor publicacoes completas. Publica via APIs oficiais das plataformas. Eventos de publicacao e metricas de performance sao rastreados pelo Traakeer — engajamento, alcance, conversoes, tudo vinculado ao ID unico do lead. Dados de performance retornam ao Braainner e ao Analiizeer para fechar o ciclo de inteligencia. |

---

### 4. Markeetteer — Inteligencia de Marketing

Coleta, analise, captacao e monitoramento proativo de dados de marketing — sem dependencia de ferramentas externas.

**Dor que resolve:** Captacao de leads qualificados, venda de produtos online, falta de visibilidade sobre performance de marketing e comportamento do cliente.

#### Modulos:

**Paagees** `Ialum.Markeetteer.Paagees`
| | |
|---|---|
| **Funcao** | Construtor de landing pages com modulos reutilizaveis (Hero, Formularios, Depoimentos, FAQ, Precos) e mini-aplicacoes interativas (calculadoras, quizzes, diagnosticos) para qualificacao de leads. Tracking nativo embutido automaticamente. |
| **Stack base** | Custom |
| **Diferenciais** | Tracking nativo em todas as paginas — zero configuracao manual. Mini-aplicacoes interativas qualificam o lead antes mesmo do primeiro contato humano. |
| **Integracoes** | Quando um visitante converte, o lead e cadastrado instantaneamente no Taalkeer com o ID unico do ecossistema, carregando todo o historico de navegacao e interacoes rastreados pelo Traakeer. Eventos de pagina (pageviews, scroll, cliques, formularios, conversoes, UTMs) alimentam o Traakeer em tempo real. Respostas das mini-aplicacoes enriquecem o perfil do lead no Coonteext. |

**Traakeer** `Ialum.Markeetteer.Traakeer`
| | |
|---|---|
| **Funcao** | Plataforma de analytics comportamental auto-hospedada. Rastreia o ID unico do visitante por eventos mapeados para cada fase da jornada: descoberta, consideracao, compra e pos-venda. Coleta eventos, grava sessoes, gera heatmaps, funis de conversao e permite testes A/B. |
| **Stack base** | SDK proprio + FastAPI + PostgreSQL |
| **Diferenciais** | Propriedade total dos dados — sem dependencia de Google Analytics ou terceiros. Eventos mapeados por fase da jornada completa do cliente, nao apenas por pagina. |
| **Integracoes** | Recebe eventos do Paagees (navegacao), do Taalkeer (conversas), do Seelleer (atendimentos, orcamentos), do Publisheer (engajamento com conteudo) e do Launcheer (performance de campanhas pagas). Integra com APIs de anuncios (Meta, Google, TikTok) para unificar dados de trafego pago. E o elo que conecta o comportamento do lead em todas as plataformas — desde o primeiro clique ate a pos-venda. Alimenta o Analiizeer com dados para dashboards e o Braainner com tendencias identificadas. |

**Analiizeer** `Ialum.Markeetteer.Analiizeer`
| | |
|---|---|
| **Funcao** | Dashboards pre-construidos e agentes de IA que respondem perguntas sobre dados em linguagem natural. Monitores proativos detectam anomalias (queda de conversoes, CPA incomum), oportunidades (segmentos de alto ROI) e alertam automaticamente. |
| **Stack base** | Grafana + Prometheus + IA |
| **Diferenciais** | Monitoramento proativo com alertas inteligentes — anomalias, metas, oportunidades, SLA. Agentes analistas que interpretam dados e respondem em linguagem natural sobre a camada de dashboards. |
| **Integracoes** | Cruza dados de todas as plataformas via Traakeer: performance de landing pages (Paagees), metricas de atendimento (Seelleer), engajamento de conteudo (Publisheer) e campanhas pagas — tudo em dashboards unificados. Campanhas de trafego podem ser ativadas ou desativadas automaticamente com base na qualificacao do lead. Tendencias e padroes identificados retornam ao Braainner. |

**Ecommerceer** `Ialum.Markeetteer.Ecommerceer`
| | |
|---|---|
| **Funcao** | Loja virtual integrada ao ecossistema Ialum. Permite venda de produtos online com toda a inteligencia da plataforma aplicada — rastreamento de comportamento de compra, atendimento por IA e logistica via Seendeer. |
| **Stack base** | Custom (desenvolvimento proprio) |
| **Diferenciais** | E-commerce nativamente integrado ao ecossistema de IA — comportamento de compra alimenta o mesmo ID unico do lead. Logistica e frete resolvidos pelo Seendeer sem depender de APIs externas. |
| **Integracoes** | Eventos de navegacao e compra alimentam o Traakeer. Atendimento ao cliente via Taalkeer com contexto completo do pedido. Cotacao de frete via Seendeer. Dados de vendas e comportamento de compra enriquecem o Braainner e o Analiizeer. |

---

## Ciclo de Inteligencia Integrado

O maior diferencial do Ialum como plataforma e o ciclo continuo de retroalimentacao entre os modulos:

```
Ialum.Braainner (conhecimento)
    |-- Transcriptor (captura)
    |-- Reminder (repositorio)
    |-- Seekeer (pesquisa externa)
    |-- Synapser (conversacao)
    |-- AgentCreator (criacao de agentes)
    |
    +--> Ialum.Seelleer (atendimento)
    |       |-- Taalkeer (comunicacao)
    |       |     +-- Paaneels (orcamentos)
    |       |-- Orchestraatoor (gestao de IAs)
    |       |-- Coonteext (inteligencia) ---> insights ---> Braainner
    |       +-- Seendeer (frete)
    |
    +--> Ialum.Publisheer (conteudo)
    |       |-- Plaanner (estrategia + editoriais)
    |       |-- Coonteent (conteudo estruturado)
    |       |-- Imaageer (criacao visual) ---> performance ---> Braainner
    |       +-- Launcheer (publicacao + trafego pago)
    |
    +--> Ialum.Markeetteer (metricas)
            |-- Paagees (landing pages) ---> leads ---> Taalkeer
            |-- Traakeer (analytics) ---> jornada completa do lead
            |-- Analiizeer (dashboards) ---> tendencias ---> Braainner
            +-- Ecommerceer (loja virtual) ---> vendas ---> Traakeer
```

O ID unico do visitante/lead percorre todo o ecossistema. Um lead capturado no Paagees e cadastrado instantaneamente no Taalkeer, rastreado pelo Traakeer em cada fase da jornada, qualificado pelo Coonteext, e acionavel por qualquer plataforma. Cada interacao alimenta o Braainner, que por sua vez enriquece todas as operacoes seguintes. A empresa fica mais inteligente a cada uso.

---

## Arquitetura de Dados

| Aspecto | Como funciona |
|---|---|
| **Servidor (padrao)** | VPS dedicada por cliente |
| **Servidor (SaaS)** | Multi-tenant para modulos pontuais (Seendeer, Taalkeer, Paagees) |
| **Banco de dados** | PostgreSQL unico com pgvector |
| **Storage de arquivos** | S3 / MinIO no servidor do cliente |
| **Acesso tecnico** | Apenas Ialum (via SSH) |
| **Acesso do cliente** | Interfaces das plataformas apenas |

---

## Estrutura de Niveis

| Nivel | Exemplo | Vendavel separado |
|---|---|---|
| Plataforma | Markeetteer, Seelleer | Nao |
| Modulo | Paagees, Traakeer, Seendeer | Sim |
| Sub-modulo | Paaneels (dentro do Taalkeer) | Depende |

---

## Diferenciais da Plataforma

| Diferencial | Descricao |
|---|---|
| **ID unico cross-plataforma** | Um unico ID conecta o lead em todas as aplicacoes — da captura a pos-venda, sem silos |
| **Jornada rastreada de ponta a ponta** | Traakeer mapeia cada evento do lead entre todos os modulos |
| **Tudo e um agente** | Cada funcao opera como um agente de IA configuravel — personalizacao total sem codigo |
| **Modular e independente** | Cada modulo funciona sozinho, mas ganha contexto quando integrado |
| **Dados proprios** | Analytics e tracking auto-hospedados, sem depender de terceiros |
| **Conhecimento como base** | Busca semantica unificada alimenta todas as operacoes |
| **IA com supervisao** | Validacao humana em pontos criticos — a IA assiste, o usuario decide |
| **Recuperacao granular** | Processos longos persistem estado e podem retomar do ponto de falha |
| **Infraestrutura hibrida** | Servidor dedicado por padrao, com opcao SaaS para modulos pontuais |
| **Generico por design** | Adaptavel a qualquer segmento de negocio sem customizacao |
| **Acompanhamento continuo** | Miniconsultoria + implantacao + suporte ativo do time Ialum |
