import { SourceStatusItem } from "../types";
import { formatTime } from "../lib/time";

const LABELS = { ok: "已更新", degraded: "来源异常", stale: "更新滞后", waiting: "等待采集", disabled: "未启用", demo: "演示数据" };
const SOURCE_LABELS: Record<string, string> = {
  "weather-bulletin/index.htm": "天气公报", "weatherperday/index.htm": "每日天气提示",
  "typhoon/warning_index.html": "台风预警", "bulletin/mid-range.htm": "中期天气",
  "news/weather_new.html": "重要天气提示",
  "country/warning/wind.html": "大风预警", "country/warning/strong_convection.html": "强对流预警",
  "country/warning/downpour.html": "暴雨预警", "country/warning/typhoon.html": "台风预警",
  "country/warning/megatemperature.html": "高温预警", "country/warning/fog.html": "大雾预警",
  "country/warning/dust.html": "沙尘暴预警", "country/warning/blizzard.html": "暴雪预警",
  "country/warning/cold.html": "寒潮预警", "country/warning/frozen.html": "冰冻预警",
  "country/warning/drought.html": "气象干旱预警", "country/warning/low-temperature.html": "低温预警",
  "mountainflood.html": "山洪灾害预警", "geohazard.html": "地质灾害风险预警",
  "waterlogging.html": "渍涝风险预报", "swdz/zxhlhsqxyj.html": "中小河流洪水风险",
  "bulletin/swpc.html": "强对流天气预报", "environment/forestfire-doc.html": "森林火险预报",
};

export function SourceStatus({ statuses }: { statuses: SourceStatusItem[] }) {
  return (
    <section className="card source-panel">
      <div className="section-heading"><div><span className="eyebrow">DATA SOURCES</span><h2>数据来源与更新状态</h2></div><span className="meta">北京时间 · UTC+8</span></div>
      <div className="source-grid">{statuses.map((s) => (
        <div key={s.source_url || s.name} className="source-row">
          <div className="row between"><strong>{SOURCE_LABELS[s.name] || s.name}</strong><span className={`status-label ${s.state}`}><i />{LABELS[s.state]}</span></div>
          <p className="meta">{s.provider} · 最近成功 {formatTime(s.last_success_at)}</p>
          {s.message && <p className="source-message">{s.message}</p>}
          {s.source_url && <a href={s.source_url} target="_blank" rel="noreferrer" className="source-link">查看来源 ↗</a>}
        </div>
      ))}</div>
    </section>
  );
}
