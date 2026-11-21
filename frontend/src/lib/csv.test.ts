import { expect, it } from "vitest";
import { makeCsv } from "./csv";

it("CSV 保留金额文本并正确转义逗号与引号", () => {
  expect(
    makeCsv([
      ["月份", "金额"],
      ["2026-11", "9999999999999.99"],
      ['a,"b', "0.00"],
    ]),
  ).toBe(
    '\ufeff"月份","金额"\r\n"2026-11","9999999999999.99"\r\n"a,""b","0.00"',
  );
});
