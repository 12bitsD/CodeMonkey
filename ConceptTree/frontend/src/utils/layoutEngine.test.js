import { describe, expect, it } from "vitest";
import { calculateLayout } from "./layoutEngine";

const node = (id, name = id) => ({ id, name });

describe("calculateLayout", () => {
  it("uses left-to-right spacing for short linear learning paths", () => {
    const positions = calculateLayout(
      [node("n1"), node("n2"), node("n3"), node("n4")],
      [
        { from: "n1", to: "n2" },
        { from: "n2", to: "n3" },
        { from: "n3", to: "n4" },
      ],
      "n4",
    );

    expect(positions.n2.x).toBeGreaterThan(positions.n1.x);
    expect(positions.n3.x).toBeGreaterThan(positions.n2.x);
    expect(positions.n4.x).toBeGreaterThan(positions.n3.x);
    expect(new Set(Object.values(positions).map((pos) => pos.y)).size).toBe(1);
  });

  it("places broad multi-node plans left-to-right (Style 3) with sibling spread", () => {
    const positions = calculateLayout(
      ["n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8"].map((id) =>
        node(id),
      ),
      [
        { from: "n1", to: "n5" },
        { from: "n2", to: "n5" },
        { from: "n3", to: "n6" },
        { from: "n4", to: "n6" },
        { from: "n5", to: "n7" },
        { from: "n6", to: "n8" },
      ],
      "n8",
    );

    // Style 3: deeper nodes go RIGHT (greater X), siblings spread vertically.
    expect(positions.n5.x).toBeGreaterThan(positions.n1.x);
    expect(positions.n8.x).toBeGreaterThan(positions.n5.x);
    expect(positions.n1.x).toBe(positions.n2.x);
    expect(positions.n1.y).not.toBe(positions.n2.y);
  });

  it("snake-wraps a pure linear chain of more than 5 nodes (β1)", () => {
    const positions = calculateLayout(
      ["n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9"].map((id) =>
        node(id),
      ),
      [
        { from: "n1", to: "n2" },
        { from: "n2", to: "n3" },
        { from: "n3", to: "n4" },
        { from: "n4", to: "n5" },
        { from: "n5", to: "n6" },
        { from: "n6", to: "n7" },
        { from: "n7", to: "n8" },
        { from: "n8", to: "n9" },
      ],
      "n9",
    );

    // 9 nodes → 2 rows. perRow = ceil(9 / ceil(9/5)) = 5.
    // Row 0 (LTR): n1..n5 at increasing X, all at y=0.
    // Row 1 (RTL): n6..n9 at decreasing X, all at the same lower y.
    const distinctYs = new Set(Object.values(positions).map((p) => p.y));
    expect(distinctYs.size).toBe(2);
    expect(positions.n6.y).toBeGreaterThan(positions.n1.y);
    expect(positions.n5.x).toBeGreaterThan(positions.n1.x);
    // Wrap edge: n5 and n6 share the same X (vertical wrap transition).
    expect(positions.n5.x).toBe(positions.n6.x);
    // Row 1 RTL: n9 is leftmost (smallest X within row 1), n6 is rightmost.
    expect(positions.n6.x).toBeGreaterThan(positions.n9.x);
  });
});
