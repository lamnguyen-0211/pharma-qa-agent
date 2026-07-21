package com.pharmamanager.core.business;

import com.pharmamanager.core.api.BusinessSessionNotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

import java.sql.ResultSet;
import java.time.OffsetDateTime;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class BusinessSessionServiceTest {
    @Mock
    private JdbcTemplate jdbc;

    private BusinessSessionService service;

    @BeforeEach
    void setUp() {
        service = new BusinessSessionService(jdbc);
    }

    @Test
    void createUserReturnsInsertedUser() throws Exception {
        OffsetDateTime createdAt = OffsetDateTime.parse("2026-07-14T10:15:30+07:00");
        OffsetDateTime updatedAt = OffsetDateTime.parse("2026-07-14T10:15:30+07:00");
        ResultSet resultSet = org.mockito.Mockito.mock(ResultSet.class);
        when(resultSet.getString("id")).thenReturn("new-user-1");
        when(resultSet.getString("external_subject")).thenReturn("subject-1");
        when(resultSet.getString("display_name")).thenReturn("Alex Morgan");
        when(resultSet.getObject("created_at", OffsetDateTime.class)).thenReturn(createdAt);
        when(resultSet.getObject("updated_at", OffsetDateTime.class)).thenReturn(updatedAt);
        when(jdbc.queryForObject(anyString(), any(RowMapper.class), anyString(), anyString(), anyString(), any(), any()))
                .thenAnswer(invocation -> ((RowMapper<UserResponse>) invocation.getArgument(1)).mapRow(resultSet, 0));

        var response = service.createUser(new UserRequest("subject-1", "Alex Morgan"));

        assertThat(response).isEqualTo(new UserResponse(
                "new-user-1", "subject-1", "Alex Morgan", createdAt, updatedAt));
    }

    @Test
    void createUserReturnsExistingUserWhenExternalSubjectAlreadyExists() throws Exception {
        OffsetDateTime createdAt = OffsetDateTime.parse("2026-07-14T10:15:30+07:00");
        OffsetDateTime updatedAt = OffsetDateTime.parse("2026-07-21T14:13:28+07:00");
        ResultSet resultSet = org.mockito.Mockito.mock(ResultSet.class);
        when(resultSet.getString("id")).thenReturn("existing-user-1");
        when(resultSet.getString("external_subject")).thenReturn("local-preview");
        when(resultSet.getString("display_name")).thenReturn("Local Preview User");
        when(resultSet.getObject("created_at", OffsetDateTime.class)).thenReturn(createdAt);
        when(resultSet.getObject("updated_at", OffsetDateTime.class)).thenReturn(updatedAt);
        when(jdbc.queryForObject(anyString(), any(RowMapper.class), anyString(), anyString(), anyString(), any(), any()))
                .thenAnswer(invocation -> ((RowMapper<UserResponse>) invocation.getArgument(1)).mapRow(resultSet, 0));

        var firstResponse = service.createUser(new UserRequest("local-preview", "Local Preview User"));
        var secondResponse = service.createUser(new UserRequest("local-preview", "Local Preview User"));

        var expectedResponse = new UserResponse(
                "existing-user-1", "local-preview", "Local Preview User", createdAt, updatedAt);
        assertThat(firstResponse).isEqualTo(expectedResponse);
        assertThat(secondResponse).isEqualTo(expectedResponse);
        verify(jdbc, org.mockito.Mockito.times(2)).queryForObject(
                """
                        INSERT INTO app_user (id, external_subject, display_name, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT (external_subject) DO UPDATE
                        SET display_name = EXCLUDED.display_name, updated_at = EXCLUDED.updated_at
                        RETURNING id, external_subject, display_name, created_at, updated_at
                        """,
                any(RowMapper.class), anyString(), eq("local-preview"), eq("Local Preview User"), any(), any());
    }

    @Test
    void createBusinessSessionVerifiesUserThenInsertsCoreOwnedSession() {
        when(jdbc.queryForObject(
                "SELECT EXISTS(SELECT 1 FROM app_user WHERE id = ?)", Boolean.class, "user-1"))
                .thenReturn(true);

        var response = service.createBusinessSession(new BusinessSessionRequest("user-1"));

        assertThat(response.id()).hasSize(36);
        assertThat(response.userId()).isEqualTo("user-1");
        assertThat(response.status()).isEqualTo("ACTIVE");

        verify(jdbc).queryForObject(
                "SELECT EXISTS(SELECT 1 FROM app_user WHERE id = ?)", Boolean.class, "user-1");
        verify(jdbc).update(
                "INSERT INTO business_session (id, user_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                response.id(), "user-1", "ACTIVE", response.createdAt(), response.updatedAt());
    }

    @Test
    void getBusinessSessionMapsPersistedRow() throws Exception {
        OffsetDateTime createdAt = OffsetDateTime.parse("2026-07-14T10:15:30+07:00");
        OffsetDateTime updatedAt = OffsetDateTime.parse("2026-07-14T10:16:30+07:00");
        ResultSet resultSet = org.mockito.Mockito.mock(ResultSet.class);
        when(resultSet.getString("id")).thenReturn("session-1");
        when(resultSet.getString("user_id")).thenReturn("user-1");
        when(resultSet.getString("status")).thenReturn("ACTIVE");
        when(resultSet.getObject("created_at", OffsetDateTime.class)).thenReturn(createdAt);
        when(resultSet.getObject("updated_at", OffsetDateTime.class)).thenReturn(updatedAt);
        when(jdbc.queryForObject(anyString(), any(RowMapper.class), eq("session-1")))
                .thenAnswer(invocation -> ((RowMapper<BusinessSessionResponse>) invocation.getArgument(1)).mapRow(resultSet, 0));

        var response = service.getBusinessSession("session-1");

        assertThat(response).isEqualTo(new BusinessSessionResponse("session-1", "user-1", "ACTIVE", createdAt, updatedAt));
    }

    @Test
    void requireSessionTranslatesMissingRowToDomainException() {
        when(jdbc.queryForObject(anyString(), any(RowMapper.class), eq("missing")))
                .thenThrow(new EmptyResultDataAccessException(1));

        assertThatThrownBy(() -> service.requireSession("missing"))
                .isInstanceOf(BusinessSessionNotFoundException.class);
    }
}
