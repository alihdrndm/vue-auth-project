import { VueQueryPlugin } from "@tanstack/vue-query";
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";
import { createMemoryHistory, createRouter, type Router } from "vue-router";

import { createQueryClient } from "../api/query";
import type { components } from "../api/schema";
import { parseFrom } from "../features/inbox/listParams";
import { json, problem } from "../testing/http";
import InboxView from "./InboxView.vue";

type DocumentSummary = components["schemas"]["DocumentSummary"];

const STATS = {
  by_status: {
    received: 0,
    processing: 1,
    needs_review: 7,
    awaiting_approval: 3,
    approved: 1,
    rejected: 1,
    exported: 0,
    failed: 0,
  },
  blocked: 2,
  overdue: 0,
  awaiting_my_approval: 0,
  llm: {
    lifetime_spent_usd: "0.00",
    lifetime_budget_usd: "2.00",
    month_spent_usd: "0.00",
    month_budget_usd: "1.00",
  },
};

const SUPPLIERS = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: "s-kessler",
      name: "Elektro Kessler GmbH",
      invoice_count: 3,
      first_seen_at: "2026-10-01T10:00:00Z",
      last_seen_at: "2026-10-08T10:00:00Z",
    },
    {
      id: "s-albers",
      name: "Spedition Albers GmbH",
      invoice_count: 2,
      first_seen_at: "2026-10-01T10:00:00Z",
      last_seen_at: "2026-10-08T10:00:00Z",
    },
  ],
};

function doc(overrides: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: "d-1",
    original_filename: "Kessler_RE-2026-0412.xml",
    kind: "xml",
    format_label: "XRechnung · UBL",
    type_code: 380,
    status: "needs_review",
    received_at: "2026-10-07T14:30:00Z",
    invoice_number: "RE-2026-0412",
    supplier_name: "Elektro Kessler GmbH",
    gross_total: "1190.00",
    currency: "EUR",
    due_date: "2099-10-23",
    is_einvoice: true,
    validation_status: "valid",
    open_block_checks: 0,
    open_warn_checks: 0,
    allowed_actions: [],
    ...overrides,
  };
}

function page(results: DocumentSummary[], count = results.length) {
  return { count, next: null, previous: null, results };
}

type ListHandler = (query: URLSearchParams) => Response | Promise<Response>;

let listHandler: ListHandler;
let statsHandler: () => Response;
let requests: URL[];
let router: Router;

const Review = { render: () => h("p", "review") };
const UploadZoneStub = {
  name: "UploadZone",
  emits: ["uploaded"],
  render: () => h("div", [h("button", { type: "button" }, "Upload")]),
};

beforeEach(() => {
  requests = [];
  listHandler = () => json(200, page([doc()]));
  statsHandler = () => json(200, STATS);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(
        input instanceof Request ? input.url : String(input),
        location.origin,
      );
      requests.push(url);
      if (url.pathname === "/api/v1/stats") return statsHandler();
      if (url.pathname === "/api/v1/suppliers") return json(200, SUPPLIERS);
      if (url.pathname === "/api/v1/documents")
        return listHandler(url.searchParams);
      return problem(404, "NOT_FOUND");
    }),
  );
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/app/inbox", name: "inbox", component: InboxView },
      { path: "/app/invoices/:id", name: "invoice", component: Review },
    ],
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

async function mountAt(path = "/app/inbox") {
  await router.push(path);
  await router.isReady();
  const wrapper = mount(InboxView, {
    global: {
      plugins: [router, [VueQueryPlugin, { queryClient: createQueryClient() }]],
      stubs: { UploadZone: UploadZoneStub },
    },
  });
  await flushPromises();
  return wrapper;
}

function listRequests(): URLSearchParams[] {
  return requests
    .filter((url) => url.pathname === "/api/v1/documents")
    .map((url) => url.searchParams);
}

function lastListQuery(): Record<string, string> {
  const last = listRequests().at(-1);
  return last ? Object.fromEntries(last.entries()) : {};
}

describe("InboxView", () => {
  it("shows the status tabs with counts from /stats", async () => {
    const wrapper = await mountAt();

    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs.map((tab) => tab.text())).toEqual([
      "Needs review7",
      "Awaiting approval3",
      "Approved1",
      "Exported0",
      "Failed0",
      "All13",
    ]);
    expect(tabs[0]?.attributes("aria-selected")).toBe("true");
    expect(lastListQuery()).toEqual({
      status: "needs_review",
      ordering: "-received_at",
    });
  });

  it("switching tabs updates the URL and the request", async () => {
    const wrapper = await mountAt();

    await wrapper.findAll('[role="tab"]')[2]?.trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.query.tab).toBe("approved");
    expect(lastListQuery().status).toBe("approved");

    await wrapper.findAll('[role="tab"]')[5]?.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.tab).toBe("all");
    expect(lastListQuery().status).toBeUndefined();
  });

  it("takes the top bar search from ?q= and highlights it", async () => {
    const wrapper = await mountAt("/app/inbox?q=kessler&tab=all");

    expect(lastListQuery()).toEqual({ q: "kessler", ordering: "-received_at" });
    expect(wrapper.find("mark").text()).toBe("Kessler");

    await wrapper.get('[aria-label="Clear search “kessler”"]').trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.q).toBeUndefined();
    expect(lastListQuery().q).toBeUndefined();
  });

  it("maps the supplier and format filters to the request", async () => {
    const wrapper = await mountAt();

    const selects = wrapper.findAll("select");
    expect(selects[0]?.findAll("option").map((o) => o.text())).toEqual([
      "All suppliers",
      "Elektro Kessler GmbH",
      "Spedition Albers GmbH",
    ]);
    await selects[0]?.setValue("s-albers");
    await flushPromises();
    expect(lastListQuery().supplier).toBe("s-albers");
    expect(router.currentRoute.value.query.supplier).toBe("s-albers");

    await wrapper.findAll("select")[1]?.setValue("Plain PDF");
    await flushPromises();
    expect(lastListQuery()).toMatchObject({
      supplier: "s-albers",
      format: "Plain PDF",
    });

    const clear = wrapper
      .findAll("button")
      .find((button) => button.text() === "Clear filters");
    await clear?.trigger("click");
    await flushPromises();
    expect(lastListQuery().supplier).toBeUndefined();
    expect(lastListQuery().format).toBeUndefined();
  });

  it("maps sortable headers to the API ordering", async () => {
    const wrapper = await mountAt();
    const header = (label: string) =>
      wrapper.findAll("th button").find((button) => button.text() === label);

    expect(
      wrapper
        .findAll("th")
        .find((th) => th.text() === "Received")
        ?.attributes("aria-sort"),
    ).toBe("descending");

    await header("Gross")?.trigger("click");
    await flushPromises();
    expect(lastListQuery().ordering).toBe("-gross_total");

    await header("Due")?.trigger("click");
    await flushPromises();
    expect(lastListQuery().ordering).toBe("due_date");

    await header("Received")?.trigger("click");
    await flushPromises();
    await header("Received")?.trigger("click");
    await flushPromises();
    expect(lastListQuery().ordering).toBe("received_at");
    expect(router.currentRoute.value.query.ordering).toBe("received_at");
  });

  it("pages through 25 at a time", async () => {
    listHandler = () => json(200, page([doc()], 60));
    const wrapper = await mountAt();

    expect(wrapper.text()).toContain("Page 1 of 3");
    const next = wrapper
      .findAll("nav button")
      .find((button) => button.text() === "Next");
    await next?.trigger("click");
    await flushPromises();
    expect(lastListQuery().page).toBe("2");
    expect(router.currentRoute.value.query.page).toBe("2");
  });

  it("shows formatted amounts, credit notes negative and overdue dates", async () => {
    listHandler = () =>
      json(
        200,
        page([
          doc({ id: "a", due_date: "2020-01-15" }),
          doc({
            id: "b",
            type_code: 381,
            gross_total: "58.31",
            status: "approved",
            format_label: "XRechnung · UBL · credit note",
            open_block_checks: 1,
            open_warn_checks: 2,
          }),
        ]),
      );
    const wrapper = await mountAt();
    const rows = wrapper.findAll("tbody tr").map((row) => ({
      text: () => row.text().replace(/ /g, " "),
      find: (selector: string) => row.find(selector),
    }));

    expect(rows[0]?.text()).toContain("1.190,00 €");
    expect(rows[0]?.text()).toContain("15 Jan 2020");
    expect(rows[0]?.text()).toContain("overdue");
    expect(rows[1]?.text()).toContain("−58,31 €");
    expect(rows[1]?.find('[role="img"]').attributes("aria-label")).toBe(
      "1 blocking check, 2 warnings",
    );
    // A credit-note label seen in the list becomes a format option.
    expect(wrapper.findAll("select")[1]?.text()).toContain(
      "XRechnung · UBL · credit note",
    );
  });

  it("shows the processing step and polls every 2 s until nothing processes", async () => {
    vi.useFakeTimers({
      toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval"],
    });
    let processing = true;
    listHandler = () =>
      json(
        200,
        page([
          processing
            ? doc({ status: "processing", processing_step: "validate" })
            : doc({ status: "needs_review" }),
        ]),
      );
    const wrapper = await mountAt("/app/inbox?tab=all");
    await vi.advanceTimersByTimeAsync(0);

    expect(wrapper.text()).toContain(
      "Step 2 of 4: checking the e-invoice rules",
    );
    expect(wrapper.get('[aria-live="polite"]').text()).toBe(
      "1 invoice is being processed",
    );
    const before = listRequests().length;
    const statsBefore = requests.filter(
      (url) => url.pathname === "/api/v1/stats",
    ).length;

    processing = false;
    await vi.advanceTimersByTimeAsync(2_000);
    expect(listRequests().length).toBe(before + 1);
    expect(wrapper.text()).not.toContain("Step 2 of 4");
    // Finishing a row refreshes the tab counts.
    expect(
      requests.filter((url) => url.pathname === "/api/v1/stats").length,
    ).toBe(statsBefore + 1);

    await vi.advanceTimersByTimeAsync(6_000);
    expect(listRequests().length).toBe(before + 1);
  });

  it("shows the empty state of each tab", async () => {
    listHandler = () => json(200, page([]));
    const wrapper = await mountAt();

    expect(wrapper.text()).toContain("Nothing needs review");
    expect(wrapper.text()).toContain(
      "New invoices land here once their checks have run.",
    );

    await router.push("/app/inbox?tab=failed");
    await flushPromises();
    expect(wrapper.text()).toContain("No failed files");
  });

  it("offers Upload on the empty All tab", async () => {
    listHandler = () => json(200, page([]));
    const wrapper = await mountAt("/app/inbox?tab=all");

    expect(wrapper.text()).toContain("No invoices yet");
    const upload = wrapper
      .findAll("button")
      .find((button) => button.text() === "Upload invoices");
    expect(upload).toBeDefined();
  });

  it("shows no results with a way to clear search and filters", async () => {
    listHandler = () => json(200, page([]));
    const wrapper = await mountAt(
      "/app/inbox?tab=all&q=zzz&format=Plain%20PDF",
    );

    expect(wrapper.text()).toContain("No invoices match");
    expect(wrapper.text()).toContain(
      "Nothing in this tab matches your search and filters.",
    );
    const clear = wrapper
      .findAll("button")
      .find((button) => button.text() === "Clear search and filters");
    await clear?.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query).toEqual({ tab: "all" });
  });

  it("shows the problem and retries", async () => {
    listHandler = () =>
      problem(403, "FORBIDDEN_ROLE", "Your role (viewer) can't do this.");
    const wrapper = await mountAt();

    expect(wrapper.get('[role="alert"]').text()).toContain(
      "Your role (viewer) can't do this.",
    );
    listHandler = () => json(200, page([doc()]));
    const retry = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Try again"));
    await retry?.trigger("click");
    await flushPromises();
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("RE-2026-0412");
  });

  it("shows skeleton rows while loading", async () => {
    listHandler = () => new Promise<Response>(() => undefined);
    const wrapper = await mountAt();

    expect(wrapper.get('[aria-busy="true"]').attributes("aria-label")).toBe(
      "Loading invoices",
    );
  });

  it("opens a row on click and on Enter, passing the list as `from`", async () => {
    const wrapper = await mountAt("/app/inbox?tab=all&q=kessler&page=2");

    await wrapper.get("tbody tr").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("invoice");
    expect(router.currentRoute.value.params.id).toBe("d-1");
    const from = String(router.currentRoute.value.query.from);
    expect(parseFrom(from)).toEqual({
      q: "kessler",
      ordering: "-received_at",
      page: 2,
    });

    router.back();
    await flushPromises();
    const again = await mountAt("/app/inbox");
    await again.get("tbody tr").trigger("keydown", { key: "Enter" });
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("invoice");
    expect(parseFrom(String(router.currentRoute.value.query.from))).toEqual({
      status: "needs_review",
      ordering: "-received_at",
    });
  });

  it("refreshes the list and counts after an upload", async () => {
    const wrapper = await mountAt();
    const lists = listRequests().length;
    const stats = requests.filter((u) => u.pathname === "/api/v1/stats").length;

    wrapper.findComponent(UploadZoneStub).vm.$emit("uploaded", "d-9");
    await flushPromises();

    expect(listRequests().length).toBe(lists + 1);
    expect(requests.filter((u) => u.pathname === "/api/v1/stats").length).toBe(
      stats + 1,
    );
  });

  it("shows cards that link to the review on phones", async () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({
        matches: true,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      })),
    );
    const wrapper = await mountAt();

    expect(wrapper.find("table").exists()).toBe(false);
    const card = wrapper.get(".cards a");
    expect(card.attributes("href")).toContain("/app/invoices/d-1?from=");
    expect(wrapper.get('input[type="search"]').attributes("aria-invalid")).toBe(
      undefined,
    );
  });
});
