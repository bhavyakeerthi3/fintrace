"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import evaluation from "./evaluation-data.json";
import promptData from "./prompt-data.json";

type ResultStatus = "unresolved" | "explained" | "aligned";
type Claim = {
  id: string; finding: string; label: string; quote: string; claimed: string; computed: string;
  formula: string; delta: string; source: string; status: ResultStatus; rationale: string;
  passages: string[]; candidate: string; validation: string; demoLabel: string; explanation: string;
  baseline?: ResultStatus; expected?: ResultStatus;
};

const claims: Claim[] = [
  {
    id: "claim-growth", finding: "FT-001", label: "Organic revenue growth",
    quote: "Organic segment revenue grew 23 percent year over year, reflecting broad-based demand.",
    claimed: "23.00%", computed: "12.73%", formula: "(124 - 110) / 110 x 100", delta: "10.27 pp",
    source: "Note 3 | Segment table", status: "unresolved",
    rationale: "No filing disclosure quantifies an acquisition, currency, divestiture, policy, or segment effect that reconciles the 10.27 percentage-point difference.",
    passages: ["Segment note p. 18: current revenue $124m; prior revenue $110m.", "MD&A p. 24: acquired operations are excluded from organic growth, with no quantified effect."],
    candidate: "No candidate passage numerically reconciles the difference.", validation: "No explanation quote submitted | remains UNRESOLVED",
    demoLabel: "Case 1 | Numerical discrepancy", explanation: "None found",
  },
  {
    id: "claim-fcf", finding: "FT-002", label: "Adjusted free cash flow",
    quote: "We delivered record adjusted free cash flow of 85 million dollars.",
    claimed: "$85m", computed: "$62m", formula: "$96m CFO - $34m capex", delta: "$23m",
    source: "Cash-flow statement + non-GAAP reconciliation", status: "explained",
    rationale: "The filing identifies an exact $23 million restructuring adjustment, and $62 million plus $23 million reconciles to the stated $85 million.",
    passages: ["Cash-flow statement p. 9: operating cash flow $96m and capital expenditures $34m.", "Non-GAAP p. 31: adjusted free cash flow excludes $23m of cash restructuring payments."],
    candidate: "Adjusted free cash flow excludes 23 million dollars of cash restructuring payments; the measure is operating cash flow less capital expenditures plus those payments.",
    validation: "Exact quote located at Fictional 10-Q p. 31 | direct connection PASS",
    demoLabel: "Case 2 | Filing-supported explanation", explanation: "$23m adjustment, exact quote validated",
  },
  {
    id: "claim-baseline", finding: "B09-F1", label: "Irrelevant disclosure trap",
    quote: "Revenue was 130 million dollars.",
    claimed: "$130m", computed: "$100m", formula: "$130m claim - $100m filed revenue", delta: "$30m",
    source: "Revenue table + Debt note p. 44", status: "unresolved",
    rationale: "The debt disclosure contains the same $30 million number, but it does not relate to revenue and cannot explain the discrepancy.",
    passages: ["Revenue table: filed revenue $100m.", "Debt note p. 44: a $30m revolving credit facility remained undrawn."],
    candidate: "A 30 million dollar revolving credit facility remained undrawn at quarter end.", validation: "Exact quote PASS | direct relationship FAIL | EXPLAINED -> UNRESOLVED",
    demoLabel: "Case 3 | Baseline failure", explanation: "Debt disclosure rejected as irrelevant", baseline: "explained", expected: "unresolved",
  },
];

const stages = [
  ["01", "Ingest & align"], ["02", "Specialist calls"], ["03", "Aggregate & dedupe"],
  ["04", "Code calculation"], ["05", "Filing retrieval"], ["06", "Second pass & validate"],
  ["07", "Analyst review"], ["08", "Human sign-off"],
];

function StatusMark({ status }: { status: ResultStatus }) {
  return <span className={`status status-${status}`}><i />{status}</span>;
}

function ArrowIcon() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 10h13M11 5l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function formatPct(value: number) {
  return value.toFixed(1);
}

export default function Home() {
  const [selected, setSelected] = useState(0);
  const [running, setRunning] = useState(false);
  const [complete, setComplete] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);
  const [signed, setSigned] = useState(false);
  const [whyOpen, setWhyOpen] = useState(false);
  const [promptIndex, setPromptIndex] = useState(0);
  const claim = claims[selected];
  const prompt = promptData[promptIndex];
  const baseline = evaluation.ablations.single_prompt;
  const fintrace = evaluation.ablations.full_fintrace;
  const correctGain = fintrace.correct_classifications - baseline.correct_classifications;
  const pointGain = (fintrace.classification_accuracy - baseline.classification_accuracy).toFixed(1);

  useEffect(() => {
    if (!running) return;
    let stage = 0;
    const timer = window.setInterval(() => {
      stage += 1;
      setActiveStage(stage);
      if (stage >= stages.length - 1) {
        window.clearInterval(timer);
        setRunning(false);
        setComplete(true);
      }
    }, 230);
    return () => window.clearInterval(timer);
  }, [running]);

  const progress = useMemo(() => Math.max(0, ((activeStage + 1) / stages.length) * 100), [activeStage]);
  function runDemo() {
    if (running) return;
    setComplete(false); setSigned(false); setActiveStage(0); setRunning(true);
    document.querySelector("#workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <main>
      <nav className="nav shell" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="FinTrace home"><span>F</span>FinTrace</a>
        <div className="nav-links"><a href="#method">Method</a><a href="#workspace">Judge demo</a><a href="#evaluation">Evaluation</a><a href="#prompts">Prompts</a><Link href="/architecture">Architecture</Link></div>
        <span className="public-pill"><i /> Public fictional demo</span>
      </nav>

      <section className="hero shell" id="top">
        <div className="hero-copy">
          <p className="eyebrow">Prompt-engineering research prototype</p>
          <h1>What they said.<br />What they filed.<br /><em>What the math says.</em></h1>
          <p className="lede">Specialist models find candidate issues. Python recomputes every number. The full filing gets a second look. Exact quotes are validated before a human decides.</p>
          <div className="hero-actions"><button className="primary" onClick={runDemo}>Run Judge Demo <ArrowIcon /></button><a className="text-link" href="#evaluation">See measured benchmark</a></div>
          <p className="disclaimer">3 controlled cases | completes in about 2 seconds | no API key required</p>
        </div>
        <div className="hero-art" aria-label="A comparison between an executive claim and filed values">
          <div className="paper paper-back"><span>FORM 10-Q</span><strong>Filed evidence</strong></div>
          <div className="paper paper-front"><div className="paper-head"><span>EARNINGS CALL</span><span>Q2 | FY26</span></div><blockquote>&quot;Organic segment revenue grew <mark>23 percent</mark> year over year.&quot;</blockquote><div className="redline"><span>Python recomputed</span><strong>12.73%</strong><small>-10.27 pp</small></div></div>
          <svg className="trace-line" viewBox="0 0 420 180" aria-hidden="true"><path d="M10 134 C90 35 205 175 410 20" /><circle cx="10" cy="134" r="4" /><circle cx="410" cy="20" r="4" /></svg>
        </div>
      </section>

      <section className="method" id="method"><div className="shell">
        <div className="section-kicker"><span>01</span><p>Models interpret. Code calculates.</p></div>
        <div className="section-heading"><h2>Every explanation must<br />survive validation.</h2><p>Specific filing evidence + direct connection + exact quote + numerical reconciliation = explained. Anything less remains unresolved.</p></div>
        <div className="stage-grid">{stages.map(([number, name], index) => <div className="stage" key={number}><span>{number}</span><strong>{name}</strong>{index < stages.length - 1 && <b aria-hidden="true">-&gt;</b>}</div>)}</div>
      </div></section>

      <section className="workspace shell" id="workspace">
        <div className="section-kicker"><span>02</span><p>Judge Demo mode | three decisive cases</p></div>
        <div className="workspace-head"><div><span className="mode-badge">JUDGE DEMO</span><h2>Northstar Mobility</h2><p>Q2 FY2026 | controlled fictional demonstration</p></div><button className={`run-button ${running ? "is-running" : ""}`} onClick={runDemo} disabled={running}><span>{running ? "Tracing evidence..." : complete ? "Run Judge Demo again" : "Run Judge Demo"}</span><ArrowIcon /></button></div>
        <div className="demo-case-strip">{claims.map((item, index) => <button key={item.id} className={selected === index ? "active" : ""} onClick={() => setSelected(index)}><span>0{index + 1}</span><strong>{item.demoLabel.split(" | ")[1]}</strong><small>{index === 0 ? "23.00% claimed vs 12.73% computed" : index === 1 ? "Disclosure + quote reconcile $23m" : "Single prompt fails; FinTrace succeeds"}</small></button>)}</div>
        <div className="progress-wrap" aria-live="polite"><div className="progress-label"><span>{running ? `Stage ${activeStage + 1} of ${stages.length} | ${stages[activeStage]?.[1]}` : complete ? "Three cases complete | awaiting human sign-off" : "Ready: unresolved + explained + within tolerance"}</span><span>{running ? `${Math.round(progress)}%` : complete ? "3 / 3" : "0 / 3"}</span></div><div className="progress"><i style={{ width: `${running || complete ? progress : 0}%` }} /></div></div>

        <div className="case-grid">
          <aside className="claims-list" aria-label="Claims"><div className="panel-label">Judge cases <span>3</span></div>{claims.map((item, index) => <button key={item.id} className={`claim-tab ${selected === index ? "active" : ""}`} onClick={() => { setSelected(index); setWhyOpen(false); }}><span>{item.finding}</span><strong>{item.label}</strong><small>Claimed {item.claimed}</small><StatusMark status={item.status} /></button>)}</aside>
          <article className="evidence-panel"><div className="panel-label">Evidence trace <span>{claim.demoLabel}</span></div><p className="quote-label">Management statement</p><blockquote>&quot;{claim.quote}&quot;</blockquote><div className="source-row"><span>Source</span><strong>Q2 earnings call | prepared remarks</strong></div><div className="connector"><span>checked against</span></div><div className="filing-card"><div><span>Filed source</span><strong>{claim.source}</strong></div><span className="verified">{claim.validation}</span></div>{claim.baseline && <div className="baseline-compare"><div><span>Single Prompt</span><strong><StatusMark status={claim.baseline} /></strong><small>FAIL</small></div><div><span>FinTrace</span><strong><StatusMark status={claim.status} /></strong><small>PASS</small></div><div><span>Expected</span><strong><StatusMark status={claim.expected!} /></strong><small>ADJUDICATED</small></div></div>}<p className="rationale">{claim.rationale}</p></article>
          <aside className="ledger"><div className="panel-label">DETERMINISTIC CODE <span>NOT AN LLM CALL</span></div><div className="ledger-values"><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Computed</span><strong>{claim.computed}</strong></div></div><div className="formula"><span>Formula</span><code>{claim.formula}</code></div><div className="delta"><span>Difference</span><strong>{claim.delta}</strong></div><div className="filing-explanation"><span>Filing explanation</span><strong>{claim.explanation}</strong></div><div className="verdict"><span>Final result</span><StatusMark status={claim.status} /></div><button className="memo-button" onClick={() => setWhyOpen((value) => !value)}>{whyOpen ? "Hide Why panel" : "Why this result?"}<ArrowIcon /></button></aside>
        </div>

        {whyOpen && <div className="why-panel" role="region" aria-label="Why this result"><div className="why-head"><span>WHY {claim.status.toUpperCase()}?</span><StatusMark status={claim.status} /></div>{claim.status === "explained" ? <><h3>Disclosure found</h3><blockquote>&quot;{claim.candidate}&quot;</blockquote><dl><div><dt>Connection</dt><dd>The disclosed $23m adjustment exactly bridges the $62m filed base to the $85m claim.</dd></div><div><dt>Quote validation</dt><dd>PASS | exact filing match and direct relationship</dd></div></dl></> : claim.baseline ? <><div className="why-math"><div><span>Computed</span><strong>{claim.computed}</strong></div><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Difference</span><strong>{claim.delta}</strong></div></div><h3>Why the plausible explanation fails</h3><blockquote>&quot;{claim.candidate}&quot;</blockquote><p>The quotation is present, but it describes an undrawn debt facility rather than revenue. Direct relationship: <b>FAIL</b>.</p><p><b>Result:</b> The baseline EXPLAINED result transitions to UNRESOLVED.</p></> : <><div className="why-math"><div><span>Computed</span><strong>{claim.computed}</strong></div><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Difference</span><strong>{claim.delta}</strong></div></div><h3>Filing explanations reviewed</h3><p>Currency | Acquisition | Divestiture | Accounting policy | Segment presentation</p><p><b>Result:</b> No filing disclosure directly reconciles the difference.</p></>}</div>}

        <div className="chain"><div className="panel-label">Expandable evidence chain <span>{claim.finding}</span></div>{[
          ["01", "Management claim", claim.quote], ["02", "Filed values", claim.passages.join(" ")], ["03", "Python calculation", claim.formula],
          ["04", "Computed vs claimed", `${claim.computed} vs ${claim.claimed}; difference ${claim.delta}`], ["05", "Filing passages searched", claim.passages.join(" | ")],
          ["06", "Candidate explanation", claim.candidate], ["07", "Second-pass decision", claim.rationale], ["08", "Quote validation", claim.validation],
          ["09", "Human decision", signed ? "Demo analyst signed the evidence package." : "Pending. The system does not make the final judgment."],
        ].map(([number, title, body]) => <details key={number}><summary><span>{number}</span><strong>{title}</strong><b>+</b></summary><p>{body}</p></details>)}</div>

        <div className="signoff"><div><span className="signoff-icon">{signed ? "OK" : "08"}</span><div><strong>{signed ? "Review signed" : "Human judgment stays in the loop"}</strong><p>{signed ? "Demo Analyst | evidence trail preserved" : "FinTrace describes inconsistencies. An analyst decides what they mean."}</p></div></div><button className={signed ? "signed" : ""} onClick={() => setSigned(true)} disabled={!complete || signed}>{signed ? "Signed off" : complete ? "Sign off demo" : "Run demo first"}</button></div>
      </section>

      <section className="benchmark" id="evaluation"><div className="shell">
        <div className="section-kicker light"><span>03</span><p>Measured controlled benchmark</p></div>
        <div className="evaluation-head"><div><h2>Same evidence. Different controls.</h2><p>{evaluation.case_count} controlled fictional cases containing {evaluation.finding_count} independently evaluated findings, executed with the {evaluation.provider} adapter.</p><div className="lift-pills"><span>+{correctGain} correct findings</span><span>+{pointGain} percentage points</span></div></div><div className="headline-scores"><div><span>Single Prompt</span><strong>{formatPct(baseline.classification_accuracy)}%</strong><small>{baseline.correct_classifications} / {baseline.finding_count} correct</small></div><div><span>Full FinTrace</span><strong>{formatPct(fintrace.classification_accuracy)}%</strong><small>{fintrace.correct_classifications} / {fintrace.finding_count} correct</small></div></div></div>
        <div className="metric-grid">{[
          ["Classification accuracy", baseline.classification_accuracy, fintrace.classification_accuracy, "%"],
          ["Unsupported-explanation count", baseline.unsupported_explanations, fintrace.unsupported_explanations, ""],
          ["Numeric reconciliation accuracy", baseline.numerical_reconciliation_accuracy, fintrace.numerical_reconciliation_accuracy, "%"],
          ["False-positive count", baseline.false_positives, fintrace.false_positives, ""],
        ].map(([label, base, full, suffix]) => <div className="metric-card" key={String(label)}><span>{label}</span><div><small>Single</small><strong>{suffix === "%" ? `${formatPct(Number(base))}%` : base}</strong></div><div><small>FinTrace</small><strong>{suffix === "%" ? `${formatPct(Number(full))}%` : full}</strong></div></div>)}</div>
        <div className="ablation"><div className="panel-label">Prompt ablation | measured, not assumed <span>suite v{evaluation.suite_version}</span></div><table><thead><tr><th>Workflow</th><th>Correct</th><th>Classification accuracy</th><th>Unsupported explanations</th><th>Numeric reconciliation accuracy</th><th>False positives</th></tr></thead><tbody>{Object.entries(evaluation.ablations).map(([name, metrics]) => <tr key={name}><td>{name.replaceAll("_", " ")}</td><td>{metrics.correct_classifications}/{metrics.finding_count}</td><td>{formatPct(metrics.classification_accuracy)}%</td><td>{metrics.unsupported_explanations}</td><td>{metrics.correct_numeric_checks}/{metrics.numeric_checks} ({formatPct(metrics.numerical_reconciliation_accuracy)}%)</td><td>{metrics.false_positives}</td></tr>)}</tbody></table></div>
        <p className="benchmark-note"><b>Reproducible formula:</b> classification accuracy = correct classifications / {evaluation.finding_count} findings x 100. Integrity checks verified {evaluation.integrity_checks.percentages_checked} percentage calculations before this artifact was generated. Results are limited to this controlled fictional benchmark and are not a claim of general model performance.</p>
        <details className="metric-clarification"><summary>Why older results showed 55.6 and 74.9</summary><p>Those values are a composite control index measured in points, not classification accuracy. Formula: {baseline.composite_control_index_formula}. Single Prompt: {baseline.composite_control_index} points. Specialists plus calculation: {evaluation.ablations.specialists_plus_calculation.composite_control_index} points. Full FinTrace: {fintrace.composite_control_index} points.</p></details>
      </div></section>

      <section className="single-prompt"><div className="shell"><div className="section-kicker light"><span>04</span><p>Why not a single prompt?</p></div><div className="single-prompt-grid"><article><span>SINGLE PROMPT</span><h2>Can identify a plausible explanation.</h2><p>In this controlled benchmark, it sometimes accepts a matching number even when the disclosure is generic, irrelevant, or cannot be quoted.</p></article><article><span>FINTRACE</span><h2>Adds explicit gates.</h2><ul><li>Requires deterministic calculation</li><li>Retrieves filing evidence</li><li>Requires direct relevance</li><li>Validates the quotation</li><li>Preserves unresolved cases</li><li>Requires human review</li></ul></article></div><p className="benchmark-note">This comparison describes the measured behavior of this controlled fictional benchmark. It does not claim that every multi-step workflow is always better.</p></div></section>

      <section className="inspector shell" id="prompts">
        <div className="section-kicker"><span>05</span><p>Prompt Inspector</p></div>
        <div className="section-heading"><h2>Inspect every model contract.</h2><p>Judges can see the version, instruction, input contract, expected schema, and sample output. Secrets never enter this interface.</p></div>
        <div className="code-boundary"><div><span>LLM CALLS</span><strong>Specialists -&gt; aggregator -&gt; second pass</strong><small>Versioned prompts and schema-validated structured outputs</small></div><b>-&gt;</b><div className="code-only"><span>DETERMINISTIC CODE</span><strong>Python calculation + quote validation</strong><small>NOT AN LLM CALL</small></div></div>
        <div className="inspector-grid"><aside>{promptData.map((item, index) => <button className={promptIndex === index ? "active" : ""} onClick={() => setPromptIndex(index)} key={item.id}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item.stage.replaceAll("_", " ")}</strong><small>v{item.version}</small></button>)}</aside><article><div className="call-label">{prompt.call_type}</div><div className="prompt-meta"><div><span>Stage</span><strong>{prompt.stage.replaceAll("_", " ")}</strong></div><div><span>Model</span><strong>{prompt.model}</strong></div><div><span>Temperature</span><strong>{prompt.temperature.toFixed(1)}</strong></div><div><span>Prompt version</span><strong>{prompt.version}</strong></div></div><h3>Purpose</h3><p className="prompt-purpose">{prompt.purpose}</p><h3>System instruction</h3><pre>{prompt.system_instruction}</pre><div className="prompt-columns"><div><h3>Input</h3><pre>{JSON.stringify(prompt.input_contract, null, 2)}</pre></div><div><h3>Structured output</h3><pre>{JSON.stringify(prompt.sample_output, null, 2)}</pre></div></div><h3>Expected JSON schema</h3><pre>{JSON.stringify(prompt.expected_json_schema, null, 2)}</pre><div className="validation-result"><span>VALIDATION RESULT</span><strong>{prompt.validation_result}</strong></div></article></div>
      </section>

      <section className="refusals"><div className="shell"><div className="section-kicker light"><span>06</span><p>Where FinTrace refuses to guess</p></div><h2>Unresolved is a feature.</h2><div className="refusal-grid">{[
        ["Insufficient filing data", "The filing names an effect but does not quantify it."],
        ["Plausible but unsupported", "The explanation sounds reasonable but is absent from the filing."],
        ["Quote cannot be validated", "A proposed quotation is not found in the supplied corpus."],
        ["Numerical gap remains", "The disclosure exists but does not bridge computed and claimed values."],
        ["Contradictory passages", "Conflicting evidence is preserved for a human instead of resolved by assumption."],
      ].map(([title, text], index) => <article key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{text}</p><strong>RESULT: UNRESOLVED</strong></article>)}</div><div className="architecture-link"><div><span>SYSTEM ARCHITECTURE</span><h3>See exactly what the LLM, Python, retrieval, validation, and human each do.</h3></div><Link href="/architecture">Open architecture page <ArrowIcon /></Link></div></div></section>

      <footer className="footer shell"><div className="brand"><span>F</span>FinTrace</div><p>Models interpret. Code calculates. Filings provide evidence.</p><span>Reverie Hacks 2026 | fictional benchmark only</span></footer>
    </main>
  );
}
