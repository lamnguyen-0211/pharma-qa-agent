package com.pharmamanager.core.ai;

import com.pharmamanager.core.api.ChatRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.List;

@Component
public class AiClient {
    private final RestClient client;

    public AiClient(@Value("${ai.backend-url}") String backendUrl) { this.client = RestClient.builder().baseUrl(backendUrl).build(); }

    public AiResult answer(ChatRequest request) {
        AiResult result = client.post().uri("/v1/chat").contentType(MediaType.APPLICATION_JSON).body(request).retrieve().body(AiResult.class);
        if (result == null) throw new IllegalStateException("AI service returned an empty response");
        return result;
    }

    public record AiResult(String answer, String risk_level, List<String> citations, String trace_id) {}
}
