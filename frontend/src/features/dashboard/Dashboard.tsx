import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useResource } from "../../lib/resource";
import type { Summary } from "../../lib/types";
import { money } from "../../lib/money";
import { Button, ErrorNotice, Loading, PageTitle } from "../../components/ui";
import Filters from "../../components/Filters";
import Chart from "../../components/Chart";

export default function Dashboard() {
  const [params, setParams] = useSearchParams();
  const [version, setVersion] = useState(0);
  const query = "?" + params.toString();
  const state = useResource<Summary>("/analytics/summary/" + query, version);
  const trend = useResource<{
    results: { snapshot_date: string; total_amount: string }[];
  }>("/analytics/trend/" + query, version);
  if (state.loading) return <Loading />;
  if (state.error || !state.data)
    return (
      <>
        <ErrorNotice error={state.error} />
        <Button onClick={() => setVersion(version + 1)}>重新读取</Button>
      </>
    );
  const data = state.data;
  const stats = [
    ["家庭资产总额", "¥" + money(data.total_amount), "来自后端精确汇总"],
    ["资金记录", String(data.total_records), "当前筛选范围"],
    ["资产所有者", String(data.owner_count), "按账号独立统计"],
    [
      "统计范围",
      data.demo
        ? "演示数据"
        : params.get("savings_status") === ""
          ? "全部状态"
          : data.status_choices.find(
              ([code]) => code === (params.get("savings_status") || "ACTIVE"),
            )?.[1] || "筛选状态",
      "全家共享查看",
    ],
  ];
  return (
    <>
      <PageTitle
        title="家庭资金总览"
        detail="看清资产分布，稳步走向每一个家庭目标。"
        actions={
          <Button onClick={() => setVersion(version + 1)}>刷新数据</Button>
        }
      />
      {data.demo && (
        <div className="notice">当前为演示数据，登录后查看真实家庭资产。</div>
      )}
      <Filters
        params={params}
        onChange={setParams}
        owners={data.owner_choices}
        banks={data.bank_choices}
        categories={data.category_choices}
        statuses={data.status_choices}
      />
      <div className="stats">
        {stats.map(([label, value, foot]) => (
          <div className="card" key={label}>
            <div className="stat-label">{label}</div>
            <div className="stat-value">{value}</div>
            <div className="stat-foot">{foot}</div>
          </div>
        ))}
      </div>
      <section className="card" style={{ marginBottom: 24 }}>
        <h2>资金快照历史趋势</h2>
        <p className="section-note">
          每日 ACTIVE 快照，仅跟随所有者筛选；其他筛选用于实时统计。
        </p>
        <ErrorNotice error={trend.error} />
        {trend.loading ? (
          <Loading />
        ) : (
          <Chart
            title="资金快照趋势"
            type="line"
            labels={trend.data?.results.map((row) => row.snapshot_date) ?? []}
            values={trend.data?.results.map((row) => row.total_amount) ?? []}
          />
        )}
      </section>
      <div className="grid-two">
        <section className="card">
          <h2>银行分布</h2>
          <Chart
            title="银行资金分布"
            labels={data.bank_summary.map((row) => row.bank_display || "")}
            values={data.bank_summary.map((row) => row.total_amount)}
          />
        </section>
        <section className="card">
          <h2>资产类别</h2>
          <Chart
            type="doughnut"
            title="资产类别分布"
            labels={data.category_summary.map(
              (row) => row.category_display || "",
            )}
            values={data.category_summary.map((row) => row.total_amount)}
          />
        </section>
      </div>
      <section className="card">
        <h2>成员资产</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>成员</th>
                <th>记录数量</th>
                <th className="money">金额</th>
              </tr>
            </thead>
            <tbody>
              {data.owner_summary.map((row, index) => (
                <tr key={index}>
                  <td className="break">{row.first_name || "待核对所有者"}</td>
                  <td>{row.record_count}</td>
                  <td className="money">¥{money(row.total_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.owner_summary.length && (
            <div className="empty">暂无符合筛选的资产</div>
          )}
        </div>
      </section>
    </>
  );
}
