import { useEffect, useRef } from "react";
import ChartJS from "chart.js/auto";
import { money } from "../lib/money";

const colors = [
  "#3559e0",
  "#12a89d",
  "#74a1f8",
  "#a68be8",
  "#f4b759",
  "#ed8da5",
];

export default function StackedChart({
  labels,
  series,
}: {
  labels: string[];
  series: { label: string; values: (string | number)[] }[];
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!ref.current || !labels.length || !series.length) return;
    const chart = new ChartJS(ref.current, {
      type: "bar",
      data: {
        labels,
        datasets: series.map((group, index) => ({
          label: group.label,
          data: group.values.map(Number),
          backgroundColor: colors[index % colors.length],
          borderRadius: 4,
          borderSkipped: false,
          maxBarThickness: 32,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? false
          : { duration: 250 },
        scales: {
          x: { stacked: true, beginAtZero: true, grid: { color: "#edf0f6" } },
          y: { stacked: true, grid: { display: false } },
        },
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10 } },
          tooltip: {
            callbacks: {
              label: (item) =>
                `${item.dataset.label}: ¥${money(series[item.datasetIndex].values[item.dataIndex])}`,
            },
          },
        },
      },
    });
    return () => chart.destroy();
  }, [JSON.stringify(labels), JSON.stringify(series)]);
  return (
    <div className={labels.length ? "chart" : "chart chart-empty"}>
      {labels.length ? (
        <canvas ref={ref} role="img" aria-label="成员资产结构" />
      ) : (
        <div className="empty">暂无数据</div>
      )}
    </div>
  );
}
