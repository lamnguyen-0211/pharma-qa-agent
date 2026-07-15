package com.pharmamanager.core.business;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record UserRequest(
        @NotBlank @Size(max = 255) String externalSubject,
        @NotBlank @Size(max = 255) String displayName) {}
