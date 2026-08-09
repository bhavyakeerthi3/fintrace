"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import evaluation from "./evaluation-data.json";
import promptData from "./prompt-data.json";

type ResultStatus = "unresolved" | "explained" | "aligned";
type Claim = {
  id: string; finding: string; label: string; quote: string; claimed: string; computed: string;
  formula: string; delta: string; source: string; status: ResultStatus; rationale: string;
  passages: string[]; candidate: string; validation: string;
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
  },
  {
    id: "claim-margin", finding: "FT-003", label: "GAAP operating margin",
    quote: "GAAP operating margin was approximately 13 percent.",
    claimed: "13.00%", computed: "12.90%", formula: "$16m operating income / $124m revenue", delta: "0.10 pp",
    source: "Income statement", status: "aligned",
    rationale: "The recomputed value falls inside the declared 0.5 percentage-point tolerance, so no finding is escalated.",
    passages: ["Income statement p. 7: operating income $16m; revenue $124m."],
    candidate: "No explanation is required because the calculation is within tolerance.", validation: "Deterministic tolerance check PASS",
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
        <div className="section-kicker"><span>02</span><p>Judge demo | three outcome types</p></div>
        <div className="workspace-head"><div><h2>Northstar Mobility</h2><p>Q2 FY2026 | controlled fictional demonstration</p></div><button className={`run-button ${running ? "is-running" : ""}`} onClick={runDemo} disabled={running}><span>{running ? "Tracing evidence..." : complete ? "Run Judge Demo again" : "Run Judge Demo"}</span><ArrowIcon /></button></div>
        <div className="progress-wrap" aria-live="polite"><div className="progress-label"><span>{running ? `Stage ${activeStage + 1} of ${stages.length} | ${stages[activeStage]?.[1]}` : complete ? "Three cases complete | awaiting human sign-off" : "Ready: unresolved + explained + within tolerance"}</span><span>{running ? `${Math.round(progress)}%` : complete ? "3 / 3" : "0 / 3"}</span></div><div className="progress"><i style={{ width: `${running || complete ? progress : 0}%` }} /></div></div>

        <div className="case-grid">
          <aside className="claims-list" aria-label="Claims"><div className="panel-label">Transcript claims <span>3</span></div>{claims.map((item, index) => <button key={item.id} className={`claim-tab ${selected === index ? "active" : ""}`} onClick={() => { setSelected(index); setWhyOpen(false); }}><span>{item.finding}</span><strong>{item.label}</strong><small>Claimed {item.claimed}</small><StatusMark status={item.status} /></button>)}</aside>
          <article className="evidence-panel"><div className="panel-label">Evidence trace <span>{claim.finding}</span></div><p className="quote-label">Management statement</p><blockquote>&quot;{claim.quote}&quot;</blockquote><div className="source-row"><span>Source</span><strong>Q2 earnings call | prepared remarks</strong></div><div className="connector"><span>checked against</span></div><div className="filing-card"><div><span>Filed source</span><strong>{claim.source}</strong></div><span className="verified">{claim.validation}</span></div><p className="rationale">{claim.rationale}</p></article>
          <aside className="ledger"><div className="panel-label">Calculation ledger <span>deterministic</span></div><div className="ledger-values"><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Computed</span><strong>{claim.computed}</strong></div></div><div className="formula"><span>Formula</span><code>{claim.formula}</code></div><div className="delta"><span>Absolute gap</span><strong>{claim.delta}</strong></div><div className="verdict"><span>Final result</span><StatusMark status={claim.status} /></div><button className="memo-button" onClick={() => setWhyOpen((value) => !value)}>{whyOpen ? "Hide Why panel" : "Why this result?"}<ArrowIcon /></button></aside>
        </div>

        {whyOpen && <div className="why-panel" role="region" aria-label="Why this result"><div className="why-head"><span>WHY {claim.status.toUpperCase()}?</span><StatusMark status={claim.status} /></div>{claim.status === "explained" ? <><h3>Disclosure found</h3><blockquote>&quot;{claim.candidate}&quot;</blockquote><dl><div><dt>Connection</dt><dd>The disclosed $23m adjustment exactly bridges the $62m filed base to the $85m claim.</dd></div><div><dt>Quote validation</dt><dd>PASS | exact filing match and direct relationship</dd></div></dl></> : claim.status === "unresolved" ? <><div className="why-math"><div><span>Computed</span><strong>{claim.computed}</strong></div><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Difference</span><strong>{claim.delta}</strong></div></div><h3>Filing explanations reviewed</h3><p>Currency | Acquisition | Divestiture | Accounting policy | Segment presentation</p><p><b>Result:</b> No filing disclosure directly reconciles the difference.</p></> : <><div className="why-math"><div><span>Computed</span><strong>{claim.computed}</strong></div><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Difference</span><strong>{claim.delta}</strong></div></div><p><b>Result:</b> Difference is inside the declared 0.5 percentage-point tolerance. No escalation is created.</p></>}</div>}

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
        <div className="evaluation-head"><div><h2>Same cases. Different workflow.</h2><p>{evaluation.case_count} fictional cases and {evaluation.finding_count} adjudicated findings, executed with the {evaluation.provider} adapter. Results apply only to this suite.</p></div><div className="headline-scores"><div><span>Single prompt</span><strong>{baseline.overall_score}%</strong><small>{baseline.correct_classifications}/{baseline.finding_count} correct</small></div><div><span>Full FinTrace</span><strong>{fintrace.overall_score}%</strong><small>{fintrace.correct_classifications}/{fintrace.finding_count} correct</small></div></div></div>
        <div className="metric-grid">{[
          ["Correct classifications", baseline.classification_accuracy, fintrace.classification_accuracy],
          ["Unsupported explanations", baseline.unsupported_explanations, fintrace.unsupported_explanations],
          ["Numerical accuracy", baseline.numerical_reconciliation_accuracy, fintrace.numerical_reconciliation_accuracy],
          ["Quote validity", baseline.citation_quote_validity, fintrace.citation_quote_validity],
          ["Unresolved accuracy", baseline.unresolved_item_accuracy, fintrace.unresolved_item_accuracy],
        ].map(([label, base, full]) => <div className="metric-card" key={String(label)}><span>{label}</span><div><small>Single</small><strong>{base}{label === "Unsupported explanations" ? "" : "%"}</strong></div><div><small>FinTrace</small><strong>{full}{label === "Unsupported explanations" ? "" : "%"}</strong></div></div>)}</div>
        <div className="ablation"><div className="panel-label">Prompt ablation | measured, not assumed <span>suite v{evaluation.suite_version}</span></div><table><thead><tr><th>Workflow</th><th>Correct</th><th>Unsupported</th><th>Numeric accuracy</th><th>Overall</th></tr></thead><tbody>{Object.entries(evaluation.ablations).map(([name, metrics]) => <tr key={name}><td>{name.replaceAll("_", " ")}</td><td>{metrics.correct_classifications}/{metrics.finding_count}</td><td>{metrics.unsupported_explanations}</td><td>{metrics.numerical_reconciliation_accuracy}%</td><td>{metrics.overall_score}%</td></tr>)}</tbody></table></div>
        <p className="benchmark-note">The score is computed from classification accuracy, false-positive rate, unsupported-explanation rate, numerical accuracy, citation validity, and unresolved-item accuracy. This controlled suite demonstrates component behavior; it is not a production accuracy claim.</p>
      </div></section>

      <section className="inspector shell" id="prompts">
        <div className="section-kicker"><span>04</span><p>Prompt Inspector</p></div>
        <div className="section-heading"><h2>Inspect every model contract.</h2><p>Judges can see the version, instruction, input contract, expected schema, and sample output. Secrets never enter this interface.</p></div>
        <div className="inspector-grid"><aside>{promptData.map((item, index) => <button className={promptIndex === index ? "active" : ""} onClick={() => setPromptIndex(index)} key={item.id}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item.stage.replaceAll("_", " ")}</strong><small>v{item.version}</small></button>)}</aside><article><div className="prompt-meta"><div><span>Stage</span><strong>{prompt.stage.replaceAll("_", " ")}</strong></div><div><span>Model</span><strong>{prompt.stage === "aggregator" ? "deterministic demo" : "provider selected"}</strong></div><div><span>Prompt version</span><strong>{prompt.version}</strong></div></div><h3>System instruction</h3><pre>{prompt.system_instruction}</pre><div className="prompt-columns"><div><h3>Input</h3><pre>{JSON.stringify(prompt.input_contract, null, 2)}</pre></div><div><h3>Expected JSON schema</h3><pre>{JSON.stringify(prompt.expected_json_schema, null, 2)}</pre></div></div><h3>Sample output</h3><pre>{JSON.stringify(prompt.sample_output, null, 2)}</pre></article></div>
      </section>

      <section className="refusals"><div className="shell"><div className="section-kicker light"><span>05</span><p>Where FinTrace refuses to guess</p></div><h2>Unresolved is a feature.</h2><div className="refusal-grid">{[
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
