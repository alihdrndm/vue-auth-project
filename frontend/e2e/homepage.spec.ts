// Homepage accessibility (HANDOFF M8: zero serious or critical axe violations) and its
// interactions in a real browser, at desktop and phone width.
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

const SIZES = [
  { width: 1440, height: 900 },
  { width: 390, height: 844 },
] as const;

for (const size of SIZES) {
  test(`homepage has no serious accessibility problems at ${size.width}`, async ({
    page,
  }) => {
    await page.setViewportSize(size);
    await page.goto("/");
    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter(
      (violation) =>
        violation.impact === "serious" || violation.impact === "critical",
    );
    expect(
      serious.map(
        (violation) => `${violation.id}: ${violation.nodes.length} nodes`,
      ),
    ).toEqual([]);
  });
}

/** Presses Tab until the focused element's text starts with `label` (at most 80 times). */
async function tabTo(page: Page, label: string): Promise<void> {
  for (let i = 0; i < 80; i += 1) {
    await page.keyboard.press("Tab");
    const text = await page.evaluate(
      () => document.activeElement?.textContent?.trim() ?? "",
    );
    if (text.startsWith(label)) return;
  }
  throw new Error(`Tab never reached "${label}"`);
}

const focusedText = (page: Page) =>
  page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");

test("both acts work with Tab and Enter alone", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  // Act 1: Tab to the first "Stamp it"; after each stamp focus moves to the next one.
  await tabTo(page, "Stamp it");
  for (let stamp = 0; stamp < 4; stamp += 1) await page.keyboard.press("Enter");
  await expect(page.locator(".done")).toContainText(
    "4 invoices stamped. 1 is a valid e-invoice.",
  );
  expect(await focusedText(page)).toContain("Do it again");

  // Act 2: focus follows each step.
  await tabTo(page, "Use example note");
  await page.keyboard.press("Enter");
  await tabTo(page, "Resolve check");
  await page.keyboard.press("Enter");
  expect(await focusedText(page)).toBe("Mark reviewed");
  await page.keyboard.press("Enter");
  expect(await focusedText(page)).toBe("Approve");
  await page.keyboard.press("Enter");
  await expect(page.locator(".card__done")).toHaveText(
    "You approved this on 09 Oct 2026.",
  );
  await expect(page.locator(".export--in")).toBeVisible();
  expect(await focusedText(page)).toContain("Do it again");
});

test("the phone layout never scrolls sideways", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(390);
});
