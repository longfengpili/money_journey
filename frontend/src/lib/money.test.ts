import { describe, it, expect } from "vitest";
import { money } from "./money";

describe("金额显示不经过浮点数", () => {
  it("保留最大汇总金额的分位", () => {
    expect(money("999999999999999999.99")).toBe("999,999,999,999,999,999.99");
  });
  it("支持零、负数和单个小数位", () => {
    expect(money("0")).toBe("0.00");
    expect(money("-1234.5")).toBe("-1,234.50");
  });
});
