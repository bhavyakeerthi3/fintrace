import { readFile } from "node:fs/promises";
import { join } from "node:path";

export const runtime = "nodejs";

export async function GET() {
  const documentation = await readFile(join(process.cwd(), "README.md"));
  return new Response(documentation, {
    headers: {
      "Content-Disposition": 'attachment; filename="fintrace-documentation.md"',
      "Content-Type": "text/markdown; charset=utf-8",
    },
  });
}
