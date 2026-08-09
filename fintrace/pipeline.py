from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .prompts import PROMPT_VERSION
from .reconcile import reconcile_claims, second_pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _digest(report: dict[str, Any]) -> str:
    canonical = {key: value for key, value in report.items() if key != "integrity"}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def run_case(case_path: Path, output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    started_at = _now()
    case = json.loads(case_path.read_text(encoding="utf-8"))
    if case.get("data_classification") != "fictional_demo":
        raise ValueError("This first engine version accepts only explicitly fictional demo data")

    reconciliations = reconcile_claims(case)
    disclosures = case.get("filing", {}).get("disclosures", [])
    if not isinstance(disclosures, list):
        raise ValueError("Filing disclosures must be an array")
    review = second_pass(reconciliations, disclosures)

    unresolved_by_id = {item["finding_id"]: item for item in review["unresolved"]}
    memos = []
    for item in reconciliations:
        if item.finding_id not in unresolved_by_id:
            continue
        memos.append(
            {
                "finding_id": item.finding_id,
                "title": f"Unresolved {item.metric_type.replace('_', ' ')} discrepancy",
                "memo": (
                    f"Management stated: \"{item.claim_quote}\" The filing-derived calculation is "
                    f"{item.computed_value:g} {item.unit}, compared with the claimed "
                    f"{item.claimed_value:g} {item.unit}. The {item.discrepancy:g} difference "
                    f"exceeds the {item.tolerance:g} tolerance. Filing references: "
                    f"{'; '.join(item.filing_references)}. No citable disclosure in the supplied "
                    "filing data reconciles the difference. This describes an inconsistency only "
                    "and makes no claim about intent."
                ),
            }
        )

    aligned = sum(item.status == "aligned" for item in reconciliations)
    flagged = sum(item.status == "flagged" for item in reconciliations)
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": f"fintrace-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "data_classification": case["data_classification"],
        "prompt_version": PROMPT_VERSION,
        "started_at": started_at,
        "finished_at": _now(),
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "company": case["company"],
        "period": case["period"],
        "stages": [
            {"name": "ingest_align", "status": "passed", "evidence": f"{len(reconciliations)} structured claims aligned"},
            {"name": "specialist_cross_check", "status": "simulated", "evidence": "Versioned contracts ready; deterministic demo uses labeled claim types"},
            {"name": "aggregate_dedupe", "status": "passed", "evidence": f"{len(reconciliations)} unique claims retained"},
            {"name": "deterministic_reconciliation", "status": "passed", "evidence": f"{aligned} aligned and {flagged} outside tolerance"},
            {"name": "second_pass_review", "status": "passed", "evidence": f"{len(review['explained'])} explained and {len(review['unresolved'])} unresolved"},
            {"name": "risk_memo", "status": "passed", "evidence": f"{len(memos)} neutral analyst memos generated"},
            {"name": "human_signoff", "status": "pending", "evidence": "Explicit analyst approval required"},
        ],
        "reconciliations": [item.to_dict() for item in reconciliations],
        "second_pass": review,
        "risk_memos": memos,
        "human_signoff": {"status": "pending", "analyst": None, "approved_at": None},
    }
    report["integrity"] = _digest(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def approve_report(path: Path, analyst: str) -> dict[str, Any]:
    analyst = analyst.strip()
    if not analyst or len(analyst) > 120:
        raise ValueError("Analyst name must be between 1 and 120 characters")
    report = json.loads(path.read_text(encoding="utf-8"))
    signoff = report.get("human_signoff")
    if not isinstance(signoff, dict):
        raise ValueError("Invalid report")
    signoff.update({"status": "approved", "analyst": analyst, "approved_at": _now()})
    for stage in report.get("stages", []):
        if isinstance(stage, dict) and stage.get("name") == "human_signoff":
            stage.update({"status": "passed", "evidence": f"Approved by {analyst}"})
    report["integrity"] = _digest(report)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
