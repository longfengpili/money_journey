import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useResource } from "../../lib/resource";
import type { Summary } from "../../lib/types";
import { interpolateMoney, money, sumMoney } from "../../lib/money";
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
  onMorphProgress: (progress: number) => void,
  onComplete: () => void,
) {
  const charts = dashboard?.querySelector<HTMLElement>(".dashboard-charts");
  if (!charts) {
    onComplete();
    return () => {};
  }
  const spark = dashboard?.querySelector<HTMLElement>(".dashboard-orbit-spark");
  const point = spark?.querySelector<HTMLElement>(
    ".dashboard-orbit-spark-point",
  );
  spark?.classList.add("is-transmuting");
  const sourceBounds = source.getBoundingClientRect();
  const start = (point ?? source).getBoundingClientRect();
  const core = dashboard?.querySelector<HTMLElement>(".dashboard-orbit-core");
  const coreBounds = core?.getBoundingClientRect();
  const coreOffsetX = coreBounds
    ? coreBounds.left + coreBounds.width / 2 - start.left - start.width / 2
    : 0;
  const coreOffsetY = coreBounds
    ? coreBounds.top + coreBounds.height / 2 - start.top - start.height / 2
    : 0;
  const centerX = coreBounds
    ? coreBounds.left + coreBounds.width / 2
    : window.innerWidth / 2;
  const centerY = Math.max(
    (coreBounds
      ? coreBounds.top + coreBounds.height / 2
      : start.top + start.height / 2) + 180,
    window.innerHeight * 0.72,
  );
  const offsetX = centerX - start.left - start.width / 2;
  const offsetY = centerY - start.top - start.height / 2;
  const animations = new Set<Animation>();
  const rays: HTMLElement[] = [];
  let progressFrame: number | null = null;
  let stopped = false;
  const inboundBeam = document.createElement("span");
  inboundBeam.className = "dashboard-inbound-beam";
  inboundBeam.setAttribute("aria-hidden", "true");
  if (point) {
    const sourceX = sourceBounds.left + sourceBounds.width / 2;
    const sourceY = sourceBounds.top + sourceBounds.height / 2;
    const targetX = start.left + start.width / 2;
    const targetY = start.top + start.height / 2;
    inboundBeam.style.left = `${sourceX}px`;
    inboundBeam.style.top = `${sourceY}px`;
    inboundBeam.style.width = `${Math.hypot(targetX - sourceX, targetY - sourceY)}px`;
    inboundBeam.style.transform = `rotate(${(Math.atan2(targetY - sourceY, targetX - sourceX) * 180) / Math.PI}deg)`;
    document.body.append(inboundBeam);
  }
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
  const getLightTargets = () => {
    const charts = Array.from(
      dashboard?.querySelectorAll<HTMLCanvasElement>('canvas[role="img"]') ??
        [],
    ).map((canvas) => {
      const impact = canvas.closest<HTMLElement>(".chart") ?? canvas;
      return { impact, card: canvas.closest<HTMLElement>(".card") ?? impact };
    });
    const maturityTable = dashboard?.querySelector<HTMLElement>(
      ".dashboard-maturity-table",
    );
    if (maturityTable)
      charts.push({
        impact: maturityTable,
        card: maturityTable.closest<HTMLElement>(".card") ?? maturityTable,
      });
    return charts;
  };
  const play = (
    element: HTMLElement,
    frames: Keyframe[],
    duration: number,
    delay = 0,
    onProgress?: (progress: number) => void,
  ) => {
    const animation = element.animate(frames, {
      duration,
      delay,
      easing: "ease-in-out",
      fill: "forwards",
    });
    animations.add(animation);
    if (onProgress) {
      const track = () => {
        if (stopped) return;
        const elapsed = Number(animation.currentTime ?? 0) - delay;
        onProgress(Math.max(0, Math.min(1, elapsed / duration)));
        if (animation.playState !== "finished")
          progressFrame = window.requestAnimationFrame(track);
      };
      progressFrame = window.requestAnimationFrame(track);
    }
    return animation.finished;
  };
  const cleanup = () => {
    if (stopped) return;
    stopped = true;
    animations.forEach((animation) => animation.cancel());
    if (progressFrame !== null) window.cancelAnimationFrame(progressFrame);
    inboundBeam.remove();
    coin.remove();
    rays.forEach((ray) => ray.remove());
    point?.classList.remove("is-hit");
    spark?.classList.remove("is-transmuting");
  };
  void (async () => {
    try {
      if (point) {
        await play(
          inboundBeam,
          [
            { clipPath: "inset(0 100% 0 0)", opacity: 0.3 },
            { clipPath: "inset(0 0 0 0)", opacity: 1, offset: 0.72 },
            { clipPath: "inset(0 0 0 0)", opacity: 0 },
          ],
          520,
        );
        inboundBeam.remove();
        point.classList.add("is-hit");
      }
      coin.classList.add("is-morphing");
      document.body.append(coin);
      await play(
        coin,
        [
          { transform: "translate(0, 0) scale(.14)", opacity: 0.9 },
          {
            transform: `translate(${coreOffsetX * 0.5}px, ${coreOffsetY * 0.5}px) scale(.5)`,
            opacity: 1,
            offset: 0.5,
          },
          {
            transform: `translate(${coreOffsetX}px, ${coreOffsetY}px) scale(1)`,
            opacity: 1,
          },
        ],
        600,
        0,
        onMorphProgress,
      );
      onMorphProgress(1);
      coin.classList.remove("is-morphing");
      coin.classList.add("is-descending");
      await play(
        coin,
        [
          {
            transform: `translate(${coreOffsetX}px, ${coreOffsetY}px) scale(1)`,
            opacity: 1,
          },
          {
            transform: `translate(${offsetX}px, ${offsetY}px) scale(1)`,
            opacity: 1,
          },
        ],
        430,
      );
      coin.classList.remove("is-descending");
      point?.classList.remove("is-hit");
      spark?.classList.remove("is-transmuting");
      const chartBounds = getLightTargets().map(({ impact }) =>
        impact.getBoundingClientRect(),
      );
      let scrollFinished: Promise<void> = Promise.resolve();
      if (chartBounds.length) {
        const top =
          Math.min(...chartBounds.map((bounds) => bounds.top)) + window.scrollY;
        const bottom =
          Math.max(...chartBounds.map((bounds) => bounds.bottom)) +
          window.scrollY;
        const span = bottom - top;
        const padding = 64;
        const targetScroll = Math.max(
          0,
          span <= window.innerHeight - padding * 2
            ? top - (window.innerHeight - span) / 2
            : top - padding,
        );
        if (Math.abs(window.scrollY - targetScroll) > 2) {
          scrollFinished = new Promise((resolve) => {
            const finish = () => {
              window.clearTimeout(timeout);
              window.removeEventListener("scrollend", finish);
              resolve();
            };
            const timeout = window.setTimeout(finish, 700);
            window.addEventListener("scrollend", finish, { once: true });
            window.scrollTo({ top: targetScroll, behavior: "smooth" });
          });
        }
      }
      await Promise.all([
        scrollFinished,
        play(
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
        ),
      ]);
      const chartTargets = getLightTargets();
      const burst = Array.from(
        {
          length: Math.max(
            18 + Math.floor(Math.random() * 7),
            chartTargets.length * 4,
          ),
        },
        (_, index) => {
          const ray = document.createElement("span");
          ray.className = "dashboard-gold-ray";
          ray.setAttribute("aria-hidden", "true");
          ray.style.left = `${centerX}px`;
          ray.style.top = `${centerY}px`;
          ray.style.width = `${1 + Math.random() * 1.2}px`;
          ray.style.height = `${80 + Math.random() * 100}px`;
          document.body.append(ray);
          rays.push(ray);
          const target = (
            chartTargets[index % chartTargets.length]?.impact ?? charts
          ).getBoundingClientRect();
          const endX =
            target.left + target.width / 2 + (Math.random() - 0.5) * 24;
          const endY =
            target.top + target.height / 2 + (Math.random() - 0.5) * 24;
          const travelX = endX - centerX;
          const travelY = endY - centerY;
          const angle = (Math.atan2(travelY, travelX) * 180) / Math.PI - 90;
          return play(
            ray,
            [
              {
                transform: `translate(0, 0) rotate(${angle}deg) scaleY(.2)`,
                opacity: 0,
              },
              {
                transform: `translate(${travelX * 0.12}px, ${travelY * 0.12}px) rotate(${angle}deg) scaleY(1)`,
                opacity: 1,
                offset: 0.18,
              },
              {
                transform: `translate(${travelX * 0.6}px, ${travelY * 0.6}px) rotate(${angle}deg) scaleY(.8)`,
                opacity: 1,
                offset: 0.65,
              },
              {
                transform: `translate(${travelX}px, ${travelY}px) rotate(${angle}deg) scaleY(.15)`,
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
      [...new Set(chartTargets.map(({ card }) => card))].forEach((card) => {
        card.classList.add("is-unfolding");
        card.addEventListener(
          "animationend",
          () => card.classList.remove("is-unfolding"),
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
  const [animatedTotal, setAnimatedTotal] = useState<string | null>(null);
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
  if (!filters.has("savings_status")) filters.set("savings_status", "ACTIVE");
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
    setAnimatedTotal(null);
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
  const savingsTotal = sumMoney(
    compassData.category_summary
      .filter((row) => row.category === "SAVINGS")
      .map((row) => row.total_amount),
  );
  const otherTotal = sumMoney(
    compassData.category_summary
      .filter((row) => row.category !== "SAVINGS")
      .map((row) => row.total_amount),
  );
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
  const includesHistoricalRecords =
    !data.demo && filters.get("savings_status") !== "ACTIVE";
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
          <h2 className="dashboard-halo-heading">资金罗盘</h2>
          <div className="dashboard-hero-foot">
            {includesHistoricalRecords
              ? "包含历史状态记录，续存资金可能与当前资产重复"
              : "每一道光，代表一类真实资产。"}
          </div>
          <div className="dashboard-structure" aria-label="资产结构金额">
            <div>
              <span>非储蓄类资产</span>
              <strong>¥{money(otherTotal)}</strong>
            </div>
            <div>
              <span>储蓄存款</span>
              <strong>¥{money(savingsTotal)}</strong>
            </div>
          </div>
          <div className="dashboard-cockpit-signal">
            <span className="dashboard-cockpit-dot" aria-hidden="true" />
            {focusedCategory
              ? "罗盘保留全部类别 · 下方已筛选"
              : "点击类别聚焦罗盘并筛选下方视图"}
          </div>
        </div>
        <section className="dashboard-orbit" aria-label="资金光环">
          <div className="dashboard-orbit-field" aria-hidden="true">
            <span className="dashboard-orbit-track dashboard-orbit-track-outer" />
            <span className="dashboard-orbit-track dashboard-orbit-track-inner" />
            <span className="dashboard-orbit-flow" />
            <span className="dashboard-orbit-spark">
              <span className="dashboard-orbit-spark-point" />
            </span>
            <span className="dashboard-orbit-aura" />
            {Array.from({ length: 16 }, (_, index) => (
              <span
                key={index}
                className="dashboard-orbit-beam"
                style={{
                  transform: `rotate(${index * 22.5}deg)`,
                  animationDelay: `${index * -0.22}s`,
                }}
              />
            ))}
            <span
              className="dashboard-orbit-progress"
              style={{ background: orbitGradient }}
            />
          </div>
          <div className="dashboard-orbit-core">
            <span>
              {includesHistoricalRecords ? "资产记录金额合计" : "家庭资产总额"}
            </span>
            <strong>¥{money(animatedTotal ?? data.total_amount)}</strong>
            <small>
              {focusedCategory
                ? `已筛选 · ${focusedCategory.category_display}`
                : activeScope}
            </small>
          </div>
          <div className="dashboard-orbit-nodes">
            {rankedCategories.map((row, index) => {
              const angle =
                -Math.PI / 2 +
                (Math.PI * 2 * index) / rankedCategories.length +
                (rankedCategories.length === 4 ? Math.PI / 4 : 0);
              return (
                <button
                  key={row.category || index}
                  type="button"
                  className={`dashboard-orbit-node${focusedCategory ? (selectedCategory === row.category ? " is-selected" : " is-muted") : ""}`}
                  style={
                    {
                      "--node-x": `${Math.cos(angle) * 220}px`,
                      "--node-y": `${Math.sin(angle) * 220}px`,
                    } as React.CSSProperties
                  }
                  onClick={(event) => {
                    const clearingCategory = selectedCategory === row.category;
                    const startAmount = animatedTotal ?? data.total_amount;
                    const targetAmount = clearingCategory
                      ? compassData.total_amount
                      : row.total_amount;
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
                      setAnimatedTotal(startAmount);
                      coinCleanupRef.current = flyCoin(
                        event.currentTarget,
                        dashboardRef.current,
                        clearingCategory
                          ? "全部资产"
                          : row.category_display || row.category || "资产",
                        clearingCategory ? 100 : orbitPercentages[index],
                        (progress) =>
                          setAnimatedTotal(
                            interpolateMoney(
                              startAmount,
                              targetAmount,
                              progress,
                            ),
                          ),
                        () => setAnimationDone(true),
                      );
                    } else {
                      setAnimatedTotal(null);
                    }
                    const next = new URLSearchParams(filters);
                    if (clearingCategory) next.delete("category");
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
              );
            })}
          </div>
          <div className="dashboard-halo-caption">
            分类占比合计 {orbitTotal ? 100 : 0}% · {rankedCategories.length}{" "}
            类资产
          </div>
        </section>
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
            setAnimatedTotal(null);
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
