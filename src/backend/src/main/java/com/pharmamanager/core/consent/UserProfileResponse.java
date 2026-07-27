package com.pharmamanager.core.consent;
import java.util.List;
public record UserProfileResponse(String id, String subject, String displayName, List<String> roles, boolean consentAccepted, String consentVersion) {}
