import { describe, expect, it } from "vitest";

import {
  costPerInvoice,
  fieldKeys,
  percent,
  primarySystem,
  type SystemResult,
  systemName,
} from "./accuracy";

function system(
  id: string,
  overrides: Partial<SystemResult> = {},
): SystemResult {
  return {
    id,
    critical_correct: { value: 0.5, ci_low: 0.4, ci_high: 0.6 },
    fields: {},
    cost_usd: "0",
    usd_per_doc: "0",
    latency_p50_ms: 1,
    latency_p95_ms: 2,
    ...overrides,
  };
}

describe("accuracy helpers", () => {
  it("formats rates and leaves absent ones as a dash", () => {
    expect(percent(0.2116)).toBe("21.2 %");
    expect(percent(1)).toBe("100.0 %");
    expect(percent(undefined)).toBe("—");
  });

  it("details the AI system and falls back to the baseline", () => {
    const baseline = system("regex-baseline");
    const llm = system("llm:m", { model: "m" });
    expect(primarySystem([baseline, llm])?.id).toBe("llm:m");
    expect(primarySystem([baseline])?.id).toBe("regex-baseline");
    expect(systemName(llm)).toBe("AI reader (m)");
    expect(systemName(baseline)).toBe("Regex baseline (no AI)");
  });

  it("orders known fields first and keeps unknown ones", () => {
    const one = system("a", {
      fields: { zeta: {}, gross_total: {}, invoice_number: {} },
    });
    expect(fieldKeys([one])).toEqual(["invoice_number", "gross_total", "zeta"]);
  });

  it("writes the cost per invoice", () => {
    expect(costPerInvoice(system("a", { usd_per_doc: "0.002019" }))).toBe(
      "$0.002",
    );
    expect(costPerInvoice(system("a", { usd_per_doc: "0.000000" }))).toBe(
      "$0.000",
    );
    expect(costPerInvoice(system("a", { usd_per_doc: "0.00042" }))).toBe(
      "$0.00042",
    );
  });
});
