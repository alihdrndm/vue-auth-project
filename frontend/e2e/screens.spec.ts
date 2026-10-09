// Visual check (HANDOFF "Design integration", rule 6): captures every screen at 1440×900
// and 390×844 with the seeded data into design/compare/<screen>-<width>.png, to be compared
// with the design export. Not part of CI. Needs `pnpm seed` and `pnpm dev` running.
//
//   pnpm exec playwright test screens
import { fileURLToPath } from "node:url";

import { expect, type Page, test } from "@playwright/test";

const EMAIL = process.env.E2E_EMAIL ?? "admin@example.invalid";
const PASSWORD = process.env.SEED_PASSWORD ?? "eingang-dev";
const OUT = new URL("../../design/compare/", import.meta.url);
const WIDTHS = [
  { width: 1440, height: 900 },
  { width: 390, height: 844 },
] as const;

async function signIn(page: Page): Promise<void> {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/app\//);
}

/** The id of the seeded document with this invoice number. */
async function documentId(page: Page, number: string): Promise<string> {
  const response = await page.request.get(
    `/api/v1/documents?q=${encodeURIComponent(number)}`,
  );
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { results: { id: string }[] };
  const first = body.results[0];
  if (!first) throw new Error(`no seeded document ${number}`);
  return first.id;
}

async function capture(page: Page, name: string, width: number): Promise<void> {
  await page.waitForLoadState("networkidle");
  await page.screenshot({
    path: fileURLToPath(new URL(`${name}-${width}.png`, OUT)),
    fullPage: true,
  });
}

for (const size of WIDTHS) {
  test(`public screens at ${size.width}`, async ({ page }) => {
    await page.setViewportSize(size);
    await page.goto("/");
    await capture(page, "homepage", size.width);
    await page.goto("/sign-in");
    await capture(page, "sign-in", size.width);
    await page.goto("/accuracy");
    await capture(page, "accuracy-public", size.width);
  });

  test(`app screens at ${size.width}`, async ({ page }) => {
    await page.setViewportSize(size);
    await signIn(page);
    const pages: [string, string][] = [
      ["inbox", "/app/inbox"],
      ["inbox-all", "/app/inbox?tab=all"],
      ["approvals", "/app/approvals"],
      ["suppliers", "/app/suppliers"],
      ["exports", "/app/exports"],
      ["accuracy", "/app/accuracy"],
      ["settings", "/app/settings"],
      ["not-found", "/app/nowhere"],
    ];
    for (const [name, path] of pages) {
      await page.goto(path);
      await capture(page, name, size.width);
    }
    const reviews: [string, string][] = [
      ["review-a-xml", "RE-2026-0412"],
      ["review-b-llm", "2026-1043"],
      ["review-c-invalid", "RE-2026-0413"],
      ["review-mismatch", "SA/26/1160"],
    ];
    for (const [name, number] of reviews) {
      await page.goto(`/app/invoices/${await documentId(page, number)}`);
      await capture(page, name, size.width);
    }
  });
}
