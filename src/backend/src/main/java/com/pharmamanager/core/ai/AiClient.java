package com.pharmamanager.core.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.pharmamanager.core.api.ChatRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class AiClient {
    private final RestClient client;

    public AiClient(@Value("${ai.backend-url}") String backendUrl) { this.client = RestClient.builder().baseUrl(backendUrl).build(); }

    public JsonNode chat(ChatRequest request) {
        JsonNode result = client.post().uri("/v1/chat").contentType(MediaType.APPLICATION_JSON).body(request).retrieve().body(JsonNode.class);
        if (result == null) throw new IllegalStateException("AI service returned an empty response");
        return result;
    }
}
