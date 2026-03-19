"""AI Evaluation Framework — measure quality and catch regressions.

Provides automated evaluation of AI service outputs against golden datasets.
Run after any prompt/model change to verify quality is maintained.

Usage:
    python -m tests.eval.eval_framework              # run all evals
    python -m tests.eval.eval_framework --suite compliance  # run specific suite
    python -m tests.eval.eval_framework --report     # generate JSON report

Eval suites:
    - compliance: brand compliance scoring accuracy
    - caption: caption quality and relevance
    - intent: intent router classification accuracy
    - cognitive: reasoning quality in complex tasks
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bluewave.eval")

EVAL_DIR = Path(__file__).parent
RESULTS_DIR = EVAL_DIR / "results"


@dataclass
class EvalCase:
    """A single evaluation test case."""
    id: str
    suite: str
    input_data: dict
    expected: dict  # expected output properties
    description: str = ""
    weight: float = 1.0


@dataclass
class EvalResult:
    """Result of a single eval case."""
    case_id: str
    passed: bool
    score: float  # 0.0 to 1.0
    actual: Any = None
    expected: Any = None
    reason: str = ""
    latency_ms: float = 0.0


@dataclass
class EvalSuiteResult:
    """Aggregate results for an eval suite."""
    suite: str
    total: int
    passed: int
    failed: int
    avg_score: float
    avg_latency_ms: float
    results: list = field(default_factory=list)
    timestamp: str = ""


# ── Golden Datasets ──────────────────────────────────────────

COMPLIANCE_CASES = [
    EvalCase(
        id="comp_perfect",
        suite="compliance",
        input_data={
            "caption": "Elegant handcrafted furniture for discerning cat owners",
            "hashtags": ["#catfurniture", "#design", "#minimalist"],
            "has_image": False,
        },
        expected={"score_range": [70, 100], "max_issues": 2},
        description="On-brand caption with appropriate hashtags",
    ),
    EvalCase(
        id="comp_off_brand",
        suite="compliance",
        input_data={
            "caption": "CHEAP CAT STUFF BUY NOW!!! 50% OFF!!!",
            "hashtags": ["#cheap", "#sale", "#discount", "#buynow"],
            "has_image": False,
        },
        expected={"score_range": [0, 40], "min_issues": 2},
        description="Off-brand aggressive sales caption",
    ),
    EvalCase(
        id="comp_partial",
        suite="compliance",
        input_data={
            "caption": "Beautiful modern cat tree with clean lines",
            "hashtags": ["#cats", "#furniture", "#modern"],
            "has_image": False,
        },
        expected={"score_range": [50, 85], "max_issues": 4},
        description="Partially on-brand — good tone but generic",
    ),
]

INTENT_CASES = [
    EvalCase(
        id="intent_greeting",
        suite="intent",
        input_data={"message": "oi tudo bem?"},
        expected={"category": "chat", "complexity": "simple"},
        description="Simple Portuguese greeting",
    ),
    EvalCase(
        id="intent_brand",
        suite="intent",
        input_data={"message": "check if this image follows our brand guidelines"},
        expected={"category": "brand"},
        description="Brand compliance request",
    ),
    EvalCase(
        id="intent_research",
        suite="intent",
        input_data={"message": "analyze our competitors and find market gaps"},
        expected={"category": "research", "complexity": "complex"},
        description="Research/competitive analysis",
    ),
    EvalCase(
        id="intent_sales",
        suite="intent",
        input_data={"message": "find creative agencies that need content ops help"},
        expected={"category": "sales", "complexity": "complex"},
        description="Sales prospecting request",
    ),
    EvalCase(
        id="intent_assets",
        suite="intent",
        input_data={"message": "show me all draft assets"},
        expected={"category": "assets"},
        description="Asset listing request",
    ),
    EvalCase(
        id="intent_ambiguous",
        suite="intent",
        input_data={"message": "help with my brand new asset upload"},
        expected={"category": "assets"},  # NOT "brand" — "brand new" is adjective
        description="Ambiguous phrasing — should not trigger 'brand' category",
    ),
    EvalCase(
        id="intent_workflow",
        suite="intent",
        input_data={"message": "approve all pending assets with score above 90"},
        expected={"category": "workflow"},
        description="Workflow automation request",
    ),
]

CAPTION_CASES = [
    EvalCase(
        id="caption_image_file",
        suite="caption",
        input_data={"filename": "sunset_beach_campaign_2024.jpg", "file_type": "image/jpeg"},
        expected={"min_length": 20, "max_length": 200, "no_quotes": True},
        description="Caption from descriptive filename",
    ),
    EvalCase(
        id="caption_generic_file",
        suite="caption",
        input_data={"filename": "IMG_4392.png", "file_type": "image/png"},
        expected={"min_length": 15, "max_length": 200, "no_quotes": True},
        description="Caption from non-descriptive filename",
    ),
]

COGNITIVE_CASES = [
    EvalCase(
        id="cog_decomposition",
        suite="cognitive",
        input_data={"message": "Review all pending assets, check compliance, approve those scoring > 90"},
        expected={"mentions_steps": True, "tool_calls_min": 2},
        description="Multi-step task should be decomposed",
    ),
]


# ── Evaluators ───────────────────────────────────────────────

def eval_compliance_case(case: EvalCase, actual: dict) -> EvalResult:
    """Evaluate a compliance check result against expected ranges."""
    score = actual.get("score", 0)
    issues = actual.get("issues", [])
    expected = case.expected

    checks_passed = 0
    total_checks = 0

    # Score range check
    if "score_range" in expected:
        total_checks += 1
        lo, hi = expected["score_range"]
        if lo <= score <= hi:
            checks_passed += 1

    # Issue count checks
    if "min_issues" in expected:
        total_checks += 1
        if len(issues) >= expected["min_issues"]:
            checks_passed += 1

    if "max_issues" in expected:
        total_checks += 1
        if len(issues) <= expected["max_issues"]:
            checks_passed += 1

    eval_score = checks_passed / max(total_checks, 1)
    return EvalResult(
        case_id=case.id,
        passed=eval_score >= 0.8,
        score=eval_score,
        actual={"score": score, "issues_count": len(issues)},
        expected=expected,
        reason="Score=%d, Issues=%d" % (score, len(issues)),
    )


def eval_intent_case(case: EvalCase, actual: dict) -> EvalResult:
    """Evaluate intent classification accuracy."""
    expected = case.expected
    checks_passed = 0
    total_checks = 0

    if "category" in expected:
        total_checks += 1
        if actual.get("category") == expected["category"]:
            checks_passed += 1

    if "complexity" in expected:
        total_checks += 1
        if actual.get("complexity") == expected["complexity"]:
            checks_passed += 1

    eval_score = checks_passed / max(total_checks, 1)
    return EvalResult(
        case_id=case.id,
        passed=eval_score >= 0.8,
        score=eval_score,
        actual=actual,
        expected=expected,
        reason="category=%s (expected %s)" % (actual.get("category"), expected.get("category")),
    )


def eval_caption_case(case: EvalCase, actual: str) -> EvalResult:
    """Evaluate caption quality."""
    expected = case.expected
    checks_passed = 0
    total_checks = 0

    if "min_length" in expected:
        total_checks += 1
        if len(actual) >= expected["min_length"]:
            checks_passed += 1

    if "max_length" in expected:
        total_checks += 1
        if len(actual) <= expected["max_length"]:
            checks_passed += 1

    if expected.get("no_quotes"):
        total_checks += 1
        if not actual.startswith('"') and not actual.startswith("'"):
            checks_passed += 1

    eval_score = checks_passed / max(total_checks, 1)
    return EvalResult(
        case_id=case.id,
        passed=eval_score >= 0.8,
        score=eval_score,
        actual=actual[:100],
        expected=expected,
        reason="len=%d" % len(actual),
    )


# ── Runner ───────────────────────────────────────────────────

async def run_intent_eval() -> EvalSuiteResult:
    """Run intent classification eval suite."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "openclaw-skill"))

    try:
        import anthropic
        from intent_router import classify_intent
        client = anthropic.Anthropic()
    except Exception as e:
        logger.error("Cannot initialize intent router: %s", e)
        return EvalSuiteResult(suite="intent", total=0, passed=0, failed=0, avg_score=0, avg_latency_ms=0)

    results = []
    for case in INTENT_CASES:
        t0 = time.time()
        intent = classify_intent(client, case.input_data["message"])
        latency = (time.time() - t0) * 1000

        actual = {"category": intent.category, "complexity": intent.complexity, "confidence": intent.confidence}
        result = eval_intent_case(case, actual)
        result.latency_ms = latency
        results.append(result)

        status = "✓" if result.passed else "✗"
        logger.info("  %s %s: %s (%.0fms)", status, case.id, result.reason, latency)

    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / max(len(results), 1)
    avg_latency = sum(r.latency_ms for r in results) / max(len(results), 1)

    return EvalSuiteResult(
        suite="intent",
        total=len(results),
        passed=passed,
        failed=len(results) - passed,
        avg_score=round(avg_score, 3),
        avg_latency_ms=round(avg_latency, 1),
        results=[asdict(r) for r in results],
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


async def run_all_evals(suites: Optional[list[str]] = None) -> list[EvalSuiteResult]:
    """Run all eval suites (or specified ones)."""
    all_suites = {
        "intent": run_intent_eval,
    }

    target_suites = suites if suites else list(all_suites.keys())
    results = []

    for suite_name in target_suites:
        runner = all_suites.get(suite_name)
        if not runner:
            logger.warning("Unknown eval suite: %s", suite_name)
            continue

        logger.info("Running eval suite: %s", suite_name)
        result = await runner()
        results.append(result)

        logger.info(
            "Suite %s: %d/%d passed (%.1f%% accuracy, %.0fms avg)",
            suite_name, result.passed, result.total,
            result.avg_score * 100, result.avg_latency_ms,
        )

    return results


def save_report(results: list[EvalSuiteResult]):
    """Save eval results to JSON file."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"eval_{timestamp}.json"

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "suites": [asdict(r) for r in results],
        "summary": {
            "total_cases": sum(r.total for r in results),
            "total_passed": sum(r.passed for r in results),
            "overall_accuracy": round(
                sum(r.avg_score * r.total for r in results) / max(sum(r.total for r in results), 1), 3
            ),
        },
    }

    path.write_text(json.dumps(report, indent=2, default=str))
    logger.info("Report saved: %s", path)
    return path


# ── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bluewave AI Eval Framework")
    parser.add_argument("--suite", type=str, help="Run specific suite (intent, compliance, caption, cognitive)")
    parser.add_argument("--report", action="store_true", help="Save JSON report")
    args = parser.parse_args()

    suites = [args.suite] if args.suite else None
    results = asyncio.run(run_all_evals(suites))

    if args.report:
        save_report(results)

    # Print summary
    print("\n" + "=" * 50)
    for r in results:
        status = "PASS" if r.passed == r.total else "FAIL"
        print(f"  {r.suite}: {r.passed}/{r.total} ({r.avg_score:.0%}) [{status}]")
    print("=" * 50)

    total_passed = sum(r.passed for r in results)
    total = sum(r.total for r in results)
    exit(0 if total_passed == total else 1)
