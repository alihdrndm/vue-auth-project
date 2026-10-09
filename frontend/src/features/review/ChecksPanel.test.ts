import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetCsrfToken } from "../../api/client";
import type { components } from "../../api/schema";
import { json, mockFetch, problem, setCsrfCookie } from "../../testing/http";
import type { Check } from "./checks";
import ChecksPanel from "./ChecksPanel.vue";

type DocumentDetail = components["schemas"]["DocumentDetail"];

function check(overrides: Partial<Check> = {}): Check {
  return {
    id: `id-${overrides.check_id ?? "C05"}`,
    check_id: "C05",
    code: "BANK_DETAILS_CHANGED",
    severity: "block",
    message: "Bank account differs from earlier invoices",
    details: {},
    resolve: { enabled: true },
    ...overrides,
  };
}

function documentWith(checks: Check[]): DocumentDetail {
  return { invoice_number: "BN-88290", checks } as unknown as DocumentDetail;
}

function mountPanel(checks: Check[]) {
  return mount(ChecksPanel, {
    props: { document: documentWith(checks) },
    attachTo: document.body,
    global: {
      stubs: {
        RouterLink: {
          props: ["to"],
          template: '<a :data-to="JSON.stringify(to)"><slot /></a>',
        },
      },
    },
  });
}

beforeEach(() => {
  setCsrfCookie("token");
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.open = true;
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.open = false;
  };
});

afterEach(() => {
  vi.unstubAllGlobals();
  setCsrfCookie(null);
  resetCsrfToken();
  document.body.innerHTML = "";
});

async function openAndType(
  wrapper: ReturnType<typeof mountPanel>,
  note: string,
) {
  await wrapper.find("button:not([disabled])").trigger("click");
  await flushPromises();
  const textarea = document.body.querySelector("textarea");
  if (!textarea) throw new Error("no textarea");
  textarea.value = note;
  textarea.dispatchEvent(new Event("input"));
  await flushPromises();
}

function confirmButton(label: string): HTMLButtonElement {
  const button = Array.from(document.body.querySelectorAll("button")).find(
    (candidate) => candidate.textContent?.trim() === label,
  );
  if (!button) throw new Error(`no ${label} button`);
  return button;
}

describe("ChecksPanel", () => {
  it("lists open checks first, worst first", () => {
    const wrapper = mountPanel([
      check({ check_id: "C04", severity: "info", message: "First invoice" }),
      check({ check_id: "C08", severity: "warn", message: "Overdue" }),
      check(),
    ]);
    const ids = wrapper.findAll(".card__id").map((node) => node.text());
    expect(ids).toEqual(["C05", "C08", "C04"]);
    wrapper.unmount();
  });

  it("shows why a check can't be resolved, and offers no button for info", () => {
    const wrapper = mountPanel([
      check({
        check_id: "C15",
        message: "Validation failed",
        resolve: {
          enabled: false,
          reason_code: "FORBIDDEN_ROLE",
          reason: "Your role (accountant) can't do this.",
        },
      }),
      check({ check_id: "C04", severity: "info" }),
    ]);
    expect(wrapper.text()).toContain("Accept anyway…");
    expect(wrapper.text()).toContain("Your role (accountant) can't do this.");
    expect(wrapper.findAll("button")).toHaveLength(1);
    wrapper.unmount();
  });

  it("refuses a note shorter than 5 characters", async () => {
    const calls = mockFetch(() => json(200, {}));
    const wrapper = mountPanel([check()]);
    await openAndType(wrapper, "ok");
    confirmButton("Resolve check").click();
    await flushPromises();
    expect(document.body.textContent).toContain("Write at least 5 characters.");
    expect(calls).toHaveLength(0);
    wrapper.unmount();
  });

  it("resolves with the note and tells the screen", async () => {
    const calls = mockFetch(() =>
      json(200, check({ resolved_at: "2026-03-01T10:00:00Z" })),
    );
    const wrapper = mountPanel([check()]);
    await openAndType(wrapper, "Called the supplier, new account confirmed.");
    confirmButton("Resolve check").click();
    await flushPromises();
    const post = calls.find((call) => call.method === "POST");
    expect(post?.path).toBe("/api/v1/checks/id-C05/resolve");
    expect(JSON.parse(post?.body ?? "{}")).toEqual({
      note: "Called the supplier, new account confirmed.",
    });
    expect(wrapper.emitted("resolved")).toHaveLength(1);
    wrapper.unmount();
  });

  it("shows the server's reason in the dialog", async () => {
    mockFetch(() =>
      problem(
        409,
        "INVALID_TRANSITION",
        "Only invoices that need review can be changed.",
      ),
    );
    const wrapper = mountPanel([check()]);
    await openAndType(wrapper, "Checked by phone.");
    confirmButton("Resolve check").click();
    await flushPromises();
    expect(document.body.textContent).toContain(
      "Only invoices that need review can be changed.",
    );
    expect(wrapper.emitted("resolved")).toBeUndefined();
    wrapper.unmount();
  });

  it("shows who resolved a check, and the PDF/XML differences", () => {
    const wrapper = mountPanel([
      check({
        check_id: "C09",
        severity: "warn",
        message: "The visible PDF shows different values",
        details: {
          differences: [
            { field: "gross_total", xml: "1200.00", pdf: "1190.00" },
          ],
        },
      }),
      check({
        resolved_at: "2026-03-01T10:00:00Z",
        resolved_by_name: "Anna Weber (sample)",
        resolution_note: "Confirmed by phone.",
        resolve: {
          enabled: false,
          reason_code: "CHECK_NOT_RESOLVABLE",
          reason: "Already resolved.",
        },
      }),
    ]);
    expect(wrapper.text()).toContain("Resolved by Anna Weber (sample)");
    expect(wrapper.text()).toContain("Confirmed by phone.");
    expect(wrapper.text()).toContain("gross total");
    expect(wrapper.text()).toContain("1190.00");
    wrapper.unmount();
  });

  it("links the earlier invoice and the source instead of showing a raw URL", () => {
    const url =
      "https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108886/eInvoicing+in+Germany";
    const wrapper = mountPanel([
      check({
        check_id: "C02",
        message: "An invoice with the same number was received earlier.",
        details: { document_id: "doc-early" },
      }),
      check({
        check_id: "C11",
        severity: "info",
        message: `This is a plain PDF. Source of the mandate dates: European Commission, "eInvoicing in Germany" (${url}).`,
        details: { source_url: url },
      }),
    ]);
    const links = wrapper.findAll(".card__message a");
    expect(links.map((link) => link.text())).toEqual([
      "Open the earlier invoice",
      "Source: European Commission",
    ]);
    expect(links[0]?.attributes("data-to")).toContain("doc-early");
    expect(links[1]?.attributes("href")).toBe(url);
    expect(wrapper.text()).not.toContain("https://");
    wrapper.unmount();
  });

  it("shows why a check can't be resolved as visible text", () => {
    const wrapper = mountPanel([
      check({
        resolve: {
          enabled: false,
          reason: "Only invoices that need review can be changed.",
        },
      }),
    ]);
    expect(wrapper.find(".card__why").text()).toBe(
      "Only invoices that need review can be changed.",
    );
    wrapper.unmount();
  });
});
