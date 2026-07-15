export type RiskLevel = "low" | "medium" | "high" | "emergency";

export type AssistantResponse = {
  businessSessionId: string;
  chatSessionId: string;
  answer: string;
  risk_level: RiskLevel;
  citations: string[];
  trace_id?: string;
};
