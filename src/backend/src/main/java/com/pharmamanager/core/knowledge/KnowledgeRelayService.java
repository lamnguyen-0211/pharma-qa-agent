package com.pharmamanager.core.knowledge;

import com.fasterxml.jackson.databind.JsonNode;
import com.pharmamanager.core.ai.AiClient;
import java.io.IOException;
import org.springframework.stereotype.Service;
import org.springframework.util.MultiValueMap;
import org.springframework.web.multipart.MultipartFile;

@Service
public class KnowledgeRelayService {
    private final AiClient aiClient;

    public KnowledgeRelayService(AiClient aiClient) {
        this.aiClient = aiClient;
    }

    public JsonNode upload(
            MultipartFile file,
            MultiValueMap<String, String> metadata) throws IOException {
        return aiClient.uploadKnowledgeDocument(
                file.getOriginalFilename(),
                file.getContentType(),
                file.getBytes(),
                metadata);
    }

    public JsonNode list() {
        return aiClient.listKnowledgeDocuments();
    }
}
