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

  // Detect language
  const isPt = browserLang.startsWith("pt");
  const lang: "pt" | "en" = isPt ? "pt" : "en";

  // Detect country from timezone
  const isBR = BR_TIMEZONES.includes(tz);
  const country = isBR ? "BR" : "US"; // simplified

  // Detect SC region (timezone + language heuristic)
  // SC is in America/Sao_Paulo timezone — we'll also check for pt-BR
  const isSC = isBR && tz === "America/Sao_Paulo" && browserLang === "pt-br";

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
  },
};
