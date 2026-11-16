import { describe, it, expect } from "vitest";
import { hauntingScore, hauntingLabel, SCORE_MAX, SCORE_MIN } from "./hauntingScore";

describe("hauntingScore", () => {
  it("returns 0 for an empty account", () => {
    expect(hauntingScore({ totalMonthlyCost: 0, tombstoneCount: 0, securityCount: 0 })).toBe(0);
  });

  it("matches the demo report (18 tombstones, $202.15/mo, 5 security) -> 53", () => {
    expect(hauntingScore({ totalMonthlyCost: 202.15, tombstoneCount: 18, securityCount: 5 })).toBe(53);
  });

  it("caps the cost component at 60 ($600/mo and beyond)", () => {
    expect(hauntingScore({ totalMonthlyCost: 600, tombstoneCount: 0, securityCount: 0 })).toBe(60);
    expect(hauntingScore({ totalMonthlyCost: 6000, tombstoneCount: 0, securityCount: 0 })).toBe(60);
  });

  it("caps the volume component at 25 (25+ tombstones)", () => {
    expect(hauntingScore({ totalMonthlyCost: 0, tombstoneCount: 25, securityCount: 0 })).toBe(25);
    expect(hauntingScore({ totalMonthlyCost: 0, tombstoneCount: 100, securityCount: 0 })).toBe(25);
  });

  it("caps the security component at 15 (3+ security tombstones)", () => {
    expect(hauntingScore({ totalMonthlyCost: 0, tombstoneCount: 0, securityCount: 3 })).toBe(15);
    expect(hauntingScore({ totalMonthlyCost: 0, tombstoneCount: 0, securityCount: 10 })).toBe(15);
  });

  it("sums to 100 at all caps", () => {
    expect(hauntingScore({ totalMonthlyCost: 1000, tombstoneCount: 50, securityCount: 10 })).toBe(100);
  });

  it("never exceeds SCORE_MAX or falls below SCORE_MIN", () => {
    expect(hauntingScore({ totalMonthlyCost: 1e9, tombstoneCount: 1e6, securityCount: 1e6 })).toBe(SCORE_MAX);
    expect(hauntingScore({ totalMonthlyCost: -50, tombstoneCount: -10, securityCount: -5 })).toBe(SCORE_MIN);
  });

  it("is deterministic for the same input", () => {
    const input = { totalMonthlyCost: 123.45, tombstoneCount: 7, securityCount: 2 };
    expect(hauntingScore(input)).toBe(hauntingScore(input));
  });

  it("rounds to the nearest integer", () => {
    // cost 20.215 + volume 18 + security 15 = 53.215 -> 53
    expect(hauntingScore({ totalMonthlyCost: 202.15, tombstoneCount: 18, securityCount: 5 })).toBe(53);
    // cost 10.5 + volume 0 + security 0 = 10.5 -> 11 (rounds half up)
    expect(hauntingScore({ totalMonthlyCost: 105, tombstoneCount: 0, securityCount: 0 })).toBe(11);
  });
});

describe("hauntingLabel", () => {
  it("labels 0..20 as Peaceful", () => {
    expect(hauntingLabel(0)).toBe("Peaceful");
    expect(hauntingLabel(20)).toBe("Peaceful");
  });

  it("labels 21..45 as Restless", () => {
    expect(hauntingLabel(21)).toBe("Restless");
    expect(hauntingLabel(45)).toBe("Restless");
  });

  it("labels 46..70 as Haunted", () => {
    expect(hauntingLabel(46)).toBe("Haunted");
    expect(hauntingLabel(70)).toBe("Haunted");
  });

  it("labels 71..100 as Cursed", () => {
    expect(hauntingLabel(71)).toBe("Cursed");
    expect(hauntingLabel(100)).toBe("Cursed");
  });

  it("labels the demo score (53) as Haunted", () => {
    expect(hauntingLabel(53)).toBe("Haunted");
  });
});
