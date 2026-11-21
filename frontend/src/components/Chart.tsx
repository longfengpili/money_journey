import { useEffect, useRef } from "react";
import ChartJS from "chart.js/auto";

export default function Chart({
  title,
  labels,
  values,
  type = "bar",
}: {
  title: string;
  labels: string[];
  values: (string | number)[];
  type?: "bar" | "doughnut" | "line";
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!ref.current || !values.length) return;
    const chart = new ChartJS(ref.current, {
      type,
      data: {
        labels,
        datasets: [
          {
            label: title,
            data: values.map(Number),
            backgroundColor:
              type === "line"
                ? "#3559e018"
                : [
                    "#3559e0",
                    "#12a89d",
                    "#74a1f8",
                    "#a68be8",
                    "#f4b759",
                    "#ed8da5",
                  ],
            borderColor: type === "line" ? "#3559e0" : "transparent",
            borderWidth: 2,
            ...(type === "line"
              ? { tension: 0.25, fill: true, pointRadius: 2 }
              : {}),
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? false
          : { duration: 250 },
        plugins: {
          legend: { display: type === "doughnut", position: "bottom" },
        },
        ...(type !== "doughnut"
          ? { scales: { y: { beginAtZero: true } } }
          : {}),
      },
    });
    return () => chart.destroy();
  }, [type, title, JSON.stringify(labels), JSON.stringify(values)]);
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
