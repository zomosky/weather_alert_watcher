import { useEffect, useState } from "react";
import { ChinaMapPanel } from "./components/ChinaMapPanel";
import { ForecastChart } from "./components/ForecastChart";
import { LocationPanel } from "./components/LocationPanel";
import { WarningList } from "./components/WarningList";
import { fetchDashboard } from "./services/api";
import { DashboardResponse, LocationPayload, MapPickPoint, ProvinceCoord, SelectedLocation, WarningItem } from "./types";

const defaultLocation: SelectedLocation = {
  lat: 39.9042,
  lon: 116.4074,
  province: "北京",
};

function normalizeProvinceName(name: string): string {
  return name
    .replace(/特别行政区/g, "")
    .replace(/维吾尔自治区|回族自治区|壮族自治区|自治区/g, "")
    .replace(/省|市/g, "")
    .trim();
}

const PROVINCE_CAPITAL_COORDS: Record<string, ProvinceCoord> = {
  北京: { lat: 39.9042, lon: 116.4074 },
  天津: { lat: 39.3434, lon: 117.3616 },
  上海: { lat: 31.2304, lon: 121.4737 },
  重庆: { lat: 29.4316, lon: 106.9123 },
  河北: { lat: 38.0428, lon: 114.5149 },
  山西: { lat: 37.8706, lon: 112.5489 },
  辽宁: { lat: 41.8057, lon: 123.4315 },
  吉林: { lat: 43.8171, lon: 125.3235 },
  黑龙江: { lat: 45.756, lon: 126.6425 },
  江苏: { lat: 32.0603, lon: 118.7969 },
  浙江: { lat: 30.2741, lon: 120.1551 },
  安徽: { lat: 31.8206, lon: 117.2272 },
  福建: { lat: 26.0745, lon: 119.2965 },
  江西: { lat: 28.6829, lon: 115.8579 },
  山东: { lat: 36.6512, lon: 117.12 },
  河南: { lat: 34.7466, lon: 113.6254 },
  湖北: { lat: 30.5928, lon: 114.3055 },
  湖南: { lat: 28.2282, lon: 112.9388 },
  广东: { lat: 23.1291, lon: 113.2644 },
  海南: { lat: 20.0442, lon: 110.1999 },
  四川: { lat: 30.5728, lon: 104.0668 },
  贵州: { lat: 26.647, lon: 106.6302 },
  云南: { lat: 25.0389, lon: 102.7183 },
  陕西: { lat: 34.3416, lon: 108.9398 },
  甘肃: { lat: 36.0611, lon: 103.8343 },
  青海: { lat: 36.6171, lon: 101.7782 },
  内蒙古: { lat: 40.8426, lon: 111.7492 },
  广西: { lat: 22.817, lon: 108.3669 },
  西藏: { lat: 29.652, lon: 91.1721 },
  宁夏: { lat: 38.4872, lon: 106.2309 },
  新疆: { lat: 43.8256, lon: 87.6168 },
  香港: { lat: 22.3193, lon: 114.1694 },
  澳门: { lat: 22.1987, lon: 113.5439 },
  台湾: { lat: 25.033, lon: 121.5654 },
};

export default function App() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [selectedLocation, setSelectedLocation] = useState<SelectedLocation>(defaultLocation);
  const [activeWarningKey, setActiveWarningKey] = useState<string>("");

  const load = async (payload: LocationPayload) => {
    setLoading(true);
    setError("");
    try {
      const next = await fetchDashboard(payload);
      setData(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(defaultLocation);
  }, []);

  const submitLocation = () => {
    void load(selectedLocation);
  };

  const handleMapPick = (point: MapPickPoint) => {
    setActiveWarningKey("");
    setSelectedLocation((prev) => ({
      ...prev,
      lat: Number(point.lat.toFixed(4)),
      lon: Number(point.lon.toFixed(4)),
      province: point.province ?? prev.province,
    }));
  };

  const handleWarningClick = (warning: WarningItem) => {
    const warningKey = `${warning.title}-${warning.issue_time}`;
    setActiveWarningKey(warningKey);
    const province = normalizeProvinceName(warning.province);
    const coord = PROVINCE_CAPITAL_COORDS[province];
    const nextLocation: SelectedLocation = {
      lat: coord ? coord.lat : selectedLocation.lat,
      lon: coord ? coord.lon : selectedLocation.lon,
      province,
      address: selectedLocation.address,
    };
    setSelectedLocation(nextLocation);
    void load(nextLocation);
  };

  const handleProvinceFocus = (province: string) => {
    setActiveWarningKey("");
    const normalizedProvince = normalizeProvinceName(province);
    const coord = PROVINCE_CAPITAL_COORDS[normalizedProvince];
    const nextLocation: SelectedLocation = {
      lat: coord ? coord.lat : selectedLocation.lat,
      lon: coord ? coord.lon : selectedLocation.lon,
      province: normalizedProvince,
      address: selectedLocation.address,
    };
    setSelectedLocation(nextLocation);
    void load(nextLocation);
  };

  return (
    <main className="page">
      <header>
        <h1>全国极端天气展示看板</h1>
        <p>当前刷新周期：30 分钟，当前省份优先高亮</p>
        {data?.last_refresh_at && <p>最近刷新：{new Date(data.last_refresh_at).toLocaleString()}</p>}
      </header>

      <LocationPanel value={selectedLocation} onChange={setSelectedLocation} onSubmit={submitLocation} />

      {loading && <p>正在加载数据...</p>}
      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <div className="layout-2">
            <ChinaMapPanel
              focusProvince={selectedLocation.province ?? data.current_province}
              warnings={data.warnings}
              selectedLocation={selectedLocation}
              onMapPick={handleMapPick}
              onProvinceFocus={handleProvinceFocus}
            />
            <WarningList
              warnings={data.warnings}
              focusProvince={selectedLocation.province ?? data.current_province ?? undefined}
              activeWarningKey={activeWarningKey}
              onWarningClick={handleWarningClick}
            />
          </div>
          <ForecastChart points={data.forecast_points} />
        </>
      )}
    </main>
  );
}
