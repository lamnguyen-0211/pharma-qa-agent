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
      if (input === "/api/business-sessions") {
        return jsonResponse({ businessSessionId: "business-1" }, 201);
      }

      expect(input).toBe("/api/chat");
      expect(JSON.parse(String(init?.body))).toEqual({
        businessSessionId: "business-1",
        question: "What can I ask?",
      });
      return jsonResponse({
        chatSessionId: "chat-1",
        answer: "Ask about approved product information.",
        risk_level: "low",
      });
    });
    global.fetch = fetchMock;

    render(<Home />);

    const sendButton = screen.getByRole("button", { name: "Send message" });
    expect(sendButton).toBeDisabled();
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask the assistant" })).toBeEnabled());

    fireEvent.click(screen.getByRole("button", { name: "What can I ask?" }));

    expect(await screen.findByText("What can I ask?")).toBeInTheDocument();
    expect(await screen.findByText("Ask about approved product information.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("keeps the question visible and offers retry after chat failure", async () => {
    const fetchMock = jest.fn(async (input: RequestInfo | URL) => {
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
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("retries the original question and starts a fresh conversation", async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock;
    fetchMock
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
    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body))).toEqual({
      businessSessionId: "business-1",
      question: "What is this preview for?",
    });

    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));

    await waitFor(() => {
      expect(screen.queryByText("What is this preview for?")).not.toBeInTheDocument();
      expect(screen.queryByText("The preview supports approved product questions.")).not.toBeInTheDocument();
    });
    expect(screen.getByRole("textbox", { name: "Ask the assistant" })).toBeEnabled();
  });
});
