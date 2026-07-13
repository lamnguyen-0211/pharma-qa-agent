package com.pharmamanager.core.api;

import java.util.List;

public record ChatResponse(String conversationId, String answer, String riskLevel, List<String> citations, String traceId) {}
