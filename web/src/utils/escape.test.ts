import { describe, it, expect } from "vitest";
import { escapeHtml, displayName } from "./escape";

describe("escapeHtml", () => {
  it("escapes &", () => expect(escapeHtml("a&b")).toBe("a&amp;b"));
  it("escapes <", () => expect(escapeHtml("<script>")).toBe("&lt;script&gt;"));
  it("escapes >", () => expect(escapeHtml("a>b")).toBe("a&gt;b"));
  it("escapes quotes", () => expect(escapeHtml('"x"')).toBe("&quot;x&quot;"));
  it("escapes single quote", () => expect(escapeHtml("it's")).toBe("it&#39;s"));
  it("passes plain text unchanged", () => expect(escapeHtml("hello world")).toBe("hello world"));
});

describe("displayName", () => {
  it("returns resource_name when present", () => {
    expect(displayName("my-volume", "vol-001")).toBe("my-volume");
  });
  it("falls back to id when name is null", () => {
    expect(displayName(null, "vol-001")).toBe("vol-001");
  });
  it("falls back to id when name is empty string", () => {
    expect(displayName("", "vol-001")).toBe("vol-001");
  });
  it("falls back to id when name is whitespace", () => {
    expect(displayName("   ", "vol-001")).toBe("vol-001");
  });
});
