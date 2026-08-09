"""Measured baseline, workflow, and ablation evaluation on controlled fixtures."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


MODES = ("single_prompt", "four_specialists", "specialists_plus_calculation", "full_fintrace")
BASELINE_PROMPT = "Review the transcript and filing. Identify any financial inconsistencies and explain them. Return your findings."
PERCENTAGE_PRECISION = 1
PERCENTAGE_TOLERANCE = 0.05


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


def _percentage(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, PERCENTAGE_PRECISION) if denominator else 100.0


def _score(outputs: list[dict[str, Any]], expected: dict[str, Mapping[str, Any]]) -> dict[str, Any]:
    total = len(outputs)
    correct = sum(item["classification"] == expected[item["finding_id"]]["expected_result"] for item in outputs)
    unsupported = sum(item["classification"] == "explained" and expected[item["finding_id"]]["expected_result"] != "explained" for item in outputs)
    false_positive = sum(expected[item["finding_id"]]["expected_result"] == "aligned" and item["classification"] != "aligned" for item in outputs)
    numeric_outputs = [item for item in outputs if expected[item["finding_id"]].get("computed_value") is not None]
    numeric = sum(item["computed_value"] == float(expected[item["finding_id"]]["computed_value"]) for item in numeric_outputs)
    explained = [item for item in outputs if item["classification"] == "explained"]
    valid_citations = sum(item["citation_valid"] is True for item in explained)
    expected_unresolved = [item for item in outputs if expected[item["finding_id"]]["expected_result"] == "unresolved"]
    unresolved_correct = sum(item["classification"] == "unresolved" for item in expected_unresolved)
    metrics = {
        "finding_count": total,
        "correct_classifications": correct,
        "incorrect_classifications": total - correct,
        "classification_accuracy": _percentage(correct, total),
        "false_positives": false_positive,
        "unsupported_explanations": unsupported,
        "numeric_checks": len(numeric_outputs),
        "correct_numeric_checks": numeric,
        "numerical_reconciliation_accuracy": _percentage(numeric, len(numeric_outputs)),
        "explained_outputs": len(explained),
        "valid_citations": valid_citations,
        "citation_quote_validity": _percentage(valid_citations, len(explained)),
        "expected_unresolved_items": len(expected_unresolved),
        "correct_unresolved_items": unresolved_correct,
        "unresolved_item_accuracy": _percentage(unresolved_correct, len(expected_unresolved)),
    }
    metrics["percentage_checks"] = {
        "classification_accuracy": {"numerator": correct, "denominator": total, "reported_percentage": metrics["classification_accuracy"]},
        "numerical_reconciliation_accuracy": {"numerator": numeric, "denominator": len(numeric_outputs), "reported_percentage": metrics["numerical_reconciliation_accuracy"]},
        "citation_quote_validity": {"numerator": valid_citations, "denominator": len(explained), "reported_percentage": metrics["citation_quote_validity"]},
        "unresolved_item_accuracy": {"numerator": unresolved_correct, "denominator": len(expected_unresolved), "reported_percentage": metrics["unresolved_item_accuracy"]},
    }
    return metrics


def validate_benchmark_integrity(result: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed when benchmark counts or any reported percentage drift."""
    comparisons = result.get("comparisons")
    ablations = result.get("ablations")
    if not isinstance(comparisons, list) or not isinstance(ablations, Mapping):
        raise ValueError("Benchmark output is missing comparisons or ablations")
    case_count = len(comparisons)
    expected_by_id = {
        item["finding_id"]: item
        for case in comparisons
        for item in case["expected_result"]
    }
    finding_count = len(expected_by_id)
    if result.get("case_count") != case_count or result.get("finding_count") != finding_count:
        raise ValueError("Benchmark case or finding count is inconsistent")

    checked_percentages = 0
    for mode in MODES:
        data = ablations.get(mode)
        if not isinstance(data, Mapping):
            raise ValueError(f"Benchmark mode is missing: {mode}")
        outputs = data.get("outputs")
        metrics = data.get("metrics")
        if not isinstance(outputs, list) or not isinstance(metrics, Mapping) or len(outputs) != finding_count:
            raise ValueError(f"Benchmark output count is inconsistent for {mode}")
        correct = sum(item["classification"] == expected_by_id[item["finding_id"]]["classification"] for item in outputs)
        incorrect = finding_count - correct
        unsupported = sum(item["classification"] == "explained" and expected_by_id[item["finding_id"]]["classification"] != "explained" for item in outputs)
        false_positives = sum(expected_by_id[item["finding_id"]]["classification"] == "aligned" and item["classification"] != "aligned" for item in outputs)
        numeric_outputs = [item for item in outputs if expected_by_id[item["finding_id"]].get("computed_value") is not None]
        correct_numeric = sum(item["computed_value"] == expected_by_id[item["finding_id"]]["computed_value"] for item in numeric_outputs)
        explained_outputs = [item for item in outputs if item["classification"] == "explained"]
        valid_citations = sum(item["citation_valid"] is True for item in explained_outputs)
        expected_unresolved = [item for item in outputs if expected_by_id[item["finding_id"]]["classification"] == "unresolved"]
        correct_unresolved = sum(item["classification"] == "unresolved" for item in expected_unresolved)
        expected_counts = {
            "finding_count": finding_count,
            "correct_classifications": correct,
            "incorrect_classifications": incorrect,
            "unsupported_explanations": unsupported,
            "false_positives": false_positives,
            "numeric_checks": len(numeric_outputs),
            "correct_numeric_checks": correct_numeric,
            "explained_outputs": len(explained_outputs),
            "valid_citations": valid_citations,
            "expected_unresolved_items": len(expected_unresolved),
            "correct_unresolved_items": correct_unresolved,
        }
        for key, expected_value in expected_counts.items():
            if metrics.get(key) != expected_value:
                raise ValueError(f"Benchmark metric {mode}.{key} is inconsistent")
        for name, check in metrics.get("percentage_checks", {}).items():
            numerator = check.get("numerator")
            denominator = check.get("denominator")
            reported = check.get("reported_percentage")
            if not isinstance(numerator, int) or not isinstance(denominator, int) or not isinstance(reported, (int, float)):
                raise ValueError(f"Benchmark percentage {mode}.{name} has an invalid basis")
            expected_percentage = _percentage(numerator, denominator)
            if abs(float(reported) - expected_percentage) > PERCENTAGE_TOLERANCE:
                raise ValueError(f"Benchmark percentage {mode}.{name} is inconsistent")
            if metrics.get(name) != reported:
                raise ValueError(f"Benchmark percentage {mode}.{name} does not match its reported metric")
            checked_percentages += 1
    return {
        "status": "passed",
        "case_count": case_count,
        "finding_count": finding_count,
        "modes_checked": len(MODES),
        "percentages_checked": checked_percentages,
    }


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
        expected_results = [{"finding_id": item["finding_id"], "classification": item["expected_result"], "computed_value": float(item["computed_value"])} for item in case["findings"]]
        baseline_correct = all(item["classification"] == expected[item["finding_id"]]["expected_result"] for item in baseline)
        fintrace_correct = all(item["classification"] == expected[item["finding_id"]]["expected_result"] for item in fintrace)
        comparisons.append({
            "case_id": case["case_id"],
            "title": case["title"],
            "input": {"claims": [item["claim"] for item in case["findings"]], "category": case["category"]},
            "baseline_output": baseline,
            "fintrace_output": fintrace,
            "expected_result": expected_results,
            "baseline_correct": baseline_correct,
            "fintrace_correct": fintrace_correct,
            "baseline_fail_fintrace_pass": not baseline_correct and fintrace_correct,
            "baseline_unsupported_explanation": any(item["classification"] == "explained" and expected[item["finding_id"]]["expected_result"] != "explained" for item in baseline),
            "fintrace_unsupported_explanation": any(item["classification"] == "explained" and expected[item["finding_id"]]["expected_result"] != "explained" for item in fintrace),
            "baseline_false_positive": any(expected[item["finding_id"]]["expected_result"] == "aligned" and item["classification"] != "aligned" for item in baseline),
            "fintrace_false_positive": any(expected[item["finding_id"]]["expected_result"] == "aligned" and item["classification"] != "aligned" for item in fintrace),
        })
    result = {
        "suite_version": suite["suite_version"],
        "provider": "local-deterministic",
        "baseline_prompt": BASELINE_PROMPT,
        "case_count": len(suite["cases"]),
        "finding_count": len(findings),
        "comparisons": comparisons,
        "ablations": {mode: {"metrics": _score(mode_outputs[mode], expected), "outputs": mode_outputs[mode]} for mode in MODES},
    }
    result["integrity_checks"] = validate_benchmark_integrity(result)
    return result
