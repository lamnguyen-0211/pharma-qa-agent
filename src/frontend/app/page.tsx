"use client";

import { FormEvent, useState } from "react";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setAnswer(null);
    const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
    const data = await response.json();
    setAnswer(data.answer ?? data.error);
    setBusy(false);
  }

  return <main className="shell"><div className="eyebrow">PHARMA MANAGER · INTERNAL PREVIEW</div><h1>Approved knowledge,<br /><span>clearer decisions.</span></h1><p className="intro">A controlled assistant for pharmaceutical teams. Ask about approved product information and workflow guidance.</p><section className="card"><div className="status"><span /> AI service boundary active</div><form onSubmit={submit}><label htmlFor="question">What do you need to know?</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about an approved product or process…" /><button disabled={busy || !question.trim()}>{busy ? "Checking…" : "Ask assistant →"}</button></form>{answer && <div className="answer"><strong>Assistant</strong><p>{answer}</p></div>}</section><p className="notice">This preview does not provide medical diagnosis or treatment. High-risk questions require qualified human review.</p></main>;
}
