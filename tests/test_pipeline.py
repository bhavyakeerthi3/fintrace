from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fintrace.pipeline import approve_report, run_case
from fintrace.prompts import PROMPT_VERSION, SECOND_PASS_REVIEWER, SPECIALISTS, prompt_manifest
from fintrace.reconcile import ReconciliationError, reconcile_claims


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "fictional-demo.json"


class FinTraceTests(unittest.TestCase):
    def test_reconciliation_computes_filed_values(self) -> None:
        case = json.loads(FIXTURE.read_text(encoding="utf-8"))
        results = {item.claim_id: item for item in reconcile_claims(case)}

        self.assertAlmostEqual(results["claim-growth"].computed_value, 12.7273, places=4)
        self.assertEqual(results["claim-growth"].status, "flagged")
        self.assertEqual(results["claim-fcf"].computed_value, 62.0)
        self.assertEqual(results["claim-fcf"].status, "flagged")
        self.assertAlmostEqual(results["claim-margin"].computed_value, 12.9032, places=4)
        self.assertEqual(results["claim-margin"].status, "aligned")

    def test_second_pass_requires_citation_and_numeric_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            report = run_case(FIXTURE, output)

            self.assertEqual(report["second_pass"]["explained"], [
                {
                    "item_id": "FT-002",
                    "explanation_quote": "Adjusted free cash flow excludes 23 million dollars of cash restructuring payments; the measure is operating cash flow less capital expenditures plus those payments.",
                }
            ])
            self.assertEqual(report["second_pass"]["unresolved"][0]["item_id"], "FT-001")
            self.assertEqual(report["second_pass"]["aligned"], [{"item_id": "FT-003"}])
            self.assertEqual(report["reconciliations"][0]["gap"], 10.2727)
            self.assertEqual(len(report["risk_memos"]), 1)
            self.assertRegex(report["integrity"], r"^sha256:[a-f0-9]{64}$")

    def test_human_signoff_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            before = run_case(FIXTURE, output)
            after = approve_report(output, "Bhavya Keerthi")
            self.assertEqual(before["human_signoff"]["status"], "pending")
            self.assertEqual(after["human_signoff"]["status"], "approved")
            self.assertNotEqual(before["integrity"], after["integrity"])

    def test_first_version_rejects_unlabeled_live_company_data(self) -> None:
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

    def test_prompt_contracts_are_complete(self) -> None:
        self.assertEqual(set(SPECIALISTS), {"revenue", "related_party", "cash_flow", "language"})
        self.assertIn('"explained"', SECOND_PASS_REVIEWER)
        self.assertIn('"unresolved"', SECOND_PASS_REVIEWER)
        self.assertIn('"aligned"', SECOND_PASS_REVIEWER)
        self.assertIn('"item_id"', SECOND_PASS_REVIEWER)
        self.assertIn("full filing", SECOND_PASS_REVIEWER)
        self.assertEqual(PROMPT_VERSION, "2026-08-09.v2")
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
