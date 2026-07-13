package com.pharmamanager.core.conversation;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pharmamanager.core.ai.AiClient;
import com.pharmamanager.core.api.ChatRequest;
import com.pharmamanager.core.api.ChatResponse;
import com.pharmamanager.core.api.ConversationResponse;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ConversationService {
    private final JdbcTemplate jdbc;
    private final AiClient aiClient;
    private final ObjectMapper objectMapper;

    public ConversationService(JdbcTemplate jdbc, AiClient aiClient, ObjectMapper objectMapper) {
        this.jdbc = jdbc; this.aiClient = aiClient; this.objectMapper = objectMapper;
    }

    @Transactional
    public ConversationResponse createConversation() {
        String id = UUID.randomUUID().toString();
        OffsetDateTime now = OffsetDateTime.now();
        jdbc.update("INSERT INTO conversation (id, created_at, updated_at) VALUES (?, ?, ?)", id, now, now);
        audit(id, "CONVERSATION_CREATED", null, "{}");
        return new ConversationResponse(id, now, now);
    }

    public ConversationResponse getConversation(String id) {
        return jdbc.queryForObject("SELECT id, created_at, updated_at FROM conversation WHERE id = ?", (rs, row) ->
                new ConversationResponse(rs.getString("id"), rs.getObject("created_at", OffsetDateTime.class), rs.getObject("updated_at", OffsetDateTime.class)), id);
    }

    @Transactional
    public ChatResponse chat(ChatRequest request) { return chat(createConversation().id(), request); }

    @Transactional
    public ChatResponse chat(String conversationId, ChatRequest request) {
        getConversation(conversationId);
        String question = request.question().trim();
        jdbc.update("INSERT INTO message (id, conversation_id, role, content, risk_level) VALUES (?, ?, 'USER', ?, 'LOW')", UUID.randomUUID().toString(), conversationId, question);
        audit(conversationId, "USER_MESSAGE_RECEIVED", null, "{}");

        AiClient.AiResult ai = aiClient.answer(new ChatRequest(question));
        String risk = ai.risk_level() == null ? "LOW" : ai.risk_level().toUpperCase();
        jdbc.update("INSERT INTO message (id, conversation_id, role, content, risk_level) VALUES (?, ?, 'ASSISTANT', ?, ?)", UUID.randomUUID().toString(), conversationId, ai.answer(), risk);
        jdbc.update("UPDATE conversation SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", conversationId);
        audit(conversationId, "ASSISTANT_MESSAGE_RECORDED", ai.trace_id(), jsonMetadata(risk, ai.citations()));
        return new ChatResponse(conversationId, ai.answer(), risk.toLowerCase(), ai.citations() == null ? List.of() : ai.citations(), ai.trace_id());
    }

    private void audit(String conversationId, String eventType, String traceId, String metadata) {
        jdbc.update("INSERT INTO audit_event (id, conversation_id, event_type, trace_id, metadata) VALUES (?, ?, ?, ?, CAST(? AS jsonb))", UUID.randomUUID().toString(), conversationId, eventType, traceId, metadata);
    }

    private String jsonMetadata(String risk, List<String> citations) {
        try { return objectMapper.writeValueAsString(Map.of("riskLevel", risk, "citationCount", citations == null ? 0 : citations.size())); }
        catch (JsonProcessingException e) { throw new IllegalStateException("Could not encode audit metadata", e); }
    }
}
