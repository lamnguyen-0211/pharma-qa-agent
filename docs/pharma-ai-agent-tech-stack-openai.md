# Pharma AI Agent Chatbot — Recommended Tech Stack

## Overview

This architecture is designed for a regulated pharmaceutical application with an AI chatbot for patients, healthcare professionals, or internal pharma teams.

The recommended approach is a **single orchestrator agent with controlled tools and Retrieval-Augmented Generation (RAG)** rather than a highly autonomous multi-agent system.

## High-Level Architecture

```text
Web / Mobile Client
        |
API Gateway + WAF
        |
Spring Boot Core API
        |-- PostgreSQL
        |-- Redis
        |-- Message Queue
        |-- FHIR / Enterprise Integrations
        |
        `-- Python AI Service
              |-- LangGraph Workflow
              |-- Safety and Policy Engine
              |-- OpenAI API
              |-- Search / Vector Database
              `-- Document Storage
```

## Recommended Stack

| Layer | Technology | Purpose |
|---|---|---|
| Web frontend | Next.js, React, TypeScript | Chat interface, streaming responses, admin portal |
| Mobile | React Native | Cross-platform mobile application |
| API gateway | Azure API Management, Kong, or AWS API Gateway | Authentication, rate limiting, routing, API versioning |
| Core backend | Spring Boot with Java LTS | Business logic, authorization, audit workflows, integrations |
| AI service | Python, FastAPI, Pydantic | LLM orchestration, retrieval, evaluation, structured outputs |
| Agent orchestration | LangGraph | Explicit workflow states, tool control, human-in-the-loop |
| LLM provider | OpenAI API | Chat completion, reasoning, extraction, classification, embeddings |
| Operational database | PostgreSQL | Users, consent, cases, conversations, workflow state |
| Search and RAG | Qrant or a managed vector database | Hybrid keyword and vector retrieval |
| Cache | Redis | Sessions, rate limits, short-lived conversation state |
| Document storage | S3-compatible object storage or Azure Blob Storage | SOPs, labels, clinical documents, approved content |
| Messaging | Kafka, RabbitMQ, Azure Service Bus, or AWS SQS | Document ingestion, notifications, asynchronous workflows |
| Identity | Entra ID, Auth0, Keycloak, or Okta | OIDC, MFA, role-based access control |
| Secrets | Cloud secret manager or HashiCorp Vault | API keys, certificates, credentials |
| Deployment | Docker with managed containers | Application deployment and scaling |
| Infrastructure | Terraform | Reproducible environments |
| Observability | OpenTelemetry with Grafana, Datadog, or cloud monitoring | Tracing, metrics, logs, agent monitoring |

## OpenAI Integration

Use the OpenAI API through a dedicated AI service instead of calling it directly from the frontend or core business services.

The AI service should handle:

- Prompt templates and versioning
- Model selection
- Structured JSON outputs
- Tool calling
- Retrieval and citation generation
- Safety classification
- Token and cost controls
- Retry and timeout policies
- Evaluation and monitoring
- Redaction of sensitive data
- Audit metadata

Keep the OpenAI API key in a secure secret manager and access it only from the backend.

## RAG Design

Use **hybrid retrieval**, combining keyword search and vector similarity.

Each indexed document chunk should include metadata such as:

```text
document_id
document_type
product
active_ingredient
market
jurisdiction
language
effective_date
expiration_date
version
approval_status
audience
source_page
access_classification
```

Only retrieve content that is:

- Approved
- Currently effective
- Valid for the user's market and role
- Permitted by access controls
- Traceable to the original document and page

Medical and product answers should include citations. The chatbot should abstain when approved evidence is insufficient.

## Agent Workflow

```text
User question
    |
Identity and consent check
    |
Intent and risk classification
    |
Approved workflow
    |-- Search approved documents
    |-- Query permitted internal APIs
    |-- Collect structured information
    |-- Generate a cited response
    `-- Escalate to a qualified human
```

Recommended tools:

```text
search_approved_knowledge
get_product_information
get_document_version
create_medical_information_case
create_adverse_event_case
create_product_complaint
transfer_to_human
```

The LLM should not have direct access to databases or unrestricted external systems.

Every write action should pass through a deterministic backend service that validates:

- User permissions
- Input schema
- Business rules
- Required approvals
- Audit requirements

## Safety Controls

1. Classify risk before answering.
2. Detect emergencies, adverse events, contraindications, pregnancy exposure, and dosing questions.
3. Enforce policies in code, not only in prompts.
4. Require structured model outputs.
5. Add human approval for high-risk actions.
6. Record prompts, model versions, retrieved documents, tool calls, and approvals.
7. Treat retrieved documents as untrusted input.
8. Prevent prompt injection from changing system rules.
9. Avoid unrestricted long-term conversational memory.
10. Redact or minimize sensitive health information before sending it to external services where required.

## Final Recommendation

```text
Frontend:
Next.js + React + TypeScript

Core Backend:
Spring Boot + Java LTS

AI Service:
Python + FastAPI + LangGraph + Pydantic

LLM Provider:
OpenAI API

Data:
PostgreSQL + Redis

RAG:
Elasticsearch / OpenSearch or managed vector search

Storage:
S3-compatible object storage or Azure Blob Storage

Messaging:
Kafka, RabbitMQ, Azure Service Bus, or AWS SQS

Security:
OIDC provider + secret manager + private networking

Observability:
OpenTelemetry + centralized logs, metrics, traces, and evaluations

Infrastructure:
Docker + Terraform + managed container platform
```

The best starting point is a controlled internal knowledge assistant with approved-document RAG, citations, strict tool permissions, human escalation, and complete auditability.
