package com.pharmamanager.core.chat;

import com.fasterxml.jackson.databind.JsonNode;
import com.pharmamanager.core.ai.AiClient;
import com.pharmamanager.core.api.ChatRequest;
import com.pharmamanager.core.business.BusinessSessionService;
import org.springframework.stereotype.Service;
import com.pharmamanager.core.consent.ConsentService;
import com.pharmamanager.core.security.AuthenticatedIdentity;
import org.springframework.security.core.Authentication;

@Service
public class ChatRelayService {
    private final BusinessSessionService businessSessions;
    private final AiClient aiClient;
    private final ConsentService consent;

    public ChatRelayService(BusinessSessionService businessSessions, AiClient aiClient, ConsentService consent) {
        this.businessSessions = businessSessions; this.aiClient = aiClient; this.consent = consent;
    }

    public ChatRelayService(BusinessSessionService businessSessions, AiClient aiClient) {
        this(businessSessions, aiClient, null);
    }

    public JsonNode chat(ChatRequest request) {
        businessSessions.requireSession(request.businessSessionId());
        return aiClient.chat(request);
    }

    public JsonNode chat(ChatRequest request, Authentication authentication) {
        consent.requireConsent(authentication);
        businessSessions.requireOwnedSession(request.businessSessionId(), AuthenticatedIdentity.from(authentication));
        return aiClient.chat(request);
    }
}
