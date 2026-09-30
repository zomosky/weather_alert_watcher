import { WarningItem } from "../types";
import { formatTime } from "../lib/time";
import { warningKey } from "../lib/warnings";

type Props = {
  warnings: WarningItem[];
  focusProvince?: string;
  activeWarningKey?: string;
  onWarningClick?: (warning: WarningItem) => void;
};

function normalizeProvinceName(name: string): string {
  return name
    .replace(/特别行政区/g, "")
    .replace(/维吾尔自治区|回族自治区|壮族自治区|自治区/g, "")
    .replace(/省|市/g, "")
    .trim();
}

function levelClass(level: string): string {
  if (level.includes("红")) return "lv-red";
  if (level.includes("橙")) return "lv-orange";
  if (level.includes("黄")) return "lv-yellow";
  return level.includes("蓝") ? "lv-blue" : "lv-unknown";
}

export function WarningList({ warnings, focusProvince, activeWarningKey, onWarningClick }: Props) {
  const normalizedFocusProvince = focusProvince ? normalizeProvinceName(focusProvince) : "";
  const sortedWarnings = [...warnings].sort((a, b) => {
    const aFocused = normalizedFocusProvince && normalizeProvinceName(a.province) === normalizedFocusProvince ? 1 : 0;
    const bFocused = normalizedFocusProvince && normalizeProvinceName(b.province) === normalizedFocusProvince ? 1 : 0;
    if (aFocused !== bFocused) return bFocused - aFocused;
    const aActive = activeWarningKey === warningKey(a) ? 1 : 0;
    const bActive = activeWarningKey === warningKey(b) ? 1 : 0;
    if (aActive !== bActive) return bActive - aActive;
    const score = (level: string) => (level.includes("红") ? 4 : level.includes("橙") ? 3 : level.includes("黄") ? 2 : 1);
    const diff = score(b.level) - score(a.level);
    if (diff !== 0) return diff;
    return new Date(b.issue_time).getTime() - new Date(a.issue_time).getTime();
  });
  const scrollable = sortedWarnings.length > 6;

  return (
    <section className="card warning-panel">
      <span className="eyebrow">WARNING SIGNALS</span>
      <h2>全国预警涉及地区 <span className="count-pill">{warnings.length}</span></h2>
      <p className="section-description">按原文涉及省份整理，预警可能仅影响省内部分地区；市县信号在下方单独展示。</p>
      {warnings.length === 0 && <div className="empty-state">已接入全国产品暂无可展示预警；不代表全国或当前省份没有预警。可查看下方地方信号与来源状态。</div>}
      <ul className={scrollable ? "warning-list scrollable" : "warning-list"}>
        {sortedWarnings.map((item) => (
          <li
            key={warningKey(item)}
            className={[
              normalizedFocusProvince && normalizeProvinceName(item.province) === normalizedFocusProvince ? "warning-focused" : "",
              activeWarningKey === warningKey(item) ? "warning-active" : "",
            ].join(" ").trim()}
            onClick={() => onWarningClick?.(item)}
            onKeyDown={(event) => {
              if (event.target !== event.currentTarget) return;
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onWarningClick?.(item);
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className="row between">
              <strong>{item.title}</strong>
              <span className={`badge ${levelClass(item.level)}`}>{item.level}</span>
            </div>
            <p>{item.summary}</p>
            <p className="meta">
              {item.province} · {item.hazard_type} · {formatTime(item.issue_time)} 发布
            </p>
            <p className="meta">
              {item.expires_at ? `原文预报覆盖至 ${formatTime(item.expires_at)}（不等同官方解除时间）` : "未披露截止时间；仅展示近 24 小时发布信息"}
            </p>
            <p className="meta">
              来源：{item.source} {item.is_ai_augmented ? "（辅助解读）" : ""}
              {" | "}
              <a href={item.detail_url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>原文 ↗</a>
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
