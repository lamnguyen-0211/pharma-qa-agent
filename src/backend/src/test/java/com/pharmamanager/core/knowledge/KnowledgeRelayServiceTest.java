package com.pharmamanager.core.knowledge;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pharmamanager.core.ai.AiClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class KnowledgeRelayServiceTest {
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Mock
    private AiClient aiClient;

    private KnowledgeRelayService service;

    @BeforeEach
    void setUp() {
        service = new KnowledgeRelayService(aiClient);
    }

    @Test
    void uploadForwardsFileAndEveryMetadataValueOnce() throws Exception {
        var file = new MockMultipartFile(
                "file",
                "label.txt",
                "text/plain",
                "Approved content".getBytes());
        var metadata = validMetadata();
        var response = objectMapper.readTree("{\"documentId\":\"document-1\",\"chunkCount\":1}");
        when(aiClient.uploadKnowledgeDocument(
                "label.txt",
                "text/plain",
                "Approved content".getBytes(),
                metadata)).thenReturn(response);

        assertThat(service.upload(file, metadata)).isEqualTo(response);

        var metadataCaptor = ArgumentCaptor.forClass(MultiValueMap.class);
        var bytesCaptor = ArgumentCaptor.forClass(byte[].class);
        verify(aiClient).uploadKnowledgeDocument(
                org.mockito.ArgumentMatchers.eq("label.txt"),
                org.mockito.ArgumentMatchers.eq("text/plain"),
                bytesCaptor.capture(),
                metadataCaptor.capture());
        assertThat(bytesCaptor.getValue()).isEqualTo("Approved content".getBytes());
        assertThat(metadataCaptor.getValue()).isEqualTo(metadata);
        verifyNoMoreInteractions(aiClient);
    }

    @Test
    void listReturnsAiOwnedPayloadUnchanged() throws Exception {
        var response = objectMapper.readTree("[{\"documentId\":\"document-1\"}]");
        when(aiClient.listKnowledgeDocuments()).thenReturn(response);

        assertThat(service.list()).isEqualTo(response);

        verify(aiClient).listKnowledgeDocuments();
        verifyNoMoreInteractions(aiClient);
    }

    private MultiValueMap<String, String> validMetadata() {
        var metadata = new LinkedMultiValueMap<String, String>();
        metadata.add("title", "Approved Label");
        metadata.add("documentType", "PRODUCT_LABEL");
        metadata.add("product", "Product A");
        metadata.add("activeIngredient", "Ingredient A");
        metadata.add("market", "Thailand");
        metadata.add("jurisdiction", "TH");
        metadata.add("language", "en");
        metadata.add("effectiveDate", "2026-01-01");
        metadata.add("expirationDate", "2027-01-01");
        metadata.add("version", "3.2");
        metadata.add("approvalStatus", "APPROVED");
        metadata.add("audience", "INTERNAL");
        metadata.add("accessClassification", "INTERNAL");
        return metadata;
    }
}
