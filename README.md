# FinTrace

**Executive claims checked against filed numbers.**

FinTrace is an evidence-first financial review pipeline built for the Reverie Hacks 2026 ML Prompt Engineering track. It compares statements from an earnings call with filed financial data, recomputes numerical claims in code, searches the filing for legitimate explanations, and preserves every decision for human review.

The included case uses a clearly labeled fictional company. FinTrace describes observable inconsistencies and does not infer intent or accuse a company or person of wrongdoing.

## What happens inside

```mermaid
flowchart LR
    A[Transcript and filing] --> B[1. Ingest and align]
    B --> C[2. Four specialist scopes]
    C --> D[3. Aggregate and dedupe]
    D --> E[4. Deterministic calculations]
    E --> F[5. Filing evidence retrieval]
    F --> G[6. Second pass and quote validation]
    G --> H[7. Memos and period comparison]
    H --> I[8. Human sign-off]
    I --> J[Versioned JSON report]
```

### 1. Ingest and align

The pipeline loads structured transcript claims and filing data. Every claim is normalized into a common record containing:

- a stable claim ID;
- the exact management quotation;
- claim type and reporting period;
- the claimed value;
- references to the filing values needed to check it.

Speaker-attributed transcript text can also be normalized into individual passages. Invalid case structures are rejected before analysis begins.

### 2. Run four isolated specialist scopes

FinTrace separates review into four narrow scopes:

- revenue and segment reporting;
- cash flow, earnings quality, and non-GAAP reconciliations;
- related-party transactions, guarantees, and commitments;
- observable language and response patterns.

When a model provider is connected, the four calls run in parallel through the `specialist_call` hook. Each scope receives its own versioned prompt and returns structured JSON. Keeping the scopes separate reduces cross-topic contamination and makes their provenance visible.

The fictional demo uses a deterministic local adapter instead of an external model, so it runs without API keys and always produces reproducible results.

### 3. Aggregate and deduplicate

Specialists can identify the same underlying issue in different ways. The aggregator groups candidates using the claim ID or normalized quotation, then:

- assigns a stable finding ID such as `F-001`;
- preserves every contributing specialist source;
- keeps the strongest severity;
- combines non-duplicate rationale;
- retains the original source finding IDs.

This prevents one issue from appearing several times in the final report.

### 4. Recompute numerical claims in code

Arithmetic is never delegated to the language model. The Python reconciliation layer supports:

- period-over-period growth;
- free cash flow;
- operating or other percentage margins;
- direct absolute-value comparisons.

Each calculation records its formula, filing inputs, claimed value, computed value, discrepancy, unit, tolerance, and whether the result falls inside that tolerance.

For example, the fictional organic-growth claim is checked as:

```text
(current revenue - prior revenue) / prior revenue * 100
(124 - 110) / 110 * 100 = 12.73%
```

The stated value is `23.0%`, leaving a `10.27 percentage-point` difference outside tolerance.

### 5. Retrieve possible filing explanations

For every surviving finding, FinTrace searches the complete supplied filing corpus, including financial statements, footnotes, segment disclosures, accounting policies, non-GAAP reconciliations, and MD&A.

Candidate passages are ranked using claim-term overlap and explanation-related terms such as acquisitions, currency, divestitures, reclassifications, restructuring, and methodology changes. Explicitly linked disclosures receive priority. Multiple passages are retained so the second pass is not forced to rely on one fragment.

### 6. Perform a filing-only second pass

The second pass asks one narrow question: does the filing contain a specific disclosure that directly explains the finding?

A finding is marked `explained` only when:

- the explanation is present in the supplied filing;
- it directly relates to the finding;
- a numerical adjustment actually reconciles the computed and claimed values when numbers are involved;
- the returned quotation can be found verbatim in the filing corpus.

If a quotation cannot be located, FinTrace automatically moves the finding to `unresolved`. Generic accounting possibilities and outside information are not accepted as explanations.

### 7. Create analyst material

Neutral risk memos are generated only for unresolved findings. A memo includes the management statement, filed evidence, deterministic calculation, candidate disclosures reviewed, and the specific reason the difference remains unresolved.

If a later-period evidence package is supplied, FinTrace also records whether the issue was:

- resolved;
- worsened;
- reclassified;
- left unaddressed.

No later-period conclusion is invented when supporting evidence is unavailable.

### 8. Require per-finding human review

Every explained or unresolved finding begins with a `needs_review` decision. An analyst must record one of:

- `accept`;
- `reject`;
- `needs_review`.

The overall sign-off remains pending until every finding has been accepted or rejected. Each decision stores the analyst name, note, review timestamp, and finding ID. Any update creates a new SHA-256 integrity digest for the report.

## Important system boundary

The Python engine is the authoritative implementation. The public Next.js page is an interactive presentation of the same versioned fictional fixture; its animation does not execute the Python pipeline in the browser.

For live model execution, an application layer must provide callbacks for `specialist_call` and `second_pass_call`. Those hooks already exist, but this public demo intentionally has no model credentials or paid provider dependency.

## Demo outcomes

The fixture demonstrates three distinct outcomes:

| Claim | Claimed | Computed | Result |
| --- | ---: | ---: | --- |
| Organic revenue growth | 23.0% | 12.73% | Unresolved after filing review |
| Adjusted free cash flow | $85m | $62m before adjustment | Explained by a validated $23m filing adjustment |
| GAAP operating margin | 13.0% | 12.90% | Aligned within tolerance |

Only the first two become candidate findings because the margin claim already agrees with the filing-derived result.

## Report contents

The generated `fintrace-demo-report.json` contains:

```text
schema_version
run_id and timestamps
data classification and prompt version
eight stage status records
normalized ingestion records
four specialist outputs
aggregated findings
deterministic reconciliations and calculations
ranked filing evidence
explained and unresolved classifications
quote-validation results
unresolved-only memos
cross-period results
per-finding human decisions
SHA-256 integrity digest
```

The contract is defined in `schema/report-schema.json` and is validated in the test suite.

## Project structure

```text
app/
  layout.tsx              Next.js document metadata and UTF-8 declaration
  page.tsx                Public interactive fictional case
  globals.css             Responsive interface styling
fintrace/
  __main__.py             Command-line interface
  models.py               Reconciliation data model
  reconcile.py            Deterministic financial calculations
  stages.py               Ingestion through human-review stage helpers
  pipeline.py             End-to-end orchestration and integrity digest
  prompts.py              Versioned structured-output prompt contracts
fixtures/
  fictional-demo.json     Fictional transcript, filing, and disclosures
schema/
  report-schema.json      Machine-readable report contract
tests/
  test_pipeline.py        Pipeline, safety, validation, and sign-off tests
```

## Run locally

Requirements:

- Python 3.11 or newer;
- Node.js 20 or newer;
- npm.

Run the analysis engine:

```bash
python -m fintrace demo
```

The report is written to `outputs/fintrace-demo-report.json`.

Inspect the current model contracts:

```bash
python -m fintrace prompts
```

Record a decision for one finding:

```bash
python -m fintrace approve outputs/fintrace-demo-report.json \
  --analyst "Your Name" \
  --finding-id F-001 \
  --decision accept \
  --note "Calculation and filing evidence reviewed"
```

Omit `--finding-id` to apply the same decision to all findings.

Run the website:

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Verify a release

```bash
python -m fintrace demo
python -m unittest discover -s tests -v
npm run lint
npm run build
npm audit --omit=dev
```

The current release passes 11 Python tests, ESLint, the Next.js production build, JSON Schema validation, and the production dependency audit.

## Deployment

The public fictional demo is deployed on Vercel:

[https://fintrace-fawn.vercel.app](https://fintrace-fawn.vercel.app)

Vercel should detect the repository as Next.js. The demo requires no authentication, environment variables, private-access gate, database, or external model credentials.

## Current limitations

- The included fixture is fictional and is not evidence about a real issuer.
- Production transcript and SEC filing parsers are not connected yet.
- Live model providers are supported through callbacks but are not configured in the public demo.
- Evaluation percentages shown in the interface are illustrative targets, not measured production performance.
- Historical benchmarking requires an adjudicated case set before accuracy claims can be made.

## Design principle

Models identify and organize candidate issues. Code performs the arithmetic. The filing must support every explanation. Humans make the final decision.
