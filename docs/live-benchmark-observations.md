# Live benchmark observations

This note records behavior observed in the completed `llama-3.3-70b-versatile` benchmark run. It describes the stored run rather than claiming general model behavior.

## Request topology

The benchmark makes four specialist requests total. Each request contains the complete 12-case, 13-finding suite, and each specialist is isolated by analytical scope: revenue, cash flow, related party, or language. The benchmark does not issue one specialist request per case.

The second pass is one additional batched request. It contains all 12 cases as filing context and the 12 findings that remained flagged after deterministic tolerance handling; `B08-F1` was classified as aligned before the second pass.

## Observed behavior: B09-F1

For the irrelevant-disclosure trap, the language specialist returned this raw finding:

```json
{
  "finding_id": "B09-F1",
  "quote": "Revenue was 130 million dollars.",
  "topic": "Revenue",
  "pattern": "Repeated deflection",
  "baseline_comparison": "Normal communication typically provides direct and clear answers to questions about revenue",
  "severity": "high",
  "rationale": "The speaker's claim of revenue being 130 million dollars may be a deflection, as it does not directly address the question of actual revenue and is not supported by the provided text."
}
```

This rationale is weakly grounded and is not clearly supported by the supplied input.

The filing-only second pass independently returned:

```json
{
  "finding_id": "B09-F1",
  "reasoning": "The provided passage does not directly relate to the claim about revenue."
}
```

That relevance decision produced the correct `unresolved` verdict independently of the language specialist's framing. The takeaway is plain: correctness here came from the relevance and citation requirement overriding an imperfect specialist output, not from every specialist reasoning well individually.

## Known gaps

Retry events currently persist the stage, HTTP status, retry attempt, delay, and timestamp. Full exception bodies are not persisted. Response redirect history is also not persisted, so the stored run cannot establish whether an HTTP redirect occurred. These are logging limitations and remain unresolved.
