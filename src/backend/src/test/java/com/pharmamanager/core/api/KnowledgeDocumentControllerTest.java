package com.pharmamanager.core.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pharmamanager.core.knowledge.KnowledgeRelayService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(KnowledgeDocumentController.class)
class KnowledgeDocumentControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private KnowledgeRelayService service;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void listIsExposedAtTheFrontendCoreContract() throws Exception {
        when(service.list()).thenReturn(objectMapper.readTree("[]"));

        mockMvc.perform(get("/api/v1/knowledge/documents"))
                .andExpect(status().isOk())
                .andExpect(content().json("[]"));

        verify(service).list();
    }
}
