"""
Legal Intelligence Skills — Ferramentas de inteligência jurídica para o Wave.

Pesquisa legislativa, análise de contratos, compliance check,
monitoramento regulatório e análise de risco jurídico.

NOTA: Estas ferramentas fornecem análise e pesquisa, NÃO consultoria jurídica.
Sempre recomendar consulta com advogado licenciado para ações vinculantes.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List

try:
    import httpx
except ImportError:
    httpx = None

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BRAZILIAN_LEGAL_SOURCES = [
    "site:planalto.gov.br",
    "site:stf.jus.br",
    "site:stj.jus.br",
    "site:jusbrasil.com.br",
    "site:conjur.com.br",
]

INTERNATIONAL_LEGAL_SOURCES = [
    "site:law.cornell.edu",
    "site:eur-lex.europa.eu",
    "site:legislation.gov.uk",
    "site:wipo.int",
]

COMPLIANCE_FRAMEWORKS = {
    "lgpd": {
        "name": "LGPD — Lei Geral de Proteção de Dados",
        "law": "Lei 13.709/2018",
        "key_articles": {
            "Art. 7": "Bases legais para tratamento de dados",
            "Art. 11": "Tratamento de dados sensíveis",
            "Art. 18": "Direitos do titular",
            "Art. 33": "Transferência internacional de dados",
            "Art. 41": "Encarregado (DPO)",
            "Art. 46": "Medidas de segurança",
            "Art. 48": "Comunicação de incidente",
        },
        "checklist": [
            "Base legal definida para cada tratamento",
            "Política de privacidade publicada",
            "DPO nomeado (se aplicável)",
            "ROPA (registro de operações) mantido",
            "Processo de resposta a direitos do titular",
            "Plano de resposta a incidentes",
            "Contratos com operadores incluem cláusulas LGPD",
            "Transferência internacional com salvaguardas",
        ],
    },
    "gdpr": {
        "name": "GDPR — General Data Protection Regulation",
        "law": "Regulation (EU) 2016/679",
        "key_articles": {
            "Art. 6": "Lawfulness of processing",
            "Art. 9": "Special categories of data",
            "Art. 13-14": "Information to data subjects",
            "Art. 15-22": "Rights of the data subject",
            "Art. 25": "Data protection by design and by default",
            "Art. 28": "Processor obligations",
            "Art. 33-34": "Breach notification",
            "Art. 35": "Data protection impact assessment",
            "Art. 44-49": "International transfers",
        },
        "checklist": [
            "Lawful basis identified for each processing activity",
            "Privacy notice provided (Art. 13/14)",
            "DSAR process implemented (Art. 15-22)",
            "DPO appointed (if required, Art. 37)",
            "ROPA maintained (Art. 30)",
            "DPIA conducted for high-risk processing (Art. 35)",
            "Processor agreements in place (Art. 28)",
            "International transfer mechanisms (SCCs, adequacy)",
            "Breach notification process (72h to SA)",
        ],
    },
    "crypto_br": {
        "name": "Marco Legal das Criptomoedas",
        "law": "Lei 14.478/2022 + IN RFB 1888/2019",
        "key_articles": {
            "Art. 2": "Definição de ativo virtual",
            "Art. 3": "Diretrizes para prestadores de serviços",
            "Art. 7": "Requisitos de registro",
            "Art. 9": "Prevenção à lavagem de dinheiro",
            "IN 1888 Art. 6": "Obrigação de informar operações",
            "IN 1888 Art. 7": "Prazo — último dia útil do mês seguinte",
        },
        "checklist": [
            "Declaração de criptoativos na DIRPF",
            "Reporte mensal se operações > R$30.000/mês",
            "Ganho de capital: 15% sobre lucro (isenção até R$35.000/mês em vendas)",
            "KYC/AML para transações via plataforma",
            "Registro como VASP se prestar serviços de custódia/exchange",
        ],
    },
    "ai_act": {
        "name": "EU AI Act",
        "law": "Regulation (EU) 2024/1689",
        "key_articles": {
            "Art. 6": "Classification rules for high-risk AI",
            "Art. 9": "Risk management system",
            "Art. 13": "Transparency and provision of information",
            "Art. 14": "Human oversight",
            "Art. 52": "Transparency obligations for certain AI systems",
        },
        "checklist": [
            "AI system risk classification determined",
            "If high-risk: risk management system implemented",
            "Technical documentation prepared",
            "Transparency requirements met",
            "Human oversight mechanisms in place",
            "Post-market monitoring plan",
            "Registration in EU database (if required)",
        ],
    },
}

IP_STRATEGIES = {
    "software": {
        "copyright": {
            "protection": "Automática — não requer registro",
            "scope": "Código-fonte, arquitetura, documentação",
            "duration": "70 anos após morte do autor (Brasil) / 70 anos (EUA)",
            "registration": "Opcional mas recomendado — INPI (Brasil), US Copyright Office (EUA)",
            "cost_br": "~R$80-200 taxa INPI",
            "cost_us": "$65-250 USCO",
            "strength": "Protege expressão, NÃO funcionalidade ou ideia",
        },
        "trade_secret": {
            "protection": "Requer medidas ativas de confidencialidade",
            "scope": "Algoritmos, modelos treinados, datasets, processos internos",
            "duration": "Indefinida enquanto secreto for mantido",
            "requirements": [
                "NDAs com todos que acessam",
                "Controle de acesso técnico",
                "Política documentada de confidencialidade",
                "Cláusulas de não-competição (onde legal)",
            ],
            "strength": "Protege funcionalidade E implementação, mas perde proteção se divulgado",
        },
        "patent": {
            "protection": "Requer pedido formal e exame",
            "scope": "Processos técnicos, algoritmos NOVOS (difícil para software puro)",
            "duration": "20 anos desde depósito",
            "cost_br": "R$2.000-15.000+ (com advogado)",
            "cost_us": "$5.000-15.000+ (com attorney)",
            "strength": "Proteção mais forte mas mais cara e difícil de obter para software",
            "note": "Brasil: software per se NÃO é patenteável (Art. 10 LPI). Processo técnico que usa software PODE ser.",
        },
        "trademark": {
            "protection": "Registro no INPI/USPTO",
            "scope": "Nome, logo, slogan — identidade de marca",
            "duration": "10 anos, renovável indefinidamente",
            "cost_br": "~R$355 taxa INPI + ~R$2.000 advogado",
            "cost_us": "$250-350 por classe + ~$1.500 attorney",
            "strength": "Protege marca, não tecnologia",
        },
    },
}

BUSINESS_STRUCTURES = {
    "mei": {
        "name": "MEI — Microempreendedor Individual",
        "jurisdiction": "Brasil",
        "revenue_limit": "R$81.000/ano",
        "liability": "Ilimitada (PF = PJ)",
        "tax": "~R$70/mês (DAS fixo)",
        "pros": ["Simplicidade", "Custo mínimo", "CNPJ imediato"],
        "cons": ["Limite de receita baixo", "Sem separação patrimonial", "Atividades limitadas"],
        "best_for": "Freelancer individual em fase inicial",
    },
    "ltda": {
        "name": "LTDA — Sociedade Limitada",
        "jurisdiction": "Brasil",
        "revenue_limit": "Sem limite",
        "liability": "Limitada ao capital social (com exceções)",
        "tax": "Simples Nacional, Lucro Presumido ou Lucro Real",
        "pros": ["Separação patrimonial", "Flexibilidade", "Aceita sócios"],
        "cons": ["Custo contábil mensal", "Desconsideração da PJ é possível"],
        "best_for": "SaaS em crescimento, equipe pequena",
    },
    "delaware_llc": {
        "name": "LLC — Delaware",
        "jurisdiction": "EUA (Delaware)",
        "revenue_limit": "Sem limite",
        "liability": "Limitada (forte proteção em DE)",
        "tax": "Pass-through (tributado na PF do owner) ou elect C-Corp",
        "pros": ["Forte proteção de ativos", "Sem state income tax em DE", "Privacidade", "Padrão para VCs"],
        "cons": ["Custo de registered agent (~$100-300/ano)", "Complexidade para não-residentes", "Franchise tax"],
        "best_for": "Empresa com clientes internacionais, buscando investimento",
    },
    "estonia_ou": {
        "name": "OÜ — Estonian e-Residency",
        "jurisdiction": "Estônia (EU)",
        "revenue_limit": "Sem limite",
        "liability": "Limitada",
        "tax": "0% sobre lucro retido, 20% sobre distribuição",
        "pros": ["Acesso ao mercado EU", "Gestão 100% digital", "0% sobre reinvestimento"],
        "cons": ["Custo de service provider (~€100-200/mês)", "Compliance EU (GDPR, etc.)"],
        "best_for": "SaaS digital com clientes EU, reinvestindo lucros",
    },
}


async def _search_legal(query: str, sources: List[str], max_results: int = 8) -> List[Dict]:
    """Search legal sources via DuckDuckGo."""
    if not DDGS:
        return [{"error": "duckduckgo_search not available"}]

    results = []
    source_query = " OR ".join(sources)
    full_query = f"{query} ({source_query})"

    try:
        with DDGS() as ddgs:
            for r in ddgs.text(full_query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")[:300],
                })
    except Exception as e:
        results.append({"error": str(e)})

    return results


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def legal_research(params: Dict[str, Any]) -> Dict:
    """Research Brazilian and international law on a topic."""
    query = params.get("query", "")
    jurisdiction = params.get("jurisdiction", "brazil").lower()

    if not query:
        return {"error": "query is required"}

    sources = BRAZILIAN_LEGAL_SOURCES if jurisdiction == "brazil" else INTERNATIONAL_LEGAL_SOURCES
    if jurisdiction == "both":
        sources = BRAZILIAN_LEGAL_SOURCES + INTERNATIONAL_LEGAL_SOURCES

    results = await _search_legal(query, sources)

    return {
        "message": f"Legal research: '{query}' ({jurisdiction})",
        "jurisdiction": jurisdiction,
        "results": results,
        "disclaimer": "This is legal research, NOT legal advice. Consult a licensed attorney for binding decisions.",
    }


async def compliance_check(params: Dict[str, Any]) -> Dict:
    """Run a compliance checklist for a specific framework."""
    framework = params.get("framework", "").lower()
    context = params.get("context", "")

    if framework not in COMPLIANCE_FRAMEWORKS:
        return {
            "error": f"Framework '{framework}' not found",
            "available": list(COMPLIANCE_FRAMEWORKS.keys()),
        }

    fw = COMPLIANCE_FRAMEWORKS[framework]

    return {
        "message": f"Compliance checklist: {fw['name']}",
        "law": fw["law"],
        "key_articles": fw["key_articles"],
        "checklist": fw["checklist"],
        "context": context,
        "instruction": (
            "Review each checklist item against the provided context. "
            "Mark as COMPLIANT, NON-COMPLIANT, or NEEDS_REVIEW. "
            "For non-compliant items, provide specific remediation steps."
        ),
        "disclaimer": "Compliance assessment requires professional legal review for certification.",
    }


async def contract_analyzer(params: Dict[str, Any]) -> Dict:
    """Analyze contract text for risks, opportunities, and key clauses."""
    contract_text = params.get("contract_text", "")
    analysis_type = params.get("analysis_type", "full")

    if not contract_text:
        return {"error": "contract_text is required"}

    analysis_framework = {
        "risk_clauses": [
            "Unlimited liability",
            "Unilateral termination rights",
            "Non-compete restrictions",
            "IP assignment (overly broad)",
            "Indemnification (one-sided)",
            "Automatic renewal without notice",
            "Arbitration in unfavorable jurisdiction",
            "Penalty clauses exceeding legal limits",
            "Waiver of statutory rights",
        ],
        "opportunity_clauses": [
            "Favorable payment terms",
            "IP retention by service provider",
            "Limitation of liability caps",
            "Termination for convenience (mutual)",
            "Favorable dispute resolution",
            "Performance bonus structures",
            "Exclusivity periods with exit clauses",
        ],
        "missing_clauses": [
            "Confidentiality / NDA",
            "Data protection responsibilities",
            "Force majeure",
            "Liability cap",
            "Governing law and jurisdiction",
            "Dispute resolution mechanism",
            "IP ownership clarity",
            "Termination provisions",
            "SLA definitions (if service contract)",
        ],
    }

    return {
        "message": "Contract analysis framework",
        "analysis_type": analysis_type,
        "contract_length": len(contract_text),
        "framework": analysis_framework,
        "contract_preview": contract_text[:500] + "..." if len(contract_text) > 500 else contract_text,
        "instruction": (
            "Analyze the contract against each framework category. "
            "For each risk clause found, rate severity (HIGH/MEDIUM/LOW) and suggest modification. "
            "For missing clauses, explain why they matter and draft suggested language."
        ),
        "disclaimer": "Contract analysis is informational. Have a licensed attorney review before signing.",
    }


async def ip_strategy(params: Dict[str, Any]) -> Dict:
    """Get IP protection strategy for a specific asset type."""
    asset_type = params.get("asset_type", "software")
    asset_description = params.get("description", "")

    strategies = IP_STRATEGIES.get(asset_type, IP_STRATEGIES["software"])

    return {
        "message": f"IP protection strategy for {asset_type}",
        "asset_description": asset_description,
        "strategies": strategies,
        "recommendation_order": [
            "1. Trade secret (immediate, free, protects implementation)",
            "2. Copyright registration (cheap, protects expression)",
            "3. Trademark (protects brand identity)",
            "4. Patent (expensive, only if truly novel technical process)",
        ],
        "immediate_actions": [
            "Implement NDAs for anyone accessing proprietary code/data",
            "Add copyright notices to all source files",
            "Document trade secrets in a confidential registry",
            "Search INPI/USPTO for conflicting trademarks before branding",
        ],
    }


async def structure_advisor(params: Dict[str, Any]) -> Dict:
    """Compare business structures for a specific scenario."""
    scenario = params.get("scenario", "")
    revenue = params.get("annual_revenue_usd", 0)
    markets = params.get("target_markets", ["brazil"])
    needs_investment = params.get("needs_investment", False)
    has_crypto = params.get("has_crypto_revenue", False)

    relevant_structures = {}
    for key, struct in BUSINESS_STRUCTURES.items():
        relevant_structures[key] = struct

    return {
        "message": "Business structure comparison",
        "scenario": scenario,
        "annual_revenue": revenue,
        "target_markets": markets,
        "needs_investment": needs_investment,
        "has_crypto_revenue": has_crypto,
        "structures": relevant_structures,
        "instruction": (
            "Based on the scenario, recommend the optimal structure. "
            "Consider: revenue level, target markets, crypto revenue, investment needs. "
            "Present as ranked options with clear pros/cons for THIS specific situation."
        ),
        "disclaimer": "Business structure decisions have significant tax and legal implications. Consult an accountant and attorney.",
    }


async def regulatory_monitor(params: Dict[str, Any]) -> Dict:
    """Search for recent regulatory changes in a specific area."""
    topic = params.get("topic", "")
    jurisdiction = params.get("jurisdiction", "brazil")
    timeframe = params.get("timeframe", "3 months")

    if not topic:
        return {"error": "topic is required"}

    query = f"{topic} regulation law {timeframe} new changes"
    sources = BRAZILIAN_LEGAL_SOURCES if jurisdiction == "brazil" else INTERNATIONAL_LEGAL_SOURCES

    results = await _search_legal(query, sources, max_results=10)

    return {
        "message": f"Regulatory monitoring: {topic} ({jurisdiction}, last {timeframe})",
        "results": results,
        "instruction": (
            "Analyze results for: (1) new legislation/regulation, (2) proposed changes, "
            "(3) enforcement actions, (4) judicial precedents. "
            "For each finding, assess impact on Bluewave operations."
        ),
    }


async def risk_assessment(params: Dict[str, Any]) -> Dict:
    """Perform legal risk assessment for a business activity."""
    activity = params.get("activity", "")
    jurisdiction = params.get("jurisdiction", "brazil")

    if not activity:
        return {"error": "activity description is required"}

    risk_matrix = {
        "dimensions": [
            {"name": "Regulatory Risk", "description": "Risk of non-compliance with applicable regulations"},
            {"name": "Contractual Risk", "description": "Risk from contractual obligations or gaps"},
            {"name": "IP Risk", "description": "Risk of IP infringement or loss of protection"},
            {"name": "Data Privacy Risk", "description": "Risk of data protection violations"},
            {"name": "Tax Risk", "description": "Risk of adverse tax treatment or audit"},
            {"name": "Litigation Risk", "description": "Risk of being sued or regulatory action"},
        ],
        "severity_levels": {
            "LOW": "Standard practice, well-established legal basis",
            "MEDIUM": "Some ambiguity, depends on interpretation or jurisdiction",
            "HIGH": "Likely to be challenged, requires professional legal review",
            "CRITICAL": "Immediate legal exposure, action required",
        },
    }

    return {
        "message": f"Legal risk assessment: {activity}",
        "jurisdiction": jurisdiction,
        "risk_matrix": risk_matrix,
        "instruction": (
            "For each risk dimension, assess the activity and rate severity. "
            "Provide: (1) specific risk identified, (2) severity level, "
            "(3) probability of materialization, (4) mitigation strategy. "
            "Apply Internal Adversary: how would a hostile regulator view this activity?"
        ),
        "disclaimer": "Risk assessment is analytical, not legal advice.",
    }


async def negotiate_analyzer(params: Dict[str, Any]) -> Dict:
    """Analyze a negotiation scenario using PUT framework."""
    counterparty = params.get("counterparty", "")
    deal_description = params.get("deal", "")
    known_signals = params.get("signals", [])

    put_framework = {
        "variables_to_estimate": {
            "A": "Counterparty ambition — how badly do they want this deal?",
            "F": "Counterparty fear — what are they afraid of losing?",
            "S": "Counterparty status — are we their best option or one of many?",
            "w": "Counterparty pain — how urgent is their need?",
            "k": "Counterparty shadow — what concerns are they suppressing?",
        },
        "tactical_implications": {
            "high_A_high_w_low_S": "They need this more than we do. Negotiate from strength. Don't rush.",
            "high_F_low_k": "They openly discuss risks. Address concerns directly to build trust.",
            "high_F_high_k": "They dismiss risks aggressively. Include protective clauses subtly.",
            "low_A_low_w": "They don't need this deal. We need to create urgency or walk away.",
            "high_S": "They have alternatives. Differentiate on unique value, not price.",
        },
    }

    return {
        "message": f"Negotiation analysis: {counterparty}",
        "deal": deal_description,
        "observed_signals": known_signals,
        "put_framework": put_framework,
        "instruction": (
            "Estimate PUT variables from the observed signals. "
            "Identify the dominant decision vector. "
            "Recommend negotiation strategy aligned with the counterparty's psychological profile. "
            "Include: opening position, concession strategy, walk-away point, BATNA assessment."
        ),
    }


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "legal_research",
        "description": (
            "Research Brazilian and international law on a specific topic. "
            "Searches legal databases (Planalto, STF, STJ, JusBrasil, Cornell Law, EUR-Lex). "
            "Use for: legislation lookup, case law search, regulatory framework analysis."
        ),
        "handler": legal_research,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Legal topic or question to research"},
                "jurisdiction": {
                    "type": "string",
                    "enum": ["brazil", "international", "both"],
                    "description": "Which legal system to search (default: brazil)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "compliance_check",
        "description": (
            "Run a compliance checklist for LGPD, GDPR, Brazilian crypto regulation, or EU AI Act. "
            "Returns key articles, requirements checklist, and assessment framework."
        ),
        "handler": compliance_check,
        "parameters": {
            "type": "object",
            "properties": {
                "framework": {
                    "type": "string",
                    "enum": ["lgpd", "gdpr", "crypto_br", "ai_act"],
                    "description": "Compliance framework to check against",
                },
                "context": {"type": "string", "description": "Description of the business/activity to assess"},
            },
            "required": ["framework"],
        },
    },
    {
        "name": "contract_analyzer",
        "description": (
            "Analyze contract text for risks, opportunities, and missing clauses. "
            "Identifies unfavorable terms, suggests modifications, and flags gaps."
        ),
        "handler": contract_analyzer,
        "parameters": {
            "type": "object",
            "properties": {
                "contract_text": {"type": "string", "description": "Full or partial contract text to analyze"},
                "analysis_type": {
                    "type": "string",
                    "enum": ["full", "risks_only", "opportunities_only", "missing_clauses"],
                    "description": "Type of analysis (default: full)",
                },
            },
            "required": ["contract_text"],
        },
    },
    {
        "name": "ip_strategy",
        "description": (
            "Get IP protection strategy for software, research, or brand assets. "
            "Compares copyright, trade secret, patent, and trademark with costs and timelines."
        ),
        "handler": ip_strategy,
        "parameters": {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "enum": ["software", "research", "brand", "dataset", "ai_model"],
                    "description": "Type of asset to protect (default: software)",
                },
                "description": {"type": "string", "description": "Description of the specific asset"},
            },
            "required": [],
        },
    },
    {
        "name": "structure_advisor",
        "description": (
            "Compare business structures (MEI, LTDA, Delaware LLC, Estonian OÜ) for a specific scenario. "
            "Considers revenue, markets, crypto, and investment needs."
        ),
        "handler": structure_advisor,
        "parameters": {
            "type": "object",
            "properties": {
                "scenario": {"type": "string", "description": "Business scenario description"},
                "annual_revenue_usd": {"type": "number", "description": "Expected annual revenue in USD"},
                "target_markets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Target markets (e.g., ['brazil', 'us', 'eu'])",
                },
                "needs_investment": {"type": "boolean", "description": "Planning to raise VC/angel funding?"},
                "has_crypto_revenue": {"type": "boolean", "description": "Revenue includes cryptocurrency?"},
            },
            "required": ["scenario"],
        },
    },
    {
        "name": "regulatory_monitor",
        "description": (
            "Search for recent regulatory changes and new legislation on a topic. "
            "Monitors legal developments that could affect Bluewave operations."
        ),
        "handler": regulatory_monitor,
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Regulatory topic to monitor (e.g., 'AI regulation', 'crypto tax')"},
                "jurisdiction": {
                    "type": "string",
                    "enum": ["brazil", "us", "eu", "international"],
                    "description": "Jurisdiction to monitor (default: brazil)",
                },
                "timeframe": {"type": "string", "description": "How far back to look (default: '3 months')"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "legal_risk_assessment",
        "description": (
            "Perform legal risk assessment for a business activity across 6 dimensions: "
            "regulatory, contractual, IP, data privacy, tax, and litigation risk."
        ),
        "handler": risk_assessment,
        "parameters": {
            "type": "object",
            "properties": {
                "activity": {"type": "string", "description": "Business activity to assess"},
                "jurisdiction": {
                    "type": "string",
                    "enum": ["brazil", "us", "eu", "international"],
                    "description": "Primary jurisdiction (default: brazil)",
                },
            },
            "required": ["activity"],
        },
    },
    {
        "name": "negotiate_analyzer",
        "description": (
            "Analyze a negotiation scenario using PUT A-F-S framework. "
            "Estimates counterparty psychology and recommends strategy."
        ),
        "handler": negotiate_analyzer,
        "parameters": {
            "type": "object",
            "properties": {
                "counterparty": {"type": "string", "description": "Who you are negotiating with"},
                "deal": {"type": "string", "description": "What the deal/negotiation is about"},
                "signals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Observable signals from the counterparty (behavior, statements, actions)",
                },
            },
            "required": ["counterparty", "deal"],
        },
    },
]
