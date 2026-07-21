export type RiskLevel = "low" | "medium" | "high" | "emergency";

export type Citation = {
  documentId: string;
  title: string;
  version: string;
  page?: number | null;
  chunkId: string;
};

export type KnowledgeDocument = {
  documentId: string;
  originalFilename: string;
  title: string;
  documentType: string;
  product?: string | null;
  activeIngredient?: string | null;
  market?: string | null;
  jurisdiction?: string | null;
  language: string;
  effectiveDate?: string | null;
  expirationDate?: string | null;
  version: string;
  approvalStatus: string;
  audience?: string | null;
  accessClassification: string;
  embeddingModelName: string;
  embeddingDimension: number;
  chunkCount: number;
  createdAt: string;
};

export type AssistantResponse = {
  businessSessionId: string;
  chatSessionId: string;
  answer: string;
  risk_level: RiskLevel;
  citations: Citation[];
  trace_id?: string;
};
