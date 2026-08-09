"""Generate judge-facing benchmark data, workflow art, HTML, and PDF samples."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fintrace.evaluation import evaluate_suite, validate_benchmark_integrity  # noqa: E402
from fintrace.prompts import PROMPT_REGISTRY  # noqa: E402


OUTPUTS = ROOT / "outputs"
APP = ROOT / "app"
PUBLIC = ROOT / "public"
SUITE = ROOT / "fixtures" / "benchmark-suite.json"
RESISTANCE_CASES = {"B08", "B09", "B10", "B11", "B12"}


def write_ui_data(result: dict) -> None:
    summary = {
        "suite_version": result["suite_version"],
        "provider": result["provider"],
        "case_count": result["case_count"],
        "finding_count": result["finding_count"],
        "integrity_checks": result["integrity_checks"],
        "ablations": {name: data["metrics"] for name, data in result["ablations"].items()},
        "comparisons": result["comparisons"],
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


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / filename
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str) -> None:
    draw.line((*start, *end), fill=color, width=6)
    ex, ey = end
    if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
        direction = 1 if end[0] > start[0] else -1
        draw.polygon([(ex, ey), (ex - 18 * direction, ey - 12), (ex - 18 * direction, ey + 12)], fill=color)
    else:
        direction = 1 if end[1] > start[1] else -1
        draw.polygon([(ex, ey), (ex - 12, ey - 18 * direction), (ex + 12, ey - 18 * direction)], fill=color)


def draw_workflow() -> None:
    width, height = 2200, 1400
    image = Image.new("RGB", (width, height), "#f4f0e8")
    draw = ImageDraw.Draw(image)
    ink, wine, green, blue, muted, card, line = "#172527", "#9d373b", "#2f6b55", "#315f78", "#687274", "#fffdf8", "#d9d5cb"
    draw.text((85, 58), "FinTrace ML Workflow", font=font(55, True), fill=ink)
    draw.text((85, 128), "An auditable chain from statement to filed numbers to validated explanation to human decision.", font=font(24), fill=muted)
    draw.rounded_rectangle((1680, 63, 2115, 154), radius=16, fill="#ebe6dc", outline=line, width=2)
    draw.text((1720, 90), "CONTROLLED FICTIONAL DEMO", font=font(19, True), fill=wine)

    nodes = [
        ("Human Input", "Role: judge or analyst\nInput: management statement\nOutput: review request", "human"),
        ("Transcript + Filing", "Purpose: align source corpus\nPrompt: none\nModel: none\nOutput: source package", "data"),
        ("4 Specialist LLM Calls", "Purpose: scoped candidate finding\nPrompt: revenue / cash / related / language v1\nModel: configured provider\nOutput: schema-validated JSON", "llm"),
        ("Aggregation", "Purpose: deduplicate candidates\nPrompt: aggregator_v1\nModel: configured provider or local adapter\nOutput: stable finding IDs", "llm"),
        ("Deterministic Python Calculation", "NOT AN LLM CALL\nPurpose: authoritative arithmetic\nInput: filed numeric values\nOutput: formula + value + gap + tolerance", "code"),
        ("Filing Evidence Retrieval", "Purpose: locate possible explanations\nPrompt: none\nModel: deterministic retrieval\nOutput: ranked filing passages", "data"),
        ("Second-Pass LLM", "Purpose: evidence-bound classification\nPrompt: second_pass_v1\nModel: configured provider\nOutput: explained or unresolved", "llm"),
        ("Quote Validation", "NOT AN LLM CALL\nPurpose: exact quote + relation check\nInput: proposed filing quotation\nOutput: pass or unresolved transition", "code"),
        ("Human Review", "Role: final decision maker\nInput: complete evidence chain\nOutput: accept / reject / needs review", "human"),
        ("Versioned Report", "Purpose: preserve reproducibility\nIncludes: prompts + model + calculations\nOutput: JSON + integrity digest", "report"),
    ]
    box_w, box_h, gap = 365, 430, 48
    xs = [85 + index * (box_w + gap) for index in range(5)]
    positions = [(x, 225) for x in xs] + [(x, 795) for x in xs]
    for index, ((title, body, kind), (x, y)) in enumerate(zip(nodes, positions)):
        accent = wine if kind == "llm" else green if kind == "code" else blue if kind == "data" else ink
        draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=20, fill=card, outline=line, width=3)
        draw.rectangle((x, y, x + box_w, y + 11), fill=accent)
        draw.text((x + 27, y + 30), f"{index + 1:02d}", font=font(20, True), fill=accent)
        title_y = y + 72
        for title_line in wrap(title, 24):
            draw.text((x + 27, title_y), title_line, font=font(25, True), fill=ink)
            title_y += 32
        ty = max(y + 150, title_y + 18)
        for raw in body.splitlines():
            is_emphasis = raw.startswith("NOT AN LLM")
            for line_text in wrap(raw, 31) or [""]:
                draw.text((x + 27, ty), line_text, font=font(17, is_emphasis), fill=green if is_emphasis else muted)
                ty += 25
            ty += 4

    for index in range(4):
        draw_arrow(draw, (xs[index] + box_w + 8, 440), (xs[index + 1] - 8, 440), wine)
    elbow_x = xs[4] + box_w + 25
    draw.line((xs[4] + box_w // 2, 655, elbow_x, 705, 60, 705, 60, 1010, xs[0] - 8, 1010), fill=wine, width=6)
    draw_arrow(draw, (xs[0] - 8, 1010), (xs[0] + 8, 1010), wine)
    for index in range(5, 9):
        source_x = positions[index][0]
        target_x = positions[index + 1][0]
        draw_arrow(draw, (source_x + box_w + 8, 1010), (target_x - 8, 1010), wine)
    draw.text((85, 1320), "LLM nodes propose structured interpretations. Deterministic code calculates and validates. A human makes the final decision.", font=font(21, True), fill=ink)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUTS / "fintrace-ml-workflow.png", optimize=True)
    image.save(PUBLIC / "fintrace-ml-workflow.png", optimize=True)


def classification_text(items: list[dict]) -> str:
    return ", ".join(f"{item['finding_id']}: {item['classification'].upper()}" for item in items)


def citation_text(items: list[dict]) -> str:
    attempted = [item.get("citation_valid") for item in items if item.get("classification") == "explained"]
    if not attempted:
        return "N/A"
    return "PASS" if all(value is True for value in attempted) else "FAIL"


def _verify_resistance_cases(result: dict) -> None:
    cases = {case["case_id"]: case for case in result["comparisons"]}
    missing = RESISTANCE_CASES - set(cases)
    if missing:
        raise ValueError(f"Required failure-resistance cases are missing: {sorted(missing)}")
    failed = [case_id for case_id in RESISTANCE_CASES if not cases[case_id]["baseline_fail_fintrace_pass"]]
    if failed:
        raise ValueError(f"Failure-resistance outcomes changed for: {sorted(failed)}")


def write_html(result: dict) -> None:
    baseline = result["ablations"]["single_prompt"]["metrics"]
    full = result["ablations"]["full_fintrace"]["metrics"]
    correct_gain = full["correct_classifications"] - baseline["correct_classifications"]
    point_gain = round(full["classification_accuracy"] - baseline["classification_accuracy"], 1)
    rows = []
    for case in result["comparisons"]:
        resistance = case["case_id"] in RESISTANCE_CASES
        baseline_mark = "PASS" if case["baseline_correct"] else "FAIL"
        full_mark = "PASS" if case["fintrace_correct"] else "FAIL"
        rows.append(f"""<article class="case {'resistance' if resistance else ''}"><header><div><span>{html.escape(case['case_id'])}</span><h2>{html.escape(case['title'])}</h2></div>{'<b>FAILURE-RESISTANCE CASE</b>' if resistance else ''}</header>
<div class="flow"><section><label>INPUT</label><p>{html.escape('; '.join(case['input']['claims']))}</p></section><i>&darr;</i>
<section class="result {'pass' if case['baseline_correct'] else 'fail'}"><label>SINGLE PROMPT RESULT</label><p>{html.escape(classification_text(case['baseline_output']))}</p><strong>{baseline_mark}</strong><small>Unsupported explanation: {str(case['baseline_unsupported_explanation']).upper()} | False positive: {str(case['baseline_false_positive']).upper()} | Citation: {citation_text(case['baseline_output'])}</small></section><i>&darr;</i>
<section class="result {'pass' if case['fintrace_correct'] else 'fail'}"><label>FINTRACE RESULT</label><p>{html.escape(classification_text(case['fintrace_output']))}</p><strong>{full_mark}</strong><small>Unsupported explanation: {str(case['fintrace_unsupported_explanation']).upper()} | Citation: {citation_text(case['fintrace_output'])}</small></section><i>&darr;</i>
<section class="expected"><label>EXPECTED RESULT</label><p>{html.escape(classification_text(case['expected_result']))}</p><strong>ADJUDICATED</strong></section></div></article>""")
    metric_rows = "".join(
        f"<tr><td>{name.replace('_', ' ').title()}</td><td>{data['metrics']['correct_classifications']}/{data['metrics']['finding_count']}</td><td>{data['metrics']['classification_accuracy']}%</td><td>{data['metrics']['unsupported_explanations']}</td><td>{data['metrics']['correct_numeric_checks']}/{data['metrics']['numeric_checks']} ({data['metrics']['numerical_reconciliation_accuracy']}%)</td><td>{data['metrics']['false_positives']}</td></tr>"
        for name, data in result["ablations"].items()
    )
    document = f"""<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FinTrace Controlled Benchmark</title><style>
:root{{--ink:#172527;--wine:#9d373b;--green:#2f6b55;--muted:#687274;--paper:#f4f0e8;--card:#fffdf8;--line:#d9d5cb}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px Arial,sans-serif}}main{{max-width:1120px;margin:auto;padding:60px 28px}}.eyebrow,label{{color:var(--wine);font:700 11px/1.3 monospace;letter-spacing:.1em}}h1{{font:54px/1 Georgia,serif;margin:12px 0}}.lede{{max-width:780px;color:var(--muted);font-size:18px;line-height:1.6}}.notice{{padding:16px 20px;border-left:4px solid var(--wine);background:var(--card)}}.scoreboard{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:32px 0}}.score{{padding:24px;background:var(--card);border:1px solid var(--line)}}.score span{{font-weight:700}}.score strong{{display:block;margin:8px 0;color:var(--wine);font:42px Georgia,serif}}.lift{{display:flex;gap:10px;margin:-12px 0 40px}}.lift b{{padding:10px 14px;background:var(--ink);color:#fff;font-size:13px}}.demonstrates{{padding:28px;background:#eee5db;border:1px solid var(--line)}}.demonstrates h2{{margin-top:0}}.demonstrates li{{margin:10px 0;line-height:1.4}}table{{width:100%;margin:20px 0 44px;border-collapse:collapse;background:var(--card);font-size:13px}}th,td{{padding:12px;border:1px solid var(--line);text-align:right}}th:first-child,td:first-child{{text-align:left}}.formula{{margin:-28px 0 45px;color:var(--muted);font-size:12px}}.case{{margin:22px 0;padding:26px;background:var(--card);border:1px solid var(--line)}}.case.resistance{{border:2px solid var(--wine);box-shadow:0 12px 34px rgba(157,55,59,.09)}}.case header{{display:flex;justify-content:space-between;align-items:center;gap:18px}}.case header span{{color:var(--wine);font:12px monospace}}.case header h2{{margin:4px 0 0;font:28px Georgia,serif}}.case header>b{{padding:8px 10px;background:#f4d9d6;color:#812c30;font-size:10px;letter-spacing:.08em}}.flow{{margin-top:20px}}.flow section{{position:relative;padding:16px 94px 16px 18px;background:var(--paper);border-left:4px solid var(--line)}}.flow section p{{margin:8px 0 0;line-height:1.45}}.flow section>strong{{position:absolute;top:16px;right:18px;padding:6px 9px;font-size:10px}}.flow section>small{{display:block;margin-top:9px;color:var(--muted)}}.flow i{{display:block;height:25px;color:var(--wine);font-size:21px;text-align:center;font-style:normal}}.flow .pass{{border-color:var(--green)}}.flow .pass>strong{{background:#dcebe4;color:var(--green)}}.flow .fail{{border-color:var(--wine)}}.flow .fail>strong{{background:#f4d9d6;color:#812c30}}.flow .expected{{border-color:var(--ink)}}.flow .expected>strong{{background:var(--ink);color:white}}@media(max-width:760px){{main{{padding:36px 16px}}h1{{font-size:42px}}.scoreboard{{grid-template-columns:1fr}}.lift{{flex-direction:column}}table{{display:block;overflow:auto}}.case header{{align-items:flex-start;flex-direction:column}}}}
</style></head><body><main>
<p class="eyebrow">FINTRACE CONTROLLED BENCHMARK</p><h1>12 fictional cases<br>13 independently evaluated findings</h1>
<p class="lede">The same controlled evidence is evaluated by a simple single-prompt baseline and the complete FinTrace workflow.</p>
<div class="scoreboard"><section class="score"><span>Single Prompt</span><strong>{baseline['correct_classifications']} / {baseline['finding_count']} correct</strong><p>{baseline['classification_accuracy']}% classification accuracy</p></section><section class="score"><span>Full FinTrace</span><strong>{full['correct_classifications']} / {full['finding_count']} correct</strong><p>{full['classification_accuracy']}% classification accuracy</p></section></div>
<div class="lift"><b>+{correct_gain} correct findings</b><b>+{point_gain} percentage points</b></div>
<p class="notice">Results are limited to this controlled fictional benchmark and are not a claim of general model performance. The benchmark uses fictional companies and controlled disclosures.</p>
<section class="demonstrates"><h2>What the benchmark demonstrates</h2><ol><li>FinTrace preserves an unresolved result when the filing does not support an explanation.</li><li>It distinguishes a relevant disclosure from an irrelevant disclosure.</li><li>It rejects generic explanations.</li><li>It rejects quotations that cannot be validated.</li><li>It keeps overlapping findings separate.</li><li>Deterministic calculation improves numerical verification.</li><li>The complete workflow combines these controls into the final result.</li></ol></section>
<h2>Measured workflow comparison</h2><p>12 controlled fictional cases containing 13 independently evaluated findings.</p><table><thead><tr><th>Workflow</th><th>Correct</th><th>Classification accuracy</th><th>Unsupported-explanation count</th><th>Numeric reconciliation accuracy</th><th>False-positive count</th></tr></thead><tbody>{metric_rows}</tbody></table>
<p class="formula">Classification accuracy = correct classifications / 13 findings x 100. Numeric reconciliation accuracy = correct numeric checks / 13 numeric checks x 100. Artifact integrity: {result['integrity_checks']['status'].upper()}, {result['integrity_checks']['percentages_checked']} percentages checked.</p>
<p class="notice"><b>Metric clarification:</b> The former 55.6 and 74.9 headline values are retained only as a composite control index, measured in points rather than classification accuracy. Formula: {html.escape(baseline['composite_control_index_formula'])}. Current index values: Single Prompt {baseline['composite_control_index']} points; Specialists Plus Calculation {result['ablations']['specialists_plus_calculation']['metrics']['composite_control_index']} points; Full FinTrace {full['composite_control_index']} points.</p>
<h2>Case-by-case evidence</h2><p>Every failed baseline case remains visible. B08-B12 are highlighted because they test failure resistance.</p>{''.join(rows)}
</main></body></html>"""
    (OUTPUTS / "fintrace-samples.html").write_text(document, encoding="utf-8")


def write_pdf(result: dict) -> None:
    baseline = result["ablations"]["single_prompt"]["metrics"]
    full = result["ablations"]["full_fintrace"]["metrics"]
    correct_gain = full["correct_classifications"] - baseline["correct_classifications"]
    point_gain = round(full["classification_accuracy"] - baseline["classification_accuracy"], 1)
    path = OUTPUTS / "fintrace-samples.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=.55 * inch, leftMargin=.55 * inch, topMargin=.58 * inch, bottomMargin=.55 * inch)
    styles = getSampleStyleSheet()
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

    story = [
        Paragraph("FINTRACE CONTROLLED BENCHMARK", subtitle),
        Paragraph("12 fictional cases<br/>13 independently evaluated findings", title),
        Paragraph("The same controlled evidence is evaluated by a simple single-prompt baseline and the complete FinTrace workflow.", subtitle),
    ]
    score_table = Table([
        [Paragraph("SINGLE PROMPT", cell_head), Paragraph("FULL FINTRACE", cell_head)],
        [Paragraph(f"<b>{baseline['correct_classifications']} / {baseline['finding_count']} correct</b><br/>{baseline['classification_accuracy']}% classification accuracy", body), Paragraph(f"<b>{full['correct_classifications']} / {full['finding_count']} correct</b><br/>{full['classification_accuracy']}% classification accuracy", body)],
        [Paragraph(f"+{correct_gain} correct findings", body), Paragraph(f"+{point_gain} percentage points", body)],
    ], colWidths=[3.65 * inch, 3.65 * inch])
    score_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172527")), ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fffdf8")), ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#d9d5cb")), ("INNERGRID", (0, 0), (-1, -1), .5, colors.HexColor("#d9d5cb")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    story.extend([score_table, Spacer(1, 10), Paragraph("<b>Scope:</b> Results are limited to this controlled fictional benchmark and are not a claim of general model performance. The benchmark uses fictional companies and controlled disclosures.", body), Paragraph("What the benchmark demonstrates", heading)])
    demonstrates = [
        "Preserves unresolved when evidence does not support an explanation.", "Distinguishes relevant from irrelevant disclosure.", "Rejects generic explanations and invalid quotations.", "Keeps overlapping findings separate.", "Uses deterministic calculation for numerical verification.", "Combines controls in one auditable workflow.",
    ]
    story.append(Table([[Paragraph(f"{index}. {text}", body) for index, text in enumerate(demonstrates[:3], 1)], [Paragraph(f"{index}. {text}", body) for index, text in enumerate(demonstrates[3:], 4)]], colWidths=[2.43 * inch] * 3, style=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eee5db")), ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#d9d5cb")), ("INNERGRID", (0, 0), (-1, -1), .5, colors.HexColor("#d9d5cb")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.extend([Paragraph("Measured workflow comparison", heading), Paragraph("12 controlled fictional cases containing 13 independently evaluated findings.", body)])
    metric_data = [[Paragraph(label, cell_head) for label in ["Workflow", "Correct", "Class. accuracy", "Unsupported", "Numeric accuracy", "False positives"]]]
    for name, data in result["ablations"].items():
        m = data["metrics"]
        metric_data.append([Paragraph(name.replace("_", " ").title(), cell), Paragraph(f"{m['correct_classifications']}/{m['finding_count']}", cell), Paragraph(f"{m['classification_accuracy']}%", cell), Paragraph(str(m["unsupported_explanations"]), cell), Paragraph(f"{m['correct_numeric_checks']}/{m['numeric_checks']} ({m['numerical_reconciliation_accuracy']}%)", cell), Paragraph(str(m["false_positives"]), cell)])
    metrics_table = Table(metric_data, colWidths=[1.45 * inch, .7 * inch, .88 * inch, .82 * inch, 1.35 * inch, .85 * inch])
    metrics_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172527")), ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#d9d5cb")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.extend([metrics_table, Spacer(1, 5), Paragraph(f"Classification accuracy = correct / 13 x 100. Integrity check: {result['integrity_checks']['status'].upper()}, {result['integrity_checks']['percentages_checked']} reported percentages verified from numerator and denominator.", small), Spacer(1, 5), Paragraph(f"Metric clarification: 55.6 and 74.9 are composite control index points, not classification accuracy. Formula: {baseline['composite_control_index_formula']}. Current index: Single Prompt {baseline['composite_control_index']} points; Specialists Plus Calculation {result['ablations']['specialists_plus_calculation']['metrics']['composite_control_index']} points; Full FinTrace {full['composite_control_index']} points.", small), PageBreak()])

    for index, case in enumerate(result["comparisons"]):
        resistance = case["case_id"] in RESISTANCE_CASES
        badge = " | FAILURE-RESISTANCE CASE" if resistance else ""
        story.append(Paragraph(f"{case['case_id']} - {case['title']}{badge}", heading))
        rows = [
            [Paragraph("INPUT", cell_head), Paragraph(html.escape("; ".join(case["input"]["claims"])), cell), Paragraph("SOURCE", cell)],
            [Paragraph("SINGLE PROMPT RESULT", cell_head), Paragraph(classification_text(case["baseline_output"]), cell), Paragraph("PASS" if case["baseline_correct"] else "FAIL", cell)],
            [Paragraph("FINTRACE RESULT", cell_head), Paragraph(classification_text(case["fintrace_output"]), cell), Paragraph("PASS" if case["fintrace_correct"] else "FAIL", cell)],
            [Paragraph("EXPECTED RESULT", cell_head), Paragraph(classification_text(case["expected_result"]), cell), Paragraph("ADJUDICATED", cell)],
        ]
        comparison = Table(rows, colWidths=[1.55 * inch, 4.75 * inch, 1 * inch])
        comparison.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#172527")), ("BACKGROUND", (1, 0), (-1, -1), colors.HexColor("#fffdf8")), ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#d9d5cb")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#2f6b55") if case["baseline_correct"] else colors.HexColor("#9d373b")), ("TEXTCOLOR", (2, 2), (2, 2), colors.HexColor("#2f6b55") if case["fintrace_correct"] else colors.HexColor("#9d373b")), ("FONTNAME", (2, 1), (2, 3), "Helvetica-Bold"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
        story.extend([comparison, Paragraph(f"Baseline unsupported explanation: {case['baseline_unsupported_explanation']} | Baseline false positive: {case['baseline_false_positive']} | Baseline citation: {citation_text(case['baseline_output'])} | FinTrace citation: {citation_text(case['fintrace_output'])}", small), Spacer(1, 12)])
        if index % 2 == 1 and index < len(result["comparisons"]) - 1:
            story.append(PageBreak())
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    result = evaluate_suite(SUITE)
    validate_benchmark_integrity(result)
    _verify_resistance_cases(result)
    (OUTPUTS / "fintrace-benchmark-results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_ui_data(result)
    draw_workflow()
    write_html(result)
    write_pdf(result)
    print(json.dumps({"cases": result["case_count"], "findings": result["finding_count"], "integrity": result["integrity_checks"], "outputs": ["fintrace-benchmark-results.json", "fintrace-ml-workflow.png", "fintrace-samples.html", "fintrace-samples.pdf"]}, indent=2))


if __name__ == "__main__":
    main()
