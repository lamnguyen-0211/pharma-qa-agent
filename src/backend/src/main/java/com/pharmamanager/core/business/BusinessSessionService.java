package com.pharmamanager.core.business;

import com.pharmamanager.core.api.BusinessSessionNotFoundException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.UUID;

@Service
public class BusinessSessionService {
    private static final String INSERT_USER =
            "INSERT INTO app_user (id, external_subject, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)";
    private static final String USER_EXISTS = "SELECT EXISTS(SELECT 1 FROM app_user WHERE id = ?)";
    private static final String INSERT_SESSION =
            "INSERT INTO business_session (id, user_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)";
    private static final String SELECT_SESSION =
            "SELECT id, user_id, status, created_at, updated_at FROM business_session WHERE id = ?";

    private final JdbcTemplate jdbc;

    public BusinessSessionService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public UserResponse createUser(UserRequest request) {
        String id = UUID.randomUUID().toString();
        OffsetDateTime now = OffsetDateTime.now();
        jdbc.update(INSERT_USER, id, request.externalSubject(), request.displayName(), now, now);
        return new UserResponse(id, request.externalSubject(), request.displayName(), now, now);
    }

    @Transactional
    public BusinessSessionResponse createBusinessSession(BusinessSessionRequest request) {
        Boolean userExists = jdbc.queryForObject(USER_EXISTS, Boolean.class, request.userId());
        if (!Boolean.TRUE.equals(userExists)) {
            throw new IllegalArgumentException("User not found.");
        }

        String id = UUID.randomUUID().toString();
        OffsetDateTime now = OffsetDateTime.now();
        jdbc.update(INSERT_SESSION, id, request.userId(), "ACTIVE", now, now);
        return new BusinessSessionResponse(id, request.userId(), "ACTIVE", now, now);
    }

    public BusinessSessionResponse getBusinessSession(String id) {
        return jdbc.queryForObject(SELECT_SESSION, (rs, rowNum) -> new BusinessSessionResponse(
                rs.getString("id"),
                rs.getString("user_id"),
                rs.getString("status"),
                rs.getObject("created_at", OffsetDateTime.class),
                rs.getObject("updated_at", OffsetDateTime.class)), id);
    }

    public BusinessSessionResponse requireSession(String id) {
        try {
            return getBusinessSession(id);
        } catch (EmptyResultDataAccessException exception) {
            throw new BusinessSessionNotFoundException(id);
        }
    }
}
