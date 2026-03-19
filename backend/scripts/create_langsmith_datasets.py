"""Create evaluation datasets in LangSmith for Bluewave AI quality assessment.

Run once to create the initial datasets:
    python -m scripts.create_langsmith_datasets

Requires LANGSMITH_API_KEY to be set.
"""

import os
import sys

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def create_datasets() -> None:
    from app.core.config import settings

    if not settings.LANGSMITH_API_KEY:
        print("ERROR: LANGSMITH_API_KEY not set. Cannot create datasets.")
        sys.exit(1)

    import langsmith

    client = langsmith.Client(api_key=settings.LANGSMITH_API_KEY)

    # ── Caption evaluation dataset ──────────────────────────────────────
    caption_dataset = client.create_dataset(
        "bluewave-caption-eval",
        description="Evaluation dataset for caption generation quality",
    )
    caption_examples = [
        {
            "input": {"filename": "hero-banner-summer.jpg", "file_type": "image/jpeg", "context": "Beach photo with surfboard"},
            "expected": "1-2 sentences, professional tone, suitable for social media, no hashtags in body",
        },
        {
            "input": {"filename": "product-launch-2026.png", "file_type": "image/png", "context": "Product on white background"},
            "expected": "Mentions product, launch tone, no price, brand-friendly",
        },
        {
            "input": {"filename": "team-retreat-photo.jpg", "file_type": "image/jpeg", "context": "Group of people at offsite event"},
            "expected": "Team/culture focus, warm and professional, suitable for LinkedIn",
        },
        {
            "input": {"filename": "Q4-earnings-infographic.png", "file_type": "image/png", "context": "Financial charts and graphs"},
            "expected": "Data-driven tone, professional, mentions performance or results",
        },
        {
            "input": {"filename": "holiday-promo-banner.webp", "file_type": "image/webp", "context": "Festive holiday sale graphic"},
            "expected": "Festive but professional, mentions promotion without being pushy",
        },
        {
            "input": {"filename": "behind-the-scenes.mp4", "file_type": "video/mp4", "context": "Video of production process"},
            "expected": "Authentic, engaging, behind-the-scenes narrative, professional",
        },
        {
            "input": {"filename": "client-testimonial.jpg", "file_type": "image/jpeg", "context": "Quote card with client photo"},
            "expected": "References testimonial/trust, professional, no direct quote duplication",
        },
        {
            "input": {"filename": "new-office-tour.mp4", "file_type": "video/mp4", "context": "Walking tour of new office space"},
            "expected": "Exciting, forward-looking, mentions the new space or growth",
        },
        {
            "input": {"filename": "sustainability-report-cover.png", "file_type": "image/png", "context": "Green-themed report cover"},
            "expected": "ESG/sustainability focus, values-driven, professional",
        },
        {
            "input": {"filename": "award-ceremony.jpg", "file_type": "image/jpeg", "context": "Team receiving an industry award"},
            "expected": "Celebratory, achievement-focused, mentions recognition",
        },
    ]
    for ex in caption_examples:
        client.create_example(
            inputs=ex["input"],
            outputs={"expected_criteria": ex["expected"]},
            dataset_id=caption_dataset.id,
        )
    print(f"Created caption dataset with {len(caption_examples)} examples")

    # ── Hashtags evaluation dataset ─────────────────────────────────────
    hashtags_dataset = client.create_dataset(
        "bluewave-hashtags-eval",
        description="Evaluation dataset for hashtag generation quality",
    )
    hashtag_examples = [
        {"input": {"filename": "hero-banner-summer.jpg", "file_type": "image/jpeg", "context": "Beach photo"}, "expected_count": "6-10"},
        {"input": {"filename": "product-launch-2026.png", "file_type": "image/png", "context": "Product shot"}, "expected_count": "6-10"},
        {"input": {"filename": "team-retreat-photo.jpg", "file_type": "image/jpeg", "context": "Team event"}, "expected_count": "6-10"},
        {"input": {"filename": "Q4-earnings-infographic.png", "file_type": "image/png", "context": "Financial data"}, "expected_count": "6-10"},
        {"input": {"filename": "behind-the-scenes.mp4", "file_type": "video/mp4", "context": "Production video"}, "expected_count": "6-10"},
    ]
    for ex in hashtag_examples:
        client.create_example(
            inputs=ex["input"],
            outputs={"expected_count": ex["expected_count"]},
            dataset_id=hashtags_dataset.id,
        )
    print(f"Created hashtags dataset with {len(hashtag_examples)} examples")

    # ── Compliance evaluation dataset ───────────────────────────────────
    compliance_dataset = client.create_dataset(
        "bluewave-compliance-eval",
        description="Evaluation dataset for compliance checking quality",
    )
    compliance_examples = [
        {
            "input": {
                "caption": "Check out our amazing new product!",
                "hashtags": ["#newproduct", "#launch"],
                "guidelines": {"tone": "professional", "dos": ["Use professional language"], "donts": ["Avoid exclamation marks"]},
            },
            "expected": "Score should be moderate (50-80), should flag exclamation mark in DON'T rule",
        },
        {
            "input": {
                "caption": "Our latest innovation delivers measurable results for your business.",
                "hashtags": ["#innovation", "#business", "#results"],
                "guidelines": {"tone": "professional", "dos": ["Focus on value proposition"], "donts": []},
            },
            "expected": "Score should be high (85-100), fully compliant with professional tone",
        },
        {
            "input": {
                "caption": "yo check this out fam!! fire content dropping soon",
                "hashtags": ["#fire", "#lit", "#fam"],
                "guidelines": {"tone": "professional", "dos": ["Maintain brand dignity"], "donts": ["Avoid slang"]},
            },
            "expected": "Score should be low (0-40), multiple violations: slang, tone, dignity",
        },
    ]
    for ex in compliance_examples:
        client.create_example(
            inputs=ex["input"],
            outputs={"expected_criteria": ex["expected"]},
            dataset_id=compliance_dataset.id,
        )
    print(f"Created compliance dataset with {len(compliance_examples)} examples")

    print("\nAll datasets created successfully!")


if __name__ == "__main__":
    create_datasets()
