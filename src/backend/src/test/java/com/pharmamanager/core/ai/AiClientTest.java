package com.pharmamanager.core.ai;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.web.client.RestClient;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class AiClientTest {
    private AiClient client;
    private MockRestServiceServer server;

    @BeforeEach
    void setUp() {
        var builder = RestClient.builder().baseUrl("http://ai.test");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new AiClient(builder.build());
    }

    @Test
    void uploadUsesMultipartWithFilenameContentAndMetadata() {
        var metadata = new LinkedMultiValueMap<String, String>();
        metadata.add("title", "Approved Label");
        metadata.add("approvalStatus", "APPROVED");
        server.expect(once(), requestTo("http://ai.test/v1/knowledge/documents"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().string(containsString("filename=\"label.txt\"")))
                .andExpect(content().string(containsString("Approved content")))
                .andExpect(content().string(containsString("Approved Label")))
                .andRespond(withSuccess(
                        "{\"documentId\":\"document-1\"}",
                        org.springframework.http.MediaType.APPLICATION_JSON));

        var response = client.uploadKnowledgeDocument(
                "label.txt",
                "text/plain",
                "Approved content".getBytes(),
                metadata);

        assertThat(response.get("documentId").asText()).isEqualTo("document-1");
        server.verify();
    }

    @Test
    void listUsesKnowledgeEndpointAndPreservesJson() {
        server.expect(once(), requestTo("http://ai.test/v1/knowledge/documents"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess(
                        "[{\"title\":\"Approved Label\"}]",
                        org.springframework.http.MediaType.APPLICATION_JSON));

        var response = client.listKnowledgeDocuments();

        assertThat(response.get(0).get("title").asText()).isEqualTo("Approved Label");
        server.verify();
    }
}
