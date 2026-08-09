from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fintrace.pipeline import approve_report, run_case
from fintrace.prompts import PROMPT_VERSION, SECOND_PASS_REVIEWER, SPECIALISTS, prompt_manifest
from fintrace.reconcile import ReconciliationError, reconcile_claims
from fintrace.stages import (
    aggregate_findings,
    cross_period_regression,
    ingest_and_align,
    parse_speaker_passages,
    validate_explanation_quotes,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "fictional-demo.json"


class FinTraceTests(unittest.TestCase):
    def test_ingest_align_normalizes_claim_contract(self) -> None:
        case = json.loads(FIXTURE.read_text(encoding="utf-8"))
        claims = ingest_and_align(case)["claims"]
        self.assertEqual(len(claims), 3)
        self.assertEqual(claims[0]["claim_type"], "growth")
        self.assertEqual(len(claims[0]["filing_references"]), 2)

    def test_transcript_parser_preserves_speakers(self) -> None:
        passages = parse_speaker_passages("CEO: Revenue grew 10%.\nAnalyst: Was that organic?")
        self.assertEqual(passages[0], {"speaker": "CEO", "text": "Revenue grew 10%."})
        self.assertEqual(passages[1]["speaker"], "Analyst")

    def test_reconciliation_computes_filed_values(self) -> None:
        case = json.loads(FIXTURE.read_text(encoding="utf-8"))
        results = {item.claim_id: item for item in reconcile_claims(case)}
        self.assertAlmostEqual(results["claim-growth"].computed_value, 12.7273, places=4)
        self.assertEqual(results["claim-growth"].status, "flagged")
        self.assertEqual(results["claim-fcf"].computed_value, 62.0)
        self.assertEqual(results["claim-fcf"].status, "flagged")
        self.assertAlmostEqual(results["claim-margin"].computed_value, 12.9032, places=4)
        self.assertEqual(results["claim-margin"].status, "aligned")

    def test_aggregation_merges_same_claim_and_preserves_sources(self) -> None:
        inputs = {
            "revenue": [{"finding_id": "R-1", "claim_id": "c-1", "claim_quote": "Revenue grew.", "filed_data_reference": "p. 2", "inconsistency": "Gap", "severity": "medium", "rationale": "Revenue rationale"}],
            "related_party": [],
            "cash_flow": [{"finding_id": "C-1", "claim_id": "c-1", "claim_quote": "Revenue grew.", "filed_data_reference": "p. 2", "gap_description": "Gap", "severity": "high", "rationale": "Cash rationale"}],
            "language": [],
        }
        findings = aggregate_findings(inputs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["finding_id"], "F-001")
        self.assertEqual(findings[0]["severity"], "high")
        self.assertEqual(findings[0]["sources"], ["revenue", "cash_flow"])

    def test_complete_pipeline_retrieves_validates_and_classifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            report = run_case(FIXTURE, output)
            self.assertEqual(report["schema_version"], "2.0")
            self.assertEqual(len(report["stages"]), 8)
            self.assertEqual([item["finding_id"] for item in report["aggregated_findings"]], ["F-001", "F-002"])
            calculations = {item["finding_id"]: item["calculation"] for item in report["calculations"]}
            self.assertEqual(calculations["F-001"]["computed_value"], 12.7273)
            self.assertEqual(calculations["F-002"]["computed_value"], 62.0)
            self.assertEqual(report["second_pass"]["unresolved"][0]["finding_id"], "F-001")
            self.assertEqual(
                report["second_pass"]["explained"],
                [{
                    "finding_id": "F-002",
                    "explanation_quote": "Adjusted free cash flow excludes 23 million dollars of cash restructuring payments; the measure is operating cash flow less capital expenditures plus those payments.",
                }],
            )
            self.assertEqual(report["quote_validation"], [{"finding_id": "F-002", "quote_valid": True, "filing_location": "Non-GAAP reconciliation - Fictional 10-Q, p. 31"}])
            self.assertGreaterEqual(len(report["evidence_retrieval"][0]["candidate_evidence"]), 2)
            self.assertEqual([item["finding_id"] for item in report["risk_memos"]], ["F-001"])
            self.assertEqual(len(report["human_signoff"]["decisions"]), 2)
            self.assertRegex(report["integrity"], r"^sha256:[a-f0-9]{64}$")

    def test_unverifiable_explanation_becomes_unresolved(self) -> None:
        case = json.loads(FIXTURE.read_text(encoding="utf-8"))
        case["filing"]["sections"] = []
        review = {"explained": [{"finding_id": "F-009", "explanation_quote": "Missing quote"}], "unresolved": []}
        final, validation = validate_explanation_quotes(case, review)
        self.assertEqual(final["explained"], [])
        self.assertEqual(final["unresolved"][0]["finding_id"], "F-009")
        self.assertFalse(validation[0]["quote_valid"])

    def test_cross_period_defaults_to_unaddressed_without_evidence(self) -> None:
        result = cross_period_regression(
            [{"finding_id": "F-001", "reasoning": "Gap"}],
            {"cross_period_updates": {}},
        )
        self.assertEqual(result[0]["status"], "unaddressed")

    def test_human_signoff_records_per_finding_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            before = run_case(FIXTURE, output)
            partial = approve_report(output, "Bhavya Keerthi", "accept", "Evidence reviewed.", "F-001")
            after = approve_report(output, "Bhavya Keerthi", "reject", "Classification changed.", "F-002")
            self.assertEqual(before["human_signoff"]["status"], "pending")
            self.assertEqual(partial["human_signoff"]["status"], "pending")
            self.assertEqual(after["human_signoff"]["status"], "complete")
            self.assertEqual([item["decision"] for item in after["human_signoff"]["decisions"]], ["accept", "reject"])
            self.assertNotEqual(before["integrity"], after["integrity"])

    def test_rejects_unlabeled_live_company_data(self) -> None:
        case = json.loads(FIXTURE.read_text(encoding="utf-8"))
        case["data_classification"] = "live_company"
        with tempfile.TemporaryDirectory() as directory:
            case_path = Path(directory) / "case.json"
            case_path.write_text(json.dumps(case), encoding="utf-8")
            with self.assertRaises(ValueError):
                run_case(case_path, Path(directory) / "report.json")

    def test_duplicate_claim_ids_are_rejected(self) -> None:
        case = json.loads(FIXTURE.read_text(encoding="utf-8"))
        case["claims"][1]["id"] = case["claims"][0]["id"]
        with self.assertRaises(ReconciliationError):
            reconcile_claims(case)

    def test_prompt_contracts_are_complete_and_neutral(self) -> None:
        self.assertEqual(set(SPECIALISTS), {"revenue", "related_party", "cash_flow", "language"})
        self.assertIn('"explained"', SECOND_PASS_REVIEWER)
        self.assertIn('"unresolved"', SECOND_PASS_REVIEWER)
        self.assertIn('"finding_id"', SECOND_PASS_REVIEWER)
        self.assertIn("complete filing", SECOND_PASS_REVIEWER)
        self.assertEqual(PROMPT_VERSION, "2026-08-09.v3")
        all_prompts = json.dumps(prompt_manifest()).lower()
        forbidden_terms = (
            "forensic" + " accountant",
            "forensic" + " analyst",
            "skep" + "tic",
            "adver" + "sarial",
            "confirmed" + " red flag",
            "veri" + "fier",
        )
        for forbidden in forbidden_terms:
            self.assertNotIn(forbidden, all_prompts)


if __name__ == "__main__":
    unittest.main()
