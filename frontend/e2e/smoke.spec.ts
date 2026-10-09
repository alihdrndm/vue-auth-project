// The smoke test (HANDOFF "Playwright smoke test"): open the sandbox, review S07's changed
// bank account, approve it, export, and check the CSV. Runs against the e2e stack
// (`pnpm test:e2e`) with the LLM switched off.
import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

const S07 = "BN-88290";
// S11 is seeded approved; S07 is approved in this test.
const APPROVED_AFTER_TEST = 2;
const BOM = String.fromCharCode(0xfeff);

test("sandbox: review, approve and export an invoice", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Open the sandbox" }).first().click();
  await page.waitForURL(/\/app\/inbox/);

  // The inbox holds the twelve samples.
  await page.getByRole("tab", { name: /^All/ }).click();
  await expect(page.getByRole("tab", { name: /^All/ })).toContainText("12");
  await expect(page.locator("tbody tr")).toHaveCount(12);

  // S07: the C05 block check for the new bank account.
  await page.getByRole("row").filter({ hasText: S07 }).click();
  await page.waitForURL(/\/app\/invoices\//);
  const check = page.locator(".card").filter({ hasText: "C05" });
  await expect(check).toBeVisible();
  await check.getByRole("button", { name: "Resolve…" }).click();
  await page
    .getByLabel("Note")
    .fill("Called the supplier on their old number: the new account is right.");
  await page.getByRole("button", { name: "Resolve check" }).click();
  await expect(check).toContainText("Resolved by");

  await page.getByRole("button", { name: "Mark reviewed" }).click();
  await expect(page.getByText("Awaiting approval").first()).toBeVisible();

  // Approvals: approve it (the sandbox has four-eyes off).
  await page.getByRole("link", { name: "Approvals" }).first().click();
  await page.waitForURL(/\/app\/approvals/);
  const row = page.locator("li, tr").filter({ hasText: S07 }).first();
  await row.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText(new RegExp(`You approved ${S07}`))).toBeVisible();

  // Exports: one CSV row per approved invoice.
  await page.getByRole("link", { name: "Exports" }).first().click();
  await page.waitForURL(/\/app\/exports/);
  await page
    .locator("label")
    .filter({ hasText: "CSV, one row per invoice" })
    .filter({ hasNotText: "invoice line" })
    .click();
  await expect(page.getByRole("radio", { checked: true })).toHaveValue(
    "csv_invoices",
  );
  await page.getByRole("button", { name: /^Export \d+ invoices?$/ }).click();
  const downloadLink = page.getByRole("link", { name: /Download/ }).first();
  await expect(downloadLink).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    downloadLink.click(),
  ]);
  const path = await download.path();
  const csv = (await readFile(path, "utf-8")).replace(BOM, "");
  const lines = csv.split("\r\n").filter((line) => line !== "");
  expect(lines[0]).toContain("Rechnungsnummer");
  expect(lines).toHaveLength(1 + APPROVED_AFTER_TEST);
  expect(csv).toContain(S07);
});
