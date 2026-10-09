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
import ApprovalsView from "./ApprovalsView.vue";

type DocumentSummary = components["schemas"]["DocumentSummary"];

const ENABLED = [
  { action: "approve", enabled: true },
  { action: "reject", enabled: true },
  { action: "send_back", enabled: true },
  { action: "delete", enabled: true },
];

function doc(overrides: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: "d-1",
    original_filename: "Kessler.xml",
    type_code: 380,
    status: "awaiting_approval",
    received_at: "2026-10-07T14:30:00Z",
    invoice_number: "RE-2026-0412",
    supplier_name: "Elektro Kessler GmbH",
    gross_total: "1190.00",
    currency: "EUR",
    due_date: "2026-10-23",
    open_block_checks: 0,
    open_warn_checks: 1,
    payee_iban_last4: "4417",
    iban_status: "known",
    reviewed_by_name: "Anna Weber",
    allowed_actions: ENABLED,
    ...overrides,
  };
}

function page(results: DocumentSummary[]) {
  return { count: results.length, next: null, previous: null, results };
}

let wrapper: VueWrapper | null = null;

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  useToast().dismiss();
  vi.unstubAllGlobals();
});

async function mountApprovals(
  handler: (request: RecordedRequest) => Response | Promise<Response>,
  organization = {},
) {
  const calls = mockFetch(handler);
  const screen = await mountScreen(
    ApprovalsView,
    "approvals",
    "/app/approvals",
    {
      role: "approver",
      organization,
    },
  );
  wrapper = screen.wrapper;
  return { ...screen, calls };
}

describe("ApprovalsView states", () => {
  it("shows a skeleton while loading", async () => {
    const { wrapper } = await mountApprovals(
      () => new Promise<Response>(() => undefined),
    );
    expect(wrapper.find('[aria-label="Loading approvals"]').exists()).toBe(
      true,
    );
  });

  it("shows the problem with Try again on an error", async () => {
    let fail = true;
    const { wrapper } = await mountApprovals(() =>
      fail
        ? problem(500, "SERVER_ERROR", "The server had a problem.")
        : json(200, page([doc()])),
    );
    expect(wrapper.find('[role="alert"]').text()).toContain(
      "The server had a problem.",
    );
    fail = false;
    await buttonByText(wrapper, "Try again").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Elektro Kessler GmbH");
  });

  it("shows the empty state", async () => {
    const { wrapper } = await mountApprovals(() => json(200, page([])));
    expect(wrapper.text()).toContain("Nothing waiting for you");
    expect(wrapper.text()).toContain(
      "Invoices arrive here once someone else marks them reviewed.",
    );
  });

  it("lists invoices awaiting approval with the IBAN tag and warnings", async () => {
    const { wrapper, calls } = await mountApprovals(
      () =>
        json(
          200,
          page([
            doc(),
            doc({
              id: "d-2",
              invoice_number: "BN-88102-G",
              type_code: 381,
              gross_total: "58.31",
              iban_status: "new",
              payee_iban_last4: "2051",
              open_warn_checks: 0,
            }),
          ]),
        ),
      { four_eyes: true },
    );
    expect(calls[0]?.path).toBe("/api/v1/documents");
    const text = wrapper.text();
    expect(text).toContain("•••• 4417");
    expect(text).toContain("Known account");
    expect(text).toContain("New account");
    expect(text).toContain("1 warning");
    expect(text).toMatch(/−58,31\s€/);
    expect(text).toContain("23 Oct 2026");
    expect(text).toContain("Four-eyes is on");
  });

  it("asks for the status awaiting_approval", async () => {
    const urls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Request) => {
        urls.push(input.url);
        return json(200, page([]));
      }),
    );
    const screen = await mountScreen(
      ApprovalsView,
      "approvals",
      "/app/approvals",
    );
    wrapper = screen.wrapper;
    expect(new URL(urls[0] ?? "").searchParams.get("status")).toBe(
      "awaiting_approval",
    );
  });
});

describe("ApprovalsView decisions", () => {
  it("approves inline and refreshes the list", async () => {
    let decided = false;
    const { wrapper, calls } = await mountApprovals((request) => {
      if (request.method === "POST") {
        decided = true;
        return json(200, { ...doc(), status: "approved" });
      }
      if (request.path === "/api/v1/stats") return json(200, {});
      return json(200, page(decided ? [] : [doc()]));
    });

    await buttonByText(wrapper, "Approve").trigger("click");
    await flushPromises();

    const post = calls.find((call) => call.method === "POST");
    expect(post?.path).toBe("/api/v1/documents/d-1/decision");
    expect(JSON.parse(post?.body ?? "{}")).toEqual({
      decision: "approved",
      comment: "",
    });
    expect(document.body.textContent).toContain("You approved RE-2026-0412.");
    expect(wrapper.text()).toContain("Nothing waiting for you");
  });

  it("rejects only with a comment of at least 5 characters", async () => {
    const { wrapper, calls } = await mountApprovals((request) =>
      request.method === "POST"
        ? json(200, { ...doc(), status: "rejected" })
        : json(200, page([doc()])),
    );

    await buttonByText(wrapper, "Reject…").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain("Reject invoice RE-2026-0412?");

    await buttonByText(wrapper, "Reject invoice").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain("Write at least 5 characters.");
    expect(calls.some((call) => call.method === "POST")).toBe(false);

    await wrapper.find("textarea").setValue("Wrong amount on line 2");
    await buttonByText(wrapper, "Reject invoice").trigger("click");
    await flushPromises();

    const post = calls.find((call) => call.method === "POST");
    expect(JSON.parse(post?.body ?? "{}")).toEqual({
      decision: "rejected",
      comment: "Wrong amount on line 2",
    });
    expect(document.body.textContent).toContain("You rejected RE-2026-0412.");
  });

  it("shows a four-eyes conflict as a disabled Approve with the reason", async () => {
    const reason = "You reviewed this invoice. Someone else must approve it.";
    const { wrapper } = await mountApprovals(() =>
      json(
        200,
        page([
          doc({
            allowed_actions: [
              {
                action: "approve",
                enabled: false,
                reason_code: "FOUR_EYES",
                reason,
              },
              { action: "reject", enabled: true },
            ],
          }),
        ]),
      ),
    );

    const approve = buttonByText(wrapper, "Approve");
    expect(approve.attributes("disabled")).toBeDefined();
    expect(
      buttonByText(wrapper, "Reject…").attributes("disabled"),
    ).toBeUndefined();
    expect(wrapper.text()).toContain(reason);
  });

  it("shows the API problem when a decision is refused", async () => {
    const { wrapper } = await mountApprovals((request) =>
      request.method === "POST"
        ? problem(403, "FOUR_EYES", "Someone else must approve it.")
        : json(200, page([doc()])),
    );
    await buttonByText(wrapper, "Approve").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain(
      "Someone else must approve it.",
    );
  });
});
