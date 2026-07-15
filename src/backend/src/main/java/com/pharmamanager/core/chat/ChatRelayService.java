package com.pharmamanager.core.chat;

import com.fasterxml.jackson.databind.JsonNode;
import com.pharmamanager.core.ai.AiClient;
import com.pharmamanager.core.api.ChatRequest;
import com.pharmamanager.core.business.BusinessSessionService;
import org.springframework.stereotype.Service;

@Service
public class ChatRelayService {
    private final BusinessSessionService businessSessions;
    private final AiClient aiClient;

    public ChatRelayService(BusinessSessionService businessSessions, AiClient aiClient) {
        this.businessSessions = businessSessions;
        this.aiClient = aiClient;
    }

    public JsonNode chat(ChatRequest request) {
        businessSessions.requireSession(request.businessSessionId());
        return aiClient.chat(request);
    }
}
