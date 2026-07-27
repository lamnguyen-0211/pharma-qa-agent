CREATE TABLE user_consent (
  user_id VARCHAR(36) NOT NULL REFERENCES app_user(id),
  consent_version VARCHAR(64) NOT NULL,
  accepted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  accepted_subject VARCHAR(255) NOT NULL,
  PRIMARY KEY (user_id, consent_version)
);
