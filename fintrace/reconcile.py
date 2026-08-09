"""Deterministic financial arithmetic used before any model judgment."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import Reconciliation


SUPPORTED_METRICS = {"growth_percent", "free_cash_flow", "margin_percent", "absolute"}


class ReconciliationError(ValueError):
    pass


def _number(metrics: Mapping[str, Any], key: str) -> float:
    value = metrics.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReconciliationError(f"Metric {key!r} must be numeric")
    return float(value)


def compute_claim(claim: Mapping[str, Any], metrics: Mapping[str, Any]) -> tuple[float, list[str]]:
    metric_type = claim.get("metric_type")
    operands = claim.get("operands")
    if metric_type not in SUPPORTED_METRICS or not isinstance(operands, Mapping):
        raise ReconciliationError("Claim has an unsupported metric_type or invalid operands")

    if metric_type == "growth_percent":
        current_key = str(operands.get("current"))
        prior_key = str(operands.get("prior"))
        current = _number(metrics, current_key)
        prior = _number(metrics, prior_key)
        if prior == 0:
            raise ReconciliationError("Cannot calculate growth from a zero prior-period value")
        return ((current / prior) - 1) * 100, [current_key, prior_key]

    if metric_type == "free_cash_flow":
        cash_key = str(operands.get("operating_cash_flow"))
        capex_key = str(operands.get("capital_expenditures"))
        return _number(metrics, cash_key) - _number(metrics, capex_key), [cash_key, capex_key]

    if metric_type == "margin_percent":
        income_key = str(operands.get("income"))
        revenue_key = str(operands.get("revenue"))
        revenue = _number(metrics, revenue_key)
        if revenue == 0:
            raise ReconciliationError("Cannot calculate margin from zero revenue")
        return (_number(metrics, income_key) / revenue) * 100, [income_key, revenue_key]

    value_key = str(operands.get("value"))
    return _number(metrics, value_key), [value_key]


def reconcile_claims(case: Mapping[str, Any]) -> list[Reconciliation]:
    filing = case.get("filing")
    claims = case.get("claims")
    if not isinstance(filing, Mapping) or not isinstance(claims, list):
        raise ReconciliationError("Case must contain a filing object and claims array")
    metrics = filing.get("metrics")
    references = filing.get("references")
    if not isinstance(metrics, Mapping) or not isinstance(references, Mapping):
        raise ReconciliationError("Filing must contain metrics and references objects")

    results: list[Reconciliation] = []
    seen_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, Mapping):
            raise ReconciliationError("Every claim must be an object")
        claim_id = str(claim.get("id", ""))
        if not claim_id or claim_id in seen_ids:
            raise ReconciliationError("Claim IDs must be non-empty and unique")
        seen_ids.add(claim_id)

        quote = claim.get("quote")
        claimed_value = claim.get("claimed_value")
        tolerance = claim.get("tolerance")
        unit = claim.get("unit")
        if (
            not isinstance(quote, str)
            or isinstance(claimed_value, bool)
            or not isinstance(claimed_value, (int, float))
            or isinstance(tolerance, bool)
            or not isinstance(tolerance, (int, float))
            or float(tolerance) < 0
            or not isinstance(unit, str)
        ):
            raise ReconciliationError(f"Claim {claim_id} has invalid required fields")

        computed, metric_keys = compute_claim(claim, metrics)
        discrepancy = float(claimed_value) - computed
        filing_references = [str(references.get(key, key)) for key in metric_keys]
        results.append(
            Reconciliation(
                finding_id=f"FT-{len(results) + 1:03d}",
                claim_id=claim_id,
                claim_quote=quote,
                metric_type=str(claim["metric_type"]),
                claimed_value=round(float(claimed_value), 4),
                computed_value=round(computed, 4),
                discrepancy=round(discrepancy, 4),
                tolerance=round(float(tolerance), 4),
                unit=unit,
                filing_references=filing_references,
                status="aligned" if abs(discrepancy) <= float(tolerance) else "flagged",
            )
        )
    return results


def second_pass(
    reconciliations: list[Reconciliation],
    disclosures: list[Mapping[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    """Validate citable explanations arithmetically where an adjustment is supplied."""

    explained: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    aligned: list[dict[str, str]] = []
    by_claim: dict[str, list[Mapping[str, Any]]] = {}
    for disclosure in disclosures:
        claim_id = disclosure.get("claim_id")
        if isinstance(claim_id, str):
            by_claim.setdefault(claim_id, []).append(disclosure)

    for item in reconciliations:
        if item.status == "aligned":
            aligned.append({"item_id": item.finding_id})
            continue
        explanation = None
        for disclosure in by_claim.get(item.claim_id, []):
            quote = disclosure.get("quote")
            adjustment = disclosure.get("numeric_adjustment")
            direction = disclosure.get("direction")
            if not isinstance(quote, str) or not quote.strip():
                continue
            if isinstance(adjustment, (int, float)) and not isinstance(adjustment, bool):
                adjusted = item.computed_value + float(adjustment) * (1 if direction == "add" else -1)
                if abs(item.claimed_value - adjusted) <= item.tolerance:
                    explanation = quote
                    break

        if explanation:
            explained.append({"item_id": item.finding_id, "explanation_quote": explanation})
        else:
            unresolved.append(
                {
                    "item_id": item.finding_id,
                    "reasoning": (
                        f"The filing-derived value is {item.computed_value:g} {item.unit} versus "
                        f"the claimed {item.claimed_value:g} {item.unit}, a {item.discrepancy:g} "
                        f"difference outside the {item.tolerance:g} tolerance, and no disclosure "
                        "arithmetically reconciles the gap."
                    ),
                }
            )
    return {"explained": explained, "unresolved": unresolved, "aligned": aligned}
