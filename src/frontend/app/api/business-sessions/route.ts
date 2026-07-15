const backendUrl = process.env.CORE_API_URL ?? "http://127.0.0.1:8080";

async function readResponse(response: Response) {
  const data = await response.json();
  return Response.json(data, { status: response.status });
}

export async function POST() {
  try {
    const userResponse = await fetch(`${backendUrl}/api/v1/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ externalSubject: "local-preview", displayName: "Local Preview User" }),
      signal: AbortSignal.timeout(15_000),
    });
    if (!userResponse.ok) return readResponse(userResponse);

    const user = await userResponse.json() as { id?: string };
    if (!user.id) return Response.json({ error: "The core backend returned an invalid user." }, { status: 503 });

    const sessionResponse = await fetch(`${backendUrl}/api/v1/business-sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: user.id }),
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
