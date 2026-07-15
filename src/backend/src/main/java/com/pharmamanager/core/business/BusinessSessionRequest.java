package com.pharmamanager.core.business;

import jakarta.validation.constraints.NotBlank;

public record BusinessSessionRequest(@NotBlank String userId) {}
