package com.pharmamanager.core.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.pharmamanager.core.knowledge.KnowledgeRelayService;
import java.io.IOException;
import org.springframework.http.MediaType;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.security.access.prepost.PreAuthorize;

@RestController
@RequestMapping("/api/v1/knowledge/documents")
public class KnowledgeDocumentController {
    private final KnowledgeRelayService service;

    public KnowledgeDocumentController(KnowledgeRelayService service) {
        this.service = service;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @PreAuthorize("hasRole('PHARMA_ADMIN')")
    public JsonNode upload(
            @RequestPart("file") MultipartFile file,
            @RequestParam MultiValueMap<String, String> metadata) throws IOException {
        return service.upload(file, metadata);
    }

    @GetMapping
    @PreAuthorize("hasRole('PHARMA_ADMIN')")
    public JsonNode list() {
        return service.list();
    }
}
