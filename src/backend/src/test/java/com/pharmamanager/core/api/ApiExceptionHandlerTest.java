package com.pharmamanager.core.api;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class ApiExceptionHandlerTest {
    private final ApiExceptionHandler handler = new ApiExceptionHandler();

    @Test
    void businessSessionNotFoundUsesTheCoreSessionErrorMessage() {
        assertThat(handler.businessSessionNotFound(new BusinessSessionNotFoundException("missing")))
                .isEqualTo(new ErrorResponse("Business session not found."));
    }
}
