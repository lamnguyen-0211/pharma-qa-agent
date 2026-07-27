import { POST } from "./route";
jest.mock("../../../lib/server-auth", () => ({ bearerHeaders: jest.fn(async (extra) => ({ Authorization: "Bearer test-token", ...(extra ?? {}) })) }));

describe("business session gateway", () => {
  afterEach(() => jest.restoreAllMocks());

  it("creates an authenticated business session without client identity fields", async () => {
    const fetchMock = jest.spyOn(global, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({ id: "business-1" }), { status: 201 }));

    const response = await POST();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8080/api/v1/business-sessions",
      expect.objectContaining({ method: "POST", headers: expect.objectContaining({ Authorization: "Bearer test-token" }) }),
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
