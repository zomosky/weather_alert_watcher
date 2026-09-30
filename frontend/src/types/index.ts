export type LocationPayload = {
  lat: number;
  lon: number;
  address?: string;
  province?: string;
};

export type SelectedLocation = LocationPayload;

export type MapPickPoint = {
  lat: number;
  lon: number;
  province?: string;
};

export type ProvinceItem = {
  name: string;
  pinyin_initial: string;
  highlighted: boolean;
};

export type WarningItem = {
  source: string;
  title: string;
  level: string;
  hazard_type: string;
  province: string;
  issue_time: string;
  expires_at: string | null;
  detail_url: string;
  summary: string;
  confidence: number;
  is_ai_augmented: boolean;
};

export type ProvinceCoord = {
  lat: number;
  lon: number;
};

export type ForecastPoint = {
  forecast_time: string;
  temperature_c: number;
  humidity_pct: number;
};

export type DashboardResponse = {
  current_province: string | null;
  provinces: ProvinceItem[];
  warnings: WarningItem[];
  forecast_points: ForecastPoint[];
  last_refresh_at: string | null;
  refresh_interval_minutes: number;
  bulletins: BulletinItem[];
  local_signals: BulletinItem[];
  source_statuses: SourceStatusItem[];
  forecast_source: string | null;
  forecast_location: string | null;
};

export type BulletinItem = {
  id: string;
  source: string;
  source_url: string;
  title: string;
  summary: string;
  provinces: string[];
  hazard_types: string[];
  kind: "bulletin" | "outlook" | "official_warning" | "cancelled_warning" | "risk_notice" | "local_signal";
  warning_level: string | null;
  published_at: string | null;
  fetched_at: string;
};

export type SourceStatusItem = {
  name: string;
  provider: string;
  state: "ok" | "degraded" | "stale" | "waiting" | "disabled" | "demo";
  last_success_at: string | null;
  last_attempt_at: string | null;
  message: string | null;
  source_url: string | null;
};
