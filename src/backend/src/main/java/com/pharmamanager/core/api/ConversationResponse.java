package com.pharmamanager.core.api;

import java.time.OffsetDateTime;

public record ConversationResponse(String id, OffsetDateTime createdAt, OffsetDateTime updatedAt) {}
