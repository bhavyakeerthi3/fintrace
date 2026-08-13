import benchmark from "../../../outputs/fintrace-benchmark-results.json";

export const dynamic = "force-static";

export async function GET() {
  return new Response(`${JSON.stringify(benchmark, null, 2)}\n`, {
    headers: {
      "Content-Disposition": 'attachment; filename="fintrace-benchmark-results.json"',
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}
