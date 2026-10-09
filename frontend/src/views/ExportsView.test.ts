import { flushPromises, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "../api/schema";
import { useToast } from "../components/ui/useToast";
import { buttonByText, mountScreen } from "../features/approvals/screenTesting";
import {
  json,
  mockFetch,
  problem,
  type RecordedRequest,
} from "../testing/http";
import ExportsView from "./ExportsView.vue";

type Role = components["schemas"]["RoleEnum"];
type ExportRow = components["schemas"]["Export"];

function stats(approved: number) {
  return {
    by_status: {
      received: 0,
      processing: 0,
      needs_review: 0,
      awaiting_approval: 0,
      approved,
      rejected: 0,
      exported: 0,
      failed: 0,
    },
    blocked: 0,
    overdue: 0,
    awaiting_my_approval: 0,
    llm: {
      lifetime_spent_usd: "0.00",
      lifetime_budget_usd: "2.00",
      month_spent_usd: "0.00",
      month_budget_usd: "1.00",
    },
  };
}

const PAST: ExportRow = {
  id: "x-1",
  format: "zip_bundle",
  row_count: 14,
  download_url: "/api/v1/exports/x-1/download",
  created_at: "2026-10-01T09:14:00Z",
  created_by_name: "Anna Weber",
};

function page(results: ExportRow[]) {
  return { count: results.length, next: null, previous: null, results };
}

let wrapper: VueWrapper | null = null;

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  useToast().dismiss();
  vi.unstubAllGlobals();
});

async function mountExports(
  handler: (request: RecordedRequest) => Response | Promise<Response>,
  role: Role = "accountant",
) {
  const calls = mockFetch(handler);
  const screen = await mountScreen(ExportsView, "exports", "/app/exports", {
    role,
  });
  wrapper = screen.wrapper;
  return { ...screen, calls };
}

describe("ExportsView states", () => {
  it("shows a skeleton for past exports while loading", async () => {
    const { wrapper } = await mountExports(
      () => new Promise<Response>(() => undefined),
    );
    expect(wrapper.find('[aria-label="Loading past exports"]').exists()).toBe(
      true,
    );
    expect(wrapper.text()).toContain("Counting approved invoices…");
  });

  it("shows the empty list and the ready count", async () => {
    const { wrapper } = await mountExports((request) =>
      request.path === "/api/v1/stats"
        ? json(200, stats(3))
        : json(200, page([])),
    );
    expect(wrapper.text()).toContain("3 invoices ready");
    expect(wrapper.text()).toContain(
      "No exports yet. Your first export appears here.",
    );
    expect(buttonByText(wrapper, "Export 3 invoices").exists()).toBe(true);
  });

  it("lists past exports with a download link", async () => {
    const { wrapper } = await mountExports((request) =>
      request.path === "/api/v1/stats"
        ? json(200, stats(0))
        : json(200, page([PAST])),
    );
    const row = wrapper.find("tbody tr");
    expect(row.text()).toContain("ZIP bundle with originals");
    expect(row.text()).toContain("14 invoices");
    expect(row.text()).toContain("Anna Weber");
    const link = row.find("a");
    expect(link.attributes("href")).toBe("/api/v1/exports/x-1/download");
    expect(link.attributes("download")).toBeDefined();
    expect(wrapper.text()).toContain("Nothing ready to export");
    expect(
      buttonByText(wrapper, "Export").attributes("disabled"),
    ).toBeDefined();
  });

  it("shows the problem for past exports and retries", async () => {
    let fail = true;
    const { wrapper } = await mountExports((request) => {
      if (request.path === "/api/v1/stats") return json(200, stats(0));
      return fail
        ? problem(500, "SERVER_ERROR", "Exports are unavailable.")
        : json(200, page([PAST]));
    });
    expect(wrapper.text()).toContain("Exports are unavailable.");
    fail = false;
    await buttonByText(wrapper, "Try again").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("ZIP bundle with originals");
  });
});

describe("ExportsView creating an export", () => {
  it("exports in the chosen format, then refreshes the list", async () => {
    let exported = false;
    const { wrapper, calls } = await mountExports((request) => {
      if (request.path === "/api/v1/stats")
        return json(200, stats(exported ? 0 : 1));
      if (request.method === "POST") {
        exported = true;
        return json(201, {
          id: "x-2",
          format: "csv_lines",
          row_count: 1,
          download_url: "/api/v1/exports/x-2/download",
        });
      }
      return json(
        200,
        page(
          exported
            ? [
                {
                  ...PAST,
                  id: "x-2",
                  format: "csv_lines",
                  row_count: 1,
                  download_url: "/api/v1/exports/x-2/download",
                },
              ]
            : [],
        ),
      );
    });

    await wrapper.find('input[value="csv_lines"]').setValue(true);
    await buttonByText(wrapper, "Export 1 invoice").trigger("click");
    await flushPromises();

    const post = calls.find((call) => call.method === "POST");
    expect(post?.path).toBe("/api/v1/exports");
    expect(JSON.parse(post?.body ?? "{}")).toEqual({ format: "csv_lines" });
    expect(document.body.textContent).toContain(
      "Export ready. 1 invoice moved to Exported.",
    );
    const links = wrapper
      .findAll("a")
      .filter((a) => a.attributes("href") === "/api/v1/exports/x-2/download");
    expect(links.length).toBeGreaterThanOrEqual(2);
    expect(wrapper.find("tbody tr").text()).toContain(
      "CSV, one row per invoice line",
    );
    expect(wrapper.text()).toContain("Nothing ready to export");
    expect(
      calls.filter(
        (call) => call.path === "/api/v1/exports" && call.method === "GET",
      ).length,
    ).toBeGreaterThanOrEqual(2);
  });

  it("explains NOTHING_TO_EXPORT", async () => {
    const { wrapper } = await mountExports((request) => {
      if (request.path === "/api/v1/stats") return json(200, stats(2));
      if (request.method === "POST")
        return problem(
          409,
          "NOTHING_TO_EXPORT",
          "There are no approved invoices to export.",
        );
      return json(200, page([]));
    });
    await buttonByText(wrapper, "Export 2 invoices").trigger("click");
    await flushPromises();
    expect(wrapper.find('[role="alert"]').text()).toContain(
      "There are no approved invoices to export.",
    );
  });

  it("disables export for roles that can't export, with the reason", async () => {
    const { wrapper, calls } = await mountExports(
      (request) =>
        request.path === "/api/v1/stats"
          ? json(200, stats(2))
          : json(200, page([])),
      "approver",
    );
    const button = buttonByText(wrapper, "Export 2 invoices");
    expect(button.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain(
      "Your role (Approver) can't export. Admins and accountants can.",
    );
    await button.trigger("click");
    await flushPromises();
    expect(calls.some((call) => call.method === "POST")).toBe(false);
  });
});
