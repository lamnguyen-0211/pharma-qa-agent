import { POST } from "./route";
jest.mock("../../../lib/server-auth", () => ({ bearerHeaders: jest.fn(async (extra) => ({ Authorization: "Bearer test-token", ...(extra ?? {}) })) }));

describe("chat gateway", () => {
  afterEach(() => jest.restoreAllMocks());

  it("rejects an empty question before contacting the AI service", async () => {
    const response = await POST(new Request("http://localhost/api/chat", {
      method: "POST",
      body: JSON.stringify({ question: " " }),
      headers: { "Content-Type": "application/json" },
    }));

    expect(response.status).toBe(400);
  });

  it("rejects a chat request without a business session", async () => {
    const response = await POST(new Request("http://localhost/api/chat", {
      method: "POST",
      body: JSON.stringify({ question: "What is this?" }),
      headers: { "Content-Type": "application/json" },
    }));

    expect(response.status).toBe(400);
  });

  it("forwards both opaque session IDs and returns the AI response unchanged", async () => {
    const aiResponse = {
      businessSessionId: "business-1",
      chatSessionId: "chat-1",
      answer: "ok",
      risk_level: "low",
      citations: [],
      trace_id: "trace-1",
    };
    const fetchMock = jest.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(aiResponse), { status: 200 }),
    );

    const response = await POST(new Request("http://localhost/api/chat", {
      method: "POST",
      body: JSON.stringify({
        businessSessionId: "business-1",
        chatSessionId: "chat-1",
        question: "What is this?",
      }),
      headers: { "Content-Type": "application/json" },
    }));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8080/api/v1/chat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          businessSessionId: "business-1",
          chatSessionId: "chat-1",
          question: "What is this?",
          useKnowledgeBase: true,
        }),
      }),
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual(aiResponse);
  });

  it("forwards an explicitly disabled knowledge choice", async () => {
    const fetchMock = jest.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ answer: "general" }), { status: 200 }),
    );

    const response = await POST(new Request("http://localhost/api/chat", {
      method: "POST",
      body: JSON.stringify({
        businessSessionId: "business-1",
        question: "Explain this topic",
        useKnowledgeBase: false,
      }),
      headers: { "Content-Type": "application/json" },
    }));

    expect(response.status).toBe(200);
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({
      question: "Explain this topic",
      useKnowledgeBase: false,
    });
  });
});
