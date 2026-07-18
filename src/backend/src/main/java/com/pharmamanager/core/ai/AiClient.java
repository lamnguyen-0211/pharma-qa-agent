package com.pharmamanager.core.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.pharmamanager.core.api.ChatRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

@Component
public class AiClient {
    private final RestClient client;

    public AiClient(@Value("${ai.backend-url}") String backendUrl) { this.client = RestClient.builder().baseUrl(backendUrl).build(); }

    AiClient(RestClient client) {
        this.client = client;
    }

    public JsonNode chat(ChatRequest request) {
        JsonNode result = client.post().uri("/v1/chat").contentType(MediaType.APPLICATION_JSON).body(request).retrieve().body(JsonNode.class);
        if (result == null) throw new IllegalStateException("AI service returned an empty response");
        return result;
    }

    public JsonNode uploadKnowledgeDocument(
            String filename,
            String contentType,
            byte[] sourceBytes,
            MultiValueMap<String, String> metadata) {
        var fileHeaders = new HttpHeaders();
        fileHeaders.setContentType(MediaType.parseMediaType(contentType));
        fileHeaders.setContentDispositionFormData("file", filename);
        var resource = new ByteArrayResource(sourceBytes) {
            @Override
            public String getFilename() {
                return filename;
            }
        };

        var parts = new LinkedMultiValueMap<String, Object>();
        parts.add("file", new HttpEntity<>(resource, fileHeaders));
        metadata.forEach((name, values) -> values.forEach(value -> parts.add(name, value)));

        JsonNode result = client.post()
                .uri("/v1/knowledge/documents")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(parts)
                .retrieve()
                .body(JsonNode.class);
        if (result == null) throw new IllegalStateException("AI service returned an empty response");
        return result;
    }

    public JsonNode listKnowledgeDocuments() {
        JsonNode result = client.get()
                .uri("/v1/knowledge/documents")
                .retrieve()
                .body(JsonNode.class);
        if (result == null) throw new IllegalStateException("AI service returned an empty response");
        return result;
    }
}
