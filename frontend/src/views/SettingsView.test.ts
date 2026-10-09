import { flushPromises, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "../api/schema";
import { useToast } from "../components/ui/useToast";
import { buttonByText, mountScreen } from "../features/approvals/screenTesting";
import { useSessionStore } from "../stores/session";
import {
  json,
  mockFetch,
  problem,
  type RecordedRequest,
} from "../testing/http";
import SettingsView from "./SettingsView.vue";

type Organization = components["schemas"]["Organization"];
type Role = components["schemas"]["RoleEnum"];

const ORG: Organization = {
  id: "00000000-0000-0000-0000-000000000002",
  name: "Holzwerk Brandt GmbH",
  slug: "holzwerk-brandt",
  kind: "standard",
  vat_id: "DE143826055",
  four_eyes: true,
  duplicate_window_days: 30,
  reminder_after_days: 3,
};

const STATS = {
  by_status: {
    received: 0,
    processing: 0,
    needs_review: 0,
    awaiting_approval: 0,
    approved: 0,
    rejected: 0,
    exported: 0,
    failed: 0,
  },
  blocked: 0,
  overdue: 0,
  awaiting_my_approval: 0,
  llm: {
    lifetime_spent_usd: "0.42",
    lifetime_budget_usd: "2.00",
    month_spent_usd: "0.95",
    month_budget_usd: "1.00",
  },
};

const MEMBERS = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: "00000000-0000-0000-0000-000000000001",
      email: "anna@example.com",
      name: "Anna",
      role: "admin",
      is_active: true,
    },
    {
      id: "m-2",
      email: "jonas@example.com",
      name: "Jonas Brandt",
      role: "approver",
      is_active: true,
    },
  ],
};

let wrapper: VueWrapper | null = null;

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  useToast().dismiss();
  vi.unstubAllGlobals();
});

type Handler = (request: RecordedRequest) => Response | undefined;

async function mountSettings(
  options: { role?: Role; org?: Organization; extra?: Handler } = {},
) {
  const org = options.org ?? ORG;
  const calls = mockFetch((request) => {
    const answer = options.extra?.(request);
    if (answer) return answer;
    if (request.path === "/api/v1/organization") return json(200, org);
    if (request.path === "/api/v1/stats") return json(200, STATS);
    if (request.path === "/api/v1/members") return json(200, MEMBERS);
    return problem(404, "NOT_FOUND");
  });
  const screen = await mountScreen(SettingsView, "settings", "/app/settings", {
    role: options.role ?? "admin",
    organization: { kind: org.kind, four_eyes: org.four_eyes },
  });
  wrapper = screen.wrapper;
  return { ...screen, calls };
}

function input(view: VueWrapper, label: string) {
  const found = view
    .findAll("label")
    .find((item) => item.text().trim() === label);
  const id = found?.attributes("for");
  if (!id) throw new Error(`No field "${label}"`);
  return view.get(`#${CSS.escape(id)}`);
}

describe("SettingsView states", () => {
  it("shows a skeleton while loading", async () => {
    mockFetch(() => new Promise<Response>(() => undefined));
    const screen = await mountScreen(
      SettingsView,
      "settings",
      "/app/settings",
      {
        role: "admin",
      },
    );
    wrapper = screen.wrapper;
    expect(wrapper.find('[aria-label="Loading the settings"]').exists()).toBe(
      true,
    );
  });

  it("shows the problem and retries", async () => {
    let fail = true;
    await mountSettings({
      extra: (request) =>
        request.path === "/api/v1/organization" && fail
          ? problem(500, "SERVER_ERROR", "Settings are unavailable.")
          : undefined,
    });
    expect(wrapper?.text()).toContain("Settings are unavailable.");
    fail = false;
    await buttonByText(wrapper as VueWrapper, "Try again").trigger("click");
    await flushPromises();
    expect(
      (input(wrapper as VueWrapper, "Name").element as HTMLInputElement).value,
    ).toBe("Holzwerk Brandt GmbH");
  });

  it("shows the AI budget meters from /stats", async () => {
    await mountSettings();
    const meters = wrapper?.findAll('[role="meter"]') ?? [];
    expect(meters).toHaveLength(2);
    expect(meters[0]?.attributes("aria-valuenow")).toBe("21");
    expect(wrapper?.text()).toContain("$0.42 of $2.00");
    expect(wrapper?.text()).toContain("$0.95 of $1.00");
    expect(wrapper?.text()).not.toContain("Sample");
  });
});

describe("SettingsView organisation form", () => {
  it("enables Save once something changed and sends only the change", async () => {
    const { calls } = await mountSettings({
      extra: (request) =>
        request.method === "PATCH"
          ? json(200, { ...ORG, ...JSON.parse(request.body) })
          : undefined,
    });
    const view = wrapper as VueWrapper;
    const save = () => buttonByText(view, "Save changes");
    expect(save().attributes("disabled")).toBeDefined();

    await input(view, "Reminder after (days)").setValue("5");
    await view.get('[role="switch"]').trigger("click");
    expect(save().attributes("disabled")).toBeUndefined();
    expect(view.text()).toContain("You have unsaved changes.");

    await save().trigger("click");
    await flushPromises();

    const patch = calls.find((call) => call.method === "PATCH");
    expect(patch?.path).toBe("/api/v1/organization");
    expect(JSON.parse(patch?.body ?? "{}")).toEqual({
      four_eyes: false,
      reminder_after_days: 5,
    });
    expect(document.body.textContent).toContain("Settings saved.");
    expect(save().attributes("disabled")).toBeDefined();
    expect(useSessionStore().me?.organization.four_eyes).toBe(false);
  });

  it("checks the windows before saving", async () => {
    const { calls } = await mountSettings();
    const view = wrapper as VueWrapper;
    await input(view, "Duplicate window (days)").setValue("0");
    await buttonByText(view, "Save changes").trigger("click");
    await flushPromises();
    expect(view.text()).toContain("Enter a whole number from 1 to 365.");
    expect(calls.some((call) => call.method === "PATCH")).toBe(false);
  });

  it("in a sandbox lets only the name change", async () => {
    await mountSettings({
      org: { ...ORG, kind: "sandbox", four_eyes: false },
    });
    const view = wrapper as VueWrapper;
    expect(input(view, "Name").attributes("disabled")).toBeUndefined();
    expect(input(view, "VAT ID").attributes("disabled")).toBeDefined();
    expect(
      input(view, "Duplicate window (days)").attributes("disabled"),
    ).toBeDefined();
    expect(view.get('[role="switch"]').attributes("disabled")).toBeDefined();
    expect(view.text()).toContain("Not available in the sandbox.");
  });

  it("in a sandbox doesn't load members and disables inviting", async () => {
    const { calls } = await mountSettings({
      org: { ...ORG, kind: "sandbox", four_eyes: false },
    });
    const view = wrapper as VueWrapper;
    expect(calls.some((call) => call.path === "/api/v1/members")).toBe(false);
    expect(
      buttonByText(view, "Invite member").attributes("disabled"),
    ).toBeDefined();
  });

  it("is read-only for everyone but admins", async () => {
    const { calls } = await mountSettings({ role: "accountant" });
    const view = wrapper as VueWrapper;
    expect(input(view, "Name").attributes("disabled")).toBeDefined();
    expect(view.text()).toContain("Only admins can change settings.");
    expect(view.text()).toContain("Only admins can manage members.");
    expect(calls.some((call) => call.path === "/api/v1/members")).toBe(false);
  });
});

describe("SettingsView members", () => {
  it("lists members and marks the viewer", async () => {
    await mountSettings();
    const rows = wrapper?.findAll("tbody tr") ?? [];
    expect(rows).toHaveLength(2);
    expect(rows[0]?.text()).toContain("You");
    expect(rows[0]?.find("select").attributes("disabled")).toBeDefined();
    expect(rows[1]?.text()).toContain("jonas@example.com");
  });

  it("shows the one-time password once after inviting someone", async () => {
    const { calls } = await mountSettings({
      extra: (request) =>
        request.method === "POST" && request.path === "/api/v1/members"
          ? json(201, {
              id: "m-3",
              email: "lena@example.com",
              name: "Lena Vogt",
              role: "accountant",
              is_active: true,
              one_time_password: "kiwi-rain-4417",
            })
          : undefined,
    });
    const view = wrapper as VueWrapper;

    const dialogButton = (label: string) =>
      view
        .findAll("dialog button")
        .find((item) => item.text().trim() === label);
    await buttonByText(view, "Invite member").trigger("click");
    await flushPromises();
    await dialogButton("Invite member")?.trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain(
      "Choose a role before you invite someone.",
    );

    const dialog = view.get("dialog");
    await dialog.get('input[type="email"]').setValue("lena@example.com");
    await dialog.findAll("input")[1]?.setValue("Lena Vogt");
    await dialog.get("select").setValue("accountant");
    await dialogButton("Invite member")?.trigger("click");
    await flushPromises();

    const post = calls.find((call) => call.method === "POST");
    expect(JSON.parse(post?.body ?? "{}")).toEqual({
      email: "lena@example.com",
      name: "Lena Vogt",
      role: "accountant",
    });
    expect(view.find("code").text()).toBe("kiwi-rain-4417");
    expect(document.body.textContent).toContain("shown only once");

    await buttonByText(view, "Done").trigger("click");
    await flushPromises();
    expect(document.body.textContent).not.toContain("kiwi-rain-4417");

    await buttonByText(view, "Invite member").trigger("click");
    await flushPromises();
    expect(document.body.textContent).not.toContain("kiwi-rain-4417");
  });
});
