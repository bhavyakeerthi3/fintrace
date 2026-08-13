import { ImageResponse } from "next/og";

export const alt = "FinTrace - What they said, what they filed, what the math says";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", padding: "62px 68px", background: "#f2eee6", color: "#172426", position: "relative", overflow: "hidden" }}>
      <div style={{ width: "54%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 20, fontWeight: 700, letterSpacing: "0.08em" }}><div style={{ width: 38, height: 38, borderRadius: 999, display: "flex", alignItems: "center", justifyContent: "center", background: "#172426", color: "#f2eee6" }}>F</div>FINTRACE</div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ color: "#ad3538", fontSize: 15, fontWeight: 700, letterSpacing: "0.18em", marginBottom: 24 }}>EVIDENCE-FIRST FINANCIAL REVIEW</div>
          <div style={{ display: "flex", flexDirection: "column", fontSize: 66, fontWeight: 600, lineHeight: 0.98, letterSpacing: "-0.045em" }}><span>What they said.</span><span>What they filed.</span><span style={{ color: "#ad3538", fontStyle: "italic", fontWeight: 400 }}>What the math says.</span></div>
        </div>
        <div style={{ fontSize: 18, color: "#5e696a" }}>Models interpret. Code calculates. Humans decide.</div>
      </div>
      <div style={{ width: "46%", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
        <div style={{ position: "absolute", width: 390, height: 390, right: -22, top: 28, background: "#e3ddd2", border: "1px solid #d2cabd", transform: "rotate(5deg)" }} />
        <div style={{ width: 430, height: 360, display: "flex", flexDirection: "column", padding: "34px 38px", background: "#fffdf8", border: "1px solid #d2cabd", boxShadow: "0 24px 55px rgba(50,45,36,.14)", transform: "rotate(-3deg)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", paddingBottom: 18, borderBottom: "1px solid #d2cabd", color: "#6b7678", fontSize: 13, letterSpacing: "0.14em" }}><span>EARNINGS CALL</span><span>Q2 | FY26</span></div>
          <div style={{ display: "flex", marginTop: 40, fontSize: 31, lineHeight: 1.25 }}>&quot;Organic revenue grew 23 percent year over year.&quot;</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 42, paddingTop: 18, borderTop: "1px solid #172426" }}><div style={{ display: "flex", flexDirection: "column", gap: 7, color: "#6b7678", fontSize: 12, letterSpacing: "0.1em" }}><span>PYTHON RECOMPUTED</span><span style={{ color: "#ad3538", letterSpacing: 0 }}>-10.27 pp</span></div><strong style={{ color: "#ad3538", fontSize: 45 }}>12.73%</strong></div>
        </div>
      </div>
      <div style={{ position: "absolute", height: 4, width: "100%", left: 0, bottom: 0, background: "#ad3538" }} />
    </div>,
    size,
  );
}
