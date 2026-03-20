"""Brand DNA Extractor — extract complete brand identity from raw materials.

Takes: PDF brand guidelines, images, or text descriptions
Returns: Structured Brand DNA JSON ready for compliance checking

This is the R$997 setup service. Each brand extraction creates a tenant-ready
Brand DNA that powers all compliance checks and content generation.

Revenue model: one-time extraction fee + ongoing compliance checks per asset.
"""

import base64
import json
import logging
import os
from typing import Optional

import anthropic

logger = logging.getLogger("openclaw.brand_dna")

MODEL = os.environ.get("BRAND_DNA_MODEL", "claude-sonnet-4-20250514")


EXTRACTION_PROMPT = """You are a senior brand strategist extracting a complete Brand DNA from the provided materials.

Analyze EVERYTHING and extract into this exact JSON structure:

{
  "brand_name": "...",
  "positioning": "one sentence brand positioning",
  "brand_personality": "3-5 adjectives",
  "archetypes": ["primary archetype", "secondary archetype"],
  "primary_colors": ["#hex1", "#hex2", "#hex3"],
  "secondary_colors": ["#hex1", "#hex2"],
  "accent_colors": ["#hex"],
  "forbidden_colors": ["#hex or description"],
  "fonts": {
    "primary": "Font Name",
    "secondary": "Font Name",
    "forbidden": ["fonts that should NOT be used"]
  },
  "tone_description": "detailed tone of voice description",
  "tone_adjectives": ["adj1", "adj2", "adj3"],
  "tone_examples": {
    "do": ["example of on-brand copy"],
    "dont": ["example of off-brand copy"]
  },
  "dos": ["specific brand rules to follow"],
  "donts": ["specific brand rules to avoid"],
  "logo_rules": {
    "primary_version": "description",
    "minimum_size": "description",
    "clear_space": "description",
    "forbidden_modifications": ["list"]
  },
  "photography_style": "description of approved photo style",
  "composition_rules": ["rule1", "rule2"],
  "target_audience": "description",
  "competitors": ["competitor1", "competitor2"],
  "channels": {
    "instagram_feed": {"aspect_ratio": "1:1", "tone": "..."},
    "instagram_stories": {"aspect_ratio": "9:16", "tone": "..."},
    "linkedin": {"tone": "..."},
    "website": {"tone": "..."}
  },
  "custom_rules": {}
}

Extract EVERY detail you can find. If a field isn't in the source material, make an intelligent inference based on what IS provided and mark it with "(inferred)".

Be exhaustive. This Brand DNA will power automated compliance checking across hundreds of assets."""


async def extract_brand_dna(
    image_b64: Optional[str] = None,
    media_type: str = "image/jpeg",
    text_content: Optional[str] = None,
    pdf_text: Optional[str] = None,
    brand_name: str = "",
) -> dict:
    """Extract Brand DNA from provided materials.

    Accepts any combination of: image (brand guide pages), text, PDF text.
    Returns structured Brand DNA JSON.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "ANTHROPIC_API_KEY not configured"}

    client = anthropic.Anthropic(api_key=api_key)

    messages_content = []

    # Add image if provided
    if image_b64:
        messages_content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": image_b64},
        })

    # Build text context
    text_parts = []
    if brand_name:
        text_parts.append(f"Brand name: {brand_name}")
    if text_content:
        text_parts.append(f"Brand description:\n{text_content[:5000]}")
    if pdf_text:
        text_parts.append(f"Brand guidelines document:\n{pdf_text[:10000]}")

    if not text_parts and not image_b64:
        return {"success": False, "error": "Need at least one input: image, text, or PDF"}

    messages_content.append({
        "type": "text",
        "text": "Extract the complete Brand DNA from these materials.\n\n" + "\n\n".join(text_parts),
    })

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=[{
                "type": "text",
                "text": EXTRACTION_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": messages_content}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        brand_dna = json.loads(raw)

        return {
            "success": True,
            "brand_dna": brand_dna,
            "tokens_used": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            },
        }

    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse Brand DNA JSON", "raw": raw[:500]}
    except Exception as e:
        logger.error("Brand DNA extraction failed: %s", e)
        return {"success": False, "error": str(e)}


async def generate_compliance_certificate(
    brand_name: str,
    asset_name: str,
    score: int,
    dimensions: dict,
    checked_at: str,
) -> str:
    """Generate a compliance certificate as formatted text.

    Returns certificate content ready to be rendered as PDF by the frontend.
    """
    passed = score >= 70
    verdict = "APROVADO" if passed else "REPROVADO"

    lines = [
        f"CERTIFICADO DE CONFORMIDADE DE MARCA",
        f"",
        f"Marca: {brand_name}",
        f"Asset: {asset_name}",
        f"Data: {checked_at}",
        f"",
        f"RESULTADO: {verdict}",
        f"Score: {score}/100",
        f"",
        f"ANÁLISE DIMENSIONAL:",
    ]

    for dim_name, dim_data in dimensions.items():
        dim_score = dim_data.get("score", "N/A")
        dim_status = "OK" if isinstance(dim_score, (int, float)) and dim_score >= 70 else "ALERTA"
        lines.append(f"  {dim_name}: {dim_score}/100 — {dim_status}")

    lines.extend([
        f"",
        f"Este certificado atesta que o asset foi analisado automaticamente",
        f"pelo Bluewave Brand Guardian em 8 dimensões de conformidade.",
        f"",
        f"Verificação: bluewave.app/verify/{checked_at[:10]}-{score}",
        f"",
        f"Bluewave — AI Creative Operations",
    ])

    return "\n".join(lines)
