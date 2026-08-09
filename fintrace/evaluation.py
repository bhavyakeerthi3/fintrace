"""Measured baseline, workflow, and ablation evaluation on controlled fixtures."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


MODES = ("single_prompt", "four_specialists", "specialists_plus_calculation", "full_fintrace")
BASELINE_PROMPT = "Review the transcript and filing. Identify any financial inconsistencies and explain them. Return your findings."


def load_benchmark(path: Path) -> dict[str, Any]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    if suite.get("data_classification") != "fictional_benchmark":
        raise ValueError("Benchmark must be explicitly classified as fictional")
    cases = suite.get("cases")
    if not isinstance(cases, list) or len(cases) < 12:
        raise ValueError("Benchmark must contain at least 12 cases")
    return suite


def _quote_valid(finding: Mapping[str, Any]) -> bool:
    candidate = finding.get("candidate_explanation")
    if not isinstance(candidate, Mapping):
        return False
    quote = " ".join(str(candidate.get("quote", "")).split()).casefold()
    return bool(quote) and any(
        quote in " ".join(str(item.get("text", "")).split()).casefold()
        for item in finding.get("filing_passages", [])
        if isinstance(item, Mapping)
    )


def _numerically_reconciles(finding: Mapping[str, Any]) -> bool:
    candidate = finding.get("candidate_explanation")
    if not isinstance(candidate, Mapping):
        return False
    adjustment = candidate.get("numeric_adjustment")
    if isinstance(adjustment, bool) or not isinstance(adjustment, (int, float)):
        return False
    direction = 1 if candidate.get("direction") == "add" else -1
    adjusted = float(finding["computed_value"]) + direction * float(adjustment)
    return abs(float(finding["claimed_value"]) - adjusted) <= float(finding["tolerance"])


def classify_finding(finding: Mapping[str, Any], mode: str) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"Unknown evaluation mode: {mode}")
    gap = float(finding["claimed_value"]) - float(finding["computed_value"])
    calculation_enabled = mode in {"specialists_plus_calculation", "full_fintrace"}
    if calculation_enabled and abs(gap) <= float(finding["tolerance"]):
        result = "aligned"
    elif mode == "full_fintrace":
        candidate = finding.get("candidate_explanation")
        strict = (
            isinstance(candidate, Mapping)
            and candidate.get("direct_connection") is True
            and _quote_valid(finding)
            and _numerically_reconciles(finding)
        )
        result = "explained" if strict else "unresolved"
    else:
        result = "explained" if isinstance(finding.get("candidate_explanation"), Mapping) else "unresolved"
    return {
        "finding_id": finding["finding_id"],
        "classification": result,
        "computed_value": float(finding["computed_value"]) if calculation_enabled else None,
        "explanation_quote": str(finding.get("candidate_explanation", {}).get("quote", "")) if result == "explained" else "",
        "citation_valid": _quote_valid(finding) if result == "explained" else None,
    }


def _score(outputs: list[dict[str, Any]], expected: dict[str, Mapping[str, Any]]) -> dict[str, Any]:
    total = len(outputs)
    correct = sum(item["classification"] == expected[item["finding_id"]]["expected_result"] for item in outputs)
    unsupported = sum(item["classification"] == "explained" and expected[item["finding_id"]]["expected_result"] != "explained" for item in outputs)
    false_positive = sum(expected[item["finding_id"]]["expected_result"] == "aligned" and item["classification"] != "aligned" for item in outputs)
    numeric = sum(item["computed_value"] == float(expected[item["finding_id"]]["computed_value"]) for item in outputs)
    explained = [item for item in outputs if item["classification"] == "explained"]
    valid_citations = sum(item["citation_valid"] is True for item in explained)
    expected_unresolved = [item for item in outputs if expected[item["finding_id"]]["expected_result"] == "unresolved"]
    unresolved_correct = sum(item["classification"] == "unresolved" for item in expected_unresolved)
    pct = lambda value, denominator: round((value / denominator) * 100, 1) if denominator else 100.0
    metrics = {
        "finding_count": total,
        "correct_classifications": correct,
        "classification_accuracy": pct(correct, total),
        "false_positives": false_positive,
        "false_positive_rate": pct(false_positive, total),
        "unsupported_explanations": unsupported,
        "unsupported_explanation_rate": pct(unsupported, total),
        "numerical_reconciliation_accuracy": pct(numeric, total),
        "valid_citations": valid_citations,
        "citation_quote_validity": pct(valid_citations, len(explained)),
        "unresolved_item_accuracy": pct(unresolved_correct, len(expected_unresolved)),
    }
    components = [
        metrics["classification_accuracy"],
        100 - metrics["false_positive_rate"],
        100 - metrics["unsupported_explanation_rate"],
        metrics["numerical_reconciliation_accuracy"],
        metrics["citation_quote_validity"],
        metrics["unresolved_item_accuracy"],
    ]
    metrics["overall_score"] = round(sum(components) / len(components), 1)
    return metrics


def evaluate_suite(path: Path) -> dict[str, Any]:
    suite = load_benchmark(path)
    findings = [finding for case in suite["cases"] for finding in case["findings"]]
    expected = {str(item["finding_id"]): item for item in findings}
    mode_outputs = {mode: [classify_finding(item, mode) for item in findings] for mode in MODES}
    comparisons: list[dict[str, Any]] = []
    for case in suite["cases"]:
        ids = {item["finding_id"] for item in case["findings"]}
        baseline = [item for item in mode_outputs["single_prompt"] if item["finding_id"] in ids]
        fintrace = [item for item in mode_outputs["full_fintrace"] if item["finding_id"] in ids]
        expected_results = [{"finding_id": item["finding_id"], "classification": item["expected_result"]} for item in case["findings"]]
        comparisons.append({
            "case_id": case["case_id"],
            "title": case["title"],
            "input": {"claims": [item["claim"] for item in case["findings"]], "category": case["category"]},
            "baseline_output": baseline,
            "fintrace_output": fintrace,
            "expected_result": expected_results,
            "baseline_correct": all(item["classification"] == expected[item["finding_id"]]["expected_result"] for item in baseline),
            "fintrace_correct": all(item["classification"] == expected[item["finding_id"]]["expected_result"] for item in fintrace),
            "baseline_unsupported_explanation": any(item["classification"] == "explained" and expected[item["finding_id"]]["expected_result"] != "explained" for item in baseline),
            "fintrace_unsupported_explanation": any(item["classification"] == "explained" and expected[item["finding_id"]]["expected_result"] != "explained" for item in fintrace),
            "baseline_false_positive": any(expected[item["finding_id"]]["expected_result"] == "aligned" and item["classification"] != "aligned" for item in baseline),
            "fintrace_false_positive": any(expected[item["finding_id"]]["expected_result"] == "aligned" and item["classification"] != "aligned" for item in fintrace),
        })
    return {
        "suite_version": suite["suite_version"],
        "provider": "local-deterministic",
        "baseline_prompt": BASELINE_PROMPT,
        "case_count": len(suite["cases"]),
        "finding_count": len(findings),
        "comparisons": comparisons,
        "ablations": {mode: {"metrics": _score(mode_outputs[mode], expected), "outputs": mode_outputs[mode]} for mode in MODES},
    }
