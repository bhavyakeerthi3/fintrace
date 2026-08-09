from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Reconciliation:
    finding_id: str
    claim_id: str
    claim_quote: str
    metric_type: str
    claimed_value: float
    computed_value: float
    discrepancy: float
    tolerance: float
    unit: str
    filing_references: list[str]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
