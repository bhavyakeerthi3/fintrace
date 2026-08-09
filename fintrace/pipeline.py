from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .prompts import PROMPT_REGISTRY, PROMPT_VERSION, SECOND_PASS_REVIEWER, validate_prompt_output
from .providers import LiveLLMProvider, LocalDeterministicProvider, ModelProvider
from .reconcile import reconcile_claims
from .stages import (
    ModelCall,
    aggregate_findings,
    attach_calculations,
    cross_period_regression,
    generate_risk_memos,
    ingest_and_align,
    pending_human_review,
    retrieve_filing_evidence,
    run_specialists,
    second_pass_review,
    validate_explanation_quotes,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _digest(report: dict[str, Any]) -> str:
    canonical = {key: value for key, value in report.items() if key not in {"integrity", "integrity_digest"}}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _result_digest(report: dict[str, Any]) -> str:
    keys = (
        "data_classification", "company", "period", "ingestion", "specialist_findings",
        "aggregated_findings", "reconciliations", "calculations", "evidence_retrieval",
        "second_pass", "quote_validation", "risk_memos", "cross_period",
    )
    encoded = json.dumps({key: report.get(key) for key in keys}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _model_second_pass(
    call: ModelCall,
    case: dict[str, Any],
    findings: list[dict[str, Any]],
    calculations: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    response = call(
        SECOND_PASS_REVIEWER,
        {
            "findings": findings,
            "calculations": calculations,
            "candidate_evidence": evidence,
            "filing": case.get("filing", {}),
        },
    )
    response = validate_prompt_output("second_pass", response)
    if not isinstance(response, dict):
        raise ValueError("Second-pass reviewer returned an invalid object")
    explained = response.get("explained")
    unresolved = response.get("unresolved")
    if not isinstance(explained, list) or not isinstance(unresolved, list):
        raise ValueError("Second-pass reviewer must return explained and unresolved arrays")
    return {
        "explained": [dict(item) for item in explained if isinstance(item, dict)],
        "unresolved": [dict(item) for item in unresolved if isinstance(item, dict)],
    }


def run_case(
    case_path: Path,
    output: Path,
    specialist_call: ModelCall | None = None,
    second_pass_call: ModelCall | None = None,
    provider: ModelProvider | None = None,
) -> dict[str, Any]:
    """Run the complete auditable pipeline for one aligned reporting period."""

    started = time.perf_counter()
    started_at = _now()
    case = json.loads(case_path.read_text(encoding="utf-8"))
    if case.get("data_classification") not in {"fictional_demo", "historical_adjudicated"}:
        raise ValueError("FinTrace accepts only fictional demos or historical adjudicated cases")
    active_provider = provider or LocalDeterministicProvider()

    ingestion = ingest_and_align(case)
    reconciliations = reconcile_claims(case)
    specialist_findings = run_specialists(case, reconciliations, specialist_call, None if specialist_call else active_provider)
    aggregated_findings = aggregate_findings(specialist_findings)
    calculations = attach_calculations(case, aggregated_findings, reconciliations)
    evidence_retrieval = retrieve_filing_evidence(case, aggregated_findings)
    if second_pass_call:
        initial_review = _model_second_pass(second_pass_call, case, aggregated_findings, calculations, evidence_retrieval)
    elif isinstance(active_provider, LiveLLMProvider):
        initial_review = active_provider.second_pass_call(payload={
            "findings": aggregated_findings,
            "calculations": calculations,
            "candidate_evidence": evidence_retrieval,
            "filing": case.get("filing", {}),
        })
    else:
        deterministic_review = second_pass_review(case, aggregated_findings, calculations)
        initial_review = active_provider.second_pass_call(payload={"deterministic_output": deterministic_review})
    final_review, quote_validation = validate_explanation_quotes(case, initial_review, aggregated_findings)
    risk_memos = generate_risk_memos(final_review, aggregated_findings, calculations, evidence_retrieval)
    cross_period = cross_period_regression(final_review["unresolved"], case.get("later_period"))
    human_signoff = pending_human_review(final_review)

    candidate_count = sum(len(items) for items in specialist_findings.values())
    valid_quotes = sum(item["quote_valid"] for item in quote_validation)
    report: dict[str, Any] = {
        "schema_version": "3.0",
        "run_id": f"fintrace-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "timestamp": started_at,
        "data_classification": case["data_classification"],
        "prompt_version": PROMPT_VERSION,
        "prompt_versions": {name: spec["version"] for name, spec in PROMPT_REGISTRY.items()},
        "fixture_version": case.get("fixture_version", "1.0.0"),
        "calculation_version": "1.0.0",
        "retrieval_version": "1.0.0",
        "model": active_provider.model,
        "execution": active_provider.metadata(),
        "started_at": started_at,
        "finished_at": _now(),
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "company": case["company"],
        "period": case["period"],
        "stages": [
            {"name": "ingest_align", "status": "passed", "evidence": f"{len(ingestion['claims'])} claims aligned to filing references"},
            {"name": "specialist_cross_check", "status": "passed", "evidence": f"{candidate_count} candidates across four isolated scopes"},
            {"name": "aggregate_dedupe", "status": "passed", "evidence": f"{len(aggregated_findings)} stable findings retained"},
            {"name": "deterministic_reconciliation", "status": "passed", "evidence": f"{sum(item['calculation'] is not None for item in calculations)} authoritative calculations attached"},
            {"name": "filing_evidence_retrieval", "status": "passed", "evidence": f"{sum(len(item['candidate_evidence']) for item in evidence_retrieval)} candidate passages retrieved"},
            {"name": "second_pass_quote_validation", "status": "passed", "evidence": f"{len(final_review['explained'])} explained, {len(final_review['unresolved'])} unresolved, {valid_quotes} quotes validated"},
            {"name": "analyst_review", "status": "passed", "evidence": f"{len(risk_memos)} unresolved-item memos; {len(cross_period)} cross-period results"},
            {"name": "human_signoff", "status": "pending", "evidence": f"{len(human_signoff['decisions'])} finding decisions require review"},
        ],
        "ingestion": ingestion,
        "specialist_findings": specialist_findings,
        "aggregated_findings": aggregated_findings,
        "reconciliations": [item.to_dict() for item in reconciliations],
        "calculations": calculations,
        "evidence_retrieval": evidence_retrieval,
        "second_pass": final_review,
        "quote_validation": quote_validation,
        "risk_memos": risk_memos,
        "cross_period": cross_period,
        "human_signoff": human_signoff,
        "human_review": human_signoff,
    }
    report["prompt_traces"] = [
        {
            "stage": name,
            "model": active_provider.model if name != "aggregator" else "deterministic-deduplicator",
            "prompt_version": spec["version"],
            "system_instruction": spec["system_instruction"],
            "input": {"contract": spec["input_contract"], "case": case.get("case_id", case.get("company"))},
            "expected_json_schema": spec["output_schema"],
            "output": specialist_findings.get(name, []) if name in specialist_findings else aggregated_findings if name == "aggregator" else final_review,
        }
        for name, spec in PROMPT_REGISTRY.items()
    ]
    report["result_digest"] = _result_digest(report)
    report["integrity_digest"] = _digest(report)
    report["integrity"] = report["integrity_digest"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def approve_report(
    path: Path,
    analyst: str,
    decision: str = "accept",
    note: str = "Classification reviewed against the evidence package.",
    finding_id: str | None = None,
) -> dict[str, Any]:
    analyst = analyst.strip()
    if not analyst or len(analyst) > 120:
        raise ValueError("Analyst name must be between 1 and 120 characters")
    if decision not in {"accept", "reject", "needs_review"}:
        raise ValueError("Decision must be accept, reject, or needs_review")
    if len(note) > 1000:
        raise ValueError("Analyst note must be 1000 characters or fewer")
    report = json.loads(path.read_text(encoding="utf-8"))
    signoff = report.get("human_signoff")
    if not isinstance(signoff, dict) or not isinstance(signoff.get("decisions"), list):
        raise ValueError("Invalid report")
    matched = False
    for item in signoff["decisions"]:
        if isinstance(item, dict) and (finding_id is None or item.get("finding_id") == finding_id):
            item.update({"decision": decision, "analyst_note": note})
            matched = True
    if finding_id is not None and not matched:
        raise ValueError(f"Finding {finding_id} does not exist in this report")
    status = "pending" if any(item.get("decision") == "needs_review" for item in signoff["decisions"] if isinstance(item, dict)) else "complete"
    signoff.update({"status": status, "analyst": analyst, "reviewed_at": _now()})
    for stage in report.get("stages", []):
        if isinstance(stage, dict) and stage.get("name") == "human_signoff":
            stage.update(
                {
                    "status": "pending" if status == "pending" else "passed",
                    "evidence": f"Per-finding decisions recorded by {analyst}",
                }
            )
    report["human_review"] = signoff
    report["integrity_digest"] = _digest(report)
    report["integrity"] = report["integrity_digest"]
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
