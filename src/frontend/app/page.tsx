"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";

type MessageRole = "user" | "assistant";
type MessageStatus = "pending" | "error";

type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  status?: MessageStatus;
  riskLevel?: string;
};

type BusinessSessionResponse = {
  businessSessionId?: string;
  error?: string;
};

type ChatResponse = {
  answer?: string;
  chatSessionId?: string;
  risk_level?: string;
  error?: string;
};

const MAX_QUESTION_LENGTH = 4000;
const starterPrompts = [
  "What can I ask?",
  "How do I ask about a product?",
  "When should I involve a qualified reviewer?",
];

let messageSequence = 0;

function createMessageId(prefix: MessageRole) {
  messageSequence += 1;
  return `${prefix}-${messageSequence}`;
}

function isElevatedRisk(riskLevel?: string) {
  return riskLevel ? ["high", "emergency"].includes(riskLevel.toLowerCase()) : false;
}

export default function Home() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [businessSessionId, setBusinessSessionId] = useState<string | null>(null);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;

    async function createBusinessSession() {
      try {
        const response = await fetch("/api/business-sessions", { method: "POST" });
        const data = await response.json() as BusinessSessionResponse;
        if (!response.ok || !data.businessSessionId) {
          throw new Error(data.error ?? "Unable to start a business session.");
        }
        if (active) setBusinessSessionId(data.businessSessionId);
      } catch (error) {
        if (active) {
          setSessionError(error instanceof Error ? error.message : "Unable to start a business session.");
        }
      }
    }

    void createBusinessSession();
    return () => {
      active = false;
    };
  }, []);

  async function sendQuestion(value: string, retryMessageId?: string) {
    const trimmedQuestion = value.trim();
    if (!trimmedQuestion || !businessSessionId || busy) return;

    const assistantMessageId = retryMessageId ?? createMessageId("assistant");
    if (retryMessageId) {
      setMessages((currentMessages) => currentMessages.map((message) => (
        message.id === retryMessageId
          ? { ...message, content: "Reviewing your question…", status: "pending", riskLevel: undefined }
          : message
      )));
    } else {
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: createMessageId("user"), role: "user", content: trimmedQuestion },
        { id: assistantMessageId, role: "assistant", content: "Reviewing your question…", status: "pending" },
      ]);
      setQuestion("");
    }

    setBusy(true);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          businessSessionId,
          ...(chatSessionId ? { chatSessionId } : {}),
          question: trimmedQuestion,
        }),
      });
      const data = await response.json() as ChatResponse;
      if (!response.ok) {
        throw new Error(data.error ?? "The assistant could not be reached.");
      }

      if (data.chatSessionId) setChatSessionId(data.chatSessionId);
      setMessages((currentMessages) => currentMessages.map((message) => (
        message.id === assistantMessageId
          ? {
            ...message,
            content: data.answer ?? data.error ?? "The assistant did not return a response.",
            status: undefined,
            riskLevel: data.risk_level,
          }
          : message
      )));
    } catch {
      setMessages((currentMessages) => currentMessages.map((message) => (
        message.id === assistantMessageId
          ? { ...message, content: "The assistant could not be reached.", status: "error", riskLevel: undefined }
          : message
      )));
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void sendQuestion(question);
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendQuestion(question);
    }
  }

  function retryMessage(messageId: string) {
    const messageIndex = messages.findIndex((message) => message.id === messageId);
    const originalQuestion = messages
      .slice(0, messageIndex)
      .reverse()
      .find((message) => message.role === "user")?.content;
    if (originalQuestion) void sendQuestion(originalQuestion, messageId);
  }

  function startNewConversation() {
    if (busy) return;
    setMessages([]);
    setChatSessionId(null);
    setQuestion("");
    setSessionError(null);
  }

  const currentRiskLevel = useMemo(
    () => [...messages].reverse().find((message) => message.riskLevel)?.riskLevel ?? "low",
    [messages],
  );
  const sessionStatus = sessionError ? "Session unavailable" : businessSessionId ? "Connected" : "Starting…";
  const canSend = Boolean(businessSessionId && question.trim() && !busy && !sessionError);

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Workspace navigation">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">PM</div>
          <div>
            <p className="brand-name">Pharma Manager</p>
            <p className="brand-subtitle">Internal assistant</p>
          </div>
        </div>

        <button className="new-conversation" type="button" onClick={startNewConversation} disabled={busy}>
          <span aria-hidden="true">+</span>
          New conversation
        </button>

        <div className="sidebar-section">
          <p className="sidebar-label">Current thread</p>
          <div className="thread-card">
            <span className="thread-icon" aria-hidden="true">◌</span>
            <span>{messages.length ? "Untitled conversation" : "New conversation"}</span>
          </div>
        </div>

        <div className="sidebar-footer">
          <p className="sidebar-label">Session status</p>
          <div className={`session-status ${sessionError ? "is-error" : ""}`}>
            <span className="status-dot" aria-hidden="true" />
            <span>{sessionStatus}</span>
          </div>
          {sessionError && <p className="session-help">Refresh after the core service is available.</p>}
        </div>
      </aside>

      <main className="chat-workspace">
        <header className="chat-header">
          <div>
            <p className="eyebrow">PHARMA MANAGER · INTERNAL PREVIEW</p>
            <h1>Pharma assistant</h1>
            <p>Approved knowledge workspace</p>
          </div>
          <div className={`connection-pill ${sessionError ? "is-error" : ""}`}>
            <span className="status-dot" aria-hidden="true" />
            {sessionStatus}
          </div>
        </header>

        {sessionError && (
          <div className="workspace-alert" role="alert">
            <strong>Session unavailable</strong>
            <span>{sessionError} Refresh after the core service is available.</span>
          </div>
        )}

        <section className="conversation" aria-label="Conversation">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="welcome-icon" aria-hidden="true">✦</div>
              <p className="eyebrow">READY WHEN YOU ARE</p>
              <h2>What can we work through?</h2>
              <p className="empty-copy">
                Ask about approved product information, internal workflows, or when a qualified reviewer should take over.
              </p>
              <div className="starter-prompts" aria-label="Starter prompts">
                {starterPrompts.map((prompt) => (
                  <button key={prompt} type="button" onClick={() => void sendQuestion(prompt)} disabled={!businessSessionId || Boolean(sessionError) || busy}>
                    <span aria-hidden="true">↗</span>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-list" aria-live="polite">
              {messages.map((message) => (
                <article className={`message-row ${message.role}`} key={message.id}>
                  <div className={`message-bubble ${message.status ?? ""} ${isElevatedRisk(message.riskLevel) ? "risk-warning" : ""}`}>
                    <div className="message-meta">
                      <span>{message.role === "user" ? "You" : "Pharma assistant"}</span>
                      {message.riskLevel && <span className="risk-label">Risk: {message.riskLevel}</span>}
                    </div>
                    <p>{message.content}</p>
                    {message.status === "error" && (
                      <button className="retry-button" type="button" onClick={() => retryMessage(message.id)} disabled={busy}>
                        Retry
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <form className="composer" aria-label="Ask the assistant" onSubmit={submit}>
          <div className="composer-input">
            <label className="sr-only" htmlFor="question">Ask the assistant</label>
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder="Ask about an approved product or process…"
              maxLength={MAX_QUESTION_LENGTH}
              rows={2}
              disabled={!businessSessionId || Boolean(sessionError)}
            />
          </div>
          <div className="composer-footer">
            <span className="character-count">{question.length}/{MAX_QUESTION_LENGTH}</span>
            <button className="send-button" type="submit" aria-label={busy ? "Sending…" : "Send message"} disabled={!canSend}>
              {busy ? "Sending…" : "Send"}
              <span aria-hidden="true">↗</span>
            </button>
          </div>
        </form>
        <p className="mobile-safety">Preview only · not a diagnostic, treatment, or emergency-response system.</p>
      </main>

      <aside className={`safety-panel ${isElevatedRisk(currentRiskLevel) ? "risk-warning" : ""}`} aria-label="Safety boundary">
        <div className="safety-heading">
          <span className="shield-icon" aria-hidden="true">✓</span>
          <div>
            <p className="sidebar-label">Safety boundary</p>
            <h2>Human judgment stays in the loop.</h2>
          </div>
        </div>
        <p>This preview supports information work. It does not provide medical diagnosis, treatment, or emergency response.</p>
        <div className="risk-state">
          <span className="risk-state-label">Current risk state</span>
          <strong>{currentRiskLevel}</strong>
        </div>
        <div className="safety-divider" />
        <p className="safety-footnote">High-risk questions are flagged for qualified human review.</p>
      </aside>
    </div>
  );
}
