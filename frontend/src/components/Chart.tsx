import { useEffect, useRef } from "react";
import ChartJS from "chart.js/auto";
import { money } from "../lib/money";

export default function Chart({
  title,
  labels,
  values,
  type = "bar",
  aurora = false,
}: {
  title: string;
  labels: string[];
  values: (string | number)[];
  type?: "bar" | "horizontalBar" | "doughnut" | "line";
  aurora?: boolean;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!ref.current || !values.length) return;
    const chart = new ChartJS(ref.current, {
      type: type === "horizontalBar" ? "bar" : type,
      data: {
        labels,
        datasets: [
          {
            label: title,
            data: values.map(Number),
            backgroundColor:
              type === "line"
                ? aurora
                  ? "#6966e829"
                  : "#3559e018"
                : aurora
                  ? ["#6966e8", "#2ccbbb", "#ffad6f", "#7ab6ff", "#e78cb7"]
                  : [
                      "#3559e0",
                      "#12a89d",
                      "#74a1f8",
                      "#a68be8",
                      "#f4b759",
                      "#ed8da5",
                    ],
            borderColor:
              type === "line"
                ? aurora
                  ? "#6966e8"
                  : "#3559e0"
                : "transparent",
            borderWidth: 2,
            borderRadius: type === "doughnut" ? 0 : 7,
            borderSkipped: false,
            maxBarThickness: 32,
            ...(type === "line"
              ? { tension: 0.25, fill: true, pointRadius: 2 }
              : {}),
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: type === "horizontalBar" ? "y" : "x",
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? false
          : { duration: 250 },
        plugins: {
          legend: {
            display: type === "doughnut",
            position: "bottom",
            labels: { color: aurora ? "#566686" : "#667085" },
          },
          tooltip: {
            callbacks: {
              label: (item) =>
                `${item.label}: ¥${money(values[item.dataIndex])}`,
            },
          },
        },
        ...(type === "doughnut" ? { cutout: "70%" } : {}),
        ...(type !== "doughnut"
          ? {
              scales: {
                [type === "horizontalBar" ? "x" : "y"]: {
                  beginAtZero: true,
                  grid: { color: aurora ? "#dbe4f2" : "#edf0f6" },
                  ticks: { color: aurora ? "#64718f" : "#667085" },
                },
                [type === "horizontalBar" ? "y" : "x"]: {
                  grid: { display: false },
                  ticks: { color: aurora ? "#64718f" : "#667085" },
                },
              },
            }
          : {}),
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
  }, [type, title, aurora, JSON.stringify(labels), JSON.stringify(values)]);
  return (
    <div className={values.length ? "chart" : "chart chart-empty"}>
      {values.length ? (
        <canvas ref={ref} role="img" aria-label={title} />
      ) : (
        <div className="empty">暂无数据</div>
      )}
    </div>
  );
}
