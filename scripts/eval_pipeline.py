"""Evaluation Pipeline — Golden test runner for agent quality.

P0 3.1: Evaluation Framework.
ГОСТ Р 51904-2002: верификация и валидация.
DO-178C: V&V gate, structural coverage.
MIL-STD-498: Software Test Report (STR).

Usage:
    python scripts/eval_pipeline.py                # Run all golden tests
    python scripts/eval_pipeline.py --level C      # Run only Level C (critical) tests
    python scripts/eval_pipeline.py --report json   # Output JSON report
"""

import argparse
import json
import sys
import os
import yaml
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden"


def load_golden_tests() -> list[dict]:
    """Load all golden test files."""
    tests = []
    for yaml_file in sorted(GOLDEN_DIR.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "tests" not in data:
            continue
        for test in data["tests"]:
            test["source_file"] = yaml_file.name
            tests.append(test)
    return tests


def evaluate_routing(test: dict) -> dict:
    """Evaluate routing accuracy (keyword-based, no LLM needed)."""
    sys.path.insert(0, str(PROJECT_ROOT))

    from services.conductor.registry import AGENTS

    query = test["input"].lower()
    expected = test.get("expected_agent", "")

    # Keyword matching (same as CONDUCTOR)
    scores = {}
    for agent in AGENTS:
        score = sum(1 for kw in agent.keywords if kw in query)
        if score > 0:
            scores[agent.name] = score

    if scores:
        predicted = max(scores, key=scores.get)
        confidence = min(0.85 + scores[predicted] * 0.05, 0.95)
    else:
        predicted = "ceo_agent"
        confidence = 0.3

    correct = predicted == expected
    min_conf = test.get("min_confidence", 0.7)

    return {
        "input": test["input"][:80],
        "expected": expected,
        "predicted": predicted,
        "correct": correct,
        "confidence": round(confidence, 2),
        "meets_confidence": confidence >= min_conf,
        "source": test.get("source_file", ""),
        "criticality": test.get("criticality", "E"),
    }


def run_evaluation(level_filter: str | None = None) -> dict:
    """Run full evaluation pipeline."""
    tests = load_golden_tests()

    # Filter by criticality level if specified
    if level_filter:
        tests = [t for t in tests if t.get("criticality", "E") == level_filter]

    results = []
    for test in tests:
        if "expected_agent" in test:
            result = evaluate_routing(test)
            results.append(result)

    # Compute metrics
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = correct / total if total > 0 else 0

    # Per-criticality metrics
    by_level = {}
    for level in ["C", "D", "E"]:
        level_results = [r for r in results if r["criticality"] == level]
        level_correct = sum(1 for r in level_results if r["correct"])
        level_total = len(level_results)
        by_level[level] = {
            "total": level_total,
            "correct": level_correct,
            "accuracy": round(level_correct / level_total, 3) if level_total > 0 else 0,
        }

    # Failed tests
    failures = [r for r in results if not r["correct"]]

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_tests": total,
        "correct": correct,
        "accuracy": round(accuracy, 3),
        "by_criticality": by_level,
        "failures": failures[:20],
        "pass": accuracy >= 0.8,  # 80% threshold (MIL-STD-498 RTM coverage)
        "golden_files": list(set(r["source"] for r in results)),
    }

    return report


def print_report(report: dict, fmt: str = "text") -> None:
    """Print evaluation report."""
    if fmt == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    print("=" * 60)
    print(f"EVALUATION REPORT — {report['timestamp']}")
    print("=" * 60)
    print(f"Total tests: {report['total_tests']}")
    print(f"Correct:     {report['correct']}")
    print(f"Accuracy:    {report['accuracy']:.1%}")
    print(f"PASS:        {'YES' if report['pass'] else 'NO'} (threshold: 80%)")
    print()

    print("By criticality (ГОСТ Р 51904-2002):")
    for level, data in report["by_criticality"].items():
        status = "PASS" if data["accuracy"] >= 0.8 else "FAIL"
        print(f"  Level {level}: {data['correct']}/{data['total']} ({data['accuracy']:.1%}) [{status}]")
    print()

    if report["failures"]:
        print(f"Failures ({len(report['failures'])}):")
        for f in report["failures"][:10]:
            print(f"  [{f['criticality']}] '{f['input']}' expected={f['expected']} got={f['predicted']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Evaluation Pipeline for Zavod-ii agents")
    parser.add_argument("--level", choices=["C", "D", "E"], help="Filter by criticality level")
    parser.add_argument("--report", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    report = run_evaluation(level_filter=args.level)
    print_report(report, fmt=args.report)

    # Exit with error code if evaluation fails
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
