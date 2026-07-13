package com.pharmamanager.core.api;

import com.pharmamanager.core.conversation.ConversationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class ConversationController {
    private final ConversationService service;
    public ConversationController(ConversationService service) { this.service = service; }

    @PostMapping("/conversations")
    @ResponseStatus(HttpStatus.CREATED)
    public ConversationResponse create() { return service.createConversation(); }

    @GetMapping("/conversations/{id}")
    public ConversationResponse get(@PathVariable String id) { return service.getConversation(id); }

    @PostMapping("/conversations/{id}/messages")
    public ChatResponse message(@PathVariable String id, @Valid @RequestBody ChatRequest request) { return service.chat(id, request); }

    @PostMapping("/chat")
    public ChatResponse chat(@Valid @RequestBody ChatRequest request) { return service.chat(request); }
}
