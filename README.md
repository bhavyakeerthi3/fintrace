# FinTrace

**Executive claims checked against filed numbers.**

FinTrace is an evidence-first forensic financial analysis workflow for the
Reverie Hacks 2026 ML Prompt Engineering track. It aligns transcript claims with
filed data, recomputes the arithmetic in code, asks a second-pass reviewer for a
specific citable explanation, and leaves final judgment to a human analyst.

FinTrace describes inconsistencies. It does not infer intent or accuse a company
or person of fraud.

## Current engine

The first version implements the hard, reproducible center of the workflow:

1. Load structured transcript claims and filing line items.
2. Recompute growth, free cash flow, margin, and absolute-value claims.
3. Compare claimed and computed values with explicit tolerances.
4. Search supplied filing disclosures for a citable numeric reconciliation.
5. Split flags into `explained` and `unresolved`.
6. Generate neutral memos for unresolved inconsistencies.
7. Require explicit analyst sign-off and update the report integrity digest.

The demo uses a clearly labeled fictional company. This avoids presenting
unfinished analysis as a claim about a real issuer.

## Run

```bash
python -m fintrace demo
python -m unittest discover -s tests -v
npm install
npm run dev
```

The public judge interface will be available at `http://localhost:3000`. The
analysis report is written to `outputs/fintrace-demo-report.json`.

## Verify the release

```bash
python -m fintrace demo
python -m unittest discover -s tests -v
npm run lint
npm run build
```

## Deploy to Vercel

Import this repository into Vercel and keep the detected **Next.js** framework
settings. No authentication, environment variables, or private-access gate are
required for the fictional public demo.

```bash
npx vercel
```

The Python engine is the reproducible analysis reference; the deployed Next.js
experience presents the same versioned fictional fixture for judges.

To run only the engine:

```bash
python -m fintrace demo
python -m unittest discover -s tests -v
```

To inspect every versioned model contract:

```bash
python -m fintrace prompts
```

After reviewing a report:

```bash
python -m fintrace approve outputs/fintrace-demo-report.json --analyst "Your Name"
```

## Demo result

- The claimed 23% organic growth recomputes to 12.73% and remains unresolved.
- Claimed adjusted free cash flow of $85m starts from filed free cash flow of
  $62m, but an exact $23m disclosed adjustment reconciles it, so it is explained.
- Claimed GAAP operating margin of 13% recomputes to 12.90%, within tolerance.

This gives the judge three distinct outcomes: aligned, initially flagged but
explained, and unresolved after the second pass.

## Next milestones

- transcript and SEC filing parsers;
- four live specialist model calls plus aggregation;
- historical, adjudicated benchmark cases;
- cross-quarter regression;
- workflow PNG, sample comparison, and final documentation.
