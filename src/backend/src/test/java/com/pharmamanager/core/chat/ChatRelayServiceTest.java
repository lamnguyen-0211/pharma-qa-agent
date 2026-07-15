package com.pharmamanager.core.chat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pharmamanager.core.ai.AiClient;
import com.pharmamanager.core.api.BusinessSessionNotFoundException;
import com.pharmamanager.core.api.ChatRequest;
import com.pharmamanager.core.business.BusinessSessionService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ChatRelayServiceTest {
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Mock
    private BusinessSessionService businessSessions;

    @Mock
    private AiClient aiClient;

    private ChatRelayService service;

    @BeforeEach
    void setUp() {
        service = new ChatRelayService(businessSessions, aiClient);
    }

    @Test
    void validChatRequestIsForwardedWithoutCorePersistence() throws Exception {
        var request = new ChatRequest("business-1", "chat-1", "What is this used for?");
        var aiResponse = objectMapper.readTree("{\"chatSessionId\":\"chat-1\",\"answer\":\"ok\"}");
        when(aiClient.chat(request)).thenReturn(aiResponse);

        assertThat(service.chat(request)).isEqualTo(aiResponse);

        var requestCaptor = ArgumentCaptor.forClass(ChatRequest.class);
        verify(businessSessions).requireSession("business-1");
        verify(aiClient).chat(requestCaptor.capture());
        assertThat(requestCaptor.getValue()).isEqualTo(request);
        verifyNoMoreInteractions(businessSessions, aiClient);
    }

    @Test
    void unknownBusinessSessionIsNotForwardedToAi() {
        var request = new ChatRequest("missing", null, "What is this used for?");
        when(businessSessions.requireSession("missing"))
                .thenThrow(new BusinessSessionNotFoundException("missing"));

        assertThatThrownBy(() -> service.chat(request))
                .isInstanceOf(BusinessSessionNotFoundException.class);

        verify(businessSessions).requireSession("missing");
        verify(aiClient, never()).chat(request);
        verifyNoMoreInteractions(businessSessions, aiClient);
    }
}
