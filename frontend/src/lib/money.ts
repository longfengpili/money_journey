// 金额格式化只处理十进制字符串，不将金额转换为浮点数。
export function money(value: string | number): string {
  const raw = String(value);
  if (!/^-?\d+(\.\d+)?$/.test(raw)) return "—";
  const [whole, fraction = ""] = raw.split(".");
  return (
    whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",") +
    "." +
    fraction.padEnd(2, "0").slice(0, 2)
  );
}

// 将后端的十进制金额转为整数分汇总，避免浮点数误差。
export function sumMoney(values: string[]): string {
  const cents = values.reduce((total, value) => {
    const match = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(value);
    if (!match) throw new Error("金额格式无效");
    const amount =
      BigInt(match[2]) * 100n + BigInt((match[3] || "").padEnd(2, "0"));
    return total + (match[1] ? -amount : amount);
  }, 0n);
  const absolute = cents < 0n ? -cents : cents;
  return `${cents < 0n ? "-" : ""}${absolute / 100n}.${String(absolute % 100n).padStart(2, "0")}`;
}

// 动画金额仍以整数分计算，避免数字滚动产生浮点误差。
export function interpolateMoney(
  start: string,
  end: string,
  progress: number,
): string {
  const toCents = (value: string) => {
    const match = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(value);
    if (!match) throw new Error("金额格式无效");
    const cents =
      BigInt(match[2]) * 100n + BigInt((match[3] || "").padEnd(2, "0"));
    return match[1] ? -cents : cents;
  };
  const startCents = toCents(start);
  const endCents = toCents(end);
  const fraction = BigInt(
    Math.round(
      Math.max(0, Math.min(1, Number.isFinite(progress) ? progress : 0)) *
        1_000_000,
    ),
  );
  const cents = startCents + ((endCents - startCents) * fraction) / 1_000_000n;
  const absolute = cents < 0n ? -cents : cents;
  return `${cents < 0n ? "-" : ""}${absolute / 100n}.${String(absolute % 100n).padStart(2, "0")}`;
}
