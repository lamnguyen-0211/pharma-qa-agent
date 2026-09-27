import { bearerHeaders } from "../../../lib/server-auth";
const backendUrl = process.env.CORE_API_URL ?? "http://127.0.0.1:8080";

async function readResponse(response: Response) {
  const data = await response.json();
  return Response.json(data, { status: response.status });
}

export async function POST() {
  const headers = await bearerHeaders({ "Content-Type": "application/json" });
  if (!headers) return Response.json({ error: "Sign in required." }, { status: 401 });
  try {
    const sessionResponse = await fetch(`${backendUrl}/api/v1/business-sessions`, {
      method: "POST",
      headers,
      signal: AbortSignal.timeout(15_000),
    });
    if (!sessionResponse.ok) return readResponse(sessionResponse);

    const session = await sessionResponse.json() as { id?: string };
    if (!session.id) return Response.json({ error: "The core backend returned an invalid session." }, { status: 503 });
    return Response.json({ businessSessionId: session.id });
  } catch {
    return Response.json({ error: "The core backend is unavailable. Start Spring Boot and try again." }, { status: 503 });
  }
}
