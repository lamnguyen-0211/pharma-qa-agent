/** @jest-environment jsdom */

import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Home from "./page";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("Pharma Manager chat workspace", () => {
  afterEach(() => {
    jest.restoreAllMocks();
    delete (globalThis as { fetch?: typeof fetch }).fetch;
  });

  it("bootstraps a business session and submits a starter prompt", async () => {
    const fetchMock = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (input === "/api/me") return jsonResponse({ displayName: "User", consentAccepted: true, consentVersion: "2026-07-27" });
      if (input === "/api/business-sessions") {
        return jsonResponse({ businessSessionId: "business-1" }, 201);
      }

      expect(input).toBe("/api/chat");
      expect(JSON.parse(String(init?.body))).toEqual({
        businessSessionId: "business-1",
        question: "What can I ask?",
        useKnowledgeBase: true,
      });
      return jsonResponse({
        chatSessionId: "chat-1",
        answer: "Ask about approved product information.",
        risk_level: "low",
      });
    });
    global.fetch = fetchMock;

    render(<Home />);

    await waitFor(() => expect(screen.getByText("Checking your workspace access…")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask the assistant" })).toBeEnabled());
    const sendButton = screen.getByRole("button", { name: "Send message" });
    expect(sendButton).toBeDisabled();
    expect(screen.getByRole("link", { name: "Knowledge base" })).toHaveAttribute("href", "/knowledge");

    fireEvent.click(screen.getByRole("button", { name: "What can I ask?" }));

    expect(await screen.findByText("What can I ask?")).toBeInTheDocument();
    expect(await screen.findByText("Ask about approved product information.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("keeps the question visible and offers retry after chat failure", async () => {
    const fetchMock = jest.fn(async (input: RequestInfo | URL) => {
      if (input === "/api/me") return jsonResponse({ displayName: "User", consentAccepted: true, consentVersion: "2026-07-27" });
      if (input === "/api/business-sessions") {
        return jsonResponse({ businessSessionId: "business-1" }, 201);
      }

      throw new Error("core unavailable");
    });
    global.fetch = fetchMock;

    render(<Home />);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask the assistant" })).toBeEnabled());

    const textarea = screen.getByRole("textbox", { name: "Ask the assistant" });
    fireEvent.change(textarea, { target: { value: "What is this preview for?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("What is this preview for?")).toBeInTheDocument();
    expect(await screen.findByText("The assistant could not be reached.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("retries the original question and starts a fresh conversation", async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock;
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ displayName: "User", consentAccepted: true, consentVersion: "2026-07-27" }))
      .mockResolvedValueOnce(jsonResponse({ businessSessionId: "business-1" }, 201))
      .mockRejectedValueOnce(new Error("core unavailable"))
      .mockResolvedValueOnce(jsonResponse({
        chatSessionId: "chat-2",
        answer: "The preview supports approved product questions.",
        risk_level: "low",
      }));

    render(<Home />);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask the assistant" })).toBeEnabled());

    const textarea = screen.getByRole("textbox", { name: "Ask the assistant" });
    fireEvent.change(textarea, { target: { value: "What is this preview for?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await screen.findByRole("button", { name: "Retry" });

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("The preview supports approved product questions.")).toBeInTheDocument();
    expect(JSON.parse(String(fetchMock.mock.calls[3][1]?.body))).toEqual({
      businessSessionId: "business-1",
      question: "What is this preview for?",
      useKnowledgeBase: true,
    });

    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));

    await waitFor(() => {
      expect(screen.queryByText("What is this preview for?")).not.toBeInTheDocument();
      expect(screen.queryByText("The preview supports approved product questions.")).not.toBeInTheDocument();
    });
    expect(screen.getByRole("textbox", { name: "Ask the assistant" })).toBeEnabled();
  });

  it("copies the current knowledge choice into each message and renders citations", async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock;
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ displayName: "User", consentAccepted: true, consentVersion: "2026-07-27" }))
      .mockResolvedValueOnce(jsonResponse({ businessSessionId: "business-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({
        chatSessionId: "chat-1",
        answer: "Product A has approved internal information.",
        risk_level: "low",
        citations: [{
          documentId: "document-1",
          title: "Approved Label",
          version: "3.2",
          page: 4,
          chunkId: "chunk-1",
        }],
      }))
      .mockResolvedValueOnce(jsonResponse({
        chatSessionId: "chat-1",
        answer: "General answer.",
        risk_level: "low",
        citations: [],
      }));

    render(<Home />);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask the assistant" })).toBeEnabled());

    const knowledgeSwitch = screen.getByRole("checkbox", { name: "Use knowledge base" });
    expect(knowledgeSwitch).toBeChecked();
    const textarea = screen.getByRole("textbox", { name: "Ask the assistant" });
    fireEvent.change(textarea, { target: { value: "What is Product A used for?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("Approved Label · v3.2 · page 4")).toBeInTheDocument();
    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body))).toMatchObject({
      question: "What is Product A used for?",
      useKnowledgeBase: true,
    });

    fireEvent.click(knowledgeSwitch);
    expect(knowledgeSwitch).not.toBeChecked();
    fireEvent.change(textarea, { target: { value: "Explain this generally" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("General answer.")).toBeInTheDocument();
    expect(JSON.parse(String(fetchMock.mock.calls[3][1]?.body))).toEqual({
      businessSessionId: "business-1",
      chatSessionId: "chat-1",
      question: "Explain this generally",
      useKnowledgeBase: false,
    });
  });
});
