import { useEffect, useState } from "react";
import { useSession } from "../../app/session";
import { api, jsonBody } from "../../lib/api";
import { money } from "../../lib/money";
import { downloadCsv } from "../../lib/csv";
import {
  Button,
  ErrorNotice,
  FormErrors,
  Field,
  Loading,
  PageTitle,
} from "../../components/ui";
import Chart from "../../components/Chart";

type Values = Record<string, string>;
type Result = {
  results: (Record<string, string | number | boolean> & {
    month: string;
    total: string;
  })[];
  summary: Record<string, string | number>;
  params: { basic: Values; age_ranges: Values[] } | null;
};
const initialBasic: Values = {
  parent_birth_year: "1987",
  child_birth_year: "2014",
  current_amount: "20000",
  keep_amount: "50000",
  three_year_rate: "1.60",
  annual_expense: "10000",
  annual_expense_month: "12",
  calculation_months: "360",
};
const initialAge = {
  start_age: "25",
  end_age: "65",
  monthly_income: "10000",
  monthly_expense: "5000",
};
const basicFields: [string, string, string, string?][] = [
  ["parent_birth_year", "家长出生年份", "1900"],
  ["child_birth_year", "孩子出生年份", "1900"],
  ["current_amount", "初始活期金额（元）", "0", ".01"],
  ["keep_amount", "活期保留金额（元）", "0", ".01"],
  ["three_year_rate", "三年定期年利率（%）", "0", ".01"],
  ["annual_expense", "年度支出（元）", "0", ".01"],
  ["annual_expense_month", "年度支出月份", "1"],
  ["calculation_months", "计算月数", "1"],
];
const ageFields = [
  ["start_age", "起始年龄"],
  ["end_age", "结束年龄"],
  ["monthly_income", "月收入（元）"],
  ["monthly_expense", "月支出（元）"],
];
const columns = [
  ["month", "月份"],
  ["age", "家长年龄"],
  ["child_age", "孩子年龄"],
  ["total", "资金总额"],
  ["current_deposit_before_expense", "期初活期"],
  ["regular_accumulated", "定期累计"],
  ["regular_transfer", "到期转入"],
  ["regular_deposit", "本月转定期"],
  ["monthly_income", "月收入"],
  ["monthly_expense", "月支出"],
  ["is_annual_expense_month", "年度支出月"],
  ["total_expense", "总支出"],
];

export default function Calculator() {
  const { session } = useSession();
  const [basic, setBasic] = useState<Values>(initialBasic);
  const [ranges, setRanges] = useState<Values[]>([{ ...initialAge }]);
  const [result, setResult] = useState<Result>();
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);
  const [mode, setMode] = useState("all");
  const [page, setPage] = useState(1);
  useEffect(() => {
    const controller = new AbortController();
    api<Result>("/calculator/result/", { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        if (data.results.length) {
          setResult(data);
          if (data.params) {
            setBasic(data.params.basic);
            setRanges(data.params.age_ranges);
          }
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);
  if (loading) return <Loading />;
  const rows = (result?.results ?? []).filter(
    (row) =>
      mode === "all" ||
      row.month.endsWith("-12") ||
      (mode === "half" && row.month.endsWith("-06")),
  );
  return (
    <>
      <PageTitle
        title="资金计算器"
        detail={
          session.user
            ? "以全家存续资产为起点，模拟未来的月度现金流。"
            : "从你的初始资金开始，尝试不同的收入与支出计划。"
        }
      />
      <ErrorNotice error={error} />
      <FormErrors error={error}>
        <form
          className="stack"
          onChange={() => setStale(true)}
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError(undefined);
            try {
              const data = await api<Result>(
                "/calculator/calculate/",
                jsonBody({ basic, age_ranges: ranges }),
              );
              setResult(data);
              setStale(false);
              setPage(1);
            } catch (e) {
              setError(e as Error);
            } finally {
              setBusy(false);
            }
          }}
        >
          <fieldset disabled={busy} className="stack">
            <section className="card">
              <h2>基本参数</h2>
              <div className="form-grid">
                {basicFields.map(([key, label, min, step]) =>
                  session.user && key === "current_amount" ? (
                    <div className="field" key={key}>
                      <span>初始活期金额</span>
                      <p>自动读取全家存续资产中的活期金额</p>
                    </div>
                  ) : (
                    <Field key={key} label={label}>
                      <input
                        type="number"
                        name={key}
                        required
                        min={min}
                        step={step || "1"}
                        max={
                          key.includes("birth_year")
                            ? new Date().getFullYear()
                            : key === "annual_expense_month"
                              ? 12
                              : key === "calculation_months"
                                ? 600
                                : key === "three_year_rate"
                                  ? 100
                                  : undefined
                        }
                        value={basic[key]}
                        onChange={(e) =>
                          setBasic({ ...basic, [key]: e.target.value })
                        }
                      />
                    </Field>
                  ),
                )}
              </div>
            </section>
            <section className="card">
              <h2>年龄段收支</h2>
              <p className="section-note">
                区间包含起止年龄。重叠区间沿用原计算规则，请避免无意重叠。
              </p>
              {ranges.map((range, index) => (
                <div className="age-row" key={index}>
                  {ageFields.map(([key, label]) => (
                    <Field key={key} label={label}>
                      <input
                        name={`age_ranges.${index}.${key}`}
                        aria-label={`年龄段${index + 1}${label}`}
                        type="number"
                        required
                        min="0"
                        max={key.includes("age") ? 150 : undefined}
                        step={key.includes("age") ? "1" : ".01"}
                        value={range[key]}
                        onChange={(e) =>
                          setRanges(
                            ranges.map((item, i) =>
                              i === index
                                ? { ...item, [key]: e.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                    </Field>
                  ))}
                  <Button
                    type="button"
                    disabled={ranges.length <= 1 || busy}
                    onClick={() => {
                      setRanges(ranges.filter((_, i) => i !== index));
                      setStale(true);
                    }}
                  >
                    移除此段
                  </Button>
                </div>
              ))}
              <div className="actions">
                <Button
                  type="button"
                  disabled={ranges.length >= 20 || busy}
                  onClick={() => {
                    setRanges([...ranges, { ...initialAge }]);
                    setStale(true);
                  }}
                >
                  添加年龄段
                </Button>
                <Button className="primary" type="submit" disabled={busy}>
                  {busy ? "计算中…" : "开始计算"}
                </Button>
              </div>
            </section>
          </fieldset>
        </form>
      </FormErrors>
      {result && (
        <section className="stack" style={{ marginTop: 24 }}>
          {stale && (
            <div className="notice" role="status">
              参数已修改，下方为上次成功计算的结果，请重新计算以更新。
            </div>
          )}
          <div className="stats">
            {[
              ["期末资金总额", "final_total"],
              ["累计收入", "total_income"],
              ["累计支出", "total_expense"],
              ["累计收支结余", "total_balance"],
            ].map(([label, key]) => (
              <div className="card" key={key}>
                <div className="stat-label">{label}</div>
                <div className="stat-value">¥{money(result.summary[key])}</div>
                <div className="stat-foot">
                  共 {result.summary.total_months} 个月
                </div>
              </div>
            ))}
          </div>
          <div className="card">
            <h2>资金变化趋势</h2>
            <Chart
              aurora
              title="规划资金总额"
              type="line"
              labels={result.results.map((row) => row.month)}
              values={result.results.map((row) => row.total)}
            />
          </div>
          <section className="card">
            <div
              className="actions"
              style={{ justifyContent: "space-between", marginBottom: 20 }}
            >
              <h2 style={{ margin: 0 }}>月度明细</h2>
              <div className="actions">
                <select
                  aria-label="明细月份范围"
                  style={{ width: "auto" }}
                  value={mode}
                  onChange={(e) => {
                    setMode(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="all">全部月份</option>
                  <option value="half">每年六月和十二月</option>
                  <option value="annual">每年十二月</option>
                </select>
                <Button
                  onClick={() =>
                    downloadCsv("家庭资金计算器.csv", [
                      columns.map(([, label]) => label),
                      ...rows.map((row) =>
                        columns.map(([key]) =>
                          key === "is_annual_expense_month"
                            ? row[key]
                              ? "是"
                              : "否"
                            : String(row[key] ?? ""),
                        ),
                      ),
                    ])
                  }
                >
                  导出 CSV
                </Button>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {columns.map(([key, label]) => (
                      <th className={key === "month" ? "" : "money"} key={key}>
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice((page - 1) * 60, page * 60).map((row) => (
                    <tr key={row.month}>
                      {columns.map(([key]) => (
                        <td
                          className={key === "month" ? "" : "money"}
                          key={key}
                        >
                          {key === "is_annual_expense_month"
                            ? row[key]
                              ? "是"
                              : "否"
                            : key === "month" || key.includes("age")
                              ? String(row[key] ?? "")
                              : money(String(row[key] ?? 0))}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span className="label">
                共 {rows.length} 个月 · 第 {page} 页
              </span>
              <div className="actions">
                <Button disabled={page === 1} onClick={() => setPage(page - 1)}>
                  上一页
                </Button>
                <Button
                  disabled={page * 60 >= rows.length}
                  onClick={() => setPage(page + 1)}
                >
                  下一页
                </Button>
              </div>
            </div>
          </section>
        </section>
      )}
    </>
  );
}
