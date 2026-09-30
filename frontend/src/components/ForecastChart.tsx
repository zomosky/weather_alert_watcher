import ReactECharts from "echarts-for-react/lib/core";
import { echarts } from "../lib/echarts";
import { ForecastPoint } from "../types";
import { formatTime } from "../lib/time";

type Props = {
  points: ForecastPoint[];
  source: string | null;
  location: string | null;
};

export function ForecastChart({ points, source, location }: Props) {
  const option = {
    tooltip: { trigger: "axis" },
    legend: { data: ["温度(°C)", "湿度(%)"] },
    xAxis: {
      type: "category",
      data: points.map((p) => formatTime(p.forecast_time)),
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
        itemStyle: { color: "#0d9488" },
        areaStyle: { color: "rgba(13,148,136,0.08)" },
        data: points.map((p) => p.temperature_c),
      },
      {
        name: "湿度(%)",
        type: "line",
        smooth: true,
        yAxisIndex: 1,
        itemStyle: { color: "#7c9caf" },
        data: points.map((p) => p.humidity_pct),
      },
    ],
    grid: { left: 48, right: 48, bottom: 60 },
  };

  return (
    <section className="card">
      <div className="section-heading"><div><span className="eyebrow">LOCAL FORECAST</span><h2>未来 7 天温湿度</h2></div><span className="meta">{location || "当前坐标"} · {source?.startsWith("Mock") ? "演示预报" : source || "暂无来源"}</span></div>
      {points.length ? <ReactECharts echarts={echarts} option={option} style={{ height: 320 }} /> : <div className="empty-state">当前坐标的预报暂不可用，请查看来源状态并稍后重试。</div>}
    </section>
  );
}
