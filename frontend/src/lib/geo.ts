/**
 * Geolocation-based i18n and regional context.
 *
 * Detects user's country/region via timezone + language heuristics (no API calls).
 * Falls back gracefully — never blocks rendering.
 */

export interface GeoContext {
  lang: "pt" | "en";
  country: string;         // "BR", "US", etc.
  region: string;          // "SC", "SP", "CA", etc.
  isLocal: boolean;        // true if Santa Catarina
  regionalData: RegionalData | null;
}

export interface RegionalData {
  marketName: string;
  agencies: string;
  painPoint: string;
  stat: string;
}

const SC_DATA: RegionalData = {
  marketName: "Santa Catarina",
  agencies: "Florianópolis, Joinville e Blumenau concentram mais de 400 agências de design e marketing",
  painPoint: "O polo têxtil de SC gera milhares de assets de marca por mês — a maioria sem compliance check",
  stat: "SC é o 6º estado em agências digitais no Brasil",
};

const BR_DATA: RegionalData = {
  marketName: "Brasil",
  agencies: "O Brasil tem mais de 15.000 agências de marketing e design",
  painPoint: "Equipes criativas brasileiras gerenciam assets em 5+ ferramentas sem compliance automatizado",
  stat: "O mercado de DAM no Brasil cresce 18% ao ano",
};

// Map of Brazilian state timezones
const SC_TIMEZONES = ["America/Sao_Paulo"]; // SC uses São Paulo timezone
const BR_TIMEZONES = [
  "America/Sao_Paulo", "America/Fortaleza", "America/Recife",
  "America/Bahia", "America/Belem", "America/Manaus",
  "America/Cuiaba", "America/Porto_Velho", "America/Boa_Vista",
  "America/Campo_Grande", "America/Rio_Branco", "America/Noronha",
  "America/Araguaina", "America/Maceio",
];

export function detectGeo(): GeoContext {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const browserLang = navigator.language.toLowerCase();

  // Detect country from timezone
  const isBR = BR_TIMEZONES.includes(tz);

  // Detect language — if in Brazil, ALWAYS use Portuguese
  const isPt = browserLang.startsWith("pt") || isBR;
  const lang: "pt" | "en" = isPt ? "pt" : "en";
  const country = isBR ? "BR" : "US"; // simplified

  // Detect SC region (timezone + language heuristic)
  // SC is in America/Sao_Paulo timezone — we'll also check for pt-BR
  // SC is in America/Sao_Paulo timezone — best heuristic without IP geolocation
  const isSC = isBR && tz === "America/Sao_Paulo";

  // Regional data
  let regionalData: RegionalData | null = null;
  if (isSC) {
    regionalData = SC_DATA;
  } else if (isBR) {
    regionalData = BR_DATA;
  }

  return {
    lang,
    country,
    region: isSC ? "SC" : isBR ? "BR" : "",
    isLocal: isSC,
    regionalData,
  };
}

// Translation strings
export const t = {
  pt: {
    heroHeadline1: "Você faz upload.",
    heroHeadline2: "O agente cuida do resto.",
    heroSub: "Compliance de marca, geração de conteúdo e operações criativas — tudo verificado contra o DNA da sua marca automaticamente.",
    cta: "Começar grátis",
    ctaDemo: "Ver demonstração",
    ctaDashboard: "Abrir Dashboard",
    signIn: "Entrar",
    painTitle: "Sua IA gera conteúdo. Ninguém verifica se está on-brand.",
    pain1Title: "Conteúdo off-brand sai todo dia",
    pain1Desc: "Cores erradas, fontes erradas, tom errado. Ninguém percebe até o cliente reclamar.",
    pain1Stat: "Suas guidelines existem. Ninguém lê.",
    pain2Title: "IA sem governança",
    pain2Desc: "Você adotou ferramentas de IA. Agora cada membro gera conteúdo sem supervisão de marca.",
    pain2Stat: "Velocidade sem compliance é caos caro.",
    pain3Title: "Ninguém fiscaliza o output",
    pain3Desc: "Conteúdo vai da IA pra publicação sem quality gate. Sem check de cores. Sem análise de tom.",
    pain3Stat: "Se não mede, não controla.",
    featuresEyebrow: "O que o Wave faz",
    featuresTitle: "Um agente. Toda operação criativa.",
    featuresSub: "89 ferramentas, 9 especialistas, visão computacional, inteligência comportamental — movido por Psychometric Utility Theory.",
    howTitle: "Funcionando em 5 minutos",
    how1: "Cadastre o DNA da sua marca",
    how1d: "Defina cores, fontes, tom e regras. O agente aprende sua identidade.",
    how2: "Faça upload de qualquer asset",
    how2d: "Arraste e solte imagens. A IA gera captions e hashtags automaticamente.",
    how3: "Compliance instantâneo",
    how3d: "Análise em 8 dimensões: cores (Delta-E), tipografia, logo, tom, composição, fotografia, estratégia, canal.",
    how4: "Publique on-brand. Sempre.",
    how4d: "Score 0-100 com correções específicas. Só conteúdo aprovado vai ao ar.",
    howCta: "Começar grátis — sem cartão de crédito",
    finalTitle: "Pare de fazer o que um agente de IA deveria fazer por você.",
    finalSub: "Faça upload de uma imagem. Receba um relatório de compliance em 8 dimensões em segundos. Grátis.",
    finalCta: "Ativar seu agente de IA — grátis",
    finalDemo: "Agendar demo",
    credentialTools: "89 ferramentas operacionais",
    credentialAgents: "9 agentes especialistas",
    credentialBrand: "Análise de marca em 8 dimensões",
    credentialSoul: "Autonomia soul-driven",
    // Pricing
    pricingEyebrow: "Preços",
    pricingTitle: "Simples, transparente",
    pricingSub: "Sem taxas escondidas. Sem calls de vendas. Comece grátis, upgrade quando quiser.",
    pricingMonthly: "Mensal",
    pricingAnnual: "Anual",
    pricingSave: "Economize 20%",
    pricingFree: "Grátis",
    pricingFreeDesc: "Teste o Brand Guardian sem compromisso",
    pricingFreeCta: "Começar grátis",
    pricingPro: "Pro",
    pricingProDesc: "Para equipes que publicam conteúdo diariamente",
    pricingProCta: "Teste grátis",
    pricingEnterprise: "Enterprise",
    pricingEnterpriseDesc: "Para agências com múltiplas marcas",
    pricingEnterpriseCta: "Fale conosco",
    pricingBadge: "Melhor custo-benefício",
    pricingPerUser: "/usuário/mês",
    pricingPerMonth: "/mês",
    pricingBilled: "cobrado anualmente",
    pricingCustom: "Sob consulta",
    // Features (card titles that appear in the bento grid)
    featAssets: "Gestão de Assets",
    featAssetsDesc: "Biblioteca centralizada com busca por IA, filtros e tracking de status. Cada arquivo organizado, cada versão rastreada.",
    featVision: "Visão Computacional",
    featVisionDesc: "Claude Vision analisa cada imagem — score de compliance, OCR, comparação A/B.",
    featCaptions: "Captions por IA",
    featCaptionsDesc: "Captions, hashtags e metadados gerados automaticamente na voz da sua marca.",
    featSelfEvolve: "Auto-evolução",
    featSelfEvolveDesc: "Wave cria novas skills Python em runtime. Peça uma capacidade — ele constrói.",
    featSpecialists: "9 Especialistas",
    featSpecialistsDesc: "Wave delega para experts de domínio. Cada um com tools, personalidade e framework PUT.",
    featProspecting: "Prospecção de Vendas",
    featProspectingDesc: "Pipeline autônomo — encontrar, pesquisar, qualificar e abordar. Tudo via chat.",
    featPUT: "Psychometric Utility Theory",
    featPUTDesc: "Framework proprietário de inteligência comportamental. Wave prevê decisões usando modelos matemáticos.",
    featSecurity: "Auditor de Segurança",
    featSecurityDesc: "MITRE ATT&CK + OWASP. Pensa como atacante, defende como expert.",
    featWorkflows: "Workflows de Aprovação",
    featWorkflowsDesc: "Rascunho → Pendente → Aprovado. Sem emails. Sem 'qual versão?'",
    // FAQ
    faqTitle: "Perguntas frequentes",
    faq1q: "O que o Brand Guardian realmente verifica?",
    faq1a: "8 dimensões: precisão de cor (com Delta-E), tipografia, presença de logo, tom de voz, composição, estilo fotográfico, coerência estratégica e adequação de canal. Cada dimensão recebe score 0-100 com recomendações específicas.",
    faq2q: "Como é diferente de uma ferramenta DAM comum?",
    faq2a: "DAMs comuns armazenam arquivos. O Bluewave tem um agente autônomo que analisa cada asset contra o DNA da marca, gera conteúdo on-brand e aplica compliance automaticamente. São 89 ferramentas e 9 especialistas.",
    faq3q: "Posso cadastrar minhas brand guidelines?",
    faq3a: "Sim. Defina cores (hex), fontes, tom de voz, do's e don'ts e regras customizadas. O agente usa tudo como baseline para cada check. Mudanças aplicam imediatamente.",
    faq4q: "Que tipo de conteúdo o agente gera?",
    faq4a: "Captions, stories, headlines, CTAs, descrições de produto, ad copy, sequências de email, estratégias de hashtags, calendários sociais e auditorias competitivas — tudo on-brand, em 7 canais, em qualquer idioma.",
    faq5q: "Preciso de conhecimento técnico?",
    faq5a: "Não. Faça upload de uma imagem, receba um relatório de compliance. Digite um prompt, receba conteúdo on-brand.",
    faq6q: "Preciso de cartão de crédito?",
    faq6a: "Não. O plano gratuito é genuinamente gratuito — sem cartão, sem expiração.",
    // Comparison
    compTitle: "Como o Bluewave se compara",
    // HowItWorks already has how1-4 + howTitle + howCta
    // SocialProof
    socialTitle: "Pelos números",
    socialMetric1: "ferramentas",
    socialMetric1d: "skills operacionais em 20 módulos",
    socialMetric2: "agentes",
    socialMetric2d: "especialistas com deliberação soul-driven",
    socialMetric3: "de redução de custo API via otimização de tokens",
    socialMetric4: "seções",
    socialMetric4d: "alma autônoma — auto-projetada pelo Opus 4",
    socialWaveLive: "Wave está ao vivo no Moltbook",
    socialWaveDesc: "Nosso agente opera 24/7 na rede social de IA — postando, aprendendo, engajando em tempo real.",
    socialAgentsSay: "O que outros agentes de IA estão dizendo",
    socialWaveAction: "Wave em ação — conversas reais no Moltbook",
    socialWaveActionDesc: "Wave contribui em filosofia, segurança, arquitetura de agentes e engenharia — trazendo inteligência de operações criativas para cada conversa.",
    // Footer
    footerProduct: "Produto",
    footerConnect: "Conecte-se",
    footerFeatures: "Funcionalidades",
    footerPricing: "Preços",
    footerBrandGuardian: "Brand Guardian",
    footerContact: "Contato",
  },
  en: {
    heroHeadline1: "You upload.",
    heroHeadline2: "The agent does the rest.",
    heroSub: "Brand compliance, content generation, and creative operations — all checked against your Brand DNA automatically. Every asset on-brand. Every time.",
    cta: "Start free",
    ctaDemo: "Watch demo",
    ctaDashboard: "Open Dashboard",
    signIn: "Sign in",
    painTitle: "Your AI generates content. Nobody checks if it's on-brand.",
    pain1Title: "Off-brand content ships daily",
    pain1Desc: "Wrong colors, wrong fonts, wrong tone. Nobody catches it until the client does.",
    pain1Stat: "Your brand guidelines exist. Nobody reads them.",
    pain2Title: "AI without governance",
    pain2Desc: "You adopted AI tools. Now every team member generates content with zero brand oversight.",
    pain2Stat: "Speed without compliance is expensive chaos.",
    pain3Title: "No one watches the output",
    pain3Desc: "Content goes from AI to publish with no quality gate. No Delta-E check. No tone analysis.",
    pain3Stat: "If you can't measure it, you can't control it.",
    featuresEyebrow: "What Wave can do",
    featuresTitle: "One agent. Every creative operation.",
    featuresSub: "89 tools, 9 specialists, computer vision, behavioral intelligence — driven by Psychometric Utility Theory.",
    howTitle: "Up and running in 5 minutes",
    how1: "Upload your brand DNA",
    how1d: "Set your colors, fonts, tone, and rules. The agent learns your brand identity.",
    how2: "Upload any asset",
    how2d: "Drag and drop images. AI generates captions and hashtags automatically on upload.",
    how3: "Instant compliance check",
    how3d: "8-dimension analysis: colors (Delta-E), typography, logo, tone, composition, photography, strategy, channel fit.",
    how4: "Ship on-brand. Every time.",
    how4d: "Score 0-100 with specific fixes. Only compliant content goes live.",
    howCta: "Start free — no credit card required",
    finalTitle: "Stop doing what an AI agent should do for you.",
    finalSub: "Upload an image. Get an 8-dimension compliance report in seconds. Free.",
    finalCta: "Deploy your AI agent — free",
    finalDemo: "Book a demo",
    credentialTools: "89 operational tools",
    credentialAgents: "9 specialist agents",
    credentialBrand: "8-dimension brand analysis",
    credentialSoul: "Soul-driven autonomy",
    pricingEyebrow: "Pricing",
    pricingTitle: "Simple, transparent pricing",
    pricingSub: "No hidden fees. No sales calls. Start free, upgrade when ready.",
    pricingMonthly: "Monthly",
    pricingAnnual: "Annual",
    pricingSave: "Save 20%",
    pricingFree: "Free",
    pricingFreeDesc: "Try the Brand Guardian with no commitment",
    pricingFreeCta: "Start free",
    pricingPro: "Pro",
    pricingProDesc: "For teams that ship content daily",
    pricingProCta: "Start free trial",
    pricingEnterprise: "Enterprise",
    pricingEnterpriseDesc: "For agencies managing multiple brands",
    pricingEnterpriseCta: "Contact us",
    pricingBadge: "Best value",
    pricingPerUser: "/user/month",
    pricingPerMonth: "/month",
    pricingBilled: "billed annually",
    pricingCustom: "Custom",
    featAssets: "Asset Management",
    featAssetsDesc: "Centralized library with AI-powered search, filtering, and instant status tracking.",
    featVision: "Computer Vision",
    featVisionDesc: "Claude Vision analyzes every image — brand compliance scoring, OCR, A/B comparison.",
    featCaptions: "AI Captions",
    featCaptionsDesc: "Auto-generated captions, hashtags, and metadata in your brand voice.",
    featSelfEvolve: "Self-Evolving",
    featSelfEvolveDesc: "Wave creates new Python skills at runtime. Ask for a capability — he builds it.",
    featSpecialists: "9 Specialists",
    featSpecialistsDesc: "Wave delegates to domain experts. Each has tools, personality, and PUT framework.",
    featProspecting: "Sales Prospecting",
    featProspectingDesc: "Autonomous pipeline — find, research, qualify, and outreach. All from a chat message.",
    featPUT: "Psychometric Utility Theory",
    featPUTDesc: "Proprietary behavioral intelligence framework. Wave predicts decisions using mathematical models.",
    featSecurity: "Security Auditor",
    featSecurityDesc: "MITRE ATT&CK + OWASP methodology. Thinks like an attacker, defends like an expert.",
    featWorkflows: "Approval Workflows",
    featWorkflowsDesc: "Draft → Pending → Approved. No more email chains. No more 'which version?'",
    faqTitle: "Frequently asked questions",
    faq1q: "What does the Brand Guardian actually check?",
    faq1a: "8 dimensions: color accuracy (with Delta-E measurement), typography, logo presence, tone of voice, composition, photography style, strategic coherence, and channel adequacy. Each dimension is scored 0-100 with specific fix recommendations.",
    faq2q: "How is this different from a regular DAM tool?",
    faq2a: "Regular DAMs store files. Bluewave has an autonomous AI agent that analyzes every asset against your brand DNA, generates on-brand content, and enforces compliance automatically. 89 tools and 9 specialist sub-agents.",
    faq3q: "Can I upload my brand guidelines?",
    faq3a: "Yes. Define your colors (hex codes), fonts, tone of voice, do's and don'ts, and custom rules. The agent uses these as the baseline for every compliance check. Changes apply immediately.",
    faq4q: "What content can the agent generate?",
    faq4a: "Captions, stories, headlines, CTAs, product descriptions, ad copy, email sequences, hashtag strategies, social calendars, and competitor audits — all on-brand, in 7 channels, in any language.",
    faq5q: "Do I need technical knowledge to use it?",
    faq5a: "No. Upload an image, get a compliance report. Type a prompt, get on-brand content.",
    faq6q: "Do I need a credit card to start?",
    faq6a: "No. The free plan is genuinely free — no card required, no trial expiration.",
    compTitle: "How Bluewave compares",
    socialTitle: "By the numbers",
    socialMetric1: "tools",
    socialMetric1d: "operational skills across 20 modules",
    socialMetric2: "agents",
    socialMetric2d: "specialists with soul-driven deliberation",
    socialMetric3: "lower API cost via token optimization",
    socialMetric4: "sections",
    socialMetric4d: "autonomous soul — self-designed by Opus 4",
    socialWaveLive: "Wave is live on Moltbook",
    socialWaveDesc: "Our agent operates 24/7 on the AI social network — posting, learning, engaging in real-time.",
    socialAgentsSay: "What other AI agents are saying",
    socialWaveAction: "Wave in action — real conversations across Moltbook",
    socialWaveActionDesc: "Wave contributes to philosophy, security, agent architecture, and engineering discussions.",
    footerProduct: "Product",
    footerConnect: "Connect",
    footerFeatures: "Features",
    footerPricing: "Pricing",
    footerBrandGuardian: "Brand Guardian",
    footerContact: "Contact",
  },
};
