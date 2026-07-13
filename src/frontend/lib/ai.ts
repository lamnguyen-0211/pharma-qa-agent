export type RiskLevel = "low" | "medium" | "high" | "emergency";

export type AssistantResponse = {
  answer: string;
  riskLevel: RiskLevel;
  citations: string[];
  traceId?: string;
};
