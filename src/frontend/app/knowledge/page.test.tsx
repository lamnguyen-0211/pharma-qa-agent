/** @jest-environment jsdom */

import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import KnowledgePage from "./page";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const indexedDocument = {
  documentId: "document-1",
  originalFilename: "label.txt",
  title: "Approved Label",
  documentType: "PRODUCT_LABEL",
  language: "en",
  version: "3.2",
  approvalStatus: "APPROVED",
  accessClassification: "INTERNAL",
  embeddingModelName: "fake-embedding",
  embeddingDimension: 1024,
  chunkCount: 1,
  createdAt: "2026-07-18T00:00:00Z",
};

describe("knowledge base workspace", () => {
  afterEach(() => {
    jest.restoreAllMocks();
    delete (globalThis as { fetch?: typeof fetch }).fetch;
  });

  it("uploads an approved document and prepends it to the list", async () => {
    const fetchMock = jest.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(indexedDocument, 201));
    global.fetch = fetchMock;

    render(<KnowledgePage />);

    expect(await screen.findByRole("heading", { name: "Knowledge base" })).toBeInTheDocument();
    const file = new File(["Product A approved information"], "label.txt", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("Document file"), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Approved Label" } });
    fireEvent.change(screen.getByLabelText("Version"), { target: { value: "3.2" } });
    expect(screen.getByLabelText("Document file")).toBeValid();
    expect(screen.getByLabelText("Title")).toBeValid();
    expect(screen.getByLabelText("Document type")).toBeValid();
    expect(screen.getByLabelText("Version")).toBeValid();
    expect(screen.getByLabelText("Language")).toBeValid();
    expect(screen.getByLabelText("Approval status")).toBeValid();
    expect(screen.getByLabelText("Access classification")).toBeValid();
    const uploadButton = screen.getByRole("button", { name: "Upload and index" });
    expect(uploadButton.closest("form")).toBeValid();
    fireEvent.click(uploadButton);

    expect(await screen.findByText("Approved Label")).toBeInTheDocument();
    expect(await screen.findByText("1 chunk")).toBeInTheDocument();
    const uploadBody = fetchMock.mock.calls[1][1]?.body as FormData;
    expect((uploadBody.get("file") as File).name).toBe("label.txt");
    expect(uploadBody.get("approvalStatus")).toBe("APPROVED");
  });

  it("keeps metadata visible when upload is retryable", async () => {
    const fetchMock = jest.fn()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ error: "The knowledge service is unavailable. Try again." }, 503));
    global.fetch = fetchMock;

    render(<KnowledgePage />);
    await screen.findByRole("heading", { name: "Knowledge base" });
    const file = new File(["Product A approved information"], "label.txt", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("Document file"), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Approved Label" } });
    const uploadButton = screen.getByRole("button", { name: "Upload and index" });
    expect(uploadButton.closest("form")).toBeValid();
    fireEvent.click(uploadButton);

    expect(await screen.findByRole("alert")).toHaveTextContent("The knowledge service is unavailable. Try again.");
    expect(screen.getByLabelText("Title")).toHaveValue("Approved Label");
    const selectedFile = (screen.getByLabelText("Document file") as HTMLInputElement).files?.[0];
    expect(selectedFile?.name).toBe("label.txt");
  });
});
