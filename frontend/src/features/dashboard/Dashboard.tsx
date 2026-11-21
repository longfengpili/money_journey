import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useResource } from "../../lib/resource";
import type { Summary } from "../../lib/types";
import { money, sumMoney } from "../../lib/money";
import { Button, ErrorNotice, Loading, PageTitle } from "../../components/ui";
import Filters from "../../components/Filters";
import Chart from "../../components/Chart";
import StackedChart from "../../components/StackedChart";

const orbitColors = ["#6966e8", "#2ccbbb", "#ffad6f", "#7ab6ff", "#b79eea"];

function percentages(amounts: number[]): number[] {
  const total = amounts.reduce((sum, amount) => sum + amount, 0);
  if (!total) return amounts.map(() => 0);
  const exact = amounts.map((amount) => (amount / total) * 100);
  const result = exact.map(Math.floor);
  const remainder = 100 - result.reduce((sum, value) => sum + value, 0);
  exact
    .map((value, index) => ({ index, fraction: value - result[index] }))
    .sort((left, right) => right.fraction - left.fraction)
    .slice(0, remainder)
    .forEach(({ index }) => result[index]++);
  return result;
}

function flyCoin(
  source: HTMLElement,
  dashboard: HTMLDivElement | null,
  label: string,
  percent: number,
  onComplete: () => void,
) {
  const charts = dashboard?.querySelector<HTMLElement>(".dashboard-charts");
  if (!charts) {
    onComplete();
    return () => {};
  }
  const start = source.getBoundingClientRect();
  const centerX = window.innerWidth / 2;
  const centerY = window.innerHeight / 2;
  const offsetX = centerX - start.left - start.width / 2;
  const offsetY = centerY - start.top - start.height / 2;
  const animations = new Set<Animation>();
  const rays: HTMLElement[] = [];
  let stopped = false;
  const coin = document.createElement("span");
  coin.className = "dashboard-filter-coin";
  coin.setAttribute("aria-hidden", "true");
  const coinLabel = document.createElement("span");
  coinLabel.className = "dashboard-filter-coin-label";
  coinLabel.textContent = label;
  const coinPercent = document.createElement("strong");
  coinPercent.className = "dashboard-filter-coin-percent";
  coinPercent.textContent = `${percent}%`;
  coin.append(coinLabel, coinPercent);
  coin.style.left = `${start.left + start.width / 2 - 22}px`;
  coin.style.top = `${start.top + start.height / 2 - 22}px`;
  document.body.append(coin);
  const play = (
    element: HTMLElement,
    frames: Keyframe[],
    duration: number,
    delay = 0,
  ) => {
    const animation = element.animate(frames, {
      duration,
      delay,
      easing: "ease-in-out",
      fill: "forwards",
    });
    animations.add(animation);
    return animation.finished;
  };
  const cleanup = () => {
    if (stopped) return;
    stopped = true;
    animations.forEach((animation) => animation.cancel());
    coin.remove();
    rays.forEach((ray) => ray.remove());
  };
  void (async () => {
    try {
      await play(
        coin,
        [
          { transform: "translate(0, 0) scale(.7)", opacity: 0.6 },
          {
            transform: `translate(${offsetX}px, ${offsetY}px) scale(1)`,
            opacity: 1,
          },
        ],
        430,
      );
      charts.scrollIntoView({ behavior: "smooth", block: "center" });
      await play(
        coin,
        [
          {
            transform: `translate(${offsetX}px, ${offsetY}px) scale(1) rotate(0)`,
          },
          {
            transform: `translate(${offsetX}px, ${offsetY}px) scale(2.5) rotate(720deg)`,
          },
        ],
        520,
      );
      const cards = Array.from(
        charts.querySelectorAll<HTMLElement>(".dashboard-chart-card"),
      );
      const area = charts.getBoundingClientRect();
      const burst = Array.from(
        { length: 15 + Math.floor(Math.random() * 8) },
        () => {
          const ray = document.createElement("span");
          ray.className = "dashboard-gold-ray";
          ray.setAttribute("aria-hidden", "true");
          ray.style.left = `${centerX}px`;
          ray.style.top = `${centerY}px`;
          ray.style.width = `${5 + Math.random() * 3}px`;
          ray.style.height = `${38 + Math.random() * 58}px`;
          document.body.append(ray);
          rays.push(ray);
          const endX = area.left + Math.random() * area.width;
          const endY = area.top + Math.random() * Math.min(area.height, 650);
          const angle = -70 + Math.random() * 140;
          const bend = (Math.random() - 0.5) * 100;
          return play(
            ray,
            [
              {
                transform: `translate(0, 0) rotate(${angle}deg) scale(.3)`,
                opacity: 0,
              },
              {
                transform: `translate(0, 0) rotate(${angle}deg) scale(1)`,
                opacity: 1,
                offset: 0.18,
              },
              {
                transform: `translate(${(endX - centerX) * 0.6 + bend}px, ${(endY - centerY) * 0.55}px) rotate(${angle + 80}deg) scale(.8)`,
                opacity: 1,
                offset: 0.65,
              },
              {
                transform: `translate(${endX - centerX}px, ${endY - centerY}px) rotate(${angle + 140}deg) scale(.15)`,
                opacity: 0,
              },
            ],
            760 + Math.random() * 340,
            Math.random() * 120,
          );
        },
      );
      await Promise.all([
        play(
          coin,
          [
            {
              transform: `translate(${offsetX}px, ${offsetY}px) scale(2.5)`,
              opacity: 1,
            },
            {
              transform: `translate(${offsetX}px, ${offsetY}px) scale(3.3)`,
              opacity: 0,
            },
          ],
          220,
        ),
        ...burst,
      ]);
      cards.forEach((card) => {
        card.classList.add("is-energized");
        card.addEventListener(
          "animationend",
          () => card.classList.remove("is-energized"),
          { once: true },
        );
      });
      onComplete();
    } catch {
      // 连续点击或离开页面时取消当前动效。
    } finally {
      cleanup();
    }
  })();
  return cleanup;
}

export default function Dashboard() {
  const [params, setParams] = useSearchParams();
  const [version, setVersion] = useState(0);
  const [transitioning, setTransitioning] = useState(false);
  const [animationDone, setAnimationDone] = useState(false);
  const dashboardRef = useRef<HTMLDivElement>(null);
  const coinCleanupRef = useRef<(() => void) | null>(null);
  const heldDataRef = useRef<Summary | null>(null);
  const returnTopTimerRef = useRef<number | null>(null);
  useEffect(
    () => () => {
      coinCleanupRef.current?.();
      if (returnTopTimerRef.current !== null)
        window.clearTimeout(returnTopTimerRef.current);
    },
    [],
  );
  const filters = new URLSearchParams(params);
  if (!filters.has("savings_status")) filters.set("savings_status", "");
  const query = "?" + filters.toString();
  const compassParams = new URLSearchParams(filters);
  compassParams.delete("category");
  const compassQuery = "?" + compassParams.toString();
  const state = useResource<Summary>(
    "/analytics/summary/" + query,
    version,
    true,
  );
  const compass = useResource<Summary>(
    "/analytics/summary/" + compassQuery,
    version,
    true,
  );
  const trend = useResource<{
    results: { snapshot_date: string; total_amount: string }[];
  }>("/analytics/trend/" + query, version, true);
  useEffect(() => {
    if (!transitioning || !animationDone || state.loading) return;
    setTransitioning(false);
    setAnimationDone(false);
    heldDataRef.current = null;
    if (state.error) return;
    returnTopTimerRef.current = window.setTimeout(() => {
      window.scrollTo({ top: 0, behavior: "smooth" });
      returnTopTimerRef.current = null;
    }, 500);
  }, [transitioning, animationDone, state.loading, state.error]);
  useEffect(() => {
    const sections =
      dashboardRef.current?.querySelectorAll(".dashboard-motion");
    if (!sections) return;
    if (!("IntersectionObserver" in window)) {
      sections.forEach((section) => section.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [state.data, compass.data, trend.data]);
  if ((state.loading && !state.data) || (compass.loading && !compass.data))
    return <Loading />;
  if (state.error || compass.error || !state.data || !compass.data)
    return (
      <>
        <ErrorNotice error={state.error || compass.error} />
        <Button onClick={() => setVersion(version + 1)}>重新读取</Button>
      </>
    );
  const data =
    transitioning && heldDataRef.current ? heldDataRef.current : state.data;
  const compassData = compass.data;
  const selectedCategory = filters.get("category");
  const trendRows = trend.data?.results ?? [];
  const maturityRows = data.maturity_summary ?? [];
  const maturityTotal = sumMoney(maturityRows.map((row) => row.total_amount));
  const maturityPeak = Math.max(
    0,
    ...maturityRows.map((row) => Number(row.total_amount)),
  );
  const rankedCategories = [...compassData.category_summary]
    .filter((row) => Number(row.total_amount) > 0)
    .sort(
      (left, right) => Number(right.total_amount) - Number(left.total_amount),
    );
  const focusedCategory = rankedCategories.find(
    (row) => row.category === selectedCategory,
  );
  const orbitTotal = rankedCategories.reduce(
    (total, row) => total + Number(row.total_amount),
    0,
  );
  const orbitAmounts = rankedCategories.map((row) => Number(row.total_amount));
  const orbitPercentages = percentages(orbitAmounts);
  let orbitPosition = 0;
  const orbitGradient = orbitTotal
    ? `conic-gradient(from -90deg, ${orbitAmounts
        .map((amount, index) => {
          const start = orbitPosition;
          orbitPosition += (amount / orbitTotal) * 100;
          const color =
            focusedCategory &&
            rankedCategories[index]?.category !== selectedCategory
              ? "#dbe3f2"
              : orbitColors[index % orbitColors.length];
          return `${color} ${start}% ${orbitPosition}%`;
        })
        .join(", ")})`
    : "conic-gradient(from -90deg, #d8e2f5 0% 100%)";
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
    : filters.get("savings_status") === ""
      ? "全部状态"
      : data.status_choices.find(
          ([code]) => code === filters.get("savings_status"),
        )?.[1] || "筛选状态";
  return (
    <div
      className={`dashboard${state.loading || transitioning ? " dashboard-filtering" : ""}`}
      ref={dashboardRef}
    >
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
      <div className="dashboard-hero dashboard-cockpit">
        <div className="dashboard-hero-main">
          <div className="dashboard-eyebrow">
            FAMILY PORTFOLIO · {activeScope}
          </div>
          <div className="dashboard-hero-label">家庭资产总额</div>
          <div className="dashboard-hero-value">
            ¥{money(data.total_amount)}
          </div>
          <div className="dashboard-hero-foot">根据当前筛选条件精确汇总</div>
          <div className="dashboard-cockpit-signal">
            <span className="dashboard-cockpit-dot" aria-hidden="true" />
            {focusedCategory
              ? "罗盘保留全部类别 · 下方已筛选"
              : "点击类别聚焦罗盘并筛选下方视图"}
          </div>
        </div>
        <div className="dashboard-orbit" aria-label="资产类别分布">
          <div className="dashboard-orbit-field" aria-hidden="true">
            <span className="dashboard-orbit-track dashboard-orbit-track-outer" />
            <span className="dashboard-orbit-track dashboard-orbit-track-inner" />
            <span className="dashboard-orbit-flow" />
            <span className="dashboard-orbit-spark" />
            <span
              className="dashboard-orbit-progress"
              style={{ background: orbitGradient }}
            />
          </div>
          <div className="dashboard-orbit-core">
            <span>{focusedCategory ? "当前聚焦" : "资产主力"}</span>
            <strong>
              {orbitTotal
                ? `${orbitPercentages[focusedCategory ? rankedCategories.indexOf(focusedCategory) : 0]}%`
                : "—"}
            </strong>
            <small>
              {(focusedCategory || rankedCategories[0])?.category_display ||
                "暂无资产"}
            </small>
          </div>
          <div className="dashboard-orbit-nodes">
            {rankedCategories.map((row, index) => (
              <button
                key={row.category || index}
                type="button"
                className={`dashboard-orbit-node${focusedCategory ? (selectedCategory === row.category ? " is-selected" : " is-muted") : ""}`}
                onClick={(event) => {
                  coinCleanupRef.current?.();
                  if (returnTopTimerRef.current !== null)
                    window.clearTimeout(returnTopTimerRef.current);
                  if (
                    !window.matchMedia("(prefers-reduced-motion: reduce)")
                      .matches
                  ) {
                    heldDataRef.current = data;
                    setTransitioning(true);
                    setAnimationDone(false);
                    coinCleanupRef.current = flyCoin(
                      event.currentTarget,
                      dashboardRef.current,
                      row.category_display || row.category || "资产",
                      orbitPercentages[index],
                      () => setAnimationDone(true),
                    );
                  }
                  const next = new URLSearchParams(filters);
                  if (selectedCategory === row.category)
                    next.delete("category");
                  else next.set("category", row.category || "");
                  next.delete("page");
                  setParams(next);
                }}
                aria-label={`聚焦${row.category_display || row.category}，占比${orbitPercentages[index]}%`}
                aria-pressed={selectedCategory === row.category}
              >
                <span
                  className="dashboard-orbit-node-icon"
                  style={{ color: orbitColors[index % orbitColors.length] }}
                  aria-hidden="true"
                >
                  ¥
                </span>
                <span className="dashboard-orbit-node-text">
                  <span>{row.category_display || row.category}</span>
                  <strong>{orbitPercentages[index]}%</strong>
                </span>
              </button>
            ))}
          </div>
        </div>
        <div className="dashboard-hero-side">
          <div>
            <span className="dashboard-metric-icon" aria-hidden="true">
              ▤
            </span>
            <span>资金记录</span>
            <strong>{data.total_records}</strong>
            <small>笔</small>
          </div>
          <div>
            <span className="dashboard-metric-icon" aria-hidden="true">
              ◉
            </span>
            <span>家庭成员</span>
            <strong>{data.owner_count}</strong>
            <small>位</small>
          </div>
          <div>
            <span className="dashboard-metric-icon" aria-hidden="true">
              ↗
            </span>
            <span>未来半年到期</span>
            <strong>
              {data.demo && selectedCategory ? "—" : `¥${money(maturityTotal)}`}
            </strong>
          </div>
        </div>
      </div>
      <details className="dashboard-filter-panel">
        <summary>筛选资产视图</summary>
        <Filters
          params={filters}
          onChange={(next) => {
            coinCleanupRef.current?.();
            if (returnTopTimerRef.current !== null)
              window.clearTimeout(returnTopTimerRef.current);
            setTransitioning(false);
            setAnimationDone(false);
            setParams(next);
          }}
          owners={data.owner_choices}
          banks={data.bank_choices}
          categories={data.category_choices}
          statuses={data.status_choices}
        />
      </details>
      <div className="dashboard-section-heading dashboard-motion">
        <div>
          <span className="dashboard-kicker">PORTFOLIO INSIGHTS</span>
          <h2>资产透视</h2>
        </div>
        <span>使用上方筛选条件查看银行、类别与成员数据</span>
      </div>
      <div
        className="dashboard-charts"
        aria-busy={state.loading || transitioning}
      >
        <section className="card dashboard-chart-card dashboard-motion">
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
        <section className="card dashboard-chart-card dashboard-motion">
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
        <section className="card dashboard-chart-card dashboard-motion">
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
      <section className="card dashboard-maturity dashboard-motion">
        <div className="dashboard-maturity-title">
          <div>
            <span className="dashboard-kicker">UPCOMING CASH FLOW</span>
            <h2>未来半年到期计划</h2>
            <p>
              {data.demo && selectedCategory
                ? "演示数据暂未提供按类别的到期时间明细。"
                : "仅统计当前筛选范围内、存续中且已填写到期日的资产。"}
            </p>
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
                {maturityRows.map((row, index) => (
                  <tr key={row.month}>
                    <td>
                      {row.month}
                      <span
                        className="dashboard-maturity-meter"
                        aria-hidden="true"
                      >
                        <span
                          style={{
                            width: `${maturityPeak ? (Number(row.total_amount) / maturityPeak) * 100 : 0}%`,
                            animationDelay: `${index * 80}ms`,
                          }}
                        />
                      </span>
                    </td>
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
      {trendRows.length > 0 && (
        <section className="card dashboard-trend dashboard-motion">
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
      <section className="card dashboard-members dashboard-motion">
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
                  <td className="break">
                    {row.first_name || "待核对所有者"}
                    <span className="dashboard-member-track" aria-hidden="true">
                      <span
                        style={{
                          width: `${Number(data.total_amount) ? (Number(row.total_amount) / Number(data.total_amount)) * 100 : 0}%`,
                        }}
                      />
                    </span>
                  </td>
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
