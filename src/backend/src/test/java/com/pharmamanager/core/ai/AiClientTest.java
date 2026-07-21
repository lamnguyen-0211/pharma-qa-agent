package com.pharmamanager.core.ai;

import com.pharmamanager.core.api.ChatRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
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

    @Test
    void springCreatesClientUsingConfiguredBackendUrl() {
        new ApplicationContextRunner()
                .withPropertyValues("ai.backend-url=http://ai.test")
                .withBean(AiClient.class)
                .run(context -> assertThat(context).hasSingleBean(AiClient.class));
    }

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

    @Test
    @Timeout(10)
    void chatUsesHttp11AndWritesJsonBody() throws Exception {
        var requestBody = new AtomicReference<String>();
        var upgradeHeader = new AtomicReference<String>();
        var httpServer = HttpServer.create(new InetSocketAddress(0), 0);
        httpServer.createContext("/v1/chat", exchange -> {
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            upgradeHeader.set(exchange.getRequestHeaders().getFirst("Upgrade"));
            var response = "{\"answer\":\"ok\"}".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, response.length);
            try (var output = exchange.getResponseBody()) {
                output.write(response);
            }
        });
        httpServer.setExecutor(command -> {
            var thread = new Thread(command);
            thread.setDaemon(true);
            thread.start();
        });
        httpServer.start();

        try {
            var realClient = new AiClient("http://127.0.0.1:" + httpServer.getAddress().getPort());
            realClient.chat(new ChatRequest("business-1", null, "What is this?", false));
        } finally {
            httpServer.stop(0);
        }

        assertThat(upgradeHeader.get()).isNull();
        assertThat(requestBody.get()).contains("\"businessSessionId\":\"business-1\"");
        assertThat(requestBody.get()).contains("\"question\":\"What is this?\"");
    }
}
