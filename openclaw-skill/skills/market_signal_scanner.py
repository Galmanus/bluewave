"""
market_signal_scanner — Revenue Intelligence
Scans Reddit for buy signals: people actively seeking paid solutions.
Ranks by weighted priority (intent × social proof).
Output: actionable leads, hot domains, 4-step monetization playbook.
"""

import json
import subprocess
import sys
import os
from datetime import datetime


def run_internal(skill_name, params):
    result = subprocess.run(
        ["python3", "skill_executor.py", skill_name, json.dumps(params)],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)) + "/.."
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except Exception:
            return None
    return None


BUY_SIGNALS = [
    "looking for", "need a tool", "anyone know a service", "willing to pay",
    "budget for", "hire someone", "outsource", "recommendations for",
    "best tool for", "does anyone offer", "need help with", "can someone build",
    "is there a service", "looking to hire", "would pay", "how much would",
    "what does it cost", "anyone recommend", "pay someone", "need to find",
    "searching for a", "trying to find", "any suggestions"
]

PAIN_SIGNALS = [
    "frustrated with", "tired of", "wish there was", "hate that",
    "struggle with", "takes too long", "no good solution", "impossible to",
    "manual process", "still doing manually", "waste hours", "pain point",
    "no tool for", "cant find", "doesn't exist", "sucks", "terrible at",
    "spending too much time", "killing us", "huge problem"
]

DOMAINS = {
    "automation":  ["automat", "workflow", "manual", "repetitive", "script", "zapier", "n8n", "make.com"],
    "analytics":   ["data", "metrics", "dashboard", "report", "track", "analytics", "kpi"],
    "marketing":   ["seo", "content", "social media", "email", "campaign", "ads", "growth"],
    "dev_tools":   ["api", "deploy", "code", "bug", "monitor", "devops", "ci/cd", "testing"],
    "finance":     ["invoice", "payment", "accounting", "expense", "billing", "revenue", "tax"],
    "hr":          ["hiring", "recruit", "employee", "onboard", "schedule", "payroll", "hr"],
    "sales":       ["crm", "lead", "prospect", "outreach", "pipeline", "cold email", "sales"],
    "ai":          ["llm", "gpt", "openai", "claude", "ai agent", "prompt", "chatbot", "rag"],
    "ecommerce":   ["shopify", "store", "product", "inventory", "shipping", "ecommerce", "woocommerce"],
}


def score_post(title, body):
    text = (title + " " + body).lower()
    buy = sum(1 for s in BUY_SIGNALS if s in text)
    pain = sum(1 for s in PAIN_SIGNALS if s in text)
    return buy * 2 + pain, buy, pain


def classify_domain(text):
    text = text.lower()
    scores = {d: sum(1 for k in kws if k in text) for d, kws in DOMAINS.items()}
    top = max(scores, key=scores.get)
    return top if scores[top] > 0 else "general"


def main(params):
    subreddits = params.get("subreddits", ["entrepreneur", "SaaS", "smallbusiness", "freelance"])
    min_score = params.get("min_score", 1)
    opportunities = []
    errors = []

    for sub in subreddits:
        data = run_internal("reddit_hot", {"subreddit": sub})
        if not data:
            errors.append(f"r/{sub}: fetch failed")
            continue

        # normalize different response shapes
        if isinstance(data, list):
            posts = data
        elif isinstance(data, dict):
            posts = data.get("posts", data.get("results", data.get("data", [])))
        else:
            errors.append(f"r/{sub}: unexpected format")
            continue

        if not isinstance(posts, list):
            errors.append(f"r/{sub}: no list in response")
            continue

        for post in posts[:30]:
            title = str(post.get("title", ""))
            body = str(post.get("selftext", post.get("body", post.get("text", ""))))
            url = post.get("url", post.get("permalink", ""))
            ups = int(post.get("ups", post.get("score", 1)) or 1)

            score, buy, pain = score_post(title, body)
            if score >= min_score:
                domain = classify_domain(title + " " + body)
                snippet = body[:280].strip() if body.strip() else "[no body]"
                opportunities.append({
                    "intent_score":      score,
                    "buy_signals":       buy,
                    "pain_signals":      pain,
                    "weighted_priority": round(score * (ups ** 0.4), 1),
                    "title":             title,
                    "domain":            domain,
                    "upvotes":           ups,
                    "source":            f"r/{sub}",
                    "url":               url,
                    "snippet":           snippet,
                })

    opportunities.sort(key=lambda x: x["weighted_priority"], reverse=True)

    domain_freq: dict = {}
    for op in opportunities:
        domain_freq[op["domain"]] = domain_freq.get(op["domain"], 0) + 1
    hot_domains = sorted(domain_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "scan_date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sources":        subreddits,
        "signals_found":  len(opportunities),
        "top_10":         opportunities[:10],
        "hot_domains":    hot_domains,
        "errors":         errors,
        "playbook": [
            "1. Pick the top opportunity by weighted_priority",
            "2. DM the poster — offer to solve their exact problem",
            "3. Charge $200-500 for first solution (manual delivery is fine)",
            "4. After 3 paying customers, automate and launch as SaaS",
        ],
    }


if __name__ == "__main__":
    p = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    print(json.dumps(main(p), indent=2))
