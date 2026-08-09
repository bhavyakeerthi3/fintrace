from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluation import evaluate_suite, validate_benchmark_integrity
from .pipeline import approve_report, run_case
from .prompts import prompt_manifest
from .providers import LiveLLMProvider, LocalDeterministicProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fintrace", description="Financial claim reconciliation")
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo")
    demo.add_argument("--case", type=Path, default=Path("fixtures/fictional-demo.json"))
    demo.add_argument("--output", type=Path, default=Path("outputs/fintrace-demo-report.json"))
    demo.add_argument("--provider", choices=("local", "live"), default="local")
    demo.add_argument("--model", default="gpt-5-mini")
    demo.add_argument("--temperature", type=float, default=0.0)
    demo.add_argument("--token-limit", type=int, default=1800)

    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("--suite", type=Path, default=Path("fixtures/benchmark-suite.json"))
    benchmark.add_argument("--output", type=Path, default=Path("outputs/fintrace-benchmark-results.json"))

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
            provider = LocalDeterministicProvider() if args.provider == "local" else LiveLLMProvider(args.model, args.temperature, args.token_limit)
            report = run_case(args.case, args.output, provider=provider)
            print(json.dumps({
                "report": str(args.output),
                "aligned": sum(item["status"] == "aligned" for item in report["reconciliations"]),
                "flagged": sum(item["status"] == "flagged" for item in report["reconciliations"]),
                "explained": len(report["second_pass"]["explained"]),
                "unresolved": len(report["second_pass"]["unresolved"]),
                "integrity": report["integrity"],
            }, indent=2))
            return 0
        if args.command == "benchmark":
            result = evaluate_suite(args.suite)
            validate_benchmark_integrity(result)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({
                "output": str(args.output),
                "cases": result["case_count"],
                "findings": result["finding_count"],
                "baseline_classification_accuracy": result["ablations"]["single_prompt"]["metrics"]["classification_accuracy"],
                "fintrace_classification_accuracy": result["ablations"]["full_fintrace"]["metrics"]["classification_accuracy"],
                "integrity_checks": result["integrity_checks"],
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
