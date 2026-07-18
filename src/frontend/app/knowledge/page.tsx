"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import type { KnowledgeDocument } from "../../lib/ai";

type UploadFields = {
  title: string;
  documentType: string;
  product: string;
  activeIngredient: string;
  market: string;
  jurisdiction: string;
  language: string;
  effectiveDate: string;
  expirationDate: string;
  version: string;
  approvalStatus: string;
  audience: string;
  accessClassification: string;
};

const initialFields: UploadFields = {
  title: "",
  documentType: "PRODUCT_LABEL",
  product: "",
  activeIngredient: "",
  market: "",
  jurisdiction: "",
  language: "en",
  effectiveDate: "",
  expirationDate: "",
  version: "1.0",
  approvalStatus: "APPROVED",
  audience: "INTERNAL",
  accessClassification: "INTERNAL",
};

function errorMessage(data: unknown) {
  if (data && typeof data === "object") {
    const value = data as { error?: unknown; detail?: unknown };
    if (typeof value.error === "string") return value.error;
    if (typeof value.detail === "string") return value.detail;
  }
  return "The document could not be indexed. Try again.";
}

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [fields, setFields] = useState<UploadFields>(initialFields);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    async function loadDocuments() {
      try {
        const response = await fetch("/api/knowledge/documents");
        const data = await response.json() as unknown;
        if (!response.ok || !Array.isArray(data)) throw new Error(errorMessage(data));
        if (active) setDocuments(data as KnowledgeDocument[]);
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Knowledge documents are unavailable.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadDocuments();
    return () => {
      active = false;
    };
  }, []);

  function updateField(name: keyof UploadFields, value: string) {
    setFields((current) => ({ ...current, [name]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || uploading) return;

    const body = new FormData();
    body.set("file", file);
    Object.entries(fields).forEach(([name, value]) => {
      if (value) body.set(name, value);
    });

    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch("/api/knowledge/documents", { method: "POST", body });
      const data = await response.json() as KnowledgeDocument | { error?: string; detail?: string };
      if (!response.ok || !("documentId" in data)) throw new Error(errorMessage(data));
      setDocuments((current) => [data, ...current.filter((item) => item.documentId !== data.documentId)]);
      setSuccess("Document indexed successfully.");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "The document could not be indexed. Try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="knowledge-workspace">
      <header className="knowledge-header">
        <div>
          <p className="eyebrow">PHARMA MANAGER · INTERNAL PREVIEW</p>
          <h1>Knowledge base</h1>
          <p>Index approved pharmaceutical documents for grounded chat responses.</p>
        </div>
        <Link className="back-link" href="/">← Back to chat</Link>
      </header>

      <div className="knowledge-warning" role="note">
        <strong>Local preview only.</strong>
        <span>Authentication and role-based document access are not implemented yet.</span>
      </div>

      {error && <div className="knowledge-alert is-error" role="alert">{error}</div>}
      {success && <div className="knowledge-alert is-success" role="status">{success}</div>}

      <div className="knowledge-grid">
        <section className="knowledge-card" aria-labelledby="upload-heading">
          <h2 id="upload-heading">Upload document</h2>
          <p>PDF, UTF-8 TXT, or Markdown up to 10 MB.</p>
          <form className="knowledge-form" onSubmit={submit}>
            <label className="full-field">
              Document file
              <input
                ref={fileInput}
                type="file"
                accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <label className="full-field">
              Title
              <input required maxLength={255} value={fields.title} onChange={(event) => updateField("title", event.target.value)} />
            </label>
            <label>
              Document type
              <input required maxLength={100} value={fields.documentType} onChange={(event) => updateField("documentType", event.target.value)} />
            </label>
            <label>
              Version
              <input required maxLength={64} value={fields.version} onChange={(event) => updateField("version", event.target.value)} />
            </label>
            <label>
              Product
              <input maxLength={255} value={fields.product} onChange={(event) => updateField("product", event.target.value)} />
            </label>
            <label>
              Active ingredient
              <input maxLength={255} value={fields.activeIngredient} onChange={(event) => updateField("activeIngredient", event.target.value)} />
            </label>
            <label>
              Market
              <input maxLength={100} value={fields.market} onChange={(event) => updateField("market", event.target.value)} />
            </label>
            <label>
              Jurisdiction
              <input maxLength={100} value={fields.jurisdiction} onChange={(event) => updateField("jurisdiction", event.target.value)} />
            </label>
            <label>
              Language
              <input required maxLength={32} value={fields.language} onChange={(event) => updateField("language", event.target.value)} />
            </label>
            <label>
              Approval status
              <select required value={fields.approvalStatus} onChange={(event) => updateField("approvalStatus", event.target.value)}>
                <option value="APPROVED">APPROVED</option>
                <option value="DRAFT">DRAFT</option>
              </select>
            </label>
            <label>
              Effective date
              <input type="date" value={fields.effectiveDate} onChange={(event) => updateField("effectiveDate", event.target.value)} />
            </label>
            <label>
              Expiration date
              <input type="date" value={fields.expirationDate} onChange={(event) => updateField("expirationDate", event.target.value)} />
            </label>
            <label>
              Audience
              <input maxLength={100} value={fields.audience} onChange={(event) => updateField("audience", event.target.value)} />
            </label>
            <label>
              Access classification
              <input required maxLength={100} value={fields.accessClassification} onChange={(event) => updateField("accessClassification", event.target.value)} />
            </label>
            <button className="upload-button full-field" type="submit" disabled={!file || uploading}>
              {uploading ? "Uploading and indexing…" : "Upload and index"}
            </button>
          </form>
        </section>

        <section className="knowledge-card document-card" aria-labelledby="documents-heading">
          <div className="document-heading">
            <div>
              <h2 id="documents-heading">Indexed documents</h2>
              <p>Newest uploads appear first.</p>
            </div>
            <span>{documents.length}</span>
          </div>
          {loading ? (
            <p className="document-empty">Loading documents…</p>
          ) : documents.length === 0 ? (
            <p className="document-empty">No documents have been indexed.</p>
          ) : (
            <ul className="document-list">
              {documents.map((document) => (
                <li key={document.documentId}>
                  <div>
                    <strong>{document.title}</strong>
                    <span>{document.originalFilename} · v{document.version}</span>
                  </div>
                  <div className="document-tags">
                    <span>{document.approvalStatus}</span>
                    <span>{document.chunkCount} {document.chunkCount === 1 ? "chunk" : "chunks"}</span>
                  </div>
                  <p>
                    Effective {document.effectiveDate ?? "not set"} · Expires {document.expirationDate ?? "not set"}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
