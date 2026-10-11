import { describe, expect, it } from "vitest";
import { dateTime, publicationLabel } from "./utils";

describe("Honest timestamp labels", () => {
  it("never turns missing publication into a discovery date", () => {
    expect(publicationLabel(undefined)).toBe("Publication unknown");
  });
  it("retains date-only precision instead of displaying a fabricated time", () => {
    expect(
      publicationLabel({
        raw: "2026-10-11",
        start: "2026-10-10T22:00:00Z",
        end: "2026-10-11T22:00:00Z",
        precision: "date",
        provenance: "source",
        timezone: "Europe/Berlin",
      }),
    ).toBe("Published 2026-10-11 · date only");
  });
  it("handles invalid dates without showing NaN", () =>
    expect(dateTime("bad")).toBe("Unknown"));
  it("uses the selected display timezone across a UTC day boundary", () => {
    expect(dateTime("2026-10-10T23:00:00Z", "Europe/Berlin")).toContain(
      "11 Oct",
    );
  });
});
