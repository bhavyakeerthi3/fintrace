from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .evaluation import evaluate_benchmark_bundle
from .pipeline import approve_report, run_case
from .prompts import prompt_manifest
from .providers import LiveLLMProvider, LocalDeterministicProvider, ProviderError


def load_local_environment(path: Path = Path(".env.local")) -> None:
    """Load simple local environment entries without replacing shell values."""

    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fintrace", description="Financial claim reconciliation")
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo")
    demo.add_argument("--case", type=Path, default=Path("fixtures/fictional-demo.json"))
    demo.add_argument("--output", type=Path, default=Path("outputs/fintrace-demo-report.json"))
    demo.add_argument("--provider", choices=("local", "live"), default="local")
    demo.add_argument("--model", default=os.getenv("FINTRACE_LLM_MODEL", "gpt-5-mini"))
    demo.add_argument("--temperature", type=float, default=0.0)
    demo.add_argument("--token-limit", type=int, default=1800)

    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("--suite", type=Path, default=Path("fixtures/benchmark-suite.json"))
    benchmark.add_argument("--output", type=Path, default=Path("outputs/fintrace-benchmark-results.json"))
    benchmark.add_argument("--provider", choices=("local", "live"), default="local")
    benchmark.add_argument("--model", default=os.getenv("FINTRACE_LLM_MODEL", "gpt-5-mini"))
    benchmark.add_argument("--temperature", type=float, default=0.0)
    benchmark.add_argument("--token-limit", type=int, default=1800)

    approve = commands.add_parser("approve")
    approve.add_argument("report", type=Path)
    approve.add_argument("--analyst", required=True)
    approve.add_argument("--decision", choices=("accept", "reject", "needs_review"), default="accept")
    approve.add_argument("--note", default="Classification reviewed against the evidence package.")
    approve.add_argument("--finding-id", help="Update one finding; omit to apply the decision to every finding")

    commands.add_parser("prompts")
    return parser


def main() -> int:
    load_local_environment()
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
            live_provider = None
            if args.provider == "live":
                live_provider = LiveLLMProvider(args.model, args.temperature, args.token_limit)
            result = evaluate_benchmark_bundle(args.suite, live_provider)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            reference_metrics = result["deterministic_reference"]["ablations"]["full_fintrace"]["metrics"]
            live_metrics = result["live_run"]["metrics"] if result["live_run"] is not None else None
            print(json.dumps({
                "output": str(args.output),
                "cases": result["case_count"],
                "findings": result["finding_count"],
                "deterministic_reference_classification_accuracy": reference_metrics["classification_accuracy"],
                "live_classification_accuracy": live_metrics["classification_accuracy"] if live_metrics else None,
                "live_model": result["live_run"]["model"] if result["live_run"] else None,
                "integrity_checks": result["integrity_checks"],
            }, indent=2))
            return 0
        if args.command == "approve":
            report = approve_report(args.report, args.analyst, args.decision, args.note, args.finding_id)
            print(json.dumps(report["human_signoff"], indent=2))
            return 0
        print(json.dumps(prompt_manifest(), indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, ProviderError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
