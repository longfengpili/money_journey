import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useResource } from "../../lib/resource";
import type { Summary } from "../../lib/types";
import { money, sumMoney } from "../../lib/money";
import { Button, ErrorNotice, Loading, PageTitle } from "../../components/ui";
import Filters from "../../components/Filters";
import Chart from "../../components/Chart";
import StackedChart from "../../components/StackedChart";

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
  const trendRows = trend.data?.results ?? [];
  const maturityRows = data.maturity_summary ?? [];
  const maturityTotal = sumMoney(maturityRows.map((row) => row.total_amount));
  const memberCategories = data.category_summary.map((category) => ({
    label: category.category_display || category.category || "其他",
    values: data.owner_summary.map(
      (owner) =>
        data.owner_category_summary?.find(
          (row) =>
            row.user_id === owner.user_id &&
            row.owner === owner.owner &&
            row.category === category.category,
        )?.total_amount ?? "0",
    ),
  }));
  const activeScope = data.demo
    ? "演示数据"
    : params.get("savings_status") === ""
      ? "全部状态"
      : data.status_choices.find(
          ([code]) => code === (params.get("savings_status") || "ACTIVE"),
        )?.[1] || "筛选状态";
  return (
    <div className="dashboard">
      <PageTitle
        title="家庭资金总览"
        detail="看清每一份资产的去向，规划家庭的下一步。"
        actions={
          <Button onClick={() => setVersion(version + 1)}>刷新数据</Button>
        }
      />
      {data.demo && (
        <section className="dashboard-login-prompt" aria-label="登录提示">
          <div>
            <h2>当前展示演示数据</h2>
            <p>登录后查看真实的家庭资产、成员和资金趋势。</p>
          </div>
          <Link to="/login" className="button primary">
            登录查看真实资产
          </Link>
        </section>
      )}
      <div className="dashboard-hero">
        <div className="dashboard-hero-main">
          <div className="dashboard-eyebrow">
            FAMILY PORTFOLIO · {activeScope}
          </div>
          <div className="dashboard-hero-label">家庭资产总额</div>
          <div className="dashboard-hero-value">
            ¥{money(data.total_amount)}
          </div>
          <div className="dashboard-hero-foot">根据当前筛选条件精确汇总</div>
        </div>
        <div className="dashboard-hero-side">
          <div>
            <span>资金记录</span>
            <strong>{data.total_records}</strong>
            <small>笔</small>
          </div>
          <div>
            <span>家庭成员</span>
            <strong>{data.owner_count}</strong>
            <small>位</small>
          </div>
          <div>
            <span>未来半年到期</span>
            <strong>¥{money(maturityTotal)}</strong>
          </div>
        </div>
      </div>
      <details className="dashboard-filter-panel">
        <summary>筛选资产视图</summary>
        <Filters
          params={params}
          onChange={setParams}
          owners={data.owner_choices}
          banks={data.bank_choices}
          categories={data.category_choices}
          statuses={data.status_choices}
        />
      </details>
      <div className="dashboard-section-heading">
        <div>
          <span className="dashboard-kicker">PORTFOLIO INSIGHTS</span>
          <h2>资产透视</h2>
        </div>
        <span>从银行、类别与成员三个角度查看</span>
      </div>
      <div className="dashboard-charts">
        <section className="card dashboard-chart-card">
          <div className="dashboard-chart-heading">
            <h3>银行分布</h3>
            <span>按金额排序</span>
          </div>
          <Chart
            aurora
            title="银行资金分布"
            type="horizontalBar"
            labels={data.bank_summary.map((row) => row.bank_display || "")}
            values={data.bank_summary.map((row) => row.total_amount)}
          />
        </section>
        <section className="card dashboard-chart-card">
          <div className="dashboard-chart-heading">
            <h3>资产类别</h3>
            <span>资金结构</span>
          </div>
          <Chart
            aurora
            type="doughnut"
            title="资产类别分布"
            labels={data.category_summary.map(
              (row) => row.category_display || "",
            )}
            values={data.category_summary.map((row) => row.total_amount)}
          />
        </section>
        <section className="card dashboard-chart-card">
          <div className="dashboard-chart-heading">
            <h3>成员资产结构</h3>
            <span>按类别分层</span>
          </div>
          <StackedChart
            aurora
            labels={data.owner_summary.map(
              (row) => row.first_name || "待核对所有者",
            )}
            series={memberCategories}
          />
        </section>
      </div>
      <section className="card dashboard-maturity">
        <div className="dashboard-maturity-title">
          <div>
            <span className="dashboard-kicker">UPCOMING CASH FLOW</span>
            <h2>未来半年到期计划</h2>
            <p>仅统计当前筛选范围内、存续中且已填写到期日的资产。</p>
          </div>
          <span className="dashboard-maturity-badge">未来 6 个月</span>
        </div>
        <div className="dashboard-maturity-content">
          <div className="dashboard-maturity-chart">
            <Chart
              aurora
              title="未来半年到期金额"
              labels={maturityRows.map((row) => row.month.slice(5) + "月")}
              values={maturityRows.map((row) => row.total_amount)}
            />
          </div>
          <div className="dashboard-maturity-table table-wrap">
            <table aria-label="未来半年到期明细">
              <thead>
                <tr>
                  <th>月份</th>
                  <th>笔数</th>
                  <th className="money">到期金额</th>
                </tr>
              </thead>
              <tbody>
                {maturityRows.map((row) => (
                  <tr key={row.month}>
                    <td>{row.month}</td>
                    <td>{row.record_count}</td>
                    <td className="money">¥{money(row.total_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!maturityRows.length && (
              <div className="empty">暂无到期计划数据</div>
            )}
          </div>
        </div>
      </section>
      <ErrorNotice error={trend.error} />
      {!trend.loading && trendRows.length > 0 && (
        <section className="card dashboard-trend">
          <div className="dashboard-chart-heading">
            <h3>资金快照历史趋势</h3>
            <span>每日 ACTIVE 快照</span>
          </div>
          <p className="section-note">
            仅跟随所有者筛选；其他筛选用于实时统计。
          </p>
          <Chart
            aurora
            title="资金快照趋势"
            type="line"
            labels={trendRows.map((row) => row.snapshot_date)}
            values={trendRows.map((row) => row.total_amount)}
          />
        </section>
      )}
      <section className="card">
        <h2>成员明细</h2>
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
    </div>
  );
}
