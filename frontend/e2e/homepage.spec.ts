// Homepage accessibility (HANDOFF M8: zero serious or critical axe violations) and its
// interactions in a real browser, at desktop and phone width.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

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

test("both acts work with the keyboard", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  for (const number of [
    "RE-2026-0412",
    "2026-1043",
    "F-2026-118",
    "RE-2026-0413",
  ]) {
    const stamp = page.getByRole("button", {
      name: new RegExp(`^Stamp it\\s*: ${number}$`),
    });
    await stamp.focus();
    await page.keyboard.press("Enter");
  }
  await expect(page.locator(".done")).toContainText(
    "4 invoices stamped. 1 is a valid e-invoice.",
  );

  await page.getByRole("button", { name: "Use example note" }).click();
  await page.getByRole("button", { name: "Resolve check" }).click();
  await page.getByRole("button", { name: "Mark reviewed" }).click();
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.locator(".card__done")).toHaveText(
    "You approved this on 09 Oct 2026.",
  );
  await expect(page.locator(".export--in")).toBeVisible();
});

test("the phone layout never scrolls sideways", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(390);
});
