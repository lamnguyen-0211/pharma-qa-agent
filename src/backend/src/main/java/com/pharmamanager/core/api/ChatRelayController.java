package com.pharmamanager.core.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.pharmamanager.core.chat.ChatRelayService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.security.core.Authentication;
import org.springframework.security.access.prepost.PreAuthorize;

@RestController
public class ChatRelayController {
    private final ChatRelayService service;

    public ChatRelayController(ChatRelayService service) {
        this.service = service;
    }

    @PostMapping("/api/v1/chat")
    @PreAuthorize("hasAnyRole('PHARMA_USER', 'PHARMA_ADMIN')")
    public JsonNode chat(@Valid @RequestBody ChatRequest request, Authentication authentication) {
        return service.chat(request, authentication);
    }

    public JsonNode chat(ChatRequest request) { return service.chat(request); }
}
