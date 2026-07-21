package com.pharmamanager.core.api;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ChatRequest(
        @NotBlank String businessSessionId,
        String chatSessionId,
        @NotBlank @Size(max = 4000) String question,
        Boolean useKnowledgeBase) {}
