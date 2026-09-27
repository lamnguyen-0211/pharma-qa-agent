package com.pharmamanager.core.api;
import com.pharmamanager.core.consent.ConsentService;
import com.pharmamanager.core.consent.UserProfileResponse;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/v1/me")
public class MeController {
  private final ConsentService consent; public MeController(ConsentService consent) { this.consent=consent; }
  @GetMapping public UserProfileResponse profile(Authentication auth) { return consent.profile(auth); }
  @PostMapping("/consent") @ResponseStatus(HttpStatus.CREATED) public UserProfileResponse accept(Authentication auth) { return consent.accept(auth); }
}
