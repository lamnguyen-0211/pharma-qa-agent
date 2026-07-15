package com.pharmamanager.core.business;

import java.time.OffsetDateTime;

public record BusinessSessionResponse(
        String id,
        String userId,
        String status,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt) {}
