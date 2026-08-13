"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import evaluation from "./evaluation-data.json";
import promptData from "./prompt-data.json";

type ResultStatus = "unresolved" | "explained" | "aligned";
type Claim = {
  id: string; finding: string; label: string; quote: string; claimed: string; computed: string;
  formula: string; delta: string; source: string; status: ResultStatus; rationale: string;
  passages: string[]; candidate: string; validation: string; demoLabel: string; explanation: string;
  baselineStatus: ResultStatus; baselineExcerpt: string; baselineCorrect: boolean; comparisonGate: string;
};

type TourStep = {
  title: string; body: string; target: string; claimIndex?: number; promptIndex?: number; showWhy?: boolean;
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
    baselineStatus: "unresolved", baselineCorrect: true,
    baselineExcerpt: "To resolve this inconsistency, it would be necessary to review the calculation of organic growth in more detail.",
    comparisonGate: "No quantified filing disclosure bridges the 10.27 percentage-point gap.",
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
    baselineStatus: "explained", baselineCorrect: true,
    baselineExcerpt: "85 million dollars - 23 million dollars = 62 million dollars.",
    comparisonGate: "Exact quote + direct relationship + $23m numerical reconciliation all pass.",
  },
  {
    id: "claim-overlap", finding: "B12-F2", label: "Non-reconciling cash-flow adjustment",
    quote: "Adjusted free cash flow was 45 million dollars.",
    claimed: "$45m", computed: "$40m", formula: "$45m claim - $40m filing-derived value", delta: "$5m",
    source: "Non-GAAP table p. 39", status: "unresolved",
    rationale: "The passage supplies only a $3 million cash payment for a $5 million free-cash-flow gap. $40 million plus $3 million is $43 million, not $45 million; the passage's $8 million add-back explains EBITDA, not this claim.",
    passages: ["Non-GAAP table p. 39: filing-derived adjusted free cash flow $40m.", "The restructuring program required $3m of cash payments; its separate $8m add-back applies to adjusted EBITDA."],
    candidate: "Adjusted EBITDA adds back 8 million dollars of restructuring expense; the same program required 3 million dollars of cash payments.", validation: "Exact quote PASS | direct relationship FAIL | numerical reconciliation FAIL",
    demoLabel: "Case 3 | Baseline failure", explanation: "$3m disclosure does not reconcile a $5m gap",
    baselineStatus: "explained", baselineCorrect: false,
    baselineExcerpt: "The cash payments of $3 million required for the restructuring program may have reduced the Adjusted Free Cash Flow.",
    comparisonGate: "The quote is real, but $40m + $3m = $43m, not the claimed $45m.",
  },
];

const stages = [
  ["01", "Ingest & align"], ["02", "Specialist calls"], ["03", "Aggregate & dedupe"],
  ["04", "Code calculation"], ["05", "Filing retrieval"], ["06", "Second pass & validate"],
  ["07", "Analyst review"], ["08", "Human sign-off"],
];

const tourSteps: TourStep[] = [
  { title: "Recompute the first claim", body: "Start with the 23% growth claim. Python derives 12.73% from the filed values before any explanation is considered.", target: "#workspace", claimIndex: 0 },
  { title: "Accept a supported explanation", body: "Case two demonstrates a valid result: the exact $23m disclosure bridges $62m to $85m and the filing quote validates.", target: "#workspace", claimIndex: 1 },
  { title: "Reject a plausible mismatch", body: "Case three is the decisive baseline failure. A $3m cash item cannot explain a $5m gap, so FinTrace keeps it unresolved.", target: "#workspace", claimIndex: 2, showWhy: true },
  { title: "Read the measured comparison", body: "The two live runs stay separate: 10/13 for the single prompt and 13/13 for the full workflow on this controlled suite.", target: "#evaluation" },
  { title: "Inspect the prompt contracts", body: "Every scope, instruction, model setting, input contract, output schema, and validation result is visible.", target: "#prompts", promptIndex: 0 },
  { title: "Try deterministic math", body: "Change the filed values or claimed percentage. The browser recomputes the result locally without an LLM call.", target: "#calculator" },
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
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [tourActive, setTourActive] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [tourSoundEnabled, setTourSoundEnabled] = useState(true);
  const [priorRevenue, setPriorRevenue] = useState("110");
  const [currentRevenue, setCurrentRevenue] = useState("124");
  const [claimedGrowth, setClaimedGrowth] = useState("23");
  const claim = claims[selected];
  const prompt = promptData[promptIndex];
  const baseline = evaluation.live_single_prompt.metrics;
  const fintrace = evaluation.live_run.metrics;
  const historicalAblation = evaluation.historical_ablation;
  const correctGain = fintrace.correct_classifications - baseline.correct_classifications;
  const pointGain = (fintrace.classification_accuracy - baseline.classification_accuracy).toFixed(1);
  const priorValue = Number(priorRevenue);
  const currentValue = Number(currentRevenue);
  const claimedValue = Number(claimedGrowth);
  const calculatorValid = Number.isFinite(priorValue) && priorValue !== 0 && Number.isFinite(currentValue) && Number.isFinite(claimedValue);
  const calculatedGrowth = calculatorValid ? ((currentValue - priorValue) / priorValue) * 100 : 0;
  const calculatedGap = calculatorValid ? claimedValue - calculatedGrowth : 0;
  const audioContextRef = useRef<AudioContext | null>(null);

  function playTourClick(force = false) {
    if (!tourSoundEnabled && !force) return;
    if (!("AudioContext" in window)) return;

    const context = audioContextRef.current ?? new window.AudioContext();
    audioContextRef.current = context;
    if (context.state === "suspended") void context.resume().catch(() => undefined);

    const duration = 0.035;
    const frameCount = Math.floor(context.sampleRate * duration);
    const buffer = context.createBuffer(1, frameCount, context.sampleRate);
    const samples = buffer.getChannelData(0);
    for (let index = 0; index < frameCount; index += 1) {
      const decay = 1 - index / frameCount;
      samples[index] = (Math.random() * 2 - 1) * decay * decay;
    }

    const source = context.createBufferSource();
    const filter = context.createBiquadFilter();
    const gain = context.createGain();
    filter.type = "bandpass";
    filter.frequency.value = 1700;
    filter.Q.value = 0.8;
    gain.gain.setValueAtTime(0.055, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + duration);
    try {
      source.buffer = buffer;
      source.connect(filter).connect(gain).connect(context.destination);
      source.start();
      source.stop(context.currentTime + duration);
    } catch {
      // Audio is optional; tour navigation must still work if playback is unavailable.
    }
  }

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

  useEffect(() => () => {
    if (audioContextRef.current) void audioContextRef.current.close().catch(() => undefined);
  }, []);

  const progress = Math.max(0, ((activeStage + 1) / stages.length) * 100);
  function runDemo() {
    if (running) return;
    setMobileNavOpen(false);
    setComplete(false); setSigned(false); setActiveStage(0); setRunning(true);
    document.querySelector("#workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function applyTourStep(index: number) {
    const next = tourSteps[index];
    setTourStep(index);
    if (next.claimIndex !== undefined) setSelected(next.claimIndex);
    if (next.promptIndex !== undefined) setPromptIndex(next.promptIndex);
    setWhyOpen(Boolean(next.showWhy));
    window.requestAnimationFrame(() => document.querySelector(next.target)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  function startTour() {
    playTourClick();
    setTourActive(true);
    setMobileNavOpen(false);
    applyTourStep(0);
    setComplete(false); setSigned(false); setActiveStage(0); setRunning(true);
  }

  function moveTour(direction: -1 | 1) {
    playTourClick();
    const next = tourStep + direction;
    if (next < 0) return;
    if (next >= tourSteps.length) {
      setTourActive(false);
      return;
    }
    applyTourStep(next);
  }

  function toggleTourSound() {
    playTourClick(true);
    setTourSoundEnabled((enabled) => !enabled);
  }

  function closeTour() {
    playTourClick();
    setTourActive(false);
  }

  return (
    <main>
      <div className="hero-surface">
        <nav className="nav shell" aria-label="Primary navigation">
          <a className="brand" href="#top" aria-label="FinTrace home"><span>F</span>FINTRACE</a>
          <button className="mobile-menu-button" type="button" aria-expanded={mobileNavOpen} aria-label="Toggle navigation" onClick={() => setMobileNavOpen((open) => !open)}><i /><i /></button>
          <div className={`nav-links ${mobileNavOpen ? "open" : ""}`}><a href="#method" onClick={() => setMobileNavOpen(false)}>Method</a><a href="#workspace" onClick={() => setMobileNavOpen(false)}>Judge demo</a><a href="#evaluation" onClick={() => setMobileNavOpen(false)}>Evaluation</a><a href="#prompts" onClick={() => setMobileNavOpen(false)}>Prompts</a><a href="#calculator" onClick={() => setMobileNavOpen(false)}>Calculator</a><a href="#architecture" onClick={() => setMobileNavOpen(false)}>Architecture</a></div>
          <button className="nav-cta" onClick={runDemo}>Run demo <ArrowIcon /></button>
        </nav>

        <section className="hero shell" id="top">
          <div className="hero-copy">
            <p className="eyebrow">Prompt-engineering research prototype</p>
            <h1><span>What they said.</span><span>What they filed.</span><em>What the math says.</em></h1>
            <p className="lede">Specialist models find candidate issues. Python recomputes every number. The full filing gets a second look. Exact quotes are validated before a human decides.</p>
            <div className="hero-actions"><button className="primary" onClick={startTour}>Start 90-sec tour <ArrowIcon /></button><button className="text-link tour-link" type="button" onClick={runDemo}>Open judge demo</button><a className="text-link" href="#evaluation">See benchmark</a></div>
            <p className="disclaimer">12 controlled cases · 13 findings · live model comparison</p>
          </div>
          <div className="hero-docs" aria-hidden="true">
            <div className="paper paper-back"><span>FORM 10-Q</span></div>
            <div className="paper paper-front">
              <div className="paper-head"><span>EARNINGS CALL</span><span>Q2&nbsp; | &nbsp;FY26</span></div>
              <blockquote>&quot;Organic segment revenue<br />grew <mark>23 percent</mark> year over<br />year.&quot;</blockquote>
              <div className="paper-result"><div><span>PYTHON RECOMPUTED</span><small>-10.27 pp</small></div><strong>12.73%</strong></div>
            </div>
            <svg className="paper-trace" viewBox="0 0 560 170" role="presentation"><path d="M10 145 C90 45 155 95 245 105 S430 112 550 18" /><circle cx="10" cy="145" r="6" /><circle cx="550" cy="18" r="6" /></svg>
          </div>
        </section>
      </div>

      <section className="method" id="method"><div className="shell">
        <div className="section-kicker"><span>01</span><p>Models interpret. Code calculates.</p></div>
        <div className="section-heading"><h2>Every explanation must<br />survive validation.</h2><p>Specific filing evidence + direct connection + exact quote + numerical reconciliation = explained. Anything less remains unresolved.</p></div>
        <div className="stage-grid">{stages.map(([number, name], index) => <div className="stage" key={number}><span>{number}</span><strong>{name}</strong>{index < stages.length - 1 && <b aria-hidden="true">-&gt;</b>}</div>)}</div>
      </div></section>

      <section className="workspace shell" id="workspace">
        <div className="section-kicker"><span>02</span><p>Judge Demo mode | three decisive cases</p></div>
        <div className="workspace-head"><div><span className="mode-badge">JUDGE DEMO</span><h2>Northstar Mobility</h2><p>Q2 FY2026 | controlled fictional demonstration</p></div><button className={`run-button ${running ? "is-running" : ""}`} onClick={runDemo} disabled={running}><span>{running ? "Tracing evidence..." : complete ? "Run Judge Demo again" : "Run Judge Demo"}</span><ArrowIcon /></button></div>
        <div className="demo-case-strip">{claims.map((item, index) => <button key={item.id} className={selected === index ? "active" : ""} onClick={() => setSelected(index)}><span>0{index + 1}</span><strong>{item.demoLabel.split(" | ")[1]}</strong><small>{index === 0 ? "23.00% claimed vs 12.73% computed" : index === 1 ? "Disclosure + quote reconcile $23m" : "Single prompt accepts $3m for a $5m gap"}</small></button>)}</div>
        <div className="progress-wrap" aria-live="polite"><div className="progress-label"><span>{running ? `Stage ${activeStage + 1} of ${stages.length} | ${stages[activeStage]?.[1]}` : complete ? "Three cases complete | awaiting human sign-off" : "Ready: unresolved + explained + within tolerance"}</span><span>{running ? `${Math.round(progress)}%` : complete ? "3 / 3" : "0 / 3"}</span></div><div className="progress"><i style={{ width: `${running || complete ? progress : 0}%` }} /></div></div>

        <div className="case-grid">
          <aside className="claims-list" aria-label="Claims"><div className="panel-label">Judge cases <span>3</span></div>{claims.map((item, index) => <button key={item.id} className={`claim-tab ${selected === index ? "active" : ""}`} onClick={() => { setSelected(index); setWhyOpen(false); }}><span>{item.finding}</span><strong>{item.label}</strong><small>Claimed {item.claimed}</small><StatusMark status={item.status} /></button>)}</aside>
          <article className="evidence-panel"><div className="panel-label">Evidence trace <span>{claim.demoLabel}</span></div><p className="quote-label">Management statement</p><blockquote>&quot;{claim.quote}&quot;</blockquote><div className="source-row"><span>Source</span><strong>Q2 earnings call | prepared remarks</strong></div><div className="connector"><span>checked against</span></div><div className="filing-card"><div><span>Filed source</span><strong>{claim.source}</strong></div><span className="verified">{claim.validation}</span></div><div className="verdict-comparison"><div className="comparison-title"><span>SAME EVIDENCE | TWO METHODS</span><strong>Expected: {claim.status}</strong></div><div className="comparison-columns"><article><div><span>LIVE SINGLE PROMPT</span><b className={claim.baselineCorrect ? "grade-pass" : "grade-fail"}>{claim.baselineCorrect ? "CORRECT" : "INCORRECT"}</b></div><StatusMark status={claim.baselineStatus} /><blockquote>&quot;{claim.baselineExcerpt}&quot;</blockquote></article><article><div><span>FULL FINTRACE</span><b className="grade-pass">CORRECT</b></div><StatusMark status={claim.status} /><p>{claim.comparisonGate}</p></article></div></div><p className="rationale">{claim.rationale}</p></article>
          <aside className="ledger"><div className="panel-label">DETERMINISTIC CODE <span>NOT AN LLM CALL</span></div><div className="ledger-values"><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Computed</span><strong>{claim.computed}</strong></div></div><div className="formula"><span>Formula</span><code>{claim.formula}</code></div><div className="delta"><span>Difference</span><strong>{claim.delta}</strong></div><div className="filing-explanation"><span>Filing explanation</span><strong>{claim.explanation}</strong></div><div className="verdict"><span>Final result</span><StatusMark status={claim.status} /></div><button className="memo-button" onClick={() => setWhyOpen((value) => !value)}>{whyOpen ? "Hide Why panel" : "Why this result?"}<ArrowIcon /></button></aside>
        </div>

        {whyOpen && <div className="why-panel" role="region" aria-label="Why this result"><div className="why-head"><span>WHY {claim.status.toUpperCase()}?</span><StatusMark status={claim.status} /></div>{claim.status === "explained" ? <><h3>Disclosure found</h3><blockquote>&quot;{claim.candidate}&quot;</blockquote><dl><div><dt>Connection</dt><dd>The disclosed $23m adjustment exactly bridges the $62m filed base to the $85m claim.</dd></div><div><dt>Quote validation</dt><dd>PASS | exact filing match and direct relationship</dd></div></dl></> : !claim.baselineCorrect ? <><div className="why-math"><div><span>Computed</span><strong>{claim.computed}</strong></div><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Difference</span><strong>{claim.delta}</strong></div></div><h3>Why the plausible explanation fails</h3><blockquote>&quot;{claim.candidate}&quot;</blockquote><p>The quote is real, but its cash-flow amount is $3m while the gap is $5m. $40m + $3m = $43m, not $45m. The separate $8m add-back applies to adjusted EBITDA.</p><p><b>Result:</b> The live single prompt says EXPLAINED; FinTrace&apos;s direct-relationship and numerical-reconciliation gates keep B12-F2 UNRESOLVED.</p></> : <><div className="why-math"><div><span>Computed</span><strong>{claim.computed}</strong></div><div><span>Claimed</span><strong>{claim.claimed}</strong></div><div><span>Difference</span><strong>{claim.delta}</strong></div></div><h3>Filing explanations reviewed</h3><p>Currency | Acquisition | Divestiture | Accounting policy | Segment presentation</p><p><b>Result:</b> No filing disclosure directly reconciles the difference.</p></>}</div>}

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
        <div className="evaluation-head"><div><h2>Same evidence. Different controls.</h2><p>{evaluation.case_count} controlled fictional cases containing {evaluation.finding_count} independently evaluated findings. Both headline runs used {evaluation.live_single_prompt.model} at temperature {evaluation.live_single_prompt.temperature.toFixed(1)}.</p><div className="lift-pills"><span>+{correctGain} correct findings</span><span>+{pointGain} percentage points</span></div></div><div className="headline-scores"><div><span>Live Single Prompt</span><strong>{formatPct(baseline.classification_accuracy)}%</strong><small>{baseline.correct_classifications} / {baseline.finding_count} correct</small></div><div><span>Live Full FinTrace</span><strong>{formatPct(fintrace.classification_accuracy)}%</strong><small>{fintrace.correct_classifications} / {fintrace.finding_count} correct</small></div></div></div>
        <div className="run-facts"><div className="run-facts-head"><div><span>RECORDED FULL-PIPELINE RUN</span><strong>Audit the result, not just the headline.</strong></div><small>Token usage and estimated cost were not persisted for this run.</small></div><div className="run-facts-grid"><div><span>Model</span><strong>{evaluation.live_run.model}</strong></div><div><span>Temperature</span><strong>{evaluation.live_run.temperature.toFixed(1)}</strong></div><div><span>Timestamp</span><strong>{evaluation.live_run.run_timestamp.slice(0, 10)} UTC</strong></div><div><span>LLM calls</span><strong>{evaluation.live_run.api_call_count} batched calls</strong></div><div><span>Logged retries</span><strong>{evaluation.live_run.retry_event_count} HTTP 429 retries</strong></div><div><span>Benchmark scope</span><strong>{evaluation.case_count} cases | {evaluation.finding_count} findings</strong></div></div><div className="artifact-actions"><a href="/downloads/benchmark" download>Benchmark JSON</a><a href="/downloads/single-prompt" download>Raw baseline JSON</a><a href="/downloads/sample-report" download>Sample report PDF</a><a href="/fintrace-ml-workflow.svg" target="_blank" rel="noreferrer">Workflow diagram</a><a href="/downloads/documentation" download>Documentation</a></div></div>
        <div className="metric-grid">{[
          ["Classification accuracy", baseline.classification_accuracy, fintrace.classification_accuracy, "%"],
          ["Unsupported-explanation count", baseline.unsupported_explanations, fintrace.unsupported_explanations, ""],
          ["Unresolved-item accuracy", baseline.unresolved_item_accuracy, fintrace.unresolved_item_accuracy, "%"],
          ["False-positive count", baseline.false_positives, fintrace.false_positives, ""],
        ].map(([label, base, full, suffix]) => <div className="metric-card" key={String(label)}><span>{label}</span><div><small>Single</small><strong>{suffix === "%" ? `${formatPct(Number(base))}%` : base}</strong></div><div><small>FinTrace</small><strong>{suffix === "%" ? `${formatPct(Number(full))}%` : full}</strong></div></div>)}</div>
        <div className="ablation"><div className="panel-label">Live comparison | separately graded raw outputs <span>suite v{evaluation.suite_version}</span></div><table><thead><tr><th>Workflow</th><th>Correct</th><th>Classification accuracy</th><th>Unsupported explanations</th><th>Unresolved-item accuracy</th><th>False positives</th></tr></thead><tbody><tr><td>live single prompt</td><td>{baseline.correct_classifications}/{baseline.finding_count}</td><td>{formatPct(baseline.classification_accuracy)}%</td><td>{baseline.unsupported_explanations}</td><td>{baseline.correct_unresolved_items}/{baseline.expected_unresolved_items} ({formatPct(baseline.unresolved_item_accuracy)}%)</td><td>{baseline.false_positives}</td></tr><tr><td>live full FinTrace</td><td>{fintrace.correct_classifications}/{fintrace.finding_count}</td><td>{formatPct(fintrace.classification_accuracy)}%</td><td>{fintrace.unsupported_explanations}</td><td>{fintrace.correct_unresolved_items}/{fintrace.expected_unresolved_items} ({formatPct(fintrace.unresolved_item_accuracy)}%)</td><td>{fintrace.false_positives}</td></tr></tbody></table></div>
        <p className="benchmark-note"><b>Reproducible formula:</b> classification accuracy = correct classifications / {evaluation.finding_count} findings x 100. Integrity checks verified {evaluation.integrity_checks.percentages_checked} percentage calculations before this artifact was generated. Results are limited to this controlled fictional benchmark and are not a claim of general model performance.</p>
        <details className="metric-clarification"><summary>Why older results showed 55.6, 61.5%, and 74.9</summary><p>55.6 and 74.9 are composite control-index points from the deterministic ablation. The earlier 61.5% was also produced by that simulated ablation, not a live single-prompt call. The current live single-prompt measurement is {formatPct(baseline.classification_accuracy)}%. Historical formula: {historicalAblation.composite_control_index_formula}.</p></details>
      </div></section>

      <section className="single-prompt"><div className="shell"><div className="section-kicker light"><span>04</span><p>Why not a single prompt?</p></div><div className="section-heading single-prompt-heading"><h2>More steps.<br />Better evidence.</h2><p>The comparison is not about adding complexity for its own sake. Each FinTrace stage owns one check that a broad prompt can skip: calculation, retrieval, relevance, quotation, reconciliation, or human judgment.</p></div><div className="single-prompt-grid"><article><span>LIVE SINGLE PROMPT</span><h2>Can identify a plausible explanation.</h2><p>In this run it missed one exact acquisition explanation, flagged one within-tolerance case, and accepted one adjustment that did not reconcile numerically.</p></article><article><span>FINTRACE</span><h2>Adds explicit gates.</h2><ul><li>Requires deterministic calculation</li><li>Retrieves filing evidence</li><li>Requires direct relevance</li><li>Validates the quotation</li><li>Preserves unresolved cases</li><li>Requires human review</li></ul></article></div><p className="benchmark-note">This comparison describes one recorded run on a controlled fictional benchmark. It does not claim that every multi-step workflow is always better.</p></div></section>

      <section className="calculator-section" id="calculator"><div className="shell"><div className="section-kicker"><span>05</span><p>Try deterministic calculation</p></div><div className="calculator-layout"><div><h2>Change the values.<br /><em>Watch the gap move.</em></h2><p>This browser-only calculator uses the same growth formula as the controlled demonstration. No model is called and no values leave the page.</p><div className="calculator-fields"><label><span>Prior-period revenue</span><input type="number" step="any" value={priorRevenue} onChange={(event) => setPriorRevenue(event.target.value)} /></label><label><span>Current-period revenue</span><input type="number" step="any" value={currentRevenue} onChange={(event) => setCurrentRevenue(event.target.value)} /></label><label><span>Claimed growth (%)</span><input type="number" step="any" value={claimedGrowth} onChange={(event) => setClaimedGrowth(event.target.value)} /></label></div></div><div className="calculator-result" aria-live="polite"><span>PYTHON-EQUIVALENT FORMULA</span><code>(current - prior) / prior x 100</code>{calculatorValid ? <><div><small>Calculated growth</small><strong>{calculatedGrowth.toFixed(2)}%</strong></div><div><small>Claim minus calculation</small><strong className={Math.abs(calculatedGap) <= 0.5 ? "within" : "outside"}>{calculatedGap.toFixed(2)} pp</strong></div><p>{Math.abs(calculatedGap) <= 0.5 ? "Within the 0.50 percentage-point demonstration tolerance." : "Outside the 0.50 percentage-point demonstration tolerance. A filing explanation would need to reconcile this gap."}</p></> : <p>Enter valid numbers. Prior-period revenue cannot be zero.</p>}</div></div></div></section>

      <section className="inspector shell" id="prompts">
        <div className="section-kicker"><span>06</span><p>Prompt Inspector</p></div>
        <div className="section-heading"><h2>Inspect every model contract.</h2><p>Judges can see the version, instruction, input contract, expected schema, and sample output. Secrets never enter this interface.</p></div>
        <div className="code-boundary"><div><span>ACTIVE LLM CALLS</span><strong>4 specialists -&gt; second pass</strong><small>Five batched calls in the benchmark; versioned prompts and schema-validated outputs</small></div><b>-&gt;</b><div className="code-only"><span>DETERMINISTIC CODE</span><strong>Aggregation + Python calculation + quote validation</strong><small>Aggregator contract is defined but not wired as an LLM call</small></div></div>
        <div className="inspector-grid"><aside aria-label="Prompt stages" role="tablist">{promptData.map((item, index) => <button type="button" role="tab" aria-selected={promptIndex === index} className={promptIndex === index ? "active" : ""} onClick={() => setPromptIndex(index)} key={item.id}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item.stage.replaceAll("_", " ")}</strong><small>v{item.version}</small></button>)}</aside><article role="tabpanel"><div className="call-label">{prompt.call_type}</div><div className="prompt-meta"><div><span>Stage</span><strong>{prompt.stage.replaceAll("_", " ")}</strong></div><div><span>Model</span><strong>{prompt.model}</strong></div><div><span>Temperature</span><strong>{prompt.temperature.toFixed(1)}</strong></div><div><span>Prompt version</span><strong>{prompt.version}</strong></div></div><h3>Purpose</h3><p className="prompt-purpose">{prompt.purpose}</p><h3>System instruction</h3><pre>{prompt.system_instruction}</pre><div className="prompt-columns"><div><h3>Input</h3><pre>{JSON.stringify(prompt.input_contract, null, 2)}</pre></div><div><h3>Structured output</h3><pre>{JSON.stringify(prompt.sample_output, null, 2)}</pre></div></div><h3>Expected JSON schema</h3><pre>{JSON.stringify(prompt.expected_json_schema, null, 2)}</pre><div className="validation-result"><span>VALIDATION RESULT</span><strong>{prompt.validation_result}</strong></div></article></div>
      </section>

      <section className="architecture-preview" id="architecture"><div className="shell"><div className="section-kicker"><span>07</span><p>System architecture</p></div><div className="architecture-preview-head"><div><h2>The complete evidence chain.</h2><p>Follow every handoff from raw transcript and filing data to scoped model calls, authoritative Python calculations, fail-closed validation, and named human sign-off.</p></div><Link href="/architecture">Read each role in detail <ArrowIcon /></Link></div><div className="architecture-preview-frame" role="region" aria-label="Scrollable FinTrace system architecture diagram" tabIndex={0}><Image src="/fintrace-ml-workflow.svg" alt="FinTrace eight-stage system architecture separating LLM calls, deterministic Python, evidence validation, analyst review, and human sign-off" width={2400} height={1500} sizes="(max-width: 760px) 1050px, 100vw" /></div><div className="architecture-legend"><span><i className="legend-llm" />LLM proposes</span><span><i className="legend-code" />Python calculates and validates</span><span><i className="legend-human" />Human decides</span><a href="/fintrace-ml-workflow.png" target="_blank" rel="noreferrer">Open full-size PNG</a></div></div></section>

      <section className="refusals"><div className="shell"><div className="section-kicker light"><span>08</span><p>Where FinTrace refuses to guess</p></div><h2>Unresolved is a feature.</h2><div className="refusal-grid">{[
        ["Insufficient filing data", "The filing names an effect but does not quantify it."],
        ["Plausible but unsupported", "The explanation sounds reasonable but is absent from the filing."],
        ["Quote cannot be validated", "A proposed quotation is not found in the supplied corpus."],
        ["Numerical gap remains", "The disclosure exists but does not bridge computed and claimed values."],
        ["Contradictory passages", "Conflicting evidence is preserved for a human instead of resolved by assumption."],
      ].map(([title, text], index) => <article key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{text}</p><strong>RESULT: UNRESOLVED</strong></article>)}</div><div className="architecture-link"><div><span>SYSTEM ARCHITECTURE</span><h3>See exactly what the LLM, Python, retrieval, validation, and human each do.</h3></div><Link href="/architecture">Open architecture page <ArrowIcon /></Link></div></div></section>

      {tourActive ? <aside className="tour-guide" aria-live="polite" aria-label="90-second judge tour"><div className="tour-progress"><span>90-SECOND TOUR</span><b>{String(tourStep + 1).padStart(2, "0")} / {String(tourSteps.length).padStart(2, "0")}</b></div><div className="tour-copy"><strong>{tourSteps[tourStep].title}</strong><p>{tourSteps[tourStep].body}</p></div><div className="tour-controls"><button type="button" className="tour-sound" aria-pressed={tourSoundEnabled} onClick={toggleTourSound}>{tourSoundEnabled ? "Sound on" : "Sound off"}</button><button type="button" onClick={() => moveTour(-1)} disabled={tourStep === 0}>Back</button><button type="button" className="tour-next" onClick={() => moveTour(1)}>{tourStep === tourSteps.length - 1 ? "Finish" : "Next"}<ArrowIcon /></button><button type="button" className="tour-close" aria-label="Close tour" onClick={closeTour}>x</button></div></aside> : null}

      <footer className="footer shell"><div className="brand"><span>F</span>FinTrace</div><p>Models interpret. Code calculates. Filings provide evidence.</p><span>Independent research prototype</span></footer>
    </main>
  );
}
