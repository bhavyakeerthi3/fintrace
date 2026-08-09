from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import approve_report, run_case
from .prompts import prompt_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fintrace", description="Financial claim reconciliation")
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo")
    demo.add_argument("--case", type=Path, default=Path("fixtures/fictional-demo.json"))
    demo.add_argument("--output", type=Path, default=Path("outputs/fintrace-demo-report.json"))

    approve = commands.add_parser("approve")
    approve.add_argument("report", type=Path)
    approve.add_argument("--analyst", required=True)
    approve.add_argument("--decision", choices=("accept", "reject", "needs_review"), default="accept")
    approve.add_argument("--note", default="Classification reviewed against the evidence package.")
    approve.add_argument("--finding-id", help="Update one finding; omit to apply the decision to every finding")

    commands.add_parser("prompts")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "demo":
            report = run_case(args.case, args.output)
            print(json.dumps({
                "report": str(args.output),
                "aligned": sum(item["status"] == "aligned" for item in report["reconciliations"]),
                "flagged": sum(item["status"] == "flagged" for item in report["reconciliations"]),
                "explained": len(report["second_pass"]["explained"]),
                "unresolved": len(report["second_pass"]["unresolved"]),
                "integrity": report["integrity"],
            }, indent=2))
            return 0
        if args.command == "approve":
            report = approve_report(args.report, args.analyst, args.decision, args.note, args.finding_id)
            print(json.dumps(report["human_signoff"], indent=2))
            return 0
        print(json.dumps(prompt_manifest(), indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
