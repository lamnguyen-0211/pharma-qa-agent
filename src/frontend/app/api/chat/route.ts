import { z } from "zod";

const requestSchema = z.object({
  businessSessionId: z.string().trim().min(1).max(36),
  chatSessionId: z.string().trim().min(1).max(36).nullable().optional(),
  question: z.string().trim().min(1).max(4000),
});
const backendUrl = process.env.CORE_API_URL ?? "http://127.0.0.1:8080";

export async function POST(request: Request) {
  try {
    const input = requestSchema.parse(await request.json());
    const response = await fetch(`${backendUrl}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      signal: AbortSignal.timeout(15_000),
    });

    const data = await response.json();
    return Response.json(data, { status: response.status });
  } catch (error) {
    if (error instanceof z.ZodError) return Response.json({ error: "Enter a question between 1 and 4,000 characters." }, { status: 400 });
    return Response.json({ error: "The core backend is unavailable. Start Spring Boot and try again." }, { status: 503 });
  }
}
