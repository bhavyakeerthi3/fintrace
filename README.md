# FinTrace

**Executive claims checked against filed numbers.**

FinTrace is an evidence-first financial analysis workflow for the
Reverie Hacks 2026 ML Prompt Engineering track. It aligns transcript claims with
filed data, recomputes the arithmetic in code, asks a second-pass reviewer for a
specific citable explanation, and leaves final judgment to a human analyst.

FinTrace describes inconsistencies. It does not infer intent or accuse a company
or person of fraud.

## Current engine

The full implementation runs eight auditable checkpoints:

1. Ingest and align transcript passages, filing tables, footnotes, and MD&A.
2. Run four scoped specialist reviews for revenue, cash flow, related-party items, and language patterns.
3. Aggregate and deduplicate overlapping findings under stable finding IDs.
4. Recompute growth, free cash flow, margins, and absolute-value claims in deterministic code with explicit tolerances.
5. Rank multiple filing passages that could explain each finding.
6. Perform a filing-only second pass, then validate every explanation quote against the source text.
7. Create neutral risk memos only for unresolved findings and compare them with prior-period disclosures.
8. Require an accept, reject, or needs-review decision for every finding before final sign-off.

Model calls are injected through specialist and second-pass hooks. The fictional demo uses a deterministic adapter so the full report is reproducible without API keys.

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
python -m fintrace approve outputs/fintrace-demo-report.json --analyst "Your Name" --finding-id F-001 --decision accept --note "Evidence reviewed"
```

## Demo result

- The claimed 23% organic growth recomputes to 12.73% and remains unresolved.
- Claimed adjusted free cash flow of $85m starts from filed free cash flow of
  $62m, but an exact $23m disclosed adjustment reconciles it, so it is explained.
- Claimed GAAP operating margin of 13% recomputes to 12.90%, within tolerance.

This gives the judge three distinct outcomes: aligned, initially flagged but
explained, and unresolved after the second pass.

## Next milestones

- connect production transcript and SEC filing parsers;
- configure live specialist model providers through the existing hooks;
- add historical, adjudicated benchmark cases;
- expand the fictional cross-period fixture set;
- publish the evaluation methodology and sample comparison.
