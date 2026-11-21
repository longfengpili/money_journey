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
  aurora = false,
}: {
  labels: string[];
  series: { label: string; values: (string | number)[] }[];
  aurora?: boolean;
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
          backgroundColor: aurora
            ? ["#6966e8", "#2ccbbb", "#ffad6f", "#7ab6ff", "#e78cb7"][index % 5]
            : colors[index % colors.length],
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
          x: {
            stacked: true,
            beginAtZero: true,
            grid: { color: aurora ? "#dbe4f2" : "#edf0f6" },
            ticks: { color: aurora ? "#64718f" : "#667085" },
          },
          y: {
            stacked: true,
            grid: { display: false },
            ticks: { color: aurora ? "#64718f" : "#667085" },
          },
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: { boxWidth: 10, color: aurora ? "#566686" : "#667085" },
          },
          tooltip: {
            callbacks: {
              label: (item) =>
                `${item.dataset.label}: ¥${money(series[item.datasetIndex].values[item.dataIndex])}`,
            },
          },
        },
      },
    });
    let resizeFrame = 0;
    const resize = () => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => chart.resize());
    };
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(resizeFrame);
      chart.destroy();
    };
  }, [aurora, JSON.stringify(labels), JSON.stringify(series)]);
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
