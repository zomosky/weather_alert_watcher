import { useState } from "react";
import { BulletinItem } from "../types";
import { formatTime } from "../lib/time";

const KIND_LABELS = { bulletin: "天气公报", official_warning: "官方预警发布", outlook: "中期展望", cancelled_warning: "预警解除", risk_notice: "风险预报", local_signal: "地方信号" };

export function BulletinFeed({ bulletins, province, onProvinceFocus }: {
  bulletins: BulletinItem[];
  province?: string;
  onProvinceFocus: (province: string) => void;
}) {
  const [kind, setKind] = useState("all");
  const [localOnly, setLocalOnly] = useState(false);
  const visible = bulletins.filter((b) => (kind === "all" || b.kind === kind)
    && (!localOnly || !province || b.provinces.length === 0 || b.provinces.includes(province)));
  return (
    <section className="card disclosure-section" aria-labelledby="disclosure-title">
      <div className="section-heading">
        <div><span className="eyebrow">PUBLIC DISCLOSURES</span><h2 id="disclosure-title">CMA 公开消息 <span className="count-pill">{bulletins.length}</span></h2></div>
        <label className="inline-check"><input type="checkbox" checked={localOnly} onChange={(e) => setLocalOnly(e.target.checked)} />关注{province || "当前省份"}</label>
      </div>
      <p className="section-description">公报、联合风险预警和解除信息分类展示。关键词可能涉及历史或否定表述，颜色以官方发布及具体区域为准。</p>
      <div className="filter-tabs" role="group" aria-label="公告类型筛选">
        {[["all", "全部消息"], ["bulletin", "天气公报"], ["official_warning", "预警发布"], ["cancelled_warning", "预警解除"], ["risk_notice", "风险预报"], ["outlook", "中期展望"]].map(([value, label]) => (
          <button type="button" key={value} className={kind === value ? "tab active" : "tab"} aria-pressed={kind === value} onClick={() => setKind(value)}>{label}</button>
        ))}
      </div>
      {visible.length === 0 ? <div className="empty-state">暂无符合筛选条件的公告。可切换到全部消息，或查看下方来源状态。</div> : (
        <div className="bulletin-grid">{visible.map((item) => (
          <article key={item.id} className="bulletin-card">
            <div className="row between"><span className={`kind-badge ${item.kind}`}>{KIND_LABELS[item.kind]}</span><time className="meta">{item.published_at ? formatTime(item.published_at) : "发布时间未披露"}</time></div>
            <h3>{item.title}</h3>
            <div className="hazard-tags">{item.hazard_types.map((h) => <span key={h}>{h}</span>)}</div>
            <p className="bulletin-excerpt">{item.summary}</p>
            <div className="province-tags" aria-label="公告涉及省份">{item.provinces.length ? item.provinces.map((p) => (
              <button type="button" className={p === province ? "province-chip selected" : "province-chip"} key={p} onClick={() => onProvinceFocus(p)}>{p}</button>
            )) : <span className="meta">原文未明确列出省份</span>}</div>
            <details className="bulletin-detail"><summary>展开原文摘录</summary><p>{item.summary}</p></details>
            <footer className="bulletin-footer"><span className="meta">采集于 {formatTime(item.fetched_at)}</span><a href={item.source_url} target="_blank" rel="noreferrer">中央气象台原文 ↗</a></footer>
          </article>
        ))}</div>
      )}
    </section>
  );
}
