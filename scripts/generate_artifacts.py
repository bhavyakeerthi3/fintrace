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

from fintrace.evaluation import evaluate_suite  # noqa: E402
from fintrace.prompts import PROMPT_REGISTRY  # noqa: E402


OUTPUTS = ROOT / "outputs"
APP = ROOT / "app"
PUBLIC = ROOT / "public"
SUITE = ROOT / "fixtures" / "benchmark-suite.json"


def write_ui_data(result: dict) -> None:
    summary = {
        "suite_version": result["suite_version"],
        "provider": result["provider"],
        "case_count": result["case_count"],
        "finding_count": result["finding_count"],
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
        }
        for name, spec in PROMPT_REGISTRY.items()
    ]
    (APP / "prompt-data.json").write_text(json.dumps(prompt_data, indent=2) + "\n", encoding="utf-8")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / filename
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def draw_workflow() -> None:
    width, height = 2200, 1400
    image = Image.new("RGB", (width, height), "#f4f0e8")
    draw = ImageDraw.Draw(image)
    ink, wine, green, muted, card, line = "#172527", "#9d373b", "#2f6b55", "#687274", "#fffdf8", "#d9d5cb"
    draw.text((110, 70), "FinTrace ML Workflow", font=font(58, True), fill=ink)
    draw.text((110, 145), "Models interpret. Code calculates. Filings provide evidence. Validators verify. Humans decide.", font=font(25), fill=muted)
    nodes = [
        ("Human input", "Role: Judge or analyst\nInput: transcript + filing\nOutput: evidence package", "human"),
        ("Transcript + filing", "Model: none\nPrompt: none\nOutput: aligned source corpus", "data"),
        ("Specialist LLM calls", "Model: configured provider\nPrompt: four scope v1 prompts\nInput: aligned claims + filing\nOutput: structured candidates", "llm"),
        ("Aggregator LLM / adapter", "Model: configured or local fallback\nPrompt: aggregator_v1 contract\nInput: specialist candidates\nOutput: stable finding IDs", "llm"),
        ("Python calculation", "DETERMINISTIC CODE - NOT AN LLM CALL\nInput: filed numeric values\nOutput: computed gap + tolerance", "code"),
        ("Filing retrieval", "Model: none\nPrompt: none\nInput: finding + full filing\nOutput: ranked passages", "data"),
        ("Second-pass LLM", "Model: configured provider\nPrompt: second_pass_v1\nInput: finding + math + passages\nOutput: explained or unresolved", "llm"),
        ("Quote validator", "Model: none\nPrompt: none\nInput: proposed filing quote\nOutput: exact match + relation check", "code"),
        ("Human analyst", "Role: final decision maker\nInput: complete evidence chain\nOutput: accept, reject, or review", "human"),
    ]
    positions = [(110,260),(785,260),(1460,260),(1460,620),(785,620),(110,620),(110,980),(785,980),(1460,980)]
    box_w, box_h = 580, 245
    for index, ((title, body, kind), (x, y)) in enumerate(zip(nodes, positions)):
        accent = wine if kind == "llm" else green if kind == "code" else ink
        draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=18, fill=card, outline=line, width=3)
        draw.rectangle((x, y, x + 11, y + box_h), fill=accent)
        draw.text((x + 38, y + 28), f"{index + 1:02d}  {title}", font=font(27, True), fill=ink)
        ty = y + 82
        for raw in body.splitlines():
            for line_text in wrap(raw, 42) or [""]:
                draw.text((x + 38, ty), line_text, font=font(19, bold=raw.startswith("DETERMINISTIC")), fill=accent if raw.startswith("DETERMINISTIC") else muted)
                ty += 28
    sequence = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8)]
    centers = [(x + box_w//2, y + box_h//2) for x,y in positions]
    for source, target in sequence:
        sx, sy = centers[source]; tx, ty = centers[target]
        if abs(tx - sx) > abs(ty - sy):
            start = (sx + (box_w//2 if tx > sx else -box_w//2), sy)
            end = (tx - (box_w//2 if tx > sx else -box_w//2), ty)
        else:
            start = (sx, sy + box_h//2)
            end = (tx, ty - box_h//2)
        draw.line((start, end), fill=wine, width=6)
        ex, ey = end
        if abs(tx - sx) > abs(ty - sy):
            direction = 1 if tx > sx else -1
            draw.polygon([(ex,ey),(ex-18*direction,ey-12),(ex-18*direction,ey+12)], fill=wine)
        else:
            draw.polygon([(ex,ey),(ex-12,ey-18),(ex+12,ey-18)], fill=wine)
    image.save(OUTPUTS / "fintrace-ml-workflow.png", optimize=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    image.save(PUBLIC / "fintrace-ml-workflow.png", optimize=True)


def classification_text(items: list[dict]) -> str:
    return ", ".join(f"{item['finding_id']}: {item['classification'].upper()}" for item in items)


def citation_text(items: list[dict]) -> str:
    attempted = [item.get("citation_valid") for item in items if item.get("classification") == "explained"]
    if not attempted:
        return "N/A"
    return "PASS" if all(value is True for value in attempted) else "FAIL"


def write_html(result: dict) -> None:
    baseline = result["ablations"]["single_prompt"]["metrics"]
    full = result["ablations"]["full_fintrace"]["metrics"]
    rows = []
    for case in result["comparisons"]:
        rows.append(f"""<article><header><span>{html.escape(case['case_id'])}</span><h2>{html.escape(case['title'])}</h2></header>
<p><b>Input:</b> {html.escape('; '.join(case['input']['claims']))}</p>
<div class="compare"><section><h3>Single Prompt</h3><p>{html.escape(classification_text(case['baseline_output']))}</p><small>Correct: {str(case['baseline_correct']).upper()} | Unsupported explanation: {str(case['baseline_unsupported_explanation']).upper()} | False positive: {str(case['baseline_false_positive']).upper()} | Citation: {citation_text(case['baseline_output'])}</small></section>
<section><h3>FinTrace Workflow</h3><p>{html.escape(classification_text(case['fintrace_output']))}</p><small>Correct: {str(case['fintrace_correct']).upper()} | Unsupported explanation: {str(case['fintrace_unsupported_explanation']).upper()} | Citation: {citation_text(case['fintrace_output'])}</small></section></div>
<p class="expected"><b>Expected:</b> {html.escape(classification_text(case['expected_result']))}</p></article>""")
    document = f"""<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FinTrace Samples</title><style>
body{{margin:0;background:#f4f0e8;color:#172527;font:15px Arial,sans-serif}}main{{max-width:1100px;margin:auto;padding:60px 28px}}h1{{font:56px Georgia,serif;margin:0}}.lede{{color:#687274;font-size:18px;line-height:1.6}}.notice{{padding:16px;border-left:4px solid #9d373b;background:#fffdf8}}.metrics{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;margin:34px 0}}.metric,article{{background:#fffdf8;border:1px solid #d9d5cb;padding:24px}}.metric strong{{font-size:36px;color:#9d373b}}article{{margin:18px 0}}article header{{display:flex;gap:16px;align-items:center}}article header span{{font:12px monospace;color:#9d373b}}h2{{font:28px Georgia,serif;margin:0}}.compare{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.compare section{{padding:16px;background:#f4f0e8}}h3{{font-size:13px;text-transform:uppercase;letter-spacing:.08em}}small{{color:#687274}}.expected{{border-top:1px solid #d9d5cb;padding-top:14px}}table{{width:100%;border-collapse:collapse;background:#fffdf8}}th,td{{padding:12px;border:1px solid #d9d5cb;text-align:right}}th:first-child,td:first-child{{text-align:left}}@media(max-width:700px){{.compare,.metrics{{grid-template-columns:1fr}}}}</style></head><body><main>
<p>REVERIE HACKS 2026 | CONTROLLED FICTIONAL BENCHMARK</p><h1>FinTrace Samples</h1><p class="lede">The same 12 cases and 13 findings are evaluated by a simple single-prompt heuristic and the complete FinTrace workflow.</p><p class="notice">Measured with the local deterministic benchmark adapter. These results describe this controlled fixture suite only and are not a claim about general model performance.</p>
<div class="metrics"><div class="metric"><span>Single-prompt overall score</span><br><strong>{baseline['overall_score']}%</strong><p>{baseline['correct_classifications']} / {baseline['finding_count']} correct classifications</p></div><div class="metric"><span>Full-workflow overall score</span><br><strong>{full['overall_score']}%</strong><p>{full['correct_classifications']} / {full['finding_count']} correct classifications</p></div></div>
<h2>Measured ablation results</h2><table><tr><th>Mode</th><th>Correct</th><th>Unsupported</th><th>Numeric accuracy</th><th>Overall</th></tr>{''.join(f"<tr><td>{name.replace('_',' ').title()}</td><td>{data['metrics']['correct_classifications']}/{data['metrics']['finding_count']}</td><td>{data['metrics']['unsupported_explanations']}</td><td>{data['metrics']['numerical_reconciliation_accuracy']}%</td><td>{data['metrics']['overall_score']}%</td></tr>" for name,data in result['ablations'].items())}</table>
<h2>Case-by-case comparison</h2>{''.join(rows)}
</main></body></html>"""
    (OUTPUTS / "fintrace-samples.html").write_text(document, encoding="utf-8")


def write_pdf(result: dict) -> None:
    path = OUTPUTS / "fintrace-samples.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=.55*inch, leftMargin=.55*inch, topMargin=.55*inch, bottomMargin=.55*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=30, leading=36, alignment=TA_CENTER, textColor=colors.HexColor("#172527"), spaceAfter=8)
    subtitle_style = ParagraphStyle(name="Subtitle", fontName="Helvetica", fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#687274"), spaceAfter=18)
    body_style = ParagraphStyle(name="ReportBody", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#172527"), spaceAfter=8)
    case_title_style = ParagraphStyle(name="CaseTitle", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=colors.HexColor("#172527"), spaceBefore=10, spaceAfter=5, keepWithNext=False)
    cell_style = ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=6.8, leading=8.5, textColor=colors.HexColor("#172527"))
    cell_head_style = ParagraphStyle(name="CellHead", parent=cell_style, fontName="Helvetica-Bold")
    story = [Paragraph("FinTrace Samples", title_style), Paragraph("Controlled fictional benchmark - 12 cases, 13 findings", subtitle_style)]
    story.append(Paragraph("Measured with the local deterministic benchmark adapter. Results apply only to this controlled suite and are not general model-performance claims.", body_style))
    story.append(Spacer(1, 14))
    data = [["Mode", "Correct", "Unsupported", "Numeric", "Overall"]]
    for name, payload in result["ablations"].items():
        m = payload["metrics"]
        data.append([name.replace("_", " ").title(), f"{m['correct_classifications']}/{m['finding_count']}", str(m["unsupported_explanations"]), f"{m['numerical_reconciliation_accuracy']}%", f"{m['overall_score']}%"])
    table = Table(data, colWidths=[2.25*inch, .8*inch, 1*inch, .85*inch, .75*inch])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#172527")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#d9d5cb")),("FONTSIZE",(0,0),(-1,-1),8),("ALIGN",(1,1),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f4f0e8")])]))
    story.extend([table, Spacer(1, 18)])
    story.append(Paragraph("How to read this report", case_title_style))
    story.append(Paragraph("Every case is labeled in advance. The single-prompt path accepts a candidate explanation without the full calculation and validation gates. FinTrace adds deterministic arithmetic, direct-connection checks, exact quote matching, and unresolved-by-default behavior. Overall score is the mean of six measured rates documented in the JSON output.", body_style))
    story.append(PageBreak())
    for index, case in enumerate(result["comparisons"]):
        story.append(Paragraph(f"{case['case_id']} - {case['title']}", case_title_style))
        story.append(Paragraph("Input: " + "; ".join(case["input"]["claims"]), body_style))
        comparison = [
            [Paragraph("Single Prompt", cell_head_style), Paragraph("FinTrace Workflow", cell_head_style), Paragraph("Expected", cell_head_style)],
            [Paragraph(classification_text(case["baseline_output"]), cell_style), Paragraph(classification_text(case["fintrace_output"]), cell_style), Paragraph(classification_text(case["expected_result"]), cell_style)],
            [Paragraph(f"Correct: {case['baseline_correct']} | Unsupported: {case['baseline_unsupported_explanation']} | Citation: {citation_text(case['baseline_output'])}", cell_style), Paragraph(f"Correct: {case['fintrace_correct']} | Unsupported: {case['fintrace_unsupported_explanation']} | Citation: {citation_text(case['fintrace_output'])}", cell_style), Paragraph("Adjudicated fixture label", cell_style)],
        ]
        case_table = Table(comparison, colWidths=[2.2*inch,2.2*inch,2.2*inch])
        case_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#ebe6dc")),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#d9d5cb")),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP"),("LEADING",(0,0),(-1,-1),9)]))
        story.extend([Spacer(1,8), case_table, Spacer(1,16)])
        if index in {3, 7}:
            story.append(PageBreak())
    doc.build(story)


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    result = evaluate_suite(SUITE)
    (OUTPUTS / "fintrace-benchmark-results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_ui_data(result)
    draw_workflow()
    write_html(result)
    write_pdf(result)
    print(json.dumps({"cases": result["case_count"], "findings": result["finding_count"], "outputs": ["fintrace-benchmark-results.json", "fintrace-ml-workflow.png", "fintrace-samples.html", "fintrace-samples.pdf"]}, indent=2))


if __name__ == "__main__":
    main()
