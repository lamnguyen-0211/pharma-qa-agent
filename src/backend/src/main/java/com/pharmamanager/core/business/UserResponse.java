package com.pharmamanager.core.business;

import java.time.OffsetDateTime;

public record UserResponse(
        String id,
        String externalSubject,
        String displayName,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt) {}
