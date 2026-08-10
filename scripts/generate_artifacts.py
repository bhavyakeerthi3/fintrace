"""Generate side-by-side benchmark HTML and PDF from a validated dual-run result file."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import pdfplumber
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fintrace.evaluation import load_benchmark, validate_benchmark_integrity, validate_live_run  # noqa: E402
from fintrace.prompts import PROMPT_REGISTRY  # noqa: E402


OUTPUTS = ROOT / "outputs"
APP = ROOT / "app"
SUITE = ROOT / "fixtures" / "benchmark-suite.json"
RESISTANCE_CASES = {"B08", "B09", "B10", "B11", "B12"}
DESIGN_BOUNDARY = (
    "The Python engine (fintrace/) is the authoritative implementation. The public Next.js page "
    "presents a versioned fictional fixture for demo reliability and does not execute the pipeline "
    "live in the browser. This is an intentional design choice, not a limitation of the workflow — "
    "full live execution is available via `python -m fintrace demo --provider live`."
)


def _load_validated_bundle(path: Path) -> dict:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    reference = bundle.get("deterministic_reference")
    live = bundle.get("live_run")
    if not isinstance(reference, dict) or not isinstance(live, dict):
        raise ValueError(
            "Artifact generation requires both deterministic_reference and live_run; "
            "run `python -m fintrace benchmark --provider live --model <name>` first"
        )
    suite = load_benchmark(SUITE)
    validate_benchmark_integrity(reference)
    validate_live_run(live, suite)
    return bundle


def write_ui_data(bundle: dict) -> None:
    reference = bundle["deterministic_reference"]
    live = bundle["live_run"]
    summary = {
        "suite_version": reference["suite_version"],
        "provider": reference["provider"],
        "case_count": reference["case_count"],
        "finding_count": reference["finding_count"],
        "integrity_checks": reference["integrity_checks"],
        "ablations": {name: data["metrics"] for name, data in reference["ablations"].items()},
        "comparisons": reference["comparisons"],
        "live_run": {
            "model": live["model"],
            "temperature": live["temperature"],
            "run_timestamp": live["run_timestamp"],
            "metrics": live["metrics"],
            "comparisons": live["comparisons"],
        },
    }
    (APP / "evaluation-data.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    prompt_data = [
        {
            "stage": name,
            "id": spec["id"],
            "version": spec["version"],
            "purpose": spec["purpose"],
            "system_instruction": spec["system_instruction"],
            "input_contract": spec["input_contract"],
            "expected_json_schema": spec["output_schema"],
            "scope_restrictions": spec["scope_restrictions"],
            "sample_output": {"explained": [], "unresolved": [{"finding_id": "B01-F1", "reasoning": "No filing disclosure directly reconciles the numerical difference."}]} if name == "second_pass" else {"findings": []},
            "call_type": "LLM CALL",
            "model": "provider selected / local deterministic adapter",
            "temperature": 0.0,
            "validation_result": "PASS - structured output is checked against the versioned JSON schema",
        }
        for name, spec in PROMPT_REGISTRY.items()
    ]
    (APP / "prompt-data.json").write_text(json.dumps(prompt_data, indent=2) + "\n", encoding="utf-8")


def classification_text(items: list[dict]) -> str:
    return ", ".join(f"{item['finding_id']}: {item['classification'].upper()}" for item in items)


def citation_text(items: list[dict]) -> str:
    attempted = [item.get("citation_valid") for item in items if item.get("classification") == "explained"]
    return "N/A" if not attempted else "PASS" if all(value is True for value in attempted) else "FAIL"


def comparison_cases(bundle: dict) -> list[dict]:
    reference = bundle["deterministic_reference"]
    live_by_case = {item["case_id"]: item for item in bundle["live_run"]["comparisons"]}
    cases = []
    for case in reference["comparisons"]:
        live = live_by_case.get(case["case_id"])
        if live is None:
            raise ValueError(f"Live benchmark is missing case {case['case_id']}")
        reference_verdicts = {item["finding_id"]: item["classification"] for item in case["fintrace_output"]}
        live_verdicts = {item["finding_id"]: item["classification"] for item in live["live_output"]}
        cases.append({
            **case,
            "live_output": live["live_output"],
            "live_correct": live["live_correct"],
            "disagreement": reference_verdicts != live_verdicts,
        })
    return cases


def metric_row(label: str, metrics: dict) -> str:
    return (
        f"<tr><td>{html.escape(label)}</td><td>{metrics['correct_classifications']}/{metrics['finding_count']}</td>"
        f"<td>{metrics['classification_accuracy']}%</td><td>{metrics['false_positives']} ({metrics['false_positive_rate']}%)</td>"
        f"<td>{metrics['unsupported_explanations']} ({metrics['unsupported_explanation_rate']}%)</td>"
        f"<td>{metrics['correct_numeric_checks']}/{metrics['numeric_checks']} ({metrics['numerical_reconciliation_accuracy']}%)</td></tr>"
    )


def write_html(bundle: dict) -> None:
    reference = bundle["deterministic_reference"]
    live = bundle["live_run"]
    reference_metrics = reference["ablations"]["full_fintrace"]["metrics"]
    live_metrics = live["metrics"]
    rows = []
    for case in comparison_cases(bundle):
        badges = (["FAILURE-RESISTANCE CASE"] if case["case_id"] in RESISTANCE_CASES else []) + (["RUNS DISAGREE"] if case["disagreement"] else [])
        rows.append(f"""<article class="case {'disagree' if case['disagreement'] else ''}"><header><div><span>{html.escape(case['case_id'])}</span><h2>{html.escape(case['title'])}</h2></div><div class="badges">{''.join(f'<b>{badge}</b>' for badge in badges)}</div></header>
<section class="input"><label>INPUT</label><p>{html.escape('; '.join(case['input']['claims']))}</p></section>
<div class="compare"><section class="result {'pass' if case['fintrace_correct'] else 'fail'}"><label>DETERMINISTIC REFERENCE</label><p>{html.escape(classification_text(case['fintrace_output']))}</p><strong>{'PASS' if case['fintrace_correct'] else 'FAIL'}</strong><small>Citation: {citation_text(case['fintrace_output'])}</small></section>
<section class="result {'pass' if case['live_correct'] else 'fail'}"><label>LIVE MODEL</label><p>{html.escape(classification_text(case['live_output']))}</p><strong>{'PASS' if case['live_correct'] else 'FAIL'}</strong><small>Citation: {citation_text(case['live_output'])}</small></section></div>
<section class="expected"><label>EXPECTED RESULT</label><p>{html.escape(classification_text(case['expected_result']))}</p><strong>ADJUDICATED</strong></section></article>""")
    metric_rows = metric_row("Deterministic reference", reference_metrics) + metric_row(f"Live model: {live['model']}", live_metrics)
    document = f"""<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FinTrace Controlled Benchmark</title><style>
:root{{--ink:#172527;--wine:#9d373b;--green:#2f6b55;--muted:#687274;--paper:#f4f0e8;--card:#fffdf8;--line:#d9d5cb}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px Arial,sans-serif}}main{{max-width:1120px;margin:auto;padding:60px 28px}}.eyebrow,label{{color:var(--wine);font:700 11px/1.3 monospace;letter-spacing:.1em}}h1{{font:54px/1 Georgia,serif;margin:12px 0}}.lede{{max-width:860px;color:var(--muted);font-size:18px;line-height:1.6}}.notice{{padding:16px 20px;border-left:4px solid var(--wine);background:var(--card);line-height:1.55}}.scoreboard,.compare{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.scoreboard{{margin:32px 0}}.score{{padding:24px;background:var(--card);border:1px solid var(--line)}}.score span{{font-weight:700}}.score strong{{display:block;margin:8px 0;color:var(--wine);font:42px Georgia,serif}}table{{width:100%;margin:20px 0 44px;border-collapse:collapse;background:var(--card);font-size:13px}}th,td{{padding:12px;border:1px solid var(--line);text-align:right}}th:first-child,td:first-child{{text-align:left}}.formula{{margin:-28px 0 45px;color:var(--muted);font-size:12px}}.case{{margin:22px 0;padding:26px;background:var(--card);border:1px solid var(--line)}}.case.disagree{{border:2px solid var(--wine);box-shadow:0 12px 34px rgba(157,55,59,.09)}}.case header{{display:flex;justify-content:space-between;align-items:flex-start;gap:18px}}.case header span{{color:var(--wine);font:12px monospace}}.case header h2{{margin:4px 0 0;font:28px Georgia,serif}}.badges{{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}}.badges b{{padding:8px 10px;background:#f4d9d6;color:#812c30;font-size:10px;letter-spacing:.06em}}.input,.result,.expected{{position:relative;margin-top:18px;padding:16px 94px 16px 18px;background:var(--paper);border-left:4px solid var(--line)}}.result p,.expected p,.input p{{margin:8px 0 0;line-height:1.45}}.result>strong,.expected>strong{{position:absolute;top:16px;right:18px;padding:6px 9px;font-size:10px}}.result>small{{display:block;margin-top:9px;color:var(--muted)}}.result.pass{{border-color:var(--green)}}.result.pass>strong{{background:#dcebe4;color:var(--green)}}.result.fail{{border-color:var(--wine)}}.result.fail>strong{{background:#f4d9d6;color:#812c30}}.expected{{border-color:var(--ink)}}.expected>strong{{background:var(--ink);color:white}}code{{font-family:Consolas,monospace}}@media(max-width:760px){{main{{padding:36px 16px}}h1{{font-size:42px}}.scoreboard,.compare{{grid-template-columns:1fr}}table{{display:block;overflow:auto}}.case header{{flex-direction:column}}.badges{{justify-content:flex-start}}}}
</style></head><body><main><p class="eyebrow">FINTRACE CONTROLLED BENCHMARK</p><h1>Deterministic reference<br>vs. live model</h1>
<p class="lede">One 12-case, 13-finding suite; two independently labeled runs. Scores are never averaged or blended.</p>
<p class="notice"><b>Design boundary:</b> {html.escape(DESIGN_BOUNDARY).replace('`', '<code>', 1).replace('`', '</code>', 1)}</p>
<div class="scoreboard"><section class="score"><span>Deterministic reference</span><strong>{reference_metrics['correct_classifications']} / {reference_metrics['finding_count']}</strong><p>{reference_metrics['classification_accuracy']}% classification accuracy</p></section><section class="score"><span>Live model: {html.escape(live['model'])}</span><strong>{live_metrics['correct_classifications']} / {live_metrics['finding_count']}</strong><p>{live_metrics['classification_accuracy']}% classification accuracy</p><small>Temperature {live['temperature']} | Run {html.escape(live['run_timestamp'])}</small></section></div>
<p class="notice">Results are limited to this controlled fictional benchmark and are not a claim of general model performance. Disagreements remain visible case by case.</p>
<h2>Independent measured results</h2><table><thead><tr><th>Run</th><th>Correct</th><th>Classification accuracy</th><th>False positives</th><th>Unsupported explanations</th><th>Numeric reconciliation</th></tr></thead><tbody>{metric_rows}</tbody></table>
<p class="formula">Same formulas and 13-finding denominator for both runs. Deterministic integrity: {reference['integrity_checks']['status'].upper()}. Live integrity: {bundle['integrity_checks']['live_run']['status'].upper()}.</p>
<h2>Case-by-case comparison</h2><p>Each case shows both verdicts. A red border and RUNS DISAGREE badge marks any difference between them.</p>{''.join(rows)}</main></body></html>"""
    (OUTPUTS / "fintrace-samples.html").write_text(document, encoding="utf-8")


def write_pdf(bundle: dict) -> None:
    reference = bundle["deterministic_reference"]
    live = bundle["live_run"]
    reference_metrics = reference["ablations"]["full_fintrace"]["metrics"]
    live_metrics = live["metrics"]
    path = OUTPUTS / "fintrace-samples.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=.55 * inch, leftMargin=.55 * inch, topMargin=.58 * inch, bottomMargin=.55 * inch)
    title = ParagraphStyle("TitleFT", fontName="Helvetica-Bold", fontSize=28, leading=32, alignment=TA_CENTER, textColor=colors.HexColor("#172527"), spaceAfter=8)
    subtitle = ParagraphStyle("SubFT", fontName="Helvetica", fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#687274"), spaceAfter=15)
    heading = ParagraphStyle("HeadFT", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#172527"), spaceBefore=9, spaceAfter=7)
    body = ParagraphStyle("BodyFT", fontName="Helvetica", fontSize=8.5, leading=12, textColor=colors.HexColor("#172527"), spaceAfter=7)
    small = ParagraphStyle("SmallFT", fontName="Helvetica", fontSize=7, leading=9, textColor=colors.HexColor("#687274"))
    cell = ParagraphStyle("CellFT", fontName="Helvetica", fontSize=7, leading=9, textColor=colors.HexColor("#172527"))
    cell_head = ParagraphStyle("CellHeadFT", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d9d5cb"))
        canvas.line(.55 * inch, .38 * inch, 7.95 * inch, .38 * inch)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#687274"))
        canvas.drawString(.55 * inch, .22 * inch, "FINTRACE CONTROLLED BENCHMARK | fictional companies and controlled disclosures")
        canvas.drawRightString(7.95 * inch, .22 * inch, f"PAGE {document.page}")
        canvas.restoreState()

    story = [Paragraph("FINTRACE CONTROLLED BENCHMARK", subtitle), Paragraph("Deterministic reference vs. live model", title), Paragraph("One 12-case, 13-finding suite; two independently labeled runs. Scores are never averaged or blended.", subtitle), Paragraph(f"<b>Design boundary:</b> {DESIGN_BOUNDARY.replace('`', '')}", body)]
    score_table = Table([
        [Paragraph("DETERMINISTIC REFERENCE", cell_head), Paragraph(f"LIVE MODEL: {live['model']}", cell_head)],
        [Paragraph(f"<b>{reference_metrics['correct_classifications']} / {reference_metrics['finding_count']} correct</b><br/>{reference_metrics['classification_accuracy']}% classification accuracy", body), Paragraph(f"<b>{live_metrics['correct_classifications']} / {live_metrics['finding_count']} correct</b><br/>{live_metrics['classification_accuracy']}% classification accuracy", body)],
        [Paragraph("Reproducible local baseline", body), Paragraph(f"Temperature {live['temperature']}<br/>Run {live['run_timestamp']}", body)],
    ], colWidths=[3.65 * inch, 3.65 * inch])
    score_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172527")), ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fffdf8")), ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#d9d5cb")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 9)]))
    story.extend([score_table, Spacer(1, 10), Paragraph("<b>Scope:</b> Results are limited to this controlled fictional benchmark and are not a claim of general model performance. Disagreements remain visible case by case.", body), Paragraph("Independent measured results", heading)])
    metric_rows = [[Paragraph("Run", cell_head), Paragraph("Correct", cell_head), Paragraph("Accuracy", cell_head), Paragraph("False positives", cell_head), Paragraph("Unsupported", cell_head), Paragraph("Numeric", cell_head)]]
    for name, metrics in (("Deterministic reference", reference_metrics), (f"Live: {live['model']}", live_metrics)):
        metric_rows.append([Paragraph(name, cell), Paragraph(f"{metrics['correct_classifications']}/{metrics['finding_count']}", cell), Paragraph(f"{metrics['classification_accuracy']}%", cell), Paragraph(f"{metrics['false_positives']} ({metrics['false_positive_rate']}%)", cell), Paragraph(f"{metrics['unsupported_explanations']} ({metrics['unsupported_explanation_rate']}%)", cell), Paragraph(f"{metrics['correct_numeric_checks']}/{metrics['numeric_checks']}", cell)])
    metrics_table = Table(metric_rows, colWidths=[1.55 * inch, .75 * inch, .8 * inch, 1.2 * inch, 1.25 * inch, 1 * inch])
    metrics_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172527")), ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#d9d5cb")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.extend([metrics_table, Spacer(1, 5), Paragraph(f"Same formulas and 13-finding denominator for both runs. Deterministic integrity: {reference['integrity_checks']['status'].upper()}. Live integrity: {bundle['integrity_checks']['live_run']['status'].upper()}.", small), PageBreak()])
    cases = comparison_cases(bundle)
    for index, case in enumerate(cases):
        tags = (["FAILURE-RESISTANCE CASE"] if case["case_id"] in RESISTANCE_CASES else []) + (["RUNS DISAGREE"] if case["disagreement"] else [])
        suffix = " | " + " | ".join(tags) if tags else ""
        story.extend([Paragraph(f"{case['case_id']} | {case['title']}{suffix}", heading), Paragraph("<b>INPUT</b><br/>" + "; ".join(case["input"]["claims"]), body)])
        rows = [
            [Paragraph("DETERMINISTIC REFERENCE", cell_head), Paragraph(f"LIVE: {live['model']}", cell_head), Paragraph("EXPECTED RESULT", cell_head)],
            [
                Paragraph(f"{classification_text(case['fintrace_output'])}<br/><b>{'PASS' if case['fintrace_correct'] else 'FAIL'}</b>", cell),
                Paragraph(f"{classification_text(case['live_output'])}<br/><b>{'PASS' if case['live_correct'] else 'FAIL'}</b>", cell),
                Paragraph(f"{classification_text(case['expected_result'])}<br/><b>ADJUDICATED</b>", cell),
            ],
        ]
        comparison = Table(rows, colWidths=[2.43 * inch, 2.43 * inch, 2.43 * inch])
        comparison.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172527")), ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fffdf8")), ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#d9d5cb")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]))
        story.extend([comparison, Paragraph(f"Reference citation: {citation_text(case['fintrace_output'])} | Live citation: {citation_text(case['live_output'])} | Runs disagree: {case['disagreement']}", small), Spacer(1, 12)])
        if index % 2 == 1 and index < len(cases) - 1:
            story.append(PageBreak())
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def verify_artifacts(bundle: dict) -> dict[str, int | str]:
    """Read generated artifacts back and fail on any drift from the result JSON."""
    html_document = (OUTPUTS / "fintrace-samples.html").read_text(encoding="utf-8")
    with pdfplumber.open(OUTPUTS / "fintrace-samples.pdf") as pdf:
        pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        page_count = len(pdf.pages)

    reference = bundle["deterministic_reference"]["ablations"]["full_fintrace"]
    live = bundle["live_run"]
    for label, run in (("Deterministic reference", reference), (f"Live model: {live['model']}", live)):
        metrics = run["metrics"]
        expected_html = (
            f"<td>{html.escape(label)}</td><td>{metrics['correct_classifications']}/{metrics['finding_count']}</td>"
            f"<td>{metrics['classification_accuracy']}%</td><td>{metrics['false_positives']} ({metrics['false_positive_rate']}%)</td>"
            f"<td>{metrics['unsupported_explanations']} ({metrics['unsupported_explanation_rate']}%)</td>"
            f"<td>{metrics['correct_numeric_checks']}/{metrics['numeric_checks']} ({metrics['numerical_reconciliation_accuracy']}%)</td>"
        )
        if expected_html not in html_document:
            raise ValueError(f"HTML metrics do not match benchmark JSON for {label}")
        if f"{metrics['correct_classifications']} / {metrics['finding_count']} correct" not in pdf_text:
            raise ValueError(f"PDF correct count does not match benchmark JSON for {label}")
        if f"{metrics['classification_accuracy']}% classification accuracy" not in pdf_text:
            raise ValueError(f"PDF classification accuracy does not match benchmark JSON for {label}")

    for run_name, run in (("deterministic_reference", reference), ("live_run", live)):
        for item in run["outputs"]:
            expected_verdict = f"{item['finding_id']}: {item['classification'].upper()}"
            if expected_verdict not in html_document:
                raise ValueError(f"HTML is missing {run_name} verdict: {expected_verdict}")
            if expected_verdict not in pdf_text:
                raise ValueError(f"PDF is missing {run_name} verdict: {expected_verdict}")

    expected_cases = int(bundle["case_count"])
    if html_document.count("DETERMINISTIC REFERENCE") < expected_cases or html_document.count("LIVE MODEL") < expected_cases:
        raise ValueError("HTML does not show both runs for every case")
    if pdf_text.count("DETERMINISTIC REFERENCE") < expected_cases or pdf_text.count(f"LIVE: {live['model']}") < expected_cases:
        raise ValueError("PDF does not show both runs for every case")
    return {"status": "passed", "cases_checked": expected_cases, "pdf_pages": page_count}


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    bundle = _load_validated_bundle(OUTPUTS / "fintrace-benchmark-results.json")
    write_ui_data(bundle)
    write_html(bundle)
    write_pdf(bundle)
    artifact_verification = verify_artifacts(bundle)
    print(json.dumps({"cases": bundle["case_count"], "findings": bundle["finding_count"], "integrity": bundle["integrity_checks"], "artifact_verification": artifact_verification, "outputs": ["fintrace-samples.html", "fintrace-samples.pdf"]}, indent=2))


if __name__ == "__main__":
    main()
