# Draft 2: Samples - live single prompt versus full FinTrace

## Run metadata

The single-prompt baseline has now been run genuinely against all 12 controlled cases and 13 findings.

| Field | Recorded value |
| --- | --- |
| Provider | `LiveLLMProvider` |
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| Model | `llama-3.3-70b-versatile` |
| Temperature | `0.0` |
| Started | `2026-08-11T08:04:36.104895+00:00` |
| Completed | `2026-08-11T08:04:50.594427+00:00` |
| API calls | 12, one unstructured request per case |
| Findings covered | 13 |
| Prompt tokens | 1,838 |
| Completion tokens | 3,129 |
| Total tokens | 4,967 |

The exact instruction was:

> Review the transcript and filing. Identify any financial inconsistencies and explain them. Return your findings.

Each request contained that instruction followed by the case's transcript and filing content in one user message. It used no system prompt, response schema, specialist scoping, or validation gates. Raw responses were saved verbatim before grading.

## Important evidence note

The earlier `8 / 13 = 61.5%` single-prompt figure was a deterministic ablation, not a live-model measurement. It has been replaced as the headline comparison by this genuine live run. The raw live outputs were graded afterward under a separate recorded rubric; the grading does not alter or reshape model text.

| Method | Correct | Classification accuracy | False-positive rate | Unsupported explanations |
| --- | ---: | ---: | ---: | ---: |
| Live Single Prompt | 10 / 13 | 76.9% | 7.7% | 1 |
| Live Full FinTrace | 13 / 13 | 100.0% | 0.0% | 0 |

The three live single-prompt errors were B03-F1, B08-F1, and B12-F2. The two live runs are not averaged or blended.

---

## Case 1 - FT-001 / B01-F1: numerical discrepancy

### Evidence

- Claim: "Organic segment revenue grew 23 percent year over year, reflecting broad-based demand."
- Filed values: 124 current and 110 prior.
- Code result: `(124 - 110) / 110 x 100 = 12.73%`.
- Gap: 10.27 percentage points.
- Disclosure: organic growth excludes acquired operations, but the acquisition effect is not quantified.

### Raw live single-prompt response - verbatim

```text
After reviewing the transcript and filing, I have identified a financial inconsistency. 

The transcript states that organic growth was 23 percent, which matches the stated value in the filing (23.0 percentage points). However, the filing-derived value is 12.73 percentage points, which is significantly lower than the stated value.

This discrepancy exceeds the comparison tolerance of 0.5 percentage points, indicating a potential error or inconsistency in the calculation of organic growth. The difference between the stated value (23.0%) and the filing-derived value (12.73%) is 10.27 percentage points, which is a substantial variance.

The segment note on page 18 of the filing provides context that organic growth excludes acquired operations. This note suggests that the calculation of organic growth might be sensitive to the treatment of acquired operations, and it is possible that the discrepancy arises from differences in how these operations are accounted for.

To resolve this inconsistency, it would be necessary to review the calculation of organic growth in more detail, including the specific methodology used to exclude acquired operations, and to verify that the filing-derived value is accurate.
```

Call usage: 132 prompt tokens, 224 completion tokens, 356 total tokens.

### Separate grading

- Graded classification: `UNRESOLVED`.
- Expected: `UNRESOLVED`.
- Result: correct.
- Reason: the response identifies the gap but requires additional review and does not accept the unquantified acquisition wording as a reconciliation.

### Full FinTrace result

`UNRESOLVED`, computed value `12.73%`. The missing quantified-disclosure gate prevents a generic acquisition statement from reconciling the 10.27-point gap.

What changed: both methods reached the adjudicated label. FinTrace made the calculation, tolerance decision, evidence search, and missing-quantification reason explicit and machine-checkable.

---

## Case 2 - FT-002 / B07-F1: filing-supported explanation

### Evidence

- Claim: "We delivered record adjusted free cash flow of 85 million dollars."
- Filed values: $96m operating cash flow and $34m capital expenditures.
- Code result: `$96m - $34m = $62m`.
- Filing adjustment: $23m of cash restructuring payments.
- Reconciliation: `$62m + $23m = $85m`.

### Raw live single-prompt response - verbatim

```text
After reviewing the transcript and filing, I have identified a financial inconsistency. 

The transcript states that the adjusted free cash flow was 85 million dollars. However, the filing-derived value for the same metric is 62.0 USD millions, which is significantly lower than the stated value of 85.0 USD millions. 

The reason for this discrepancy can be found in the non-GAAP reconciliation on page 31 of the filing. It is mentioned that the adjusted free cash flow adds back 23 million dollars of cash restructuring payments. This suggests that the company has made adjustments to the original cash flow figure to arrive at the adjusted free cash flow of 85 million dollars.

To reconcile the difference, we can subtract the added-back cash restructuring payments from the stated adjusted free cash flow:

Stated adjusted free cash flow: 85 million dollars
Added-back cash restructuring payments: 23 million dollars
Filing-derived value: 62 million dollars

If we subtract the added-back cash restructuring payments from the stated adjusted free cash flow, we get:

85 million dollars - 23 million dollars = 62 million dollars

This matches the filing-derived value, indicating that the company has indeed added back the cash restructuring payments to arrive at the adjusted free cash flow figure. The comparison tolerance of 0.5 USD millions is not relevant in this case, as the difference between the stated and filing-derived values is much larger than the tolerance.

In conclusion, the financial inconsistency is due to the addition of cash restructuring payments to the original cash flow figure to arrive at the adjusted free cash flow. The filing-derived value of 62 million dollars represents the original cash flow figure before the adjustments, while the stated adjusted free cash flow of 85 million dollars includes the added-back cash restructuring payments.
```

Call usage: 148 prompt tokens, 357 completion tokens, 505 total tokens.

### Separate grading

- Graded classification: `EXPLAINED`.
- Expected: `EXPLAINED`.
- Result: correct.
- Reason: the response performs and accepts the exact $23m restructuring-payment reconciliation.

### Full FinTrace result

`EXPLAINED`, computed base `$62m`, with the exact $23m filing quote validated. Direct relationship, quotation, and numerical reconciliation all pass.

What changed: both methods reached the adjudicated label. FinTrace enforced the checks as separate gates rather than relying on the model's narrative.

---

## Case 3 - B12-F2: non-reconciling cash-flow adjustment

### Evidence

- Claim: "Adjusted free cash flow was 45 million dollars."
- Filing-derived value: $40m.
- Code calculation: `$45m - $40m = $5m` gap, outside the $0.5m tolerance.
- Filing passage: "Adjusted EBITDA adds back 8 million dollars of restructuring expense; the same program required 3 million dollars of cash payments."
- The $8m add-back directly reconciles the companion EBITDA finding B12-F1: `$40m + $8m = $48m`.
- For B12-F2, the only cash-flow amount is $3m: `$40m + $3m = $43m`, not the claimed $45m.

### Raw live single-prompt response - verbatim

```text
After reviewing the transcript and filing, I have identified the following financial inconsistencies:

1. **Adjusted EBITDA**: The transcript states that Adjusted EBITDA was $48 million, while the filing-derived value is $40 million. This represents a discrepancy of $8 million, which exceeds the comparison tolerance of $0.5 million. The filing notes that the Adjusted EBITDA adds back $8 million of restructuring expense, which may be the cause of the discrepancy.

2. **Adjusted Free Cash Flow**: The transcript states that Adjusted Free Cash Flow was $45 million, while the filing-derived value is $40 million. This represents a discrepancy of $5 million, which also exceeds the comparison tolerance of $0.5 million. The filing notes that the same restructuring program required $3 million of cash payments, which may have affected the Adjusted Free Cash Flow.

The inconsistencies can be explained by the following:

* The addition of $8 million of restructuring expense to Adjusted EBITDA may not have been fully accounted for in the filing-derived value, resulting in a lower value.
* The cash payments of $3 million required for the restructuring program may have reduced the Adjusted Free Cash Flow, resulting in a lower filing-derived value.
* The comparison tolerance of $0.5 million is relatively low, which may not account for normal fluctuations in financial data.

Overall, the discrepancies between the transcript and filing values suggest that there may be differences in the calculation or presentation of Adjusted EBITDA and Adjusted Free Cash Flow. Further review and reconciliation of the financial data may be necessary to resolve these inconsistencies.
```

Call usage: 259 prompt tokens, 328 completion tokens, 587 total tokens. B12-F1 and B12-F2 were presented together in this one case-level request, so usage is shared.

### Separate grading

- Graded classification: `EXPLAINED`.
- Expected: `UNRESOLVED`.
- Result: incorrect.
- Reason: under the recorded rubric, the response places the $3m cash payment under "The inconsistencies can be explained" and treats it as affecting the $5m gap. The amount does not reconcile, and the passage's direct $8m add-back applies to adjusted EBITDA rather than adjusted free cash flow.

### Full FinTrace result

```json
{
  "finding_id": "B12-F2",
  "classification": "unresolved",
  "computed_value": 40.0,
  "explanation_quote": "",
  "citation_valid": null,
  "model_decision": "unresolved",
  "model_reasoning": "The provided evidence does not directly explain the difference in adjusted free cash flow.",
  "transition": "unresolved"
}
```

Adjudication: the live single prompt concluded `EXPLAINED`; expected and full FinTrace concluded `UNRESOLVED`. The exact quotation exists, so quote presence alone is insufficient. The direct-relationship gate rejects using an EBITDA reconciliation as a free-cash-flow explanation, and the numerical-reconciliation gate rejects `$3m` as a bridge for a `$5m` gap. Those gates change the outcome.

---

## What the comparison demonstrates

The first two showcase cases were classified correctly by both methods. B12-F2 is the measured baseline failure that demonstrates a different final outcome. The other two genuine single-prompt errors remain visible rather than being selected around:

- B03-F1: the single prompt noticed the exact acquisition contribution but still required clarification, producing `UNRESOLVED` instead of `EXPLAINED`.
- B08-F1: it acknowledged that 12.9% was within the 0.5-point tolerance of approximately 13%, but still reported an inconsistency requiring review instead of `ALIGNED`.
- B12-F2, shown above: it treated a $3m cash payment as an explanation for a $5m gap, producing an unsupported `EXPLAINED` result instead of `UNRESOLVED`.

Full FinTrace classified all three correctly because calculation, tolerance, relevance, quotation, and reconciliation are enforced independently of the model narrative.

B09-F1 remains useful as a separate relevance-gate example: both the genuine live single prompt and FinTrace correctly rejected the unrelated $30m debt disclosure. It is no longer presented as a baseline failure.

## Submission-readiness status

The previously missing live single-prompt evidence has now been captured. The complete unmodified responses for all 12 calls, prompts, per-call usage, timestamps, and separate 13-finding grading record are stored in `outputs/fintrace-single-prompt-live-results.json` in the project repository.

Open item: the track page says four files are required but names only workflow diagram, samples, and documentation. Do not invent a fourth artifact. Confirm the actual requirement with the organizers, then add it if needed.
