package com.pharmamanager.core.security;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
public record AuthenticatedIdentity(String subject, String displayName) {
  public static AuthenticatedIdentity from(Authentication authentication) {
    if (!(authentication instanceof JwtAuthenticationToken token) || token.getToken().getSubject() == null) throw new IllegalArgumentException("A valid OIDC identity is required.");
    Object value = token.getToken().getClaims().get("name");
    if (!(value instanceof String) || ((String) value).isBlank()) value = token.getToken().getClaims().get("preferred_username");
    if (!(value instanceof String) || ((String) value).isBlank()) value = token.getToken().getClaims().get("email");
    return new AuthenticatedIdentity(token.getToken().getSubject(), value instanceof String name && !name.isBlank() ? name : token.getToken().getSubject());
  }
}
