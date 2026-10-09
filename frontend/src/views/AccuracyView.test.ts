import { flushPromises, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { components } from "../api/schema";
import { buttonByText, mountScreen } from "../features/approvals/screenTesting";
import { EVALS_URL } from "../features/accuracy/accuracy";
import { json, mockFetch, problem } from "../testing/http";
import AccuracyPublicView from "./AccuracyPublicView.vue";
import AccuracyView from "./AccuracyView.vue";

type AccuracyReport = components["schemas"]["AccuracyReport"];

const REPORT: AccuracyReport = {
  generated_at: "2026-10-09T19:34:10Z",
  dataset: {
    name: "zugferd-corpus-hybrid-cii",
    documents: 104,
    corpus_commit: "d891458e9822e34271a5438497bf924e89955979",
  },
  systems: [
    {
      id: "regex-baseline",
      critical_correct: { value: 0.2116, ci_low: 0.1346, ci_high: 0.2884 },
      fields: {
        invoice_number: { accuracy: 0.3365, abstention: 0.3365 },
        payee_iban: {
          accuracy: 0.9143,
          hallucination: 0.1449,
          abstention: 0.0286,
        },
      },
      cost_usd: "0",
      usd_per_doc: "0.000000",
      latency_p50_ms: 3.3,
      latency_p95_ms: 6.2,
    },
    {
      id: "llm:test-model",
      model: "test-model",
      critical_correct: { value: 0.875, ci_low: 0.81, ci_high: 0.93 },
      fields: {
        invoice_number: {
          accuracy: 0.95,
          hallucination: 0.01,
          abstention: 0.02,
        },
        payee_iban: { accuracy: 0.97 },
      },
      cost_usd: "0.21",
      usd_per_doc: "0.002019",
      latency_p50_ms: 900,
      latency_p95_ms: 2100,
    },
  ],
  parity: {
    files: 176,
    excluded: 64,
    verdict_agreement: 1,
    rule_set_agreement: 0.995,
  },
};

let wrapper: VueWrapper | null = null;

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  vi.unstubAllGlobals();
});

async function mountAccuracy(
  respond: () => Response | Promise<Response>,
  publicPage = false,
) {
  const calls = mockFetch(respond);
  const screen = publicPage
    ? await mountScreen(AccuracyPublicView, "accuracy-public", "/accuracy")
    : await mountScreen(AccuracyView, "accuracy", "/app/accuracy");
  wrapper = screen.wrapper;
  return { ...screen, calls };
}

describe("Accuracy pages", () => {
  it("show a skeleton while loading", async () => {
    await mountAccuracy(() => new Promise<Response>(() => undefined));
    expect(wrapper?.find('[aria-label="Loading the results"]').exists()).toBe(
      true,
    );
  });

  it("render the published numbers, not samples", async () => {
    const { calls } = await mountAccuracy(() => json(200, REPORT));
    expect(calls[0]?.path).toBe("/api/v1/accuracy");
    const text = wrapper?.text() ?? "";
    // Headline per system with its interval.
    expect(text).toContain("Regex baseline (no AI)");
    expect(text).toContain("21.2 %");
    expect(text).toContain("95 % confidence interval 13.5–28.8 %");
    expect(text).toContain("AI reader (test-model)");
    expect(text).toContain("87.5 %");
    // Per field: the AI reader's rates, "—" where a rate is absent, the baseline's accuracy.
    const iban = wrapper
      ?.findAll("tbody tr")
      .find((row) => row.text().startsWith("IBAN"));
    expect(iban?.findAll("td").map((cell) => cell.text())).toEqual([
      "97.0 %",
      "—",
      "—",
      "91.4 %",
    ]);
    // Parity, cost and dataset.
    expect(text).toContain("100.0 %");
    expect(text).toContain("99.5 %");
    expect(text).toContain("176 files compared, 64 excluded.");
    expect(text).toContain("$0.002");
    expect(text).toContain("$0.000");
    expect(text).toContain("104 documents");
    expect(text).toContain("d891458");
    expect(text).not.toMatch(/sample\)/i);
    expect(wrapper?.find(`a[href="${EVALS_URL}"]`).exists()).toBe(true);
  });

  it("show the empty state when nothing is published", async () => {
    await mountAccuracy(() =>
      problem(404, "NOT_AVAILABLE", "No results published yet."),
    );
    expect(wrapper?.text()).toContain("No results published yet");
    expect(wrapper?.find(`a[href="${EVALS_URL}"]`).exists()).toBe(true);
  });

  it("show the problem and retry", async () => {
    let fail = true;
    await mountAccuracy(() =>
      fail
        ? problem(500, "SERVER_ERROR", "Results are unavailable.")
        : json(200, REPORT),
    );
    expect(wrapper?.text()).toContain("Results are unavailable.");
    fail = false;
    await buttonByText(wrapper as VueWrapper, "Try again").trigger("click");
    await flushPromises();
    expect(wrapper?.text()).toContain("21.2 %");
  });

  it("public page has its own header and the same report", async () => {
    await mountAccuracy(() => json(200, REPORT), true);
    expect(wrapper?.find("main h1").text()).toBe(
      "How accurately does Eingang read invoices?",
    );
    expect(
      buttonByText(wrapper as VueWrapper, "Open the sandbox").exists(),
    ).toBe(true);
    expect(wrapper?.text()).toContain("87.5 %");
  });
});
