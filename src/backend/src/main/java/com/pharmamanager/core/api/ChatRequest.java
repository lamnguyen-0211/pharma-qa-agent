package com.pharmamanager.core.api;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ChatRequest(
        @NotBlank String businessSessionId,
        String chatSessionId,
        @NotBlank @Size(max = 4000) String question) {}
