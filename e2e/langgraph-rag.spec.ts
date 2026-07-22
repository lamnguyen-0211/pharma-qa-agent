import { expect, test } from "@playwright/test";

const indexedDocument = {
  documentId: "document-1",
  originalFilename: "label.txt",
  title: "Approved Label",
  documentType: "PRODUCT_LABEL",
  language: "en",
  version: "3.2",
  approvalStatus: "APPROVED",
  accessClassification: "INTERNAL",
  embeddingModelName: "fake-embedding",
  embeddingDimension: 1024,
  chunkCount: 1,
  createdAt: "2026-07-18T00:00:00Z",
};

test("uploads approved knowledge and uses it in chat", async ({ page }) => {
  let uploadBody = "";
  let chatPayload: unknown;
  await page.route("**/api/knowledge/documents", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: [] });
      return;
    }
    uploadBody = route.request().postData() ?? "";
    await route.fulfill({ status: 201, json: indexedDocument });
  });
  await page.route("**/api/business-sessions", async (route) => {
    await route.fulfill({ status: 201, json: { businessSessionId: "business-1" } });
  });
  await page.route("**/api/chat", async (route) => {
    chatPayload = route.request().postDataJSON();
    await route.fulfill({
      json: {
        chatSessionId: "chat-1",
        answer: "Product A has approved internal information.",
        risk_level: "low",
        citations: [{
          documentId: "document-1",
          title: "Approved Label",
          version: "3.2",
          page: 1,
          chunkId: "chunk-1",
        }, {
          documentId: "document-2",
          title: "Safety Monograph",
          version: "1.1",
          page: 4,
          chunkId: "chunk-2",
        }],
      },
    });
  });

  await page.goto("/knowledge");
  await page.getByLabel("Document file").setInputFiles({
    name: "label.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Product A is approved for internal information work."),
  });
  await page.getByLabel("Title").fill("Approved Label");
  await page.getByLabel("Version").fill("3.2");
  await page.getByRole("button", { name: "Upload and index" }).click();
  await expect(page.getByText("Approved Label", { exact: true })).toBeVisible();
  expect(uploadBody).toContain("Approved Label");

  await page.goto("/");
  await expect(page.getByRole("checkbox", { name: "Use knowledge base" })).toBeChecked();
  await page.getByRole("textbox", { name: "Ask the assistant" }).fill("What is Product A used for?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText("Approved Label · v3.2 · page 1")).toBeVisible();
  await expect(page.getByText("Safety Monograph · v1.1 · page 4")).toBeVisible();
  await expect(
    page.getByRole("list", { name: "Citations" }).locator("li").allTextContents(),
  ).resolves.toEqual([
    "Approved Label · v3.2 · page 1",
    "Safety Monograph · v1.1 · page 4",
  ]);
  expect(chatPayload).toMatchObject({
    businessSessionId: "business-1",
    question: "What is Product A used for?",
    useKnowledgeBase: true,
  });
});

test("keeps upload metadata available when indexing is unavailable", async ({ page }) => {
  await page.route("**/api/knowledge/documents", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: [] });
      return;
    }
    await route.fulfill({
      status: 503,
      json: { error: "The knowledge service is unavailable. Try again." },
    });
  });

  await page.goto("/knowledge");
  await page.getByLabel("Document file").setInputFiles({
    name: "label.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Product A is approved for internal information work."),
  });
  await page.getByLabel("Title").fill("Approved Label");
  await page.getByRole("button", { name: "Upload and index" }).click();

  await expect(page.locator(".knowledge-alert[role=alert]")).toContainText("The knowledge service is unavailable. Try again.");
  await expect(page.getByLabel("Title")).toHaveValue("Approved Label");
  await expect(page.getByLabel("Document file")).toHaveValue(/label\.txt$/);
  await expect(page.getByRole("button", { name: "Upload and index" })).toBeEnabled();
});
