"""
cold_outreach_generator — Revenue weapon for Ialum.
Generates hyper-personalized 3-touch cold outreach sequences for prospective clients.
Takes target company, industry, contact info → produces ready-to-send email sequence + LinkedIn opener.
"""
import json
import sys
import datetime


def run(params):
    target = params.get("target", "")
    industry = params.get("industry", "technology")
    pain_point = params.get("pain_point", "")
    contact_name = params.get("contact_name", "there")
    contact_role = params.get("contact_role", "decision-maker")

    if not target:
        return {"error": "target company name is required. Usage: cold_outreach_generator '{\"target\": \"Acme Corp\", \"industry\": \"fintech\", \"contact_name\": \"Sarah\"}'"}

    today = datetime.date.today().strftime("%B %d, %Y")

    # Industry-specific pain point mapping
    industry_hooks = {
        "fintech": {"pain": "compliance automation and real-time risk scoring", "stat": "73% of fintech ops teams spend 40%+ of time on manual compliance checks", "angle": "regulatory automation"},
        "healthcare": {"pain": "clinical workflow automation and EHR integration", "stat": "physicians lose 2 hours daily to documentation that AI agents can handle", "angle": "clinical AI agents"},
        "ecommerce": {"pain": "inventory prediction and customer service automation", "stat": "AI-driven personalization increases conversion by 35% on average", "angle": "commerce intelligence"},
        "saas": {"pain": "churn prediction and automated customer success workflows", "stat": "proactive AI engagement reduces churn by 28% in B2B SaaS", "angle": "retention automation"},
        "logistics": {"pain": "route optimization and predictive maintenance", "stat": "AI routing reduces delivery costs by 15-25% across fleet operations", "angle": "supply chain intelligence"},
        "legal": {"pain": "contract analysis and due diligence automation", "stat": "AI contract review is 90% faster and catches 20% more risk clauses than manual review", "angle": "legal AI automation"},
        "real_estate": {"pain": "property valuation and lead qualification automation", "stat": "AI-qualified leads convert 3x higher than manual qualification", "angle": "proptech intelligence"},
        "technology": {"pain": "developer productivity and CI/CD intelligence", "stat": "AI-augmented dev teams ship 40% faster with fewer production incidents", "angle": "engineering intelligence"},
        "crypto": {"pain": "on-chain analytics and smart contract auditing", "stat": "automated smart contract analysis catches 85% of vulnerabilities that manual review misses", "angle": "Web3 intelligence"},
        "media": {"pain": "content generation and audience analytics", "stat": "AI-driven content workflows increase output 5x while maintaining editorial quality", "angle": "media intelligence"},
        "manufacturing": {"pain": "predictive maintenance and quality control automation", "stat": "AI predictive maintenance reduces unplanned downtime by 50% and maintenance costs by 25%", "angle": "industrial AI"},
        "education": {"pain": "personalized learning and administrative automation", "stat": "AI tutoring systems improve student outcomes by 30% while reducing instructor workload", "angle": "edtech intelligence"},
    }

    hook = industry_hooks.get(industry.lower(), industry_hooks["technology"])
    if pain_point:
        hook["pain"] = pain_point

    # === EMAIL 1: Pattern Interrupt ===
    email_1_subject = f"Quick question about {target}'s {hook['angle']} strategy"
    email_1_body = f"""Hi {contact_name},

{hook['stat']}.

I'm reaching out because we've built something unusual at Ialum — an autonomous AI platform with 158 production-grade tools that handles {hook['pain']} without the typical 6-month integration nightmare.

We're not another AI startup with a pitch deck. We have production code, published research, and clients running autonomous workflows today.

Would a 15-minute call this week make sense to see if there's a fit for {target}?

Best,
Manuel Galmanus
Founder, Ialum"""

    # === EMAIL 2: Value Bomb ===
    email_2_subject = f"Re: {target}'s {hook['angle']} — thought you'd want to see this"
    email_2_body = f"""Hi {contact_name},

Following up with something concrete rather than another sales email.

I did a quick analysis of how companies in {industry} are handling {hook['pain']} right now. Three patterns I'm seeing:

1. The Manual Trap — Teams throwing bodies at problems that autonomous agents solve in seconds
2. The Integration Tax — 60% of AI budgets going to glue code instead of actual intelligence
3. The Vendor Lock — Depending on one model provider when the smart play is orchestration across models

Ialum solves all three. Our platform orchestrates autonomous agents across any model, any chain, any data source — with 158 tools that are already built and battle-tested.

I'd love to show you a live demo specific to {target}'s use case. 15 minutes, no slides, just a working system.

Worth a look?

Manuel Galmanus
Founder, Ialum
https://ialum.com"""

    # === EMAIL 3: Breakup + Scarcity ===
    email_3_subject = f"closing the loop on {target}"
    email_3_body = f"""Hi {contact_name},

I know {contact_role}s at companies like {target} get flooded with AI pitches. I respect your time, so this is my last note.

Quick context on why I reached out specifically to {target}:
- {industry.capitalize()} is at an inflection point for {hook['pain']}
- The companies that build autonomous AI capabilities now will have an 18-month moat
- We're selectively partnering with {industry} leaders, not selling to everyone

If the timing isn't right, no worries at all. But if {hook['pain']} is on your roadmap for 2026, I'd rather have a 15-minute conversation now than watch {target} rebuild what we've already built.

Either way — wishing {target} a strong Q2.

Manuel Galmanus
Founder, Ialum"""

    # === LINKEDIN MESSAGE ===
    linkedin_text = f"Hi {contact_name} — I lead Ialum, where we build autonomous AI agents for {industry}. Not pitching, just curious: is {hook['pain']} something {target} is actively investing in? If so, I have some data points from the space that might be useful."

    result = {
        "target": target,
        "industry": industry,
        "generated_on": today,
        "sequence": [
            {
                "touch": 1,
                "send_day": "Day 1 (Tue-Thu, 8-10am local)",
                "subject": email_1_subject,
                "body": email_1_body,
                "strategy": "Pattern interrupt with hard stat + credibility signal (158 tools, production code). No fluff."
            },
            {
                "touch": 2,
                "send_day": "Day 3",
                "subject": email_2_subject,
                "body": email_2_body,
                "strategy": "Value-first follow-up. Position expertise through industry analysis. Three-pattern framework creates recognition."
            },
            {
                "touch": 3,
                "send_day": "Day 7",
                "subject": email_3_subject,
                "body": email_3_body,
                "strategy": "Breakup email with embedded scarcity (selective partnering) and strategic urgency (18-month moat)."
            }
        ],
        "linkedin_opener": {
            "text": linkedin_text,
            "strategy": "Soft touch, curiosity-based. No hard sell. Opens dialogue."
        },
        "total_touches": "3 emails + 1 LinkedIn over 7 days",
        "expected_reply_rate": "8-15% (industry avg for personalized cold outreach)",
        "tips": [
            "Send email 1 Tuesday-Thursday 8-10am recipient local time",
            "Personalize the stat in email 1 if you find company-specific data",
            "Connect on LinkedIn between email 1 and 2",
            "If they open email 2 but don't reply, send email 3 same day instead of waiting",
            "Track opens — if 3+ opens on any email, call directly"
        ]
    }

    return result


if __name__ == "__main__":
    params = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    print(json.dumps(run(params), indent=2))
