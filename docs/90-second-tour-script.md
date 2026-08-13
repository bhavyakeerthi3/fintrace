# FinTrace 90-second judge tour

Use the red **Start 90-sec tour** button on the homepage. Advance when each spoken segment is complete.

## 1. Recompute the first claim - 0:00 to 0:13

"FinTrace starts with a management claim and the filed values behind it. Here, management says organic revenue grew 23 percent. Deterministic Python recomputes 12.73 percent, exposing a 10.27-point gap before the model interprets anything."

## 2. Accept a supported explanation - 0:13 to 0:25

"Not every gap is a problem. In case two, the filing contains an exact 23-million-dollar disclosure. It bridges the computed 62 million to the claimed 85 million, so the explanation passes."

## 3. Reject a plausible mismatch - 0:25 to 0:38

"Case three shows the key failure mode. A single prompt accepts a plausible three-million-dollar cash item, but the gap is five million. FinTrace checks the arithmetic and keeps the result unresolved."

## 4. Read the measured comparison - 0:38 to 0:49

"On the same controlled benchmark, the live single prompt classified 10 of 13 findings correctly. The full FinTrace workflow classified all 13 correctly. These are separate recorded runs, not averaged scores."

## 5. Try deterministic math - 0:49 to 1:00

"Judges can change the values themselves. This calculator runs locally without an LLM, making the numerical control transparent and reproducible."

## 6. Inspect the prompt contracts - 1:00 to 1:12

"Every model contract is inspectable: its scope, prompt version, temperature, input contract, output schema, and validation result. The aggregator is clearly labeled as deterministic, not an active LLM call."

## 7. Trace the system architecture - 1:12 to 1:30

"Finally, the architecture separates responsibility. Four scoped LLM calls propose candidates. Python deduplicates and calculates. Retrieval supplies filing evidence. A second model proposes a verdict, but deterministic gates verify quotation, relevance, and numerical reconciliation. Then a named human decides. Models interpret, code calculates, filings provide evidence, and humans decide."

## Architecture-only short version

If a judge asks only about the diagram, say:

"The workflow separates responsibilities so no single prompt controls the result. Four scoped LLM calls propose candidate issues. Deterministic Python deduplicates them and recomputes the financial math. Retrieval supplies relevant filing passages. A second LLM proposes explained or unresolved, but deterministic quote, relevance, and numerical-reconciliation gates can override it. Finally, an analyst reviews the complete evidence chain and a named human signs off."
