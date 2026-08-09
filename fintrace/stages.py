"""Auditable pipeline stages surrounding deterministic financial reconciliation."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .models import Reconciliation
from .prompts import SPECIALISTS


SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
SPECIALIST_NAMES = ("revenue", "related_party", "cash_flow", "language")
EVIDENCE_TERMS = {
    "accounting",
    "acquisition",
    "commitment",
    "currency",
    "divestiture",
    "foreign exchange",
    "impairment",
    "methodology",
    "non-gaap",
    "one-time",
    "reclassification",
    "related party",
    "restructuring",
    "segment",
    "translation",
    "working capital",
}
ModelCall = Callable[[str, dict[str, Any]], Mapping[str, Any]]


def parse_speaker_passages(transcript: str | Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Normalize a string or structured transcript into speaker-attributed passages."""

    passages: list[dict[str, str]] = []
    if isinstance(transcript, str):
        for raw_line in transcript.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            speaker, separator, text = line.partition(":")
            passages.append({"speaker": speaker.strip() if separator else "Unknown", "text": text.strip() if separator else line})
        return passages
    for item in transcript:
        speaker = item.get("speaker")
        text = item.get("text")
        if isinstance(speaker, str) and isinstance(text, str) and text.strip():
            passages.append({"speaker": speaker.strip() or "Unknown", "text": text.strip()})
    return passages


def _claim_type(claim: Mapping[str, Any]) -> str:
    explicit = claim.get("claim_type")
    allowed = {"revenue", "growth", "profitability", "cash_flow", "segment", "accounting", "related_party", "other"}
    if explicit in allowed:
        return str(explicit)
    metric_type = claim.get("metric_type")
    return {
        "growth_percent": "growth",
        "free_cash_flow": "cash_flow",
        "margin_percent": "profitability",
        "absolute": "other",
    }.get(str(metric_type), "other")


def ingest_and_align(case: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Create the normalized Stage 1 claim-to-filing mapping."""

    claims = case.get("claims")
    filing = case.get("filing")
    if not isinstance(claims, list) or not isinstance(filing, Mapping):
        raise ValueError("Case must include structured claims and a filing")
    references = filing.get("references", {})
    if not isinstance(references, Mapping):
        raise ValueError("Filing references must be an object")

    aligned: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, Mapping):
            raise ValueError("Every claim must be an object")
        operands = claim.get("operands", {})
        operand_keys = list(operands.values()) if isinstance(operands, Mapping) else []
        aligned.append(
            {
                "claim_id": str(claim.get("id", "")),
                "claim_quote": str(claim.get("quote", "")),
                "claim_type": _claim_type(claim),
                "period": str(claim.get("period", case.get("period", ""))),
                "claimed_value": claim.get("claimed_value"),
                "filing_references": [str(references.get(str(key), key)) for key in operand_keys],
            }
        )
    return {"claims": aligned}


def _severity(item: Reconciliation) -> str:
    ratio = abs(item.discrepancy) / max(item.tolerance, 0.0001)
    if ratio >= 10:
        return "critical"
    if ratio >= 4:
        return "high"
    if ratio >= 2:
        return "medium"
    return "low"


def _deterministic_specialists(
    case: Mapping[str, Any], reconciliations: Sequence[Reconciliation]
) -> dict[str, list[dict[str, Any]]]:
    results = {name: [] for name in SPECIALIST_NAMES}
    for item in reconciliations:
        if item.status != "flagged":
            continue
        source = "cash_flow" if item.metric_type in {"free_cash_flow", "margin_percent"} else "revenue"
        finding: dict[str, Any] = {
            "finding_id": f"SP-{source}-{len(results[source]) + 1:03d}",
            "claim_id": item.claim_id,
            "claim_quote": item.claim_quote,
            "severity": _severity(item),
            "rationale": (
                f"The filed calculation is {item.computed_value:g} {item.unit}, compared with "
                f"the stated {item.claimed_value:g} {item.unit}."
            ),
        }
        reference = "; ".join(item.filing_references)
        if source == "revenue":
            finding.update(
                {
                    "filed_data_reference": reference,
                    "inconsistency": f"The stated value differs from the filing-derived value by {item.discrepancy:g} {item.unit}.",
                }
            )
        else:
            finding.update(
                {
                    "filed_data_reference": reference,
                    "gap_description": f"The stated value differs from the filing-derived value by {item.discrepancy:g} {item.unit}.",
                }
            )
        results[source].append(finding)

    supplied = case.get("specialist_findings", {})
    if isinstance(supplied, Mapping):
        for name in SPECIALIST_NAMES:
            items = supplied.get(name)
            if isinstance(items, list):
                results[name].extend(item for item in items if isinstance(item, Mapping))
    return results


def run_specialists(
    case: Mapping[str, Any],
    reconciliations: Sequence[Reconciliation],
    model_call: ModelCall | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Run four model scopes in parallel, or use the reproducible demo adapter."""

    if model_call is None:
        return _deterministic_specialists(case, reconciliations)
    context = {"claims": case.get("claims", []), "filing": case.get("filing", {})}

    def invoke(name: str) -> tuple[str, list[dict[str, Any]]]:
        response = model_call(SPECIALISTS[name], context)
        findings = response.get("findings", []) if isinstance(response, Mapping) else []
        if not isinstance(findings, list):
            raise ValueError(f"Specialist {name} returned an invalid findings array")
        return name, [dict(item) for item in findings if isinstance(item, Mapping)]

    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(invoke, SPECIALIST_NAMES))


def _normalized_quote(item: Mapping[str, Any]) -> str:
    quote = str(item.get("claim_quote", item.get("quote", ""))).lower()
    return re.sub(r"\W+", " ", quote).strip()


def aggregate_findings(specialist_results: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    """Deduplicate findings using stable claim identity and retain provenance."""

    grouped: dict[str, dict[str, Any]] = {}
    for source in SPECIALIST_NAMES:
        for item in specialist_results.get(source, []):
            key = str(item.get("claim_id") or _normalized_quote(item) or item.get("finding_id"))
            severity = str(item.get("severity", "low"))
            if severity not in SEVERITY_ORDER:
                severity = "low"
            rationale = str(item.get("rationale", "")).strip()
            evidence = str(
                item.get("evidence_reference")
                or item.get("filed_data_reference")
                or item.get("footnote_reference")
                or ""
            )
            issue = str(item.get("inconsistency") or item.get("gap_description") or item.get("concern") or item.get("pattern") or "")
            if key not in grouped:
                grouped[key] = {
                    "claim_id": item.get("claim_id"),
                    "claim_quote": str(item.get("claim_quote", item.get("quote", ""))),
                    "evidence_reference": evidence,
                    "severity": severity,
                    "rationale_parts": [rationale] if rationale else [],
                    "sources": [source],
                    "issue": issue,
                    "source_finding_ids": [str(item.get("finding_id", ""))],
                }
                continue
            target = grouped[key]
            if SEVERITY_ORDER[severity] > SEVERITY_ORDER[str(target["severity"])]:
                target["severity"] = severity
            if rationale and rationale not in target["rationale_parts"]:
                target["rationale_parts"].append(rationale)
            if source not in target["sources"]:
                target["sources"].append(source)
            if evidence and evidence not in str(target["evidence_reference"]):
                target["evidence_reference"] = "; ".join(filter(None, [str(target["evidence_reference"]), evidence]))
            target["source_finding_ids"].append(str(item.get("finding_id", "")))

    final: list[dict[str, Any]] = []
    for index, item in enumerate(grouped.values(), 1):
        final.append(
            {
                "finding_id": f"F-{index:03d}",
                "claim_id": item["claim_id"],
                "claim_quote": item["claim_quote"],
                "evidence_reference": item["evidence_reference"],
                "severity": item["severity"],
                "rationale": " ".join(item["rationale_parts"]),
                "sources": item["sources"],
                "issue": item["issue"],
                "source_finding_ids": item["source_finding_ids"],
            }
        )
    return final


def _calculation_for(claim: Mapping[str, Any], item: Reconciliation, metrics: Mapping[str, Any]) -> dict[str, Any]:
    operands = claim.get("operands", {})
    metric_type = claim.get("metric_type")
    if not isinstance(operands, Mapping):
        operands = {}
    formulas = {
        "growth_percent": "(current_period - prior_period) / prior_period * 100",
        "free_cash_flow": "operating_cash_flow - capital_expenditures",
        "margin_percent": "income / revenue * 100",
        "absolute": "filed_value",
    }
    inputs = {name: metrics.get(str(key)) for name, key in operands.items()}
    return {
        "formula": formulas.get(str(metric_type), "unsupported"),
        "inputs": inputs,
        "computed_value": item.computed_value,
        "claimed_value": item.claimed_value,
        "discrepancy": item.discrepancy,
        "tolerance": item.tolerance,
        "within_tolerance": abs(item.discrepancy) <= item.tolerance,
        "unit": item.unit,
    }


def attach_calculations(
    case: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
    reconciliations: Sequence[Reconciliation],
) -> list[dict[str, Any]]:
    """Attach authoritative code-produced calculations to numerical findings."""

    claims = {str(item.get("id")): item for item in case.get("claims", []) if isinstance(item, Mapping)}
    by_claim = {item.claim_id: item for item in reconciliations}
    filing = case.get("filing", {})
    metrics = filing.get("metrics", {}) if isinstance(filing, Mapping) else {}
    output: list[dict[str, Any]] = []
    for finding in findings:
        claim_id = str(finding.get("claim_id", ""))
        calculation = None
        if claim_id in claims and claim_id in by_claim and isinstance(metrics, Mapping):
            calculation = _calculation_for(claims[claim_id], by_claim[claim_id], metrics)
        output.append({"finding_id": str(finding["finding_id"]), "calculation": calculation})
    return output


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z][a-z-]{3,}", value.lower()) if token not in {"that", "this", "with", "from", "were", "have"}}


def retrieve_filing_evidence(
    case: Mapping[str, Any], findings: Sequence[Mapping[str, Any]], limit: int = 5
) -> list[dict[str, Any]]:
    """Rank multiple filing passages that may explain each candidate finding."""

    filing = case.get("filing", {})
    if not isinstance(filing, Mapping):
        raise ValueError("Filing must be an object")
    sections = [dict(item) for item in filing.get("sections", []) if isinstance(item, Mapping)]
    disclosures = [dict(item) for item in filing.get("disclosures", []) if isinstance(item, Mapping)]
    results: list[dict[str, Any]] = []
    for finding in findings:
        query = " ".join(
            str(finding.get(key, "")) for key in ("claim_quote", "evidence_reference", "rationale", "issue")
        )
        query_tokens = _tokens(query)
        claim_id = str(finding.get("claim_id", ""))
        candidates: list[tuple[int, dict[str, str]]] = []
        for section in sections:
            text = str(section.get("text", ""))
            lowered = text.lower()
            overlap = len(query_tokens & _tokens(text))
            domain_hits = sum(term in lowered for term in EVIDENCE_TERMS)
            score = overlap * 3 + domain_hits
            if score:
                candidates.append(
                    (
                        score,
                        {
                            "section": str(section.get("section", "Filing")),
                            "location": str(section.get("location", "Unspecified")),
                            "text": text,
                            "relevance": f"{overlap} claim-term matches and {domain_hits} explanation-term matches",
                        },
                    )
                )
        for disclosure in disclosures:
            if str(disclosure.get("claim_id", "")) != claim_id:
                continue
            candidates.append(
                (
                    100,
                    {
                        "section": str(disclosure.get("section", "Filing disclosure")),
                        "location": str(disclosure.get("location", "Unspecified")),
                        "text": str(disclosure.get("quote", "")),
                        "relevance": "Disclosure is explicitly linked to the underlying claim",
                    },
                )
            )
        ordered: list[dict[str, str]] = []
        seen_text: set[str] = set()
        for _, candidate in sorted(candidates, key=lambda value: (-value[0], value[1]["location"])):
            normalized = " ".join(candidate["text"].split()).lower()
            if not normalized or normalized in seen_text:
                continue
            seen_text.add(normalized)
            ordered.append(candidate)
            if len(ordered) >= limit:
                break
        results.append({"finding_id": str(finding["finding_id"]), "candidate_evidence": ordered})
    return results


def second_pass_review(
    case: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
    calculations: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    """Classify only filing-supported explanations as explained."""

    filing = case.get("filing", {})
    disclosures = filing.get("disclosures", []) if isinstance(filing, Mapping) else []
    calculations_by_id = {str(item.get("finding_id")): item.get("calculation") for item in calculations}
    explained: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    for finding in findings:
        finding_id = str(finding["finding_id"])
        claim_id = str(finding.get("claim_id", ""))
        calculation = calculations_by_id.get(finding_id)
        explanation = None
        for disclosure in disclosures if isinstance(disclosures, list) else []:
            if not isinstance(disclosure, Mapping) or str(disclosure.get("claim_id", "")) != claim_id:
                continue
            quote = disclosure.get("quote")
            if not isinstance(quote, str) or not quote.strip():
                continue
            if isinstance(calculation, Mapping):
                adjustment = disclosure.get("numeric_adjustment")
                direction = disclosure.get("direction")
                if isinstance(adjustment, (int, float)) and not isinstance(adjustment, bool):
                    adjusted = float(calculation["computed_value"]) + float(adjustment) * (1 if direction == "add" else -1)
                    if abs(float(calculation["claimed_value"]) - adjusted) <= float(calculation["tolerance"]):
                        explanation = quote
                        break
            elif disclosure.get("directly_explains") is True:
                explanation = quote
                break
        if explanation:
            explained.append({"finding_id": finding_id, "explanation_quote": explanation})
            continue
        if isinstance(calculation, Mapping):
            reasoning = (
                f"The code-derived value is {float(calculation['computed_value']):g} {calculation['unit']} versus "
                f"the stated {float(calculation['claimed_value']):g} {calculation['unit']}, leaving a "
                f"{float(calculation['discrepancy']):g} difference outside the {float(calculation['tolerance']):g} tolerance. "
                "No filing disclosure directly accounts for that difference."
            )
        else:
            reasoning = "No specific filing disclosure directly explains the documented difference."
        unresolved.append({"finding_id": finding_id, "reasoning": reasoning})
    return {"explained": explained, "unresolved": unresolved}


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def validate_explanation_quotes(
    case: Mapping[str, Any], review: Mapping[str, Sequence[Mapping[str, str]]]
) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, Any]]]:
    """Verify every model-returned quote against the supplied filing corpus."""

    filing = case.get("filing", {})
    sections = filing.get("sections", []) if isinstance(filing, Mapping) else []
    corpus = [
        {
            "text": str(item.get("text", "")),
            "location": f"{item.get('section', 'Filing')} - {item.get('location', 'Unspecified')}",
        }
        for item in sections
        if isinstance(item, Mapping)
    ]
    validated_explained: list[dict[str, str]] = []
    unresolved = [dict(item) for item in review.get("unresolved", [])]
    validations: list[dict[str, Any]] = []
    for item in review.get("explained", []):
        finding_id = str(item.get("finding_id", ""))
        quote = str(item.get("explanation_quote", ""))
        normalized_quote = _normalize_text(quote)
        match = next((entry for entry in corpus if normalized_quote and normalized_quote in _normalize_text(entry["text"])), None)
        if match:
            validated_explained.append({"finding_id": finding_id, "explanation_quote": quote})
            validations.append({"finding_id": finding_id, "quote_valid": True, "filing_location": match["location"]})
        else:
            error = "Quoted disclosure could not be located in the filing."
            unresolved.append({"finding_id": finding_id, "reasoning": error})
            validations.append({"finding_id": finding_id, "quote_valid": False, "validation_error": error})
    return {"explained": validated_explained, "unresolved": unresolved}, validations


def generate_risk_memos(
    review: Mapping[str, Sequence[Mapping[str, str]]],
    findings: Sequence[Mapping[str, Any]],
    calculations: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Create neutral memos only for unresolved findings."""

    finding_by_id = {str(item["finding_id"]): item for item in findings}
    calculation_by_id = {str(item["finding_id"]): item.get("calculation") for item in calculations}
    evidence_by_id = {str(item["finding_id"]): item.get("candidate_evidence", []) for item in evidence}
    memos: list[dict[str, str]] = []
    for unresolved in review.get("unresolved", []):
        finding_id = str(unresolved["finding_id"])
        finding = finding_by_id[finding_id]
        calculation = calculation_by_id.get(finding_id)
        reviewed = evidence_by_id.get(finding_id, [])
        locations = ", ".join(str(item.get("location", "Unspecified")) for item in reviewed) or "No candidate passages located"
        calculation_text = "No numerical calculation was applicable."
        if isinstance(calculation, Mapping):
            calculation_text = (
                f"Code computed {float(calculation['computed_value']):g} {calculation['unit']} versus "
                f"the stated {float(calculation['claimed_value']):g}, a {float(calculation['discrepancy']):g} difference."
            )
        memo = (
            f"Management statement: \"{finding['claim_quote']}\" Filing evidence: {finding['evidence_reference']}. "
            f"{calculation_text} Candidate disclosures reviewed: {locations}. {unresolved['reasoning']} "
            "This memo describes the observable evidence and does not infer intent."
        )
        memos.append({"finding_id": finding_id, "title": f"Unresolved finding {finding_id}", "memo": memo})
    return memos


def cross_period_regression(
    unresolved: Sequence[Mapping[str, str]], later_period: Mapping[str, Any] | None
) -> list[dict[str, str]]:
    """Normalize supplied later-period decisions without inventing unavailable evidence."""

    if not later_period:
        return []
    updates = later_period.get("cross_period_updates", {})
    if not isinstance(updates, Mapping):
        return []
    allowed = {"resolved", "worsened", "reclassified", "unaddressed"}
    results: list[dict[str, str]] = []
    for item in unresolved:
        finding_id = str(item.get("finding_id", ""))
        update = updates.get(finding_id)
        if not isinstance(update, Mapping):
            results.append({"finding_id": finding_id, "status": "unaddressed", "evidence_quote": "", "reasoning": "No later-period evidence was supplied for this finding."})
            continue
        status = str(update.get("status", "unaddressed"))
        if status not in allowed:
            raise ValueError(f"Invalid cross-period status for {finding_id}")
        results.append(
            {
                "finding_id": finding_id,
                "status": status,
                "evidence_quote": str(update.get("evidence_quote", "")),
                "reasoning": str(update.get("reasoning", "")),
            }
        )
    return results


def pending_human_review(review: Mapping[str, Sequence[Mapping[str, str]]]) -> dict[str, Any]:
    finding_ids = [str(item["finding_id"]) for key in ("explained", "unresolved") for item in review.get(key, [])]
    return {
        "status": "pending",
        "analyst": None,
        "reviewed_at": None,
        "decisions": [
            {"finding_id": finding_id, "decision": "needs_review", "analyst_note": ""}
            for finding_id in sorted(finding_ids)
        ],
    }
