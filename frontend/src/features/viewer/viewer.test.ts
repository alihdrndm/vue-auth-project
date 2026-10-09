import { describe, expect, it } from "vitest";

import { findEvidence, markLines } from "./evidence";
import { highlightXml } from "./xml";

describe("highlightXml", () => {
  it("colours names, attributes, values and text, one line at a time", () => {
    const lines = highlightXml(
      '<?xml version="1.0"?>\n<cbc:ID schemeID="x">RE-1</cbc:ID>\n',
    );
    expect(lines).toHaveLength(2);
    expect(lines[1]).toEqual([
      { kind: "bracket", text: "<" },
      { kind: "name", text: "cbc:ID" },
      { kind: "bracket", text: " " },
      { kind: "attr", text: "schemeID" },
      { kind: "bracket", text: "=" },
      { kind: "value", text: '"x"' },
      { kind: "bracket", text: ">" },
      { kind: "text", text: "RE-1" },
      { kind: "bracket", text: "</" },
      { kind: "name", text: "cbc:ID" },
      { kind: "bracket", text: ">" },
    ]);
  });

  it("keeps markup as text and splits tags that span lines", () => {
    const lines = highlightXml('<a\n  b="<script>">&lt;x&gt;</a>');
    expect(lines).toHaveLength(2);
    expect(
      lines
        .flat()
        .map((token) => token.text)
        .join(""),
    ).toBe('<a  b="<script>">&lt;x&gt;</a>');
    expect(lines[1]?.find((token) => token.kind === "value")?.text).toBe(
      '"<script>"',
    );
  });
});

describe("evidence", () => {
  it("finds the evidence exactly, or ignoring case and spacing", () => {
    const text = "Rechnung 2026-1043\nGesamtbetrag  1.547,00 €";
    expect(findEvidence(text, "2026-1043")).toEqual([9, 18]);
    expect(findEvidence(text, "gesamtbetrag 1.547,00 €")).not.toBeNull();
    expect(findEvidence(text, "nowhere")).toBeNull();
    expect(findEvidence(text, null)).toBeNull();
  });

  it("marks the range inside its lines", () => {
    const text = "Rechnung 2026-1043\nZahlbar bis 20.10.2026";
    const lines = markLines(text, findEvidence(text, "2026-1043"));
    expect(lines[0]).toEqual({
      number: 1,
      hit: true,
      segments: [
        { text: "Rechnung ", mark: false },
        { text: "2026-1043", mark: true },
      ],
    });
    expect(lines[1]?.hit).toBe(false);
  });
});
