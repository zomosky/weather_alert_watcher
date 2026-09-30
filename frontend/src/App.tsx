import { useEffect, useRef, useState } from "react";
import { ChinaMapPanel } from "./components/ChinaMapPanel";
import { ForecastChart } from "./components/ForecastChart";
import { LocationPanel } from "./components/LocationPanel";
import { WarningList } from "./components/WarningList";
import { BulletinFeed } from "./components/BulletinFeed";
import { SourceStatus } from "./components/SourceStatus";
import { LocalSignalFeed } from "./components/LocalSignalFeed";
import { OfficialResources } from "./components/OfficialResources";
import { fetchDashboard } from "./services/api";
import { normalizeProvinceName, PROVINCE_CAPITAL_COORDS } from "./lib/location";
import { formatTime } from "./lib/time";
import { warningKey } from "./lib/warnings";
import { DashboardResponse, LocationPayload, MapPickPoint, SelectedLocation, WarningItem } from "./types";

const defaultLocation: SelectedLocation = { lat: 39.9042, lon: 116.4074, province: "北京" };

export default function App() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedLocation, setSelectedLocation] = useState<SelectedLocation>(defaultLocation);
  const [loadedPayload, setLoadedPayload] = useState<LocationPayload | null>(null);
  const [activeWarningKey, setActiveWarningKey] = useState("");
  const requestRef = useRef<AbortController | null>(null);

  const load = async (payload: LocationPayload) => {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    const timeout = window.setTimeout(() => controller.abort("timeout"), 45000);
    setLoading(true);
    setError("");
    try {
      const next = await fetchDashboard(payload, controller.signal);
      if (requestRef.current === controller) { setData(next); setLoadedPayload(payload); }
    } catch (err) {
      if (requestRef.current === controller && (!controller.signal.aborted || controller.signal.reason === "timeout")) {
        setError(controller.signal.aborted ? "请求超时，请重试或查看来源状态。" : err instanceof Error ? err.message : "加载失败");
      }
    } finally {
      window.clearTimeout(timeout);
      if (requestRef.current === controller) setLoading(false);
    }
  };

  useEffect(() => {
    void load(defaultLocation);
    return () => requestRef.current?.abort();
  }, []);

  const submitLocation = () => { void load(selectedLocation); };
  const handleMapPick = (point: MapPickPoint) => {
    setActiveWarningKey("");
    const next = { ...selectedLocation, lat: Number(point.lat.toFixed(4)), lon: Number(point.lon.toFixed(4)), province: point.province ?? selectedLocation.province };
    setSelectedLocation(next);
    void load(next);
  };
  const focusProvince = (name: string) => {
    const province = normalizeProvinceName(name);
    const next = { ...selectedLocation, ...PROVINCE_CAPITAL_COORDS[province], province };
    setSelectedLocation(next);
    void load(next);
  };
  const handleWarningClick = (warning: WarningItem) => {
    setActiveWarningKey(warningKey(warning));
    focusProvince(warning.province);
  };
  const handleProvinceFocus = (province: string) => {
    setActiveWarningKey("");
    focusProvince(province);
  };
  const demo = data?.warnings.some((w) => w.source.startsWith("Mock")) || data?.forecast_source?.startsWith("Mock");
  const unhealthy = data?.source_statuses.filter((s) => ["degraded", "stale"].includes(s.state)).length || 0;
  const loadedLocation = loadedPayload?.province;
  const locationChanged = !!loadedPayload && (loadedPayload.lat !== selectedLocation.lat || loadedPayload.lon !== selectedLocation.lon || loadedPayload.province !== selectedLocation.province);

  return (
    <main className="page">
      <header className="masthead">
        <div className="brand-row"><span className="brand-mark">WX</span><span>气象观察 <span className="brand-divider">/</span> 全国极端天气</span><span className="live-pill">{demo ? "含演示数据" : "公开数据观察"}</span></div>
        <div className="hero-row"><div><span className="eyebrow">NATIONAL WEATHER WATCH</span><h1>全国极端天气看板</h1><p>从官方披露到区域态势，关注每一次天气变化。</p></div>
          <div className="hero-refresh"><span>最近完整更新</span><strong>{formatTime(data?.last_refresh_at)}</strong><small>采集间隔 {data?.refresh_interval_minutes || 30} 分钟</small></div>
        </div>
      </header>
      <div className="overview-grid" aria-label="气象信息摘要">
        <div className="stat-card"><span>当前关注</span><strong>{selectedLocation.province || "自选位置"}</strong><small>{selectedLocation.lat.toFixed(4)}°N · {selectedLocation.lon.toFixed(4)}°E</small></div>
        <div className="stat-card"><span>全国预警涉及地区</span><strong>{data?.warnings.length ?? "—"}<em>条</em></strong><small>{demo ? "包含明确标注的演示预警" : "官方发布语句 · 按地区预报时段"}</small></div>
        <div className="stat-card"><span>CMA 公开消息</span><strong>{data?.bulletins.length ?? "—"}<em>篇</em></strong><small>公报 · 预警 · 解除 · 风险 · 展望</small></div>
        <div className="stat-card"><span>来源状态</span><strong className={unhealthy ? "text-amber" : "text-teal"}>{unhealthy ? `${unhealthy} 项待恢复` : data ? "已检查" : "待检查"}</strong><small>各来源状态与最近成功时间见下方</small></div>
      </div>
      <LocationPanel value={selectedLocation} onChange={setSelectedLocation} onSubmit={submitLocation} loading={loading} />
      {loading && <p className="loading-banner" role="status">正在更新 {selectedLocation.province || "当前位置"} 的看板信息…</p>}
      {error && <p className="error-banner" role="alert">{error}</p>}
      {demo && <p className="demo-banner">当前预警或曲线包含演示数据，具体来源已标注。CMA 公告来自公开披露。</p>}
      {data && locationChanged && <p className="loading-banner">位置已切换；下方信息对应上次加载的 {loadedLocation || "坐标"}，请更新看板。</p>}
      {data && <>
        <div className="layout-2">
          <ChinaMapPanel focusProvince={selectedLocation.province ?? data.current_province} warnings={data.warnings}
            selectedLocation={selectedLocation} onMapPick={handleMapPick} onProvinceFocus={handleProvinceFocus} />
          <WarningList warnings={data.warnings} focusProvince={selectedLocation.province ?? data.current_province ?? undefined}
            activeWarningKey={activeWarningKey} onWarningClick={handleWarningClick} />
        </div>
        <BulletinFeed bulletins={data.bulletins} province={selectedLocation.province} onProvinceFocus={handleProvinceFocus} />
        <ForecastChart points={data.forecast_points} source={data.forecast_source} location={data.forecast_location} />
        <LocalSignalFeed signals={data.local_signals} province={selectedLocation.province} />
        <SourceStatus statuses={data.source_statuses} />
        <OfficialResources />
      </>}
      {!data && !loading && <section className="card empty-state">看板暂未加载，请使用“更新看板”重试。</section>}
      <footer className="page-footer"><span>气象观察 · 全国极端天气看板</span><span>发布时间与采集时间独立展示 · 来源可追溯</span></footer>
    </main>
  );
}
