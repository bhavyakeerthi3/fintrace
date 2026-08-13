"""Apply a separate, explicit grading record to a completed raw baseline run."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def percentage(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 100.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "outputs" / "fintrace-single-prompt-live-results.json")
    parser.add_argument("--suite", type=Path, default=ROOT / "fixtures" / "benchmark-suite.json")
    parser.add_argument("--decisions", type=Path, default=ROOT / "fixtures" / "single-prompt-live-grading.json")
    args = parser.parse_args()

    run = json.loads(args.run.read_text(encoding="utf-8"))
    suite = json.loads(args.suite.read_text(encoding="utf-8"))
    grading_source = json.loads(args.decisions.read_text(encoding="utf-8"))
    expected = {
        finding["finding_id"]: finding["expected_result"]
        for case in suite["cases"]
        for finding in case["findings"]
    }
    raw_by_finding = {
        finding_id: result["raw_output"]
        for result in run["results"]
        for finding_id in result["finding_ids"]
    }
    decisions = {item["finding_id"]: dict(item) for item in grading_source["decisions"]}
    if set(decisions) != set(expected):
        raise ValueError("Grading decisions must cover every benchmark finding exactly once")

    outputs: list[dict[str, Any]] = []
    for finding_id in expected:
        decision = decisions[finding_id]
        excerpt = decision["output_excerpt"]
        if excerpt not in raw_by_finding[finding_id]:
            raise ValueError(f"Grading excerpt for {finding_id} is not verbatim in the raw output")
        classification = decision["classification"]
        if classification not in {"explained", "unresolved", "aligned"}:
            raise ValueError(f"Invalid classification for {finding_id}: {classification}")
        outputs.append({
            **decision,
            "expected_result": expected[finding_id],
            "correct": classification == expected[finding_id],
        })

    correct = sum(item["correct"] for item in outputs)
    false_positives = sum(
        item["expected_result"] == "aligned" and item["classification"] != "aligned"
        for item in outputs
    )
    unsupported = sum(
        item["classification"] == "explained" and item["expected_result"] != "explained"
        for item in outputs
    )
    expected_unresolved = [item for item in outputs if item["expected_result"] == "unresolved"]
    correct_unresolved = sum(item["classification"] == "unresolved" for item in expected_unresolved)
    metrics = {
        "finding_count": len(outputs),
        "correct_classifications": correct,
        "incorrect_classifications": len(outputs) - correct,
        "classification_accuracy": percentage(correct, len(outputs)),
        "false_positives": false_positives,
        "false_positive_rate": percentage(false_positives, len(outputs)),
        "unsupported_explanations": unsupported,
        "unsupported_explanation_rate": percentage(unsupported, len(outputs)),
        "expected_unresolved_items": len(expected_unresolved),
        "correct_unresolved_items": correct_unresolved,
        "unresolved_item_accuracy": percentage(correct_unresolved, len(expected_unresolved)),
    }
    run["grading"] = {
        "grading_version": grading_source["grading_version"],
        "graded_at": datetime.now(UTC).isoformat(),
        "method": grading_source["method"],
        "rubric": grading_source["rubric"],
        "metrics": metrics,
        "outputs": outputs,
    }
    args.run.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
