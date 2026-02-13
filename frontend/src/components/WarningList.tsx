import { WarningItem } from "../types";

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
  return "lv-blue";
}

export function WarningList({ warnings, focusProvince, activeWarningKey, onWarningClick }: Props) {
  const normalizedFocusProvince = focusProvince ? normalizeProvinceName(focusProvince) : "";
  const sortedWarnings = [...warnings].sort((a, b) => {
    const aFocused = normalizedFocusProvince && normalizeProvinceName(a.province) === normalizedFocusProvince ? 1 : 0;
    const bFocused = normalizedFocusProvince && normalizeProvinceName(b.province) === normalizedFocusProvince ? 1 : 0;
    if (aFocused !== bFocused) return bFocused - aFocused;
    const aActive = activeWarningKey === `${a.title}-${a.issue_time}` ? 1 : 0;
    const bActive = activeWarningKey === `${b.title}-${b.issue_time}` ? 1 : 0;
    if (aActive !== bActive) return bActive - aActive;
    const score = (level: string) => (level.includes("红") ? 4 : level.includes("橙") ? 3 : level.includes("黄") ? 2 : 1);
    const diff = score(b.level) - score(a.level);
    if (diff !== 0) return diff;
    return new Date(b.issue_time).getTime() - new Date(a.issue_time).getTime();
  });
  const scrollable = sortedWarnings.length > 6;

  return (
    <section className="card">
      <h3>预警信息</h3>
      <ul className={scrollable ? "warning-list scrollable" : "warning-list"}>
        {sortedWarnings.map((item) => (
          <li
            key={`${item.title}-${item.issue_time}`}
            className={[
              normalizedFocusProvince && normalizeProvinceName(item.province) === normalizedFocusProvince ? "warning-focused" : "",
              activeWarningKey === `${item.title}-${item.issue_time}` ? "warning-active" : "",
            ].join(" ").trim()}
            onClick={() => onWarningClick?.(item)}
            onKeyDown={(event) => {
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
              {item.province} | {item.hazard_type} | {new Date(item.issue_time).toLocaleString()}
            </p>
            <p className="meta">
              来源：{item.source} {item.is_ai_augmented ? "（辅助解读）" : ""}
              {" | "}
              <a href={item.detail_url} target="_blank" rel="noreferrer">原文</a>
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
