package com.pharmamanager.core.api;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(org.springframework.dao.EmptyResultDataAccessException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ErrorResponse notFound(Exception ignored) { return new ErrorResponse("Conversation not found."); }

    @ExceptionHandler({IllegalStateException.class, org.springframework.web.client.RestClientException.class})
    @ResponseStatus(HttpStatus.SERVICE_UNAVAILABLE)
    public ErrorResponse dependencyUnavailable(Exception ignored) { return new ErrorResponse("The AI service is unavailable."); }
}
