package com.pharmamanager.core.api;

public class BusinessSessionNotFoundException extends RuntimeException {
    public BusinessSessionNotFoundException(String id) {
        super("Business session not found: " + id);
    }
}
