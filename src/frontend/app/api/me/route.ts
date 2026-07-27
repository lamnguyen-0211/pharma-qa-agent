import { bearerHeaders } from "../../../lib/server-auth";
const backendUrl = process.env.CORE_API_URL ?? "http://127.0.0.1:8080";
async function relay(response: Response) { return new Response(await response.text(), { status: response.status, headers: { "Content-Type": "application/json" } }); }
export async function GET() {
  const headers = await bearerHeaders();
  if (!headers) return Response.json({ error: "Sign in required." }, { status: 401 });
  try { return relay(await fetch(`${backendUrl}/api/v1/me`, { headers, signal: AbortSignal.timeout(15_000) })); }
  catch { return Response.json({ error: "The core backend is unavailable." }, { status: 503 }); }
}
export async function POST() {
  const headers = await bearerHeaders();
  if (!headers) return Response.json({ error: "Sign in required." }, { status: 401 });
  try { return relay(await fetch(`${backendUrl}/api/v1/me/consent`, { method: "POST", headers, signal: AbortSignal.timeout(15_000) })); }
  catch { return Response.json({ error: "The core backend is unavailable." }, { status: 503 }); }
}
