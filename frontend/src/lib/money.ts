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
