"""Run the recorded single-prompt baseline without schema or workflow gates."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BASELINE_PROMPT = (
    "Review the transcript and filing. Identify any financial inconsistencies and explain them. "
    "Return your findings."
)


def load_local_environment(path: Path) -> None:
    """Load simple KEY=VALUE entries without printing or persisting their values."""

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


load_local_environment(ROOT / ".env.local")

from fintrace.evaluation import load_benchmark  # noqa: E402
from fintrace.providers import LiveLLMProvider  # noqa: E402


def build_unstructured_prompt(case: dict[str, Any]) -> str:
    transcript_lines = [
        f"- [{finding['finding_id']}] {finding['claim']}"
        for finding in case["findings"]
    ]
    filing_lines: list[str] = []
    for finding in case["findings"]:
        filing_lines.append(
            f"- [{finding['finding_id']}] Filed comparison data: stated value {finding['claimed_value']} "
            f"{finding['unit']}; filing-derived value {finding['computed_value']} {finding['unit']}; "
            f"comparison tolerance {finding['tolerance']} {finding['unit']}."
        )
        filing_lines.extend(
            f"- [{finding['finding_id']}] {passage['location']}: {passage['text']}"
            for passage in finding["filing_passages"]
        )
    return "\n".join([
        BASELINE_PROMPT,
        "",
        "Transcript:",
        *transcript_lines,
        "",
        "Filing:",
        *filing_lines,
    ])


def sum_usage(results: list[dict[str, Any]]) -> dict[str, int | None]:
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    totals: dict[str, int | None] = {}
    for key in keys:
        values = [item["usage"].get(key) for item in results]
        totals[key] = sum(int(value) for value in values) if all(isinstance(value, int) for value in values) else None
    return totals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=ROOT / "fixtures" / "benchmark-suite.json")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "fintrace-single-prompt-live-results.json")
    parser.add_argument("--model", default=os.getenv("FINTRACE_LLM_MODEL", ""))
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--token-limit", type=int, default=1800)
    args = parser.parse_args()
    if not args.model:
        raise SystemExit("FINTRACE_LLM_MODEL or --model is required")

    suite = load_benchmark(args.suite)
    provider = LiveLLMProvider(args.model, args.temperature, args.token_limit)
    started_at = datetime.now(UTC).isoformat()
    results: list[dict[str, Any]] = []
    for case in suite["cases"]:
        prompt_payload = build_unstructured_prompt(case)
        response = provider.raw_prompt_call(prompt_payload, stage=f"single_prompt:{case['case_id']}")
        results.append({
            "case_id": case["case_id"],
            "title": case["title"],
            "finding_ids": [finding["finding_id"] for finding in case["findings"]],
            "prompt_payload": prompt_payload,
            **response,
        })

    artifact = {
        "schema_version": "1.0",
        "data_classification": "fictional_benchmark",
        "suite_version": suite["suite_version"],
        "baseline_prompt": BASELINE_PROMPT,
        "provider": "LiveLLMProvider",
        "endpoint": provider.endpoint,
        "model": provider.model,
        "temperature": provider.temperature,
        "token_limit": provider.token_limit,
        "run_started_at": started_at,
        "run_completed_at": datetime.now(UTC).isoformat(),
        "case_count": len(suite["cases"]),
        "finding_count": sum(len(case["findings"]) for case in suite["cases"]),
        "api_call_count": len(results),
        "usage": sum_usage(results),
        "results": results,
        "execution": provider.metadata(),
        "grading": None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "provider": artifact["provider"],
        "model": artifact["model"],
        "temperature": artifact["temperature"],
        "case_count": artifact["case_count"],
        "finding_count": artifact["finding_count"],
        "api_call_count": artifact["api_call_count"],
        "usage": artifact["usage"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
