import { describe, it, expect } from "vitest";
import {
  interpolateMoney,
  money,
  sumMoney,
} from "../../../frontend/src/lib/money";

describe("金额显示不经过浮点数", () => {
  it("保留最大汇总金额的分位", () => {
    expect(money("999999999999999999.99")).toBe("999,999,999,999,999,999.99");
  });
  it("支持零、负数和单个小数位", () => {
    expect(money("0")).toBe("0.00");
    expect(money("-1234.5")).toBe("-1,234.50");
  });
  it("精确汇总多个到期金额", () => {
    expect(sumMoney(["0.10", "0.20", "999999999999999999.99"])).toBe(
      "1000000000000000000.29",
    );
  });
  it("动画金额按分插值，起终点保持精确", () => {
    expect(interpolateMoney("1280000.00", "680000.00", 0)).toBe("1280000.00");
    expect(interpolateMoney("1280000.00", "680000.00", 0.5)).toBe("980000.00");
    expect(interpolateMoney("1280000.00", "680000.00", 1)).toBe("680000.00");
    expect(interpolateMoney("999999999999999999.99", "0.01", 1)).toBe("0.01");
  });
});
