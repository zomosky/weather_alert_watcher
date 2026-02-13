import ReactECharts from "echarts-for-react";
import { ForecastPoint } from "../types";

type Props = {
  points: ForecastPoint[];
};

export function ForecastChart({ points }: Props) {
  const option = {
    tooltip: { trigger: "axis" },
    legend: { data: ["温度(°C)", "湿度(%)"] },
    xAxis: {
      type: "category",
      data: points.map((p) => new Date(p.forecast_time).toLocaleString()),
      axisLabel: { showMaxLabel: true, hideOverlap: true },
    },
    yAxis: [
      { type: "value", name: "温度(°C)" },
      { type: "value", name: "湿度(%)", min: 0, max: 100 },
    ],
    series: [
      {
        name: "温度(°C)",
        type: "line",
        smooth: true,
        data: points.map((p) => p.temperature_c),
      },
      {
        name: "湿度(%)",
        type: "line",
        smooth: true,
        yAxisIndex: 1,
        data: points.map((p) => p.humidity_pct),
      },
    ],
    grid: { left: 48, right: 48, bottom: 60 },
  };

  return (
    <section className="card">
      <h3>未来 7 天温湿度曲线</h3>
      <ReactECharts option={option} style={{ height: 380 }} />
    </section>
  );
}
