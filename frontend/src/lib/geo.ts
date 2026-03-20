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
  painPoint: "Agências catarinenses gastam em média 12h/semana revisando assets manualmente — a IA faz em segundos",
  stat: "",
};

const BR_DATA: RegionalData = {
  marketName: "Brasil",
  agencies: "O Brasil tem mais de 15.000 agências de marketing e design",
  painPoint: "Equipes criativas brasileiras publicam conteúdo off-brand toda semana porque ninguém tem tempo de revisar tudo",
  stat: "",
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
    heroHeadline1: "Sua marca tá despadronizada?",
    heroHeadline2: "Resolve em 30 segundos.",
    heroSub: "Manda uma imagem. A IA analisa se tá dentro do padrão da sua marca. Cores, fontes, logo, tom — tudo checado automaticamente.",
    cta: "Testar grátis",
    ctaDemo: "Como funciona",
    ctaDashboard: "Abrir Painel",
    signIn: "Entrar",
    painTitle: "Isso acontece na sua agência?",
    pain1Title: "O estagiário mandou o logo errado",
    pain1Desc: "Cor errada, fonte diferente, logo esticado. O cliente viu antes de você. Já passou por isso?",
    pain1Stat: "Acontece toda semana em 70% das agências.",
    pain2Title: "Ninguém segue o manual de marca",
    pain2Desc: "Você fez um manual lindo. Tá no Google Drive. Ninguém abre. Todo mundo faz do jeito que quer.",
    pain2Stat: "O manual existe. Ninguém lê.",
    pain3Title: "Retrabalho que come seu lucro",
    pain3Desc: "Cliente reclama, você refaz. De novo. O tempo gasto refazendo é tempo que não fatura.",
    pain3Stat: "Cada refação custa em média R$150 do seu tempo.",
    featuresEyebrow: "O que você ganha",
    featuresTitle: "Tudo que sua agência precisa pra manter a marca no padrão.",
    featuresSub: "Upload de imagem, análise automática, score de aprovação, geração de conteúdo — tudo numa plataforma só.",
    howTitle: "Funciona em 3 passos",
    how1: "Cadastre sua marca",
    how1d: "Coloca as cores, fontes e regras. Ou manda o PDF do manual que a IA extrai tudo.",
    how2: "Manda a imagem",
    how2d: "Arrasta e solta. Pode ser post de Instagram, banner, story, o que for.",
    how3: "Recebe o diagnóstico",
    how3d: "A IA mostra o que tá certo e o que tá errado. Com nota de 0 a 100 e como corrigir.",
    how4: "Publica com confiança",
    how4d: "Se passou no teste, tá aprovado. Sem medo de cliente reclamar.",
    howCta: "Testar grátis — sem cartão",
    finalTitle: "Sua marca merece consistência. Sua equipe merece uma ferramenta que ajude.",
    finalSub: "Manda uma imagem agora e veja o diagnóstico em segundos. É grátis.",
    finalCta: "Testar agora — grátis",
    finalDemo: "Falar com a gente",
    credentialTools: "Análise automática por IA",
    credentialAgents: "Score de 0 a 100",
    credentialBrand: "Correções específicas",
    credentialSoul: "",
    // Pricing
    pricingEyebrow: "Quanto custa",
    pricingTitle: "Começa grátis. Paga só se precisar de mais.",
    pricingSub: "Sem cartão de crédito. Sem pegadinha. Cancela quando quiser.",
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
    faqTitle: "Dúvidas frequentes",
    faq1q: "O que exatamente a ferramenta faz?",
    faq1a: "Você manda uma imagem (post, banner, story). A IA compara com o padrão da sua marca: cores, fontes, logo, tom. Em segundos, você recebe uma nota de 0 a 100 e o que precisa corrigir.",
    faq2q: "Preciso ser designer pra usar?",
    faq2a: "Não. É feito pra qualquer pessoa da equipe. Arrasta a imagem, recebe o diagnóstico. Se o estagiário sabe usar Instagram, sabe usar o Bluewave.",
    faq3q: "Como cadastro o padrão da minha marca?",
    faq3a: "Você pode digitar as cores e fontes manualmente, ou mandar o PDF do manual de marca. A IA extrai tudo automaticamente.",
    faq4q: "Quanto custa?",
    faq4a: "O plano básico é grátis pra sempre. Sem cartão de crédito, sem pegadinha. Planos pagos a partir de R$197/mês pra quem precisa de mais marcas e funcionalidades.",
    faq5q: "Funciona pra qualquer tipo de marca?",
    faq5a: "Sim. Agência, freelancer, empresa. Qualquer marca que tenha cores, fontes e regras visuais definidas. Se tem manual de marca, funciona.",
    faq6q: "Gera conteúdo também?",
    faq6a: "Sim. Captions pra Instagram, textos pra LinkedIn, hashtags, headlines — tudo seguindo o tom e estilo da sua marca automaticamente.",
    // Comparison
    compTitle: "Como o Bluewave se compara",
    // HowItWorks already has how1-4 + howTitle + howCta
    // SocialProof
    socialTitle: "Como funciona",
    socialMetric1: "dimensões",
    socialMetric1d: "analisadas por imagem",
    socialMetric2d: "tempo médio de análise",
    socialMetric3: "ferramentas",
    socialMetric3d: "de IA integradas",
    socialMetric4: "tipos",
    socialMetric4d: "de conteúdo gerados on-brand",
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
    heroHeadline1: "Brand compliance.",
    heroHeadline2: "Automated. 8 dimensions.",
    heroSub: "Upload any asset. Get a compliance score in seconds — colors, typography, logo, tone, composition, photography, strategy, and channel fit. All checked against your brand DNA.",
    cta: "Start free",
    ctaDemo: "See how it works",
    ctaDashboard: "Open Dashboard",
    signIn: "Sign in",
    painTitle: "The brand governance gap your team doesn't talk about.",
    pain1Title: "Only 25% of brands enforce their guidelines",
    pain1Desc: "You built a brand book. Your team ignores it. Off-brand content ships daily and nobody catches it until the client complains.",
    pain1Stat: "Marq, 2024: 69% say guidelines aren't widely adopted.",
    pain2Title: "AI made it worse",
    pain2Desc: "Every team member now generates content with AI. Zero brand oversight. The output is fast, consistent, and consistently off-brand.",
    pain2Stat: "Speed without governance is expensive chaos.",
    pain3Title: "Compliance tools cost $25K+/year",
    pain3Desc: "Adobe GenStudio, Sprinklr, Brandfolder — enterprise pricing for what should be a standard workflow. Your team can't justify the budget.",
    pain3Stat: "Bluewave starts free. 8-dimension checks from day one.",
    featuresEyebrow: "What you get",
    featuresTitle: "Everything Frontify charges $25K for. Starting at $0.",
    featuresSub: "8-dimension compliance scoring, AI content generation, approval workflows, and brand DNA extraction — in one platform.",
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
    finalTitle: "Brand compliance shouldn't cost $25K/year.",
    finalSub: "Upload an image. Get an 8-dimension compliance score in seconds. Free tier, no credit card.",
    finalCta: "Start free — no credit card",
    finalDemo: "Book a demo",
    credentialTools: "8-dimension scoring",
    credentialAgents: "AI content generation",
    credentialBrand: "Brand DNA extraction",
    credentialSoul: "",
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
    socialTitle: "How it works",
    socialMetric1: "dimensions",
    socialMetric1d: "analyzed per image",
    socialMetric2d: "average analysis time",
    socialMetric3: "AI tools",
    socialMetric3d: "integrated in one platform",
    socialMetric4: "content types",
    socialMetric4d: "generated on-brand automatically",
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
