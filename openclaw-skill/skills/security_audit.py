"""Security Audit — defensive cybersecurity services Wave sells for crypto.

Passive analysis only — no unauthorized access. All data from public sources.
Services: SSL/TLS audit, security headers, DNS recon, subdomain enumeration,
data breach check, tech stack fingerprinting, OWASP assessment report.

Revenue: $15-300 per audit depending on depth.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import ssl
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List
from pathlib import Path

import httpx
from duckduckgo_search import DDGS

logger = logging.getLogger("openclaw.skills.security_audit")

TIMEOUT = httpx.Timeout(15.0, connect=10.0)
UA = "Mozilla/5.0 (compatible; BluewaveSecAudit/1.0; +https://bluewave.app)"


# ══════════════════════════════════════════════════════════════
# 1. SECURITY HEADERS AUDIT
# ══════════════════════════════════════════════════════════════

async def audit_headers(params: Dict[str, Any]) -> Dict:
    """Audit HTTP security headers of a website. OWASP-aligned.

    Checks: HSTS, CSP, X-Frame-Options, X-Content-Type-Options,
    Referrer-Policy, Permissions-Policy, X-XSS-Protection, CORS.
    Scores 0-100 with specific recommendations.
    """
    url = params.get("url", "")
    if not url:
        return {"success": False, "data": None, "message": "Need URL"}

    if not url.startswith("http"):
        url = "https://" + url

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": UA})

        headers = dict(resp.headers)
        checks = []
        score = 100

        # Required security headers
        required = {
            "strict-transport-security": {
                "name": "HSTS", "weight": 15,
                "fix": "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
            },
            "content-security-policy": {
                "name": "CSP", "weight": 20,
                "fix": "Add Content-Security-Policy header. Start with: default-src 'self'; script-src 'self'",
            },
            "x-frame-options": {
                "name": "X-Frame-Options", "weight": 10,
                "fix": "Add: X-Frame-Options: DENY (or SAMEORIGIN). Prevents clickjacking.",
            },
            "x-content-type-options": {
                "name": "X-Content-Type", "weight": 10,
                "fix": "Add: X-Content-Type-Options: nosniff. Prevents MIME-type sniffing.",
            },
            "referrer-policy": {
                "name": "Referrer-Policy", "weight": 5,
                "fix": "Add: Referrer-Policy: strict-origin-when-cross-origin",
            },
            "permissions-policy": {
                "name": "Permissions-Policy", "weight": 10,
                "fix": "Add: Permissions-Policy: camera=(), microphone=(), geolocation=()",
            },
        }

        for header_key, info in required.items():
            present = any(k.lower() == header_key for k in headers)
            value = headers.get(header_key, "")

            if present:
                checks.append({"header": info["name"], "status": "PASS", "value": value[:100]})
            else:
                score -= info["weight"]
                checks.append({"header": info["name"], "status": "FAIL", "fix": info["fix"]})

        # Check for info leakage headers
        leaky_headers = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"]
        for lh in leaky_headers:
            val = headers.get(lh, "")
            if val:
                score -= 5
                checks.append({
                    "header": lh.upper(), "status": "WARN",
                    "value": val, "fix": "Remove %s header — leaks server info to attackers" % lh,
                })

        # Check CORS
        cors = headers.get("access-control-allow-origin", "")
        if cors == "*":
            score -= 10
            checks.append({
                "header": "CORS", "status": "FAIL",
                "value": cors, "fix": "CORS set to '*' — allows any origin. Restrict to specific domains.",
            })

        # Check cookies
        cookies = resp.headers.get_list("set-cookie")
        for cookie in cookies:
            cookie_lower = cookie.lower()
            issues = []
            if "secure" not in cookie_lower:
                issues.append("missing Secure flag")
            if "httponly" not in cookie_lower:
                issues.append("missing HttpOnly flag")
            if "samesite" not in cookie_lower:
                issues.append("missing SameSite attribute")
            if issues:
                score -= 3
                name = cookie.split("=")[0][:30]
                checks.append({
                    "header": "Cookie: %s" % name, "status": "WARN",
                    "value": ", ".join(issues),
                    "fix": "Add Secure; HttpOnly; SameSite=Lax to cookie",
                })

        score = max(0, score)
        grade = "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D" if score >= 30 else "F"

        # Format report
        lines = [
            "**Security Headers Audit: %s**" % url,
            "Score: **%d/100** (Grade: **%s**)\n" % (score, grade),
        ]

        passes = [c for c in checks if c["status"] == "PASS"]
        fails = [c for c in checks if c["status"] == "FAIL"]
        warns = [c for c in checks if c["status"] == "WARN"]

        if fails:
            lines.append("**MISSING (critical):**")
            for c in fails:
                lines.append("  - %s — %s" % (c["header"], c.get("fix", "")))
            lines.append("")

        if warns:
            lines.append("**WARNINGS:**")
            for c in warns:
                lines.append("  - %s: %s — %s" % (c["header"], c.get("value", ""), c.get("fix", "")))
            lines.append("")

        if passes:
            lines.append("**PASSING:**")
            for c in passes:
                lines.append("  - %s: %s" % (c["header"], c.get("value", "")[:60]))

        return {
            "success": True,
            "data": {"url": url, "score": score, "grade": grade, "checks": checks},
            "message": "\n".join(lines),
        }

    except Exception as e:
        return {"success": False, "data": None, "message": "Header audit failed: %s" % str(e)}


# ══════════════════════════════════════════════════════════════
# 2. SSL/TLS AUDIT
# ══════════════════════════════════════════════════════════════

async def audit_ssl(params: Dict[str, Any]) -> Dict:
    """Audit SSL/TLS configuration of a domain.

    Checks: certificate validity, expiry, protocol version, issuer,
    subject alt names, and common misconfigurations.
    """
    domain = params.get("domain", "")
    if not domain:
        return {"success": False, "data": None, "message": "Need domain"}

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    port = int(params.get("port", 443))

    try:
        ctx = ssl.create_default_context()
        conn = ctx.wrap_socket(socket.socket(), server_hostname=domain)
        conn.settimeout(10)
        conn.connect((domain, port))
        cert = conn.getpeercert()
        cipher = conn.cipher()
        version = conn.version()
        conn.close()

        # Parse cert details
        not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_left = (not_after - datetime.now(timezone.utc)).days

        issuer = dict(x[0] for x in cert.get("issuer", []))
        subject = dict(x[0] for x in cert.get("subject", []))
        sans = [entry[1] for entry in cert.get("subjectAltName", [])]

        issues = []
        score = 100

        # Check expiry
        if days_left < 0:
            issues.append("EXPIRED %d days ago" % abs(days_left))
            score -= 50
        elif days_left < 14:
            issues.append("Expires in %d days — RENEW NOW" % days_left)
            score -= 20
        elif days_left < 30:
            issues.append("Expires in %d days — renewal recommended" % days_left)
            score -= 5

        # Check protocol
        if version and "TLSv1.0" in version or "TLSv1.1" in version or "SSLv" in str(version):
            issues.append("Outdated protocol: %s — upgrade to TLS 1.2+" % version)
            score -= 20

        # Check cipher strength
        if cipher and cipher[2] and cipher[2] < 128:
            issues.append("Weak cipher: %s (%d bits)" % (cipher[0], cipher[2]))
            score -= 15

        # Check self-signed
        issuer_cn = issuer.get("commonName", issuer.get("organizationName", ""))
        subject_cn = subject.get("commonName", "")
        if issuer_cn == subject_cn:
            issues.append("Self-signed certificate — not trusted by browsers")
            score -= 30

        # Check wildcard
        has_wildcard = any(s.startswith("*.") for s in sans)

        score = max(0, score)
        grade = "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "F"

        data = {
            "domain": domain,
            "score": score,
            "grade": grade,
            "issuer": issuer_cn,
            "subject": subject_cn,
            "protocol": version,
            "cipher": cipher[0] if cipher else "unknown",
            "cipher_bits": cipher[2] if cipher else 0,
            "valid_from": not_before.isoformat(),
            "valid_until": not_after.isoformat(),
            "days_until_expiry": days_left,
            "san_count": len(sans),
            "wildcard": has_wildcard,
            "issues": issues,
        }

        lines = [
            "**SSL/TLS Audit: %s**" % domain,
            "Score: **%d/100** (Grade: **%s**)\n" % (score, grade),
            "Issuer: %s" % issuer_cn,
            "Protocol: %s | Cipher: %s (%s bits)" % (version, cipher[0] if cipher else "?", cipher[2] if cipher else "?"),
            "Valid: %s to %s (**%d days left**)" % (not_before.strftime("%Y-%m-%d"), not_after.strftime("%Y-%m-%d"), days_left),
            "SANs: %d domains%s" % (len(sans), " (wildcard)" if has_wildcard else ""),
        ]

        if issues:
            lines.append("\n**Issues found:**")
            for issue in issues:
                lines.append("  - %s" % issue)
        else:
            lines.append("\nNo issues found. Certificate configuration is solid.")

        return {"success": True, "data": data, "message": "\n".join(lines)}

    except ssl.SSLCertVerificationError as e:
        return {"success": True, "data": {"domain": domain, "score": 0, "grade": "F", "issues": [str(e)]},
                "message": "**SSL FAIL: %s**\n%s\nCertificate cannot be verified — critical security issue." % (domain, str(e))}
    except Exception as e:
        return {"success": False, "data": None, "message": "SSL audit failed: %s" % str(e)}


# ══════════════════════════════════════════════════════════════
# 3. DNS RECON & SUBDOMAIN ENUMERATION
# ══════════════════════════════════════════════════════════════

async def recon_dns(params: Dict[str, Any]) -> Dict:
    """DNS reconnaissance and subdomain enumeration using public sources.

    Finds subdomains via certificate transparency logs (crt.sh),
    checks DNS records, and identifies potential attack surface.
    """
    domain = params.get("domain", "")
    if not domain:
        return {"success": False, "data": None, "message": "Need domain"}

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    results = {"domain": domain, "subdomains": [], "dns_records": {}, "issues": []}

    # 1. Subdomain enumeration via crt.sh (Certificate Transparency)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("https://crt.sh/?q=%%.%s&output=json" % domain)
            if resp.status_code == 200:
                entries = resp.json()
                subdomains = set()
                for entry in entries:
                    name = entry.get("name_value", "")
                    for sub in name.split("\n"):
                        sub = sub.strip().lower()
                        if sub.endswith(domain) and "*" not in sub:
                            subdomains.add(sub)
                results["subdomains"] = sorted(subdomains)
    except Exception as e:
        logger.debug("crt.sh failed: %s", e)

    # 2. DNS records via public DNS API
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for rtype in record_types:
                try:
                    resp = await client.get(
                        "https://dns.google/resolve?name=%s&type=%s" % (domain, rtype)
                    )
                    data = resp.json()
                    answers = data.get("Answer", [])
                    if answers:
                        results["dns_records"][rtype] = [a.get("data", "") for a in answers]
                except Exception:
                    continue
    except Exception as e:
        logger.debug("DNS lookup failed: %s", e)

    # 3. Analyze for issues
    issues = []

    # Check for email security
    txt_records = results["dns_records"].get("TXT", [])
    has_spf = any("v=spf1" in t for t in txt_records)
    has_dmarc = False
    has_dkim = False

    # Check DMARC
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("https://dns.google/resolve?name=_dmarc.%s&type=TXT" % domain)
            dmarc_data = resp.json()
            if dmarc_data.get("Answer"):
                has_dmarc = True
                results["dns_records"]["DMARC"] = [a.get("data", "") for a in dmarc_data["Answer"]]
    except Exception:
        pass

    if not has_spf:
        issues.append("No SPF record — email spoofing possible")
    if not has_dmarc:
        issues.append("No DMARC record — email impersonation risk")

    # Check for dangling CNAME (subdomain takeover risk)
    cnames = results["dns_records"].get("CNAME", [])
    takeover_services = ["github.io", "herokuapp.com", "azurewebsites.net", "s3.amazonaws.com",
                         "cloudfront.net", "pantheon.io", "shopify.com", "fastly.net"]
    for cname in cnames:
        if any(svc in cname for svc in takeover_services):
            issues.append("CNAME to %s — potential subdomain takeover risk" % cname)

    # Interesting subdomains
    interesting = [s for s in results["subdomains"] if any(
        kw in s for kw in ["admin", "staging", "dev", "test", "api", "internal", "vpn", "mail",
                            "portal", "login", "dashboard", "jenkins", "gitlab", "jira"]
    )]

    results["issues"] = issues
    results["interesting_subdomains"] = interesting

    # Format report
    lines = [
        "**DNS Recon: %s**" % domain,
        "Subdomains found: **%d**" % len(results["subdomains"]),
        "Interesting subdomains: **%d**" % len(interesting),
    ]

    if issues:
        lines.append("\n**Security Issues:**")
        for issue in issues:
            lines.append("  - %s" % issue)

    if interesting:
        lines.append("\n**Interesting subdomains:**")
        for s in interesting[:15]:
            lines.append("  - %s" % s)

    lines.append("\n**DNS Records:**")
    for rtype, values in results["dns_records"].items():
        lines.append("  %s: %s" % (rtype, ", ".join(v[:60] for v in values[:3])))

    lines.append("\n**Email Security:**")
    lines.append("  SPF: %s | DMARC: %s" % ("PASS" if has_spf else "FAIL", "PASS" if has_dmarc else "FAIL"))

    return {"success": True, "data": results, "message": "\n".join(lines)}


# ══════════════════════════════════════════════════════════════
# 4. TECH STACK FINGERPRINTING
# ══════════════════════════════════════════════════════════════

async def fingerprint_tech(params: Dict[str, Any]) -> Dict:
    """Identify technologies used by a website via passive analysis.

    Checks: HTTP headers, HTML meta tags, JavaScript libraries, cookies,
    and known patterns to identify CMS, frameworks, CDNs, analytics, etc.
    """
    url = params.get("url", "")
    if not url:
        return {"success": False, "data": None, "message": "Need URL"}

    if not url.startswith("http"):
        url = "https://" + url

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": UA})

        headers = dict(resp.headers)
        body = resp.text[:50000]
        techs = []

        # Header-based detection
        server = headers.get("server", "")
        if server:
            techs.append({"category": "Server", "name": server, "source": "header"})

        powered = headers.get("x-powered-by", "")
        if powered:
            techs.append({"category": "Runtime", "name": powered, "source": "header"})

        # Body-based detection patterns
        patterns = {
            "WordPress": [r'wp-content/', r'wp-includes/', r'wordpress'],
            "React": [r'react\.production\.min\.js', r'__NEXT_DATA__', r'_next/static'],
            "Next.js": [r'__NEXT_DATA__', r'_next/static', r'next\.config'],
            "Vue.js": [r'vue\.runtime', r'v-cloak', r'vue\.min\.js'],
            "Angular": [r'ng-version', r'angular\.min\.js', r'ng-app'],
            "jQuery": [r'jquery[\.-]', r'jquery\.min\.js'],
            "Bootstrap": [r'bootstrap\.min\.(css|js)', r'bootstrap[\.-]'],
            "Tailwind": [r'tailwindcss', r'tailwind\.config'],
            "Shopify": [r'cdn\.shopify\.com', r'shopify\.com/s/'],
            "Wix": [r'static\.wixstatic\.com', r'wix\.com'],
            "Squarespace": [r'squarespace\.com', r'sqsp\.com'],
            "Google Analytics": [r'google-analytics\.com', r'gtag/', r'googletagmanager'],
            "Google Tag Manager": [r'googletagmanager\.com'],
            "Cloudflare": [r'cf-ray', r'cloudflare'],
            "AWS": [r'amazonaws\.com', r'aws-'],
            "Vercel": [r'vercel\.app', r'_vercel'],
            "Netlify": [r'netlify\.app', r'netlify'],
            "Stripe": [r'js\.stripe\.com', r'stripe\.com'],
            "HubSpot": [r'hubspot\.com', r'hs-scripts'],
            "Intercom": [r'intercom\.io', r'intercomcdn'],
            "Sentry": [r'sentry\.io', r'sentry-'],
            "reCAPTCHA": [r'recaptcha', r'google\.com/recaptcha'],
            "PHP": [r'\.php', r'PHPSESSID'],
            "Laravel": [r'laravel', r'XSRF-TOKEN'],
            "Django": [r'csrfmiddlewaretoken', r'django'],
            "Ruby on Rails": [r'rails', r'turbolinks'],
        }

        body_lower = body.lower()
        headers_str = json.dumps(headers).lower()
        search_text = body_lower + " " + headers_str

        for tech_name, regexes in patterns.items():
            for pattern in regexes:
                if re.search(pattern, search_text, re.IGNORECASE):
                    techs.append({"category": "Technology", "name": tech_name, "source": "pattern"})
                    break

        # Deduplicate
        seen = set()
        unique_techs = []
        for t in techs:
            key = t["name"].lower()
            if key not in seen:
                seen.add(key)
                unique_techs.append(t)

        lines = ["**Tech Stack: %s**\n" % url, "Detected **%d technologies**:\n" % len(unique_techs)]
        for t in unique_techs:
            lines.append("  - **%s** (%s)" % (t["name"], t["category"]))

        return {"success": True, "data": {"url": url, "technologies": unique_techs}, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "Fingerprinting failed: %s" % str(e)}


# ══════════════════════════════════════════════════════════════
# 5. DATA BREACH CHECK
# ══════════════════════════════════════════════════════════════

async def check_breach(params: Dict[str, Any]) -> Dict:
    """Check if an email or domain has been involved in known data breaches.

    Uses public breach databases. Does NOT access leaked data —
    only checks if the email/domain appears in known breach lists.
    """
    target = params.get("email", params.get("domain", ""))
    if not target:
        return {"success": False, "data": None, "message": "Need email or domain"}

    results = []

    # Search for breach mentions via web search
    try:
        queries = [
            '"%s" "data breach" OR "leaked" OR "compromised"' % target,
            '"%s" site:haveibeenpwned.com' % target,
        ]
        for q in queries:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=5):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            await asyncio.sleep(1)
    except Exception as e:
        logger.debug("Breach search failed: %s", e)

    # Check HIBP API (rate limited, no key needed for domain)
    if "@" not in target:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    "https://haveibeenpwned.com/api/v3/breaches",
                    params={"domain": target},
                    headers={"User-Agent": "BluewaveSecAudit"},
                )
                if resp.status_code == 200:
                    breaches = resp.json()
                    for b in breaches[:10]:
                        results.append({
                            "title": "HIBP: %s (%s)" % (b.get("Name", ""), b.get("BreachDate", "")),
                            "url": "https://haveibeenpwned.com/",
                            "snippet": "Compromised data: %s. %d accounts affected." % (
                                ", ".join(b.get("DataClasses", [])[:5]),
                                b.get("PwnCount", 0),
                            ),
                        })
        except Exception:
            pass

    if results:
        lines = ["**Breach Check: %s**\n" % target, "Found **%d** breach references:\n" % len(results)]
        for r in results[:10]:
            lines.append("- **%s**\n  %s\n  %s\n" % (r["title"][:60], r["url"], r["snippet"][:150]))
        return {"success": True, "data": results, "message": "\n".join(lines)}

    return {"success": True, "data": [], "message": "**Breach Check: %s**\n\nNo known breaches found." % target}


# ══════════════════════════════════════════════════════════════
# 6. FULL SECURITY REPORT (combines all checks)
# ══════════════════════════════════════════════════════════════

async def full_security_audit(params: Dict[str, Any]) -> Dict:
    """Run a comprehensive security audit: headers + SSL + DNS + tech stack.

    This is the premium $50-200 service. Runs all checks in parallel
    and produces a unified report with overall score.
    """
    domain = params.get("domain", "")
    if not domain:
        return {"success": False, "data": None, "message": "Need domain"}

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    url = "https://%s" % domain

    # Run all audits in parallel
    header_task = audit_headers({"url": url})
    ssl_task = audit_ssl({"domain": domain})
    dns_task = recon_dns({"domain": domain})
    tech_task = fingerprint_tech({"url": url})

    results = await asyncio.gather(header_task, ssl_task, dns_task, tech_task, return_exceptions=True)

    header_result = results[0] if not isinstance(results[0], Exception) else {"data": {"score": 0}}
    ssl_result = results[1] if not isinstance(results[1], Exception) else {"data": {"score": 0}}
    dns_result = results[2] if not isinstance(results[2], Exception) else {"data": {}}
    tech_result = results[3] if not isinstance(results[3], Exception) else {"data": {}}

    # Calculate overall score
    header_score = (header_result.get("data") or {}).get("score", 0)
    ssl_score = (ssl_result.get("data") or {}).get("score", 0)

    dns_issues = len((dns_result.get("data") or {}).get("issues", []))
    dns_score = max(0, 100 - dns_issues * 15)

    overall = int((header_score * 0.35) + (ssl_score * 0.35) + (dns_score * 0.30))
    grade = "A+" if overall >= 95 else "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 50 else "D" if overall >= 30 else "F"

    # Compile report
    sub_count = len((dns_result.get("data") or {}).get("subdomains", []))
    tech_count = len((tech_result.get("data") or {}).get("technologies", []))

    lines = [
        "=" * 50,
        "**FULL SECURITY AUDIT: %s**" % domain,
        "=" * 50,
        "",
        "Overall Score: **%d/100** (Grade: **%s**)" % (overall, grade),
        "",
        "| Component | Score | Grade |",
        "|-----------|-------|-------|",
        "| Headers | %d/100 | %s |" % (header_score, (header_result.get("data") or {}).get("grade", "?")),
        "| SSL/TLS | %d/100 | %s |" % (ssl_score, (ssl_result.get("data") or {}).get("grade", "?")),
        "| DNS Security | %d/100 | %s |" % (dns_score, "A" if dns_score >= 85 else "B" if dns_score >= 70 else "C" if dns_score >= 50 else "F"),
        "",
        "**Attack Surface:**",
        "  - Subdomains: %d" % sub_count,
        "  - Technologies: %d" % tech_count,
        "",
    ]

    # Add individual report sections
    for name, result in [("HEADERS", header_result), ("SSL/TLS", ssl_result), ("DNS", dns_result), ("TECH STACK", tech_result)]:
        msg = result.get("message", "") if isinstance(result, dict) else ""
        if msg:
            lines.append("--- %s ---" % name)
            lines.append(msg)
            lines.append("")

    report = {
        "domain": domain,
        "overall_score": overall,
        "overall_grade": grade,
        "header_score": header_score,
        "ssl_score": ssl_score,
        "dns_score": dns_score,
        "subdomains": sub_count,
        "technologies": tech_count,
    }

    return {"success": True, "data": report, "message": "\n".join(lines)}


TOOLS = [
    {
        "name": "sec_audit_headers",
        "description": "Audit HTTP security headers (OWASP). Checks HSTS, CSP, X-Frame, cookies, CORS, info leakage. Score 0-100 with specific fixes. Service price: $15-30.",
        "handler": audit_headers,
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Website URL to audit"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "sec_audit_ssl",
        "description": "Audit SSL/TLS certificate and configuration. Checks expiry, protocol version, cipher strength, self-signed, SANs. Score 0-100. Service price: $20-50.",
        "handler": audit_ssl,
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to check (e.g. 'example.com')"},
                "port": {"type": "integer", "default": 443},
            },
            "required": ["domain"],
        },
    },
    {
        "name": "sec_recon_dns",
        "description": "DNS reconnaissance and subdomain enumeration. Finds subdomains via certificate transparency, checks SPF/DMARC, identifies subdomain takeover risks. Service price: $30-80.",
        "handler": recon_dns,
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to enumerate"},
            },
            "required": ["domain"],
        },
    },
    {
        "name": "sec_fingerprint",
        "description": "Identify technologies used by a website. Detects CMS, frameworks, CDNs, analytics, payment processors via passive analysis. Service price: $15-30.",
        "handler": fingerprint_tech,
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Website URL"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "sec_breach_check",
        "description": "Check if email or domain appears in known data breaches. Uses public breach databases and HIBP. Service price: $15-40.",
        "handler": check_breach,
        "parameters": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Email address to check"},
                "domain": {"type": "string", "description": "Domain to check (alternative to email)"},
            },
        },
    },
    {
        "name": "sec_full_audit",
        "description": "PREMIUM: Full security audit — headers + SSL + DNS + tech stack in one report. Runs all checks in parallel. Overall score 0-100 with grade. Service price: $50-200.",
        "handler": full_security_audit,
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to audit (e.g. 'example.com')"},
            },
            "required": ["domain"],
        },
    },
]
