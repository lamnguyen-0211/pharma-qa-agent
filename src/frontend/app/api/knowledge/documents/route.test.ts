import { GET, POST } from "./route";

describe("knowledge documents gateway", () => {
  afterEach(() => jest.restoreAllMocks());

  it("relays list status and body from core", async () => {
    jest.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ title: "Approved Label" }]), { status: 200 }),
    );

    const response = await GET();

    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8080/api/v1/knowledge/documents",
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual([{ title: "Approved Label" }]);
  });

  it("forwards multipart without setting a content type boundary", async () => {
    const fetchMock = jest.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ documentId: "document-1", chunkCount: 1 }), { status: 201 }),
    );
    const body = new FormData();
    body.set("file", new File(["Approved content"], "label.txt", { type: "text/plain" }));
    body.set("title", "Approved Label");

    const response = await POST(new Request("http://localhost/api/knowledge/documents", {
      method: "POST",
      body,
    }));

    expect(response.status).toBe(201);
    const options = fetchMock.mock.calls[0][1];
    expect(options?.body).toBeInstanceOf(FormData);
    expect(options?.headers).toBeUndefined();
    const forwarded = options?.body as FormData;
    expect(forwarded.get("title")).toBe("Approved Label");
    expect((forwarded.get("file") as File).name).toBe("label.txt");
  });

  it("rejects files over 10 MB before contacting core", async () => {
    const fetchMock = jest.spyOn(global, "fetch");
    const body = new FormData();
    body.set("file", new File([new Uint8Array(10_485_761)], "large.txt", { type: "text/plain" }));

    const response = await POST(new Request("http://localhost/api/knowledge/documents", {
      method: "POST",
      body,
    }));

    expect(response.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects unsupported file extensions before contacting core", async () => {
    const fetchMock = jest.spyOn(global, "fetch");
    const body = new FormData();
    body.set("file", new File(["content"], "label.docx"));

    const response = await POST(new Request("http://localhost/api/knowledge/documents", {
      method: "POST",
      body,
    }));

    expect(response.status).toBe(415);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("maps an unavailable core service to 503", async () => {
    jest.spyOn(global, "fetch").mockRejectedValue(new Error("core unavailable"));

    const response = await GET();

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      error: "The knowledge service is unavailable. Try again.",
    });
  });
});
