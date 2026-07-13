import { POST } from "./route";

describe("chat gateway", () => {
  it("rejects an empty question before contacting the AI service", async () => {
    const response = await POST(new Request("http://localhost/api/chat", {
      method: "POST",
      body: JSON.stringify({ question: " " }),
      headers: { "Content-Type": "application/json" },
    }));

    expect(response.status).toBe(400);
  });
});
