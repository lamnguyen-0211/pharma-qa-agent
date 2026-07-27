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
import org.springframework.security.core.Authentication;
import com.pharmamanager.core.security.AuthenticatedIdentity;
import com.pharmamanager.core.consent.ConsentService;
import org.springframework.security.access.prepost.PreAuthorize;

@RestController
@RequestMapping("/api/v1")
public class BusinessSessionController {
    private final BusinessSessionService service;
    private final ConsentService consent;

    public BusinessSessionController(BusinessSessionService service, ConsentService consent) {
        this.service = service; this.consent = consent;
    }

    public BusinessSessionController(BusinessSessionService service) {
        this(service, null);
    }

    @PostMapping("/users")
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse createUser(Authentication authentication) {
        return service.ensureUser(AuthenticatedIdentity.from(authentication));
    }

    @PostMapping("/business-sessions")
    @PreAuthorize("hasAnyRole('PHARMA_USER', 'PHARMA_ADMIN')")
    @ResponseStatus(HttpStatus.CREATED)
    public BusinessSessionResponse createBusinessSession(@Valid @RequestBody(required = false) BusinessSessionRequest ignored, Authentication authentication) {
        consent.requireConsent(authentication);
        return service.createBusinessSessionFor(AuthenticatedIdentity.from(authentication));
    }

    public BusinessSessionResponse createBusinessSession(BusinessSessionRequest request) { return service.createBusinessSession(request); }

    @GetMapping("/business-sessions/{id}")
    public BusinessSessionResponse getBusinessSession(@PathVariable String id, Authentication authentication) {
        return service.requireOwnedSession(id, AuthenticatedIdentity.from(authentication));
    }

    public BusinessSessionResponse getBusinessSession(String id) { return service.requireSession(id); }
}
