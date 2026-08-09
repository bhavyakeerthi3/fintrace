"""Versioned prompt registry and strict structured-output validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROMPT_ROOT = Path(__file__).resolve().parent.parent / "prompts"
PROMPT_FILES = {
    "revenue": "revenue_v1.json",
    "cash_flow": "cash_flow_v1.json",
    "related_party": "related_party_v1.json",
    "language": "language_v1.json",
    "aggregator": "aggregator_v1.json",
    "second_pass": "second_pass_v1.json",
}
PROMPT_VERSION = "2026-08-09.v4"


class PromptValidationError(ValueError):
    """Raised when a model response violates a registered output contract."""


def _load_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for stage, filename in PROMPT_FILES.items():
        path = PROMPT_ROOT / filename
        spec = json.loads(path.read_text(encoding="utf-8"))
        required = {
            "id", "version", "purpose", "input_contract", "output_schema",
            "scope_restrictions", "evaluation_notes", "system_instruction",
        }
        missing = required - set(spec)
        if missing:
            raise ValueError(f"Prompt {stage} is missing fields: {sorted(missing)}")
        registry[stage] = spec
    return registry


PROMPT_REGISTRY = _load_registry()
SPECIALISTS = {name: PROMPT_REGISTRY[name]["system_instruction"] for name in ("revenue", "related_party", "cash_flow", "language")}
AGGREGATOR = PROMPT_REGISTRY["aggregator"]["system_instruction"]
SECOND_PASS_REVIEWER = PROMPT_REGISTRY["second_pass"]["system_instruction"]

MEMO = """You are a senior financial analyst preparing a concise review memo for one unresolved finding. Use only supplied transcript evidence, filing evidence, and deterministic calculations. Describe observable differences without inferring intent. Respond in concise plain text."""
REGRESSION = """Compare a previously unresolved item with later-period supplied evidence. Return only JSON with status resolved, worsened, reclassified, or unaddressed; an evidence_quote; and reasoning. Never invent unavailable evidence."""
OPTIMIZER = """Revise a financial-review prompt using adjudicated evaluation results. Make the smallest change that addresses a measured failure while preserving scope and output schema. Return only the revised prompt."""


def _validate_type(value: Any, expected: str, path: str) -> None:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
    }
    if expected in checks and not checks[expected](value):
        raise PromptValidationError(f"{path} must be {expected}")


def _validate_schema(value: Any, schema: dict[str, Any], path: str = "output") -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, str):
        _validate_type(value, expected_type, path)
    if "enum" in schema and value not in schema["enum"]:
        raise PromptValidationError(f"{path} must be one of {schema['enum']}")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise PromptValidationError(f"{path} is missing fields: {missing}")
        properties = schema.get("properties", {})
        for key, child in properties.items():
            if key in value and isinstance(child, dict):
                _validate_schema(value[key], child, f"{path}.{key}")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            _validate_schema(item, schema["items"], f"{path}[{index}]")


def validate_prompt_output(stage: str, output: Any) -> dict[str, Any]:
    if stage not in PROMPT_REGISTRY:
        raise PromptValidationError(f"Unknown prompt stage: {stage}")
    _validate_schema(output, PROMPT_REGISTRY[stage]["output_schema"])
    return dict(output)


def prompt_manifest() -> dict[str, object]:
    return {
        "version": PROMPT_VERSION,
        "registry": PROMPT_REGISTRY,
        "specialists": SPECIALISTS,
        "aggregator": AGGREGATOR,
        "second_pass_reviewer": SECOND_PASS_REVIEWER,
        "memo": MEMO,
        "regression": REGRESSION,
        "optimizer": OPTIMIZER,
    }
