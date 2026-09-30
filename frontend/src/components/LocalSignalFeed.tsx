import { useEffect, useState } from "react";
import { BulletinItem } from "../types";
import { formatTime } from "../lib/time";

const PAGE_SIZE = 12;

export function LocalSignalFeed({ signals, province }: { signals: BulletinItem[]; province?: string }) {
  const [localOnly, setLocalOnly] = useState(true);
  const [page, setPage] = useState(0);
  const visible = signals.filter((item) => !localOnly || !province || item.provinces.includes(province));
  const pages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const selectedPage = Math.min(page, pages - 1);
  useEffect(() => setPage(0), [province, localOnly]);
  return (
    <section className="card local-signal-section" aria-labelledby="local-signals-title">
      <div className="section-heading"><div><span className="eyebrow">LOCAL WARNING INDEX</span><h2 id="local-signals-title">地方预警信号 <span className="count-pill">{visible.length}</span></h2></div>
        <label className="inline-check"><input type="checkbox" checked={localOnly} onChange={(e) => setLocalOnly(e.target.checked)} />只看{province || "当前省份"}</label></div>
      <p className="section-description">NMC 官方公开索引共收录 {signals.length} 条。省、市、县发布范围保留在标题中；索引未提供完整有效/解除状态，不用于全国地图填色。</p>
      {!visible.length ? <div className="empty-state">当前索引没有匹配条目，不代表当地无预警。请查看来源状态或官方列表。</div> : (
        <ul className="local-signal-list">{visible.slice(selectedPage * PAGE_SIZE, (selectedPage + 1) * PAGE_SIZE).map((item) => (
          <li key={item.id}><div><a href={item.source_url} target="_blank" rel="noreferrer">{item.title} ↗</a><p className="meta">发布 {formatTime(item.published_at)} · 索引采集 {formatTime(item.fetched_at)}</p></div>
            <span className="kind-badge">{item.warning_level || "查看原文"}</span></li>
        ))}</ul>
      )}
      <div className="local-pagination"><button type="button" disabled={selectedPage === 0} onClick={() => setPage(selectedPage - 1)}>上一页</button><span className="meta">第 {selectedPage + 1} / {pages} 页</span><button type="button" disabled={selectedPage + 1 >= pages} onClick={() => setPage(selectedPage + 1)}>下一页</button><a href="https://www.nmc.cn/publish/alarm.html" target="_blank" rel="noreferrer">官方完整列表 ↗</a></div>
    </section>
  );
}
