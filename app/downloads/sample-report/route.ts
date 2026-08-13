import { readFile } from "node:fs/promises";
import { join } from "node:path";

export const runtime = "nodejs";

export async function GET() {
  const report = await readFile(join(process.cwd(), "outputs", "fintrace-samples.pdf"));
  return new Response(report, {
    headers: {
      "Content-Disposition": 'attachment; filename="fintrace-samples.pdf"',
      "Content-Type": "application/pdf",
    },
  });
}
