import { POST } from "./route";

describe("business session gateway", () => {
  afterEach(() => jest.restoreAllMocks());

  it("creates a local preview user and returns the core business session ID", async () => {
    const fetchMock = jest.spyOn(global, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "user-1" }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "business-1" }), { status: 201 }));

    const response = await POST();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:8080/api/v1/users",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ externalSubject: "local-preview", displayName: "Local Preview User" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://127.0.0.1:8080/api/v1/business-sessions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ userId: "user-1" }),
      }),
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ businessSessionId: "business-1" });
  });

  it("returns 503 when the core session cannot be created", async () => {
    jest.spyOn(global, "fetch").mockRejectedValue(new Error("core unavailable"));

    const response = await POST();

    expect(response.status).toBe(503);
  });
});
