package com.pharmamanager.core.api;

import com.pharmamanager.core.business.BusinessSessionRequest;
import com.pharmamanager.core.business.BusinessSessionResponse;
import com.pharmamanager.core.business.BusinessSessionService;
import com.pharmamanager.core.business.UserRequest;
import com.pharmamanager.core.business.UserResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class BusinessSessionController {
    private final BusinessSessionService service;

    public BusinessSessionController(BusinessSessionService service) {
        this.service = service;
    }

    @PostMapping("/users")
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse createUser(@Valid @RequestBody UserRequest request) {
        return service.createUser(request);
    }

    @PostMapping("/business-sessions")
    @ResponseStatus(HttpStatus.CREATED)
    public BusinessSessionResponse createBusinessSession(@Valid @RequestBody BusinessSessionRequest request) {
        return service.createBusinessSession(request);
    }

    @GetMapping("/business-sessions/{id}")
    public BusinessSessionResponse getBusinessSession(@PathVariable String id) {
        return service.requireSession(id);
    }
}
