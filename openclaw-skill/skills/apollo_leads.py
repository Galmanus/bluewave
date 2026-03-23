"""
Apollo.io — B2B lead database for prospect discovery.

Find companies and people with email, phone, title, company size.
Free tier: 50 credits/month.

Setup: APOLLO_API_KEY env var from https://app.apollo.io/
"""

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger("openclaw.apollo")

APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")
APOLLO_URL = "https://api.apollo.io/v1"


async def search_people(params: Dict[str, Any]) -> Dict:
    """Search for B2B leads by title, company, industry."""
    title = params.get("title", "")
    company = params.get("company", "")
    industry = params.get("industry", "")
    limit = min(int(params.get("limit", 5)), 10)

    if not (title or company or industry):
        return {"success": False, "data": None, "message": "Need at least one of: title, company, industry"}

    if not APOLLO_API_KEY:
        return {"success": False, "data": None, "message": "APOLLO_API_KEY not configured. Get one free at apollo.io"}

    try:
        payload = {"page": 1, "per_page": limit}
        if title:
            payload["person_titles"] = [title]
        if company:
            payload["q_organization_name"] = company
        if industry:
            payload["organization_industry_tag_ids"] = [industry]

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{APOLLO_URL}/mixed_people/search",
                                  json=payload,
                                  headers={"X-Api-Key": APOLLO_API_KEY, "Content-Type": "application/json"})
            data = r.json()

        leads = []
        for person in data.get("people", [])[:limit]:
            org = person.get("organization", {}) or {}
            leads.append({
                "name": person.get("name", ""),
                "title": person.get("title", ""),
                "email": person.get("email", ""),
                "company": org.get("name", ""),
                "industry": org.get("industry", ""),
                "company_size": org.get("estimated_num_employees", ""),
                "linkedin": person.get("linkedin_url", ""),
            })

        return {
            "success": True,
            "data": {"leads": leads, "total": data.get("pagination", {}).get("total_entries", 0)},
            "message": f"Found {len(leads)} leads"
        }
    except Exception as e:
        logger.error("Apollo search failed: %s", e)
        return {"success": False, "data": None, "message": str(e)}


async def search_companies(params: Dict[str, Any]) -> Dict:
    """Search for companies by industry, size, technology."""
    industry = params.get("industry", "")
    keyword = params.get("keyword", "")
    min_employees = int(params.get("min_employees", 10))
    limit = min(int(params.get("limit", 5)), 10)

    if not (industry or keyword):
        return {"success": False, "data": None, "message": "Need industry or keyword"}

    if not APOLLO_API_KEY:
        return {"success": False, "data": None, "message": "APOLLO_API_KEY not configured"}

    try:
        payload = {"page": 1, "per_page": limit}
        if keyword:
            payload["q_organization_name"] = keyword
        if min_employees:
            payload["organization_num_employees_ranges"] = [f"{min_employees},"]

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{APOLLO_URL}/mixed_companies/search",
                                  json=payload,
                                  headers={"X-Api-Key": APOLLO_API_KEY, "Content-Type": "application/json"})
            data = r.json()

        companies = []
        for org in data.get("organizations", [])[:limit]:
            companies.append({
                "name": org.get("name", ""),
                "domain": org.get("primary_domain", ""),
                "industry": org.get("industry", ""),
                "employees": org.get("estimated_num_employees", ""),
                "founded": org.get("founded_year", ""),
                "linkedin": org.get("linkedin_url", ""),
            })

        return {
            "success": True,
            "data": {"companies": companies},
            "message": f"Found {len(companies)} companies"
        }
    except Exception as e:
        return {"success": False, "data": None, "message": str(e)}


TOOLS = [
    {
        "name": "search_people",
        "description": "Find B2B leads with email and title. Use for prospect discovery and outreach targeting.",
        "parameters": {
            "title": "string — job title (e.g., 'CTO', 'VP Marketing')",
            "company": "string — company name (optional)",
            "industry": "string — industry (optional)",
            "limit": "int — max results (default 5)",
        },
        "handler": search_people,
    },
    {
        "name": "search_companies",
        "description": "Find companies by industry, size, or keyword. Use for market research and prospect identification.",
        "parameters": {
            "keyword": "string — company name or keyword",
            "industry": "string — industry filter",
            "min_employees": "int — minimum company size (default 10)",
            "limit": "int — max results (default 5)",
        },
        "handler": search_companies,
    },
]
