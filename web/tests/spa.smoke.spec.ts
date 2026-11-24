import { expect, test } from "@playwright/test";

const MOCK_MODELS = {
  defaut: "resnet50-onnx-int8",
  modeles: [
    {
      id: "resnet50-onnx-int8",
      label: "ResNet-50 ONNX int8 (prod)",
      source: "models/onnx/resnet50-int8-static.onnx",
      statut: "ready",
      charge: true,
      accuracy: 0.685,
      p50_ms: 21.5,
      p95_ms: 28.6,
      taille_mo: 24.9,
      cout_estime_usd_par_million: 1.8,
      space_only: false,
    },
    {
      id: "efficientnet-b0-onnx-int8",
      label: "EfficientNet-B0 ONNX int8",
      source: "HF google/efficientnet-b0 → ONNX int8",
      statut: "building",
      charge: false,
      accuracy: 0.66,
      p50_ms: 10,
      p95_ms: 13,
      taille_mo: 5.5,
      cout_estime_usd_par_million: 0.82,
      space_only: false,
    },
    {
      id: "clip-vit-b32",
      label: "CLIP ViT-B/32 (Space ZeroGPU)",
      source: "HF openai/clip-vit-base-patch32",
      statut: "space_only",
      charge: false,
      accuracy: 0.765,
      p50_ms: 83,
      p95_ms: 114,
      taille_mo: 577,
      cout_estime_usd_par_million: null,
      space_only: true,
    },
  ],
};

const MOCK_HEALTH = {
  status: "ok",
  version: "0.6.0",
  modele: "resnet50-onnx-int8",
  modele_charge: true,
  modeles_charges: ["resnet50-onnx-int8"],
};

const MOCK_PREDICT = {
  categorie: "Électronique",
  titre_suggere: "Ordinateur portable",
  description_suggeree: "Ordinateur portable à vendre. Catégorie proposée : Électronique.",
  confiance: 0.92,
  statut: "auto",
  top3: [{ label: "laptop", categorie: "Électronique", score: 0.92 }],
  propositions: [
    { categorie: "Électronique", score: 0.95, titre: "Ordinateur portable" },
  ],
  modele: "resnet50-onnx-int8",
  latence_ms: 24.1,
  cout_estime_usd_par_million: 1.8,
};

async function mockApi(page: import("@playwright/test").Page) {
  await page.route("**/api/models", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_MODELS),
    });
  });
  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_HEALTH),
    });
  });
  await page.route("**/api/predict", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_PREDICT),
    });
  });
}

test.describe("SPA smoke (mocks)", () => {
  test("Studio brand + upload → predict mock", async ({ page }) => {
    await mockApi(page);
    await page.goto("/");

    await expect(page.getByText("MarketPlace Vision")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Une photo devient une annonce." }),
    ).toBeVisible();
    await expect(page.getByText("a_confirmer").first()).toBeVisible();

    await page.getByLabel("Bearer token").fill("test-token");

    const buffer = Buffer.from(
      "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAQMEEQUhMQYSQVEUYXEiMwUigQYRoSMwUjLBFRXSM0YhCRYkVTQzQmJxFBkwgZChMichaZGikaKjw8XLzNTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q==",
      "base64",
    );
    await page.getByLabel("Choisir une photo d’objet").setInputFiles({
      name: "objet.jpg",
      mimeType: "image/jpeg",
      buffer,
    });

    await page.getByRole("button", { name: "Analyser" }).click();
    await expect(page.getByText("Électronique").first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Ordinateur portable").first()).toBeVisible();
    await expect(
      page.getByText("Pas un second modèle."),
    ).toBeVisible();
  });

  test("Comparateur + Garde-fous routes", async ({ page }) => {
    await mockApi(page);
    await page.goto("/comparateur");
    await expect(
      page.getByRole("heading", { name: "Mesuré et estimé ne se comparent pas." }),
    ).toBeVisible();
    await expect(page.getByText("resnet50-onnx-int8").first()).toBeVisible();
    await expect(page.getByText("mesuré", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("region", { name: "Lecture jury" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Jeu focal, n = 100/ })).toBeVisible();
    await expect(page.getByText("n = 20").first()).toBeVisible();
    await expect(page.getByText("Jeu focal non mesuré")).toHaveCount(0);
    await expect(page.getByText("écarté", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("hors du tableau")).toBeVisible();
    await expect(
      page.getByRole("img", { name: /focus_caltech_/ }).first(),
    ).toBeVisible();

    await page.goto("/garde-fous");
    await expect(
      page.getByRole("heading", {
        name: "La photo est lue en mémoire puis oubliée.",
      }),
    ).toBeVisible();
    await expect(page.getByText("sessionStorage")).toBeVisible();
    await expect(page.getByText("0", { exact: true })).toBeVisible();
  });

  test("Parcours précédent / suivant et itérations", async ({ page }) => {
    await mockApi(page);
    await page.goto("/parcours");
    await expect(
      page.getByRole("heading", { name: "Une idée, puis la suivante." }),
    ).toBeVisible();
    await expect(page.getByText("Photos différentes")).toBeVisible();
    await page.getByRole("button", { name: "Suivant" }).click();
    await expect(page.getByRole("heading", { name: "Données" })).toBeVisible();
    await expect(
      page.getByRole("img", { name: /Proxy de laboratoire/ }).first(),
    ).toBeVisible();
    await page.getByRole("button", { name: "ONNX" }).click();
    await expect(page.getByRole("heading", { name: "Mesure" })).toBeVisible();
    await page.getByRole("button", { name: "Précédent" }).click();
    await expect(page.getByRole("heading", { name: "Choix du modèle" })).toBeVisible();
  });
});
