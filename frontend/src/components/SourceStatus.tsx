import { SourceStatusItem } from "../types";
import { formatTime } from "../lib/time";

const LABELS = { ok: "已更新", degraded: "来源异常", stale: "更新滞后", waiting: "等待采集", disabled: "未启用", demo: "演示数据" };
const SOURCE_LABELS: Record<string, string> = {
  "weather-bulletin/index.htm": "天气公报", "weatherperday/index.htm": "每日天气提示",
  "typhoon/warning_index.html": "台风预警", "bulletin/mid-range.htm": "中期天气",
  "news/weather_new.html": "重要天气提示",
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
