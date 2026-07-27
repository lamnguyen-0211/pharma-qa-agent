package com.pharmamanager.core.consent;
import com.pharmamanager.core.business.BusinessSessionService;
import com.pharmamanager.core.security.AuthenticatedIdentity;
import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
@Service
public class ConsentService {
  private final JdbcTemplate jdbc; private final BusinessSessionService users; private final String version;
  public ConsentService(JdbcTemplate jdbc, BusinessSessionService users, @Value("${pharma.consent-version}") String version) { this.jdbc=jdbc; this.users=users; this.version=version; }
  @Transactional public UserProfileResponse profile(Authentication auth) {
    var identity=AuthenticatedIdentity.from(auth); var user=users.ensureUser(identity);
    boolean accepted=Boolean.TRUE.equals(jdbc.queryForObject("SELECT EXISTS(SELECT 1 FROM user_consent WHERE user_id = ? AND consent_version = ?)", Boolean.class, user.id(), version));
    List<String> roles=auth.getAuthorities().stream().map(a -> a.getAuthority().replaceFirst("^ROLE_", "")).sorted().toList();
    return new UserProfileResponse(user.id(), identity.subject(), user.displayName(), roles, accepted, version);
  }
  @Transactional public UserProfileResponse accept(Authentication auth) {
    var identity=AuthenticatedIdentity.from(auth); var user=users.ensureUser(identity);
    jdbc.update("INSERT INTO user_consent(user_id, consent_version, accepted_at, accepted_subject) VALUES (?, ?, ?, ?) ON CONFLICT (user_id, consent_version) DO UPDATE SET accepted_at=EXCLUDED.accepted_at, accepted_subject=EXCLUDED.accepted_subject", user.id(), version, OffsetDateTime.now(), identity.subject());
    return profile(auth);
  }
  public void requireConsent(Authentication auth) { if (!profile(auth).consentAccepted()) throw new ConsentRequiredException(version); }
}
