const backendUrl = process.env.CORE_API_URL ?? "http://127.0.0.1:8080";
import { bearerHeaders } from "../../../../lib/server-auth";
const knowledgeUrl = `${backendUrl}/api/v1/knowledge/documents`;
const MAX_UPLOAD_BYTES = 10_485_760;
const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".md"];

async function relay(response: Response) {
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}

function unavailable() {
  return Response.json(
    { error: "The knowledge service is unavailable. Try again." },
    { status: 503 },
  );
}

export async function GET() {
  const headers = await bearerHeaders();
  if (!headers) return Response.json({ error: "Sign in required." }, { status: 401 });
  try {
    const response = await fetch(knowledgeUrl, {
      method: "GET",
      headers,
      signal: AbortSignal.timeout(60_000),
    });
    return relay(response);
  } catch {
    return unavailable();
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.formData();
    const file = body.get("file");
    if (!(file instanceof File)) {
      return Response.json({ error: "Select a document file." }, { status: 400 });
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      return Response.json({ error: "Documents must be 10 MB or smaller." }, { status: 413 });
    }
    const lowerName = file.name.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
      return Response.json({ error: "Use a PDF, TXT, or Markdown document." }, { status: 415 });
    }
    const headers = await bearerHeaders();
    if (!headers) return Response.json({ error: "Sign in required." }, { status: 401 });

    const response = await fetch(knowledgeUrl, {
      method: "POST",
      body,
      headers,
      signal: AbortSignal.timeout(60_000),
    });
    return relay(response);
  } catch {
    return unavailable();
  }
}
