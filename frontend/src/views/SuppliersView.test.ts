import { flushPromises, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "../api/schema";
import { buttonByText, mountScreen } from "../features/approvals/screenTesting";
import { json, problem } from "../testing/http";
import SupplierDetailView from "./SupplierDetailView.vue";
import SuppliersView from "./SuppliersView.vue";

type SupplierDetail = components["schemas"]["SupplierDetail"];

const SUPPLIERS = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: "s-nord",
      name: "Bürobedarf Nord KG",
      vat_id: "DE811111111",
      invoice_count: 3,
      first_seen_at: "2026-10-02T08:55:00Z",
      last_seen_at: "2026-10-09T07:58:00Z",
    },
    {
      id: "s-kessler",
      name: "Elektro Kessler GmbH",
      invoice_count: 1,
      first_seen_at: "2026-10-07T10:00:00Z",
      last_seen_at: "2026-10-07T10:00:00Z",
    },
  ],
};

function detail(overrides: Partial<SupplierDetail> = {}): SupplierDetail {
  return {
    id: "s-nord",
    name: "Bürobedarf Nord KG",
    invoice_count: 3,
    first_seen_at: "2026-10-02T08:55:00Z",
    last_seen_at: "2026-10-09T07:58:00Z",
    ibans: [
      {
        iban: "DE89370400440532013000",
        first_seen_invoice_id: "inv-11",
        first_seen_document_id: "doc-11",
        first_seen_at: "2026-10-02T08:55:00Z",
        last_seen_at: "2026-10-09T07:58:00Z",
        trusted: true,
        status: "known",
      },
      {
        iban: "DE02120300000000202051",
        first_seen_invoice_id: "inv-7",
        first_seen_document_id: "doc-7",
        first_seen_at: "2026-10-07T10:05:00Z",
        last_seen_at: "2026-10-07T10:05:00Z",
        trusted: false,
        status: "new",
      },
    ],
    invoices: [
      {
        document_id: "doc-2",
        invoice_number: "BN-88213",
        gross_total: "412.34",
        currency: "EUR",
        status: "awaiting_approval",
        received_at: "2026-10-09T07:58:00Z",
      },
      {
        document_id: "doc-7",
        invoice_number: "BN-88290",
        gross_total: "97.58",
        currency: "EUR",
        status: "needs_review",
        received_at: "2026-10-07T10:05:00Z",
      },
      {
        document_id: "doc-11",
        invoice_number: "BN-88102-G",
        // As the API sends a credit note: a positive amount and type code 381.
        type_code: 381,
        gross_total: "58.31",
        currency: "EUR",
        status: "approved",
        received_at: "2026-10-02T08:55:00Z",
      },
    ],
    ...overrides,
  };
}

let wrapper: VueWrapper | null = null;
let urls: URL[] = [];

function serve(handler: (url: URL) => Response | Promise<Response>): void {
  urls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request) => {
      const url = new URL(input.url);
      urls.push(url);
      return handler(url);
    }),
  );
}

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("SuppliersView", () => {
  it("shows a skeleton while loading", async () => {
    serve(() => new Promise<Response>(() => undefined));
    const screen = await mountScreen(
      SuppliersView,
      "suppliers",
      "/app/suppliers",
    );
    wrapper = screen.wrapper;
    expect(wrapper.find('[aria-label="Loading suppliers"]').exists()).toBe(
      true,
    );
  });

  it("lists suppliers with their invoice counts and opens one", async () => {
    serve(() => json(200, SUPPLIERS));
    const screen = await mountScreen(
      SuppliersView,
      "suppliers",
      "/app/suppliers",
    );
    wrapper = screen.wrapper;
    const text = wrapper.text();
    expect(text).toContain("2 suppliers");
    expect(text).toContain("Bürobedarf Nord KG");
    expect(text).toContain("DE811111111");
    expect(wrapper.findAll("tbody tr")[0]?.text()).toContain("3");

    await wrapper.findAll("tbody tr")[1]?.trigger("click");
    await flushPromises();
    expect(screen.router.currentRoute.value.path).toBe(
      "/app/suppliers/s-kessler",
    );
  });

  it("searches with ?q= and offers to clear an empty result", async () => {
    serve((url) =>
      json(
        200,
        url.searchParams.get("q")
          ? { count: 0, next: null, previous: null, results: [] }
          : SUPPLIERS,
      ),
    );
    const screen = await mountScreen(
      SuppliersView,
      "suppliers",
      "/app/suppliers?q=zzz",
    );
    wrapper = screen.wrapper;
    expect(urls.at(-1)?.searchParams.get("q")).toBe("zzz");
    expect(wrapper.text()).toContain("No suppliers match");

    await buttonByText(wrapper, "Clear search").trigger("click");
    await flushPromises();
    expect(screen.router.currentRoute.value.query.q).toBeUndefined();
    expect(wrapper.text()).toContain("Elektro Kessler GmbH");
  });

  it("puts typed search text into the URL", async () => {
    serve(() => json(200, SUPPLIERS));
    const screen = await mountScreen(
      SuppliersView,
      "suppliers",
      "/app/suppliers",
    );
    wrapper = screen.wrapper;
    vi.useFakeTimers();
    await wrapper.find('input[type="search"]').setValue("nord");
    vi.advanceTimersByTime(400);
    vi.useRealTimers();
    await flushPromises();
    expect(screen.router.currentRoute.value.query.q).toBe("nord");
  });

  it("shows the empty state when there are no suppliers", async () => {
    serve(() =>
      json(200, { count: 0, next: null, previous: null, results: [] }),
    );
    const screen = await mountScreen(
      SuppliersView,
      "suppliers",
      "/app/suppliers",
    );
    wrapper = screen.wrapper;
    expect(wrapper.text()).toContain("No suppliers yet");
  });

  it("shows the problem and retries", async () => {
    let fail = true;
    serve(() =>
      fail
        ? problem(500, "SERVER_ERROR", "Down for a moment.")
        : json(200, SUPPLIERS),
    );
    const screen = await mountScreen(
      SuppliersView,
      "suppliers",
      "/app/suppliers",
    );
    wrapper = screen.wrapper;
    expect(wrapper.text()).toContain("Down for a moment.");
    fail = false;
    await buttonByText(wrapper, "Try again").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Bürobedarf Nord KG");
  });
});

describe("SupplierDetailView", () => {
  async function mountDetail(body: () => Response | Promise<Response>) {
    serve(body);
    const screen = await mountScreen(
      SupplierDetailView,
      "supplier",
      "/app/suppliers/s-nord",
    );
    wrapper = screen.wrapper;
    return screen;
  }

  it("shows a skeleton while loading", async () => {
    await mountDetail(() => new Promise<Response>(() => undefined));
    expect(wrapper?.find('[aria-label="Loading the supplier"]').exists()).toBe(
      true,
    );
  });

  it("highlights an unconfirmed IBAN and links to its check", async () => {
    const screen = await mountDetail(() => json(200, detail()));
    const items = wrapper?.findAll(".iban") ?? [];
    expect(items).toHaveLength(2);
    const unconfirmed = items[0];
    expect(unconfirmed?.classes()).toContain("iban--new");
    expect(unconfirmed?.text()).toContain("DE02 1203 0000 0000 2020 51");
    expect(unconfirmed?.text()).toContain("New account");
    expect(unconfirmed?.text()).toContain("Not confirmed yet");
    expect(unconfirmed?.text()).toContain("BN-88290");
    const link = unconfirmed?.find("a");
    expect(link?.text()).toContain("Open the check on BN-88290");
    expect(link?.attributes("href")).toBe("/app/invoices/doc-7");

    expect(items[1]?.text()).toContain("Known account");
    expect(items[1]?.text()).toContain("BN-88102-G");

    await wrapper?.findAll("tbody tr")[0]?.trigger("click");
    await flushPromises();
    expect(screen.router.currentRoute.value.path).toBe("/app/invoices/doc-2");
  });

  it("names who confirmed a changed IBAN, when, and the note", async () => {
    await mountDetail(() =>
      json(
        200,
        detail({
          ibans: [
            {
              iban: "DE02120300000000202051",
              first_seen_invoice_id: "inv-7",
              first_seen_document_id: "doc-7",
              first_seen_at: "2026-10-07T10:05:00Z",
              last_seen_at: "2026-10-07T10:05:00Z",
              trusted: true,
              status: "confirmed",
              confirmed_by_name: "Anna Weber",
              confirmed_at: "2026-10-09T09:00:00Z",
              confirmation_note: "Called on the number we already had.",
            },
          ],
        }),
      ),
    );
    const item = wrapper?.find(".iban");
    expect(item?.classes()).toContain("iban--confirmed");
    expect(item?.text()).toContain("Confirmed change");
    expect(item?.text()).toContain("Confirmed by Anna Weber, 09 Oct 2026");
    expect(item?.text()).toContain("‘Called on the number we already had.’");
    expect(item?.text()).not.toContain("Not confirmed yet");
  });

  it("shows the invoices with their status and the amounts", async () => {
    await mountDetail(() => json(200, detail()));
    const text = wrapper?.text() ?? "";
    expect(text).toContain("3 invoices since 02 Oct 2026");
    expect(text).toContain("412,34 €");
    expect(text).toContain("−58,31 €");
    expect(text).toContain("Awaiting approval");
  });

  it("shows an empty IBAN history", async () => {
    await mountDetail(() => json(200, detail({ ibans: [] })));
    expect(wrapper?.text()).toContain(
      "No bank account on this supplier’s invoices yet.",
    );
  });

  it("shows the problem and a not-found state", async () => {
    await mountDetail(() => problem(500, "SERVER_ERROR", "Down for a moment."));
    expect(wrapper?.text()).toContain("Down for a moment.");
    wrapper?.unmount();
    await mountDetail(() => problem(404, "NOT_FOUND", "No such supplier."));
    expect(wrapper?.text()).toContain("No such supplier");
  });
});
