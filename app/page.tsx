"use client";

import { useEffect, useMemo, useState } from "react";

type ResultStatus = "unresolved" | "explained" | "aligned";
type Claim = { id: string; finding: string; label: string; quote: string; claimed: string; computed: string; formula: string; delta: string; source: string; status: ResultStatus; rationale: string };

const claims: Claim[] = [
  { id: "claim-growth", finding: "FT-001", label: "Organic revenue growth", quote: "Organic segment revenue grew 23 percent year over year, reflecting broad-based demand.", claimed: "23.0%", computed: "12.73%", formula: "(124 − 110) ÷ 110 × 100", delta: "10.27 pp", source: "Note 3 · Segment table", status: "unresolved", rationale: "The filing says acquired operations are excluded from organic growth, but provides no quantified acquisition effect that reconciles 12.73% to 23.0%." },
  { id: "claim-fcf", finding: "FT-002", label: "Adjusted free cash flow", quote: "We delivered record adjusted free cash flow of 85 million dollars.", claimed: "$85m", computed: "$62m", formula: "$96m CFO − $34m capex", delta: "$23m", source: "Cash-flow statement", status: "explained", rationale: "“Adjusted free cash flow excludes 23 million dollars of cash restructuring payments; the measure is operating cash flow less capital expenditures plus those payments.”" },
  { id: "claim-margin", finding: "FT-003", label: "GAAP operating margin", quote: "GAAP operating margin was approximately 13 percent.", claimed: "13.0%", computed: "12.90%", formula: "$16m operating income ÷ $124m revenue", delta: "0.10 pp", source: "Income statement", status: "aligned", rationale: "The recomputed value is within the explicit 0.5 percentage-point tolerance." },
];

const stages = [["01", "Ingest & align"], ["02", "Specialist review"], ["03", "Aggregate"], ["04", "Reconcile"], ["05", "Second pass"], ["06", "Risk memo"], ["07", "Human sign-off"]];

function StatusMark({ status }: { status: ResultStatus }) { return <span className={`status status-${status}`}><i />{status}</span>; }
function ArrowIcon() { return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 10h13M11 5l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>; }

export default function Home() {
  const [selected, setSelected] = useState(0);
  const [running, setRunning] = useState(false);
  const [complete, setComplete] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);
  const [signed, setSigned] = useState(false);
  const [memoOpen, setMemoOpen] = useState(false);
  const claim = claims[selected];

  useEffect(() => {
    if (!running) return;
    let stage = 0;
    const timer = window.setInterval(() => {
      stage += 1; setActiveStage(stage);
      if (stage >= stages.length - 1) { window.clearInterval(timer); setRunning(false); setComplete(true); }
    }, 230);
    return () => window.clearInterval(timer);
  }, [running]);

  const progress = useMemo(() => Math.max(0, ((activeStage + 1) / stages.length) * 100), [activeStage]);
  function runAnalysis() { if (running) return; setComplete(false); setSigned(false); setActiveStage(0); setRunning(true); document.querySelector("#workspace")?.scrollIntoView({ behavior: "smooth", block: "start" }); }

  return (
    <main>
      <nav className="nav shell" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="FinTrace home"><span>F</span>FinTrace</a>
        <div className="nav-links"><a href="#method">Method</a><a href="#benchmark">Benchmark</a><a href="#workspace">Live demo</a></div>
        <span className="public-pill"><i /> Public demo</span>
      </nav>

      <section className="hero shell" id="top">
        <div className="hero-copy">
          <p className="eyebrow">Evidence-first financial forensics</p>
          <h1>What they said.<br />What they filed.<br /><em>What the math says.</em></h1>
          <p className="lede">FinTrace turns earnings-call claims into traceable calculations, then searches the full filing for explanations before anything reaches an analyst.</p>
          <div className="hero-actions"><button className="primary" onClick={runAnalysis}>Run the investigation <ArrowIcon /></button><a className="text-link" href="#method">See the seven-stage method</a></div>
          <p className="disclaimer">Fictional demonstration data · No accusation or inference of intent</p>
        </div>
        <div className="hero-art" aria-label="A comparison between an executive claim and filed values">
          <div className="paper paper-back"><span>FORM 10-Q</span><strong>Filed evidence</strong></div>
          <div className="paper paper-front"><div className="paper-head"><span>EARNINGS CALL</span><span>Q2 · FY26</span></div><blockquote>“Organic segment revenue grew <mark>23 percent</mark> year over year.”</blockquote><div className="redline"><span>Recomputed</span><strong>12.73%</strong><small>−10.27 pp</small></div></div>
          <svg className="trace-line" viewBox="0 0 420 180" aria-hidden="true"><path d="M10 134 C90 35 205 175 410 20" /><circle cx="10" cy="134" r="4" /><circle cx="410" cy="20" r="4" /></svg>
        </div>
      </section>

      <section className="method" id="method"><div className="shell">
        <div className="section-kicker"><span>01</span><p>Designed for evidence, not vibes</p></div>
        <div className="section-heading"><h2>Every flag must survive<br />a second look.</h2><p>A model can notice. Code must calculate. The filing gets the last word—and a human signs off.</p></div>
        <div className="stage-grid">{stages.map(([number, name], index) => <div className="stage" key={number}><span>{number}</span><strong>{name}</strong>{index < stages.length - 1 && <b aria-hidden="true">→</b>}</div>)}</div>
      </div></section>

      <section className="workspace shell" id="workspace">
        <div className="section-kicker"><span>02</span><p>Interactive case file</p></div>
        <div className="workspace-head"><div><h2>Northstar Mobility</h2><p>Q2 FY2026 · fictional demonstration</p></div><button className={`run-button ${running ? "is-running" : ""}`} onClick={runAnalysis} disabled={running}><span>{running ? "Tracing evidence…" : complete ? "Run again" : "Run analysis"}</span><ArrowIcon /></button></div>
        <div className="progress-wrap" aria-live="polite"><div className="progress-label"><span>{running ? `Stage ${activeStage + 1} of 7 · ${stages[activeStage]?.[1]}` : complete ? "Analysis complete · awaiting human sign-off" : "Ready to trace three claims"}</span><span>{running ? `${Math.round(progress)}%` : complete ? "3 / 3" : "0 / 3"}</span></div><div className="progress"><i style={{ width: `${running || complete ? progress : 0}%` }} /></div></div>

        <div className="case-grid">
          <aside className="claims-list" aria-label="Claims"><div className="panel-label">Transcript claims <span>3</span></div>{claims.map((item, index) => <button key={item.id} className={`claim-tab ${selected === index ? "active" : ""}`} onClick={() => setSelected(index)}><span>{item.finding}</span><strong>{item.label}</strong><small>Claimed {item.claimed}</small><StatusMark status={item.status} /></button>)}</aside>
          <article className="evidence-panel"><div className="panel-label">Evidence trace <span>{claim.finding}</span></div><p className="quote-label">Management statement</p><blockquote>“{claim.quote}”</blockquote><div className="source-row"><span>Source</span><strong>Q2 earnings call · prepared remarks</strong></div><div className="connector"><span>checked against</span></div><div className="filing-card"><div><span>Filed source</span><strong>{claim.source}</strong></div><span className="verified">✓ located</span></div><p className="rationale">{claim.rationale}</p></article>
          <aside className="ledger"><div className="panel-label">Calculation ledger <span>deterministic</span></div><div className="ledger-values"><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Computed</span><strong>{claim.computed}</strong></div></div><div className="formula"><span>Formula</span><code>{claim.formula}</code></div><div className="delta"><span>Absolute gap</span><strong>{claim.delta}</strong></div><div className="verdict"><span>Second-pass verdict</span><StatusMark status={claim.status} /></div><button className="memo-button" onClick={() => setMemoOpen((value) => !value)}>{memoOpen ? "Hide analyst memo" : "Open analyst memo"}<ArrowIcon /></button></aside>
        </div>

        {memoOpen && <div className="memo" role="region" aria-label="Analyst memo"><div><span>ANALYST MEMO · {claim.finding}</span><StatusMark status={claim.status} /></div><p>{claim.status === "unresolved" ? "The stated organic growth rate cannot be reproduced from the cited filing values. The filing names acquisition effects but does not quantify them, so the 10.27 percentage-point gap remains unresolved. Escalate for source-document review; do not infer intent." : claim.status === "explained" ? "The initial gap is fully reconciled by a specifically disclosed $23 million restructuring adjustment. Preserve the quotation and mark this finding explained." : "The claim agrees with the filed values within the declared calculation tolerance. No escalation is recommended."}</p></div>}
        <div className="signoff"><div><span className="signoff-icon">{signed ? "✓" : "07"}</span><div><strong>{signed ? "Review signed" : "Human judgment stays in the loop"}</strong><p>{signed ? "Demo Analyst · evidence trail preserved" : "FinTrace describes inconsistencies. An analyst decides what they mean."}</p></div></div><button className={signed ? "signed" : ""} onClick={() => setSigned(true)} disabled={!complete || signed}>{signed ? "Signed off" : complete ? "Sign off demo" : "Run analysis first"}</button></div>
      </section>

      <section className="benchmark" id="benchmark"><div className="shell benchmark-inner">
        <div className="benchmark-copy"><div className="section-kicker light"><span>03</span><p>Evaluation-ready by design</p></div><h2>Measure the workflow,<br />not the theater.</h2><p>Every output has a citation, calculation, prompt version, decision state, and integrity digest—so reviewers can reproduce the result.</p><small>Illustrative starter targets; replace with adjudicated cases before making performance claims.</small></div>
        <div className="scorecard"><div className="score-head"><span>Illustrative evaluation design</span><span>BASELINE → FINTRACE</span></div><div className="score-row"><strong>Citation coverage</strong><div><i style={{ width: "28%" }} /><em style={{ width: "96%" }} /></div><span>28 → 96%</span></div><div className="score-row"><strong>Reproducible math</strong><div><i style={{ width: "16%" }} /><em style={{ width: "100%" }} /></div><span>16 → 100%</span></div><div className="score-row"><strong>Explanation check</strong><div><i style={{ width: "12%" }} /><em style={{ width: "92%" }} /></div><span>12 → 92%</span></div><div className="score-foot"><span><i className="base-dot" /> Naive prompt</span><span><i className="trace-dot" /> FinTrace target</span></div></div>
      </div></section>

      <footer className="footer shell"><div className="brand"><span>F</span>FinTrace</div><p>Executive claims checked against filed numbers.</p><span>Built for Reverie Hacks 2026 · Fictional demo</span></footer>
    </main>
  );
}
