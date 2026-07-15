"use client";

import { FormEvent, useState } from "react";
import { useEffect } from "react";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [businessSessionId, setBusinessSessionId] = useState<string | null>(null);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;

    async function createBusinessSession() {
      try {
        const response = await fetch("/api/business-sessions", { method: "POST" });
        const data = await response.json() as { businessSessionId?: string; error?: string };
        if (!response.ok || !data.businessSessionId) {
          throw new Error(data.error ?? "Unable to start a business session.");
        }
        if (active) setBusinessSessionId(data.businessSessionId);
      } catch (error) {
        if (active) setSessionError(error instanceof Error ? error.message : "Unable to start a business session.");
      }
    }

    void createBusinessSession();
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || !businessSessionId) return;
    setBusy(true);
    setAnswer(null);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          businessSessionId,
          ...(chatSessionId ? { chatSessionId } : {}),
          question,
        }),
      });
      const data = await response.json() as { answer?: string; chatSessionId?: string; error?: string };
      if (response.ok && data.chatSessionId) setChatSessionId(data.chatSessionId);
      setAnswer(data.answer ?? data.error ?? "The assistant did not return a response.");
    } catch {
      setAnswer("The core backend is unavailable. Start Spring Boot and try again.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="shell"><div className="eyebrow">PHARMA MANAGER · INTERNAL PREVIEW</div><h1>Approved knowledge,<br /><span>clearer decisions.</span></h1><p className="intro">A controlled assistant for pharmaceutical teams. Ask about approved product information and workflow guidance.</p><section className="card"><div className="status"><span /> {businessSessionId ? "AI service boundary active" : "Starting secure business session…"}</div><form onSubmit={submit}><label htmlFor="question">What do you need to know?</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about an approved product or process…" /><button disabled={busy || !question.trim() || !businessSessionId}>{busy ? "Checking…" : "Ask assistant →"}</button></form>{sessionError && <div className="answer"><strong>Session unavailable</strong><p>{sessionError}</p></div>}{answer && <div className="answer"><strong>Assistant</strong><p>{answer}</p></div>}</section><p className="notice">This preview does not provide medical diagnosis or treatment. High-risk questions require qualified human review.</p></main>;
}
