export type RiskLevel = "low" | "medium" | "high" | "emergency";

export type Citation = {
  documentId: string;
  title: string;
  version: string;
  page?: number | null;
  chunkId: string;
};

export type AssistantResponse = {
  businessSessionId: string;
  chatSessionId: string;
  answer: string;
  risk_level: RiskLevel;
  citations: Citation[];
  trace_id?: string;
};
