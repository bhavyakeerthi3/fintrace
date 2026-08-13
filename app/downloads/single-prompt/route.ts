import results from "../../../outputs/fintrace-single-prompt-live-results.json";

export const dynamic = "force-static";

export async function GET() {
  return new Response(`${JSON.stringify(results, null, 2)}\n`, {
    headers: {
      "Content-Disposition": 'attachment; filename="fintrace-single-prompt-live-results.json"',
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}
