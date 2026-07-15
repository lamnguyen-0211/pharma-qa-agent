package com.pharmamanager.core.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.pharmamanager.core.chat.ChatRelayService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ChatRelayController {
    private final ChatRelayService service;

    public ChatRelayController(ChatRelayService service) {
        this.service = service;
    }

    @PostMapping("/api/v1/chat")
    public JsonNode chat(@Valid @RequestBody ChatRequest request) {
        return service.chat(request);
    }
}
