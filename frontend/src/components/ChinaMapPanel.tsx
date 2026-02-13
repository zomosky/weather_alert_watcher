import ReactECharts from "echarts-for-react";
import { useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import chinaGeoJson from "../assets/china.json";
import { MapPickPoint, SelectedLocation, WarningItem } from "../types";

type Props = {
  focusProvince: string | null;
  warnings: WarningItem[];
  selectedLocation: SelectedLocation;
  onMapPick: (point: MapPickPoint) => void;
  onProvinceFocus: (province: string) => void;
};

const LEVEL_SCORE: Record<string, number> = {
  红色: 4,
  橙色: 3,
  黄色: 2,
  蓝色: 1,
};
const FOCUS_EDGE_COLOR = "#111827";
const MAIN_MAP_NAME = "china_main_no_south";
const SOUTH_SEA_MAP_NAME = "south_china_sea";

function warningScore(level: string): number {
  const direct = LEVEL_SCORE[level];
  if (direct) return direct;
  if (level.includes("红")) return 4;
  if (level.includes("橙")) return 3;
  if (level.includes("黄")) return 2;
  return 1;
}

function normalizeProvinceName(name: string): string {
  return name
    .replace(/特别行政区/g, "")
    .replace(/维吾尔自治区|回族自治区|壮族自治区|自治区/g, "")
    .replace(/省|市/g, "")
    .trim();
}

const mainChinaGeoJson = {
  type: "FeatureCollection",
  features: (chinaGeoJson.features as Array<{ properties?: { name?: string } }>).filter(
    (feature) => feature.properties?.name !== "南海诸岛"
  ),
};

if (!echarts.getMap(MAIN_MAP_NAME)) {
  echarts.registerMap(MAIN_MAP_NAME, mainChinaGeoJson as never);
}
echarts.registerMap(MAIN_MAP_NAME, mainChinaGeoJson as never);

const southSeaGeoJson = {
  type: "FeatureCollection",
  features: (chinaGeoJson.features as Array<{ properties?: { name?: string } }>).filter(
    (feature) => feature.properties?.name === "南海诸岛"
  ),
};

if (southSeaGeoJson.features.length > 0 && !echarts.getMap(SOUTH_SEA_MAP_NAME)) {
  echarts.registerMap(SOUTH_SEA_MAP_NAME, southSeaGeoJson as never);
}

export function ChinaMapPanel({ focusProvince, warnings, selectedLocation, onMapPick, onProvinceFocus }: Props) {
  const chartRef = useRef<ReactECharts | null>(null);
  const [mapMessage, setMapMessage] = useState("");
  const [pickMode, setPickMode] = useState(false);
  const mapNames = useMemo(
    () => (mainChinaGeoJson.features as Array<{ properties: { name: string } }>).map((f) => f.properties.name),
    []
  );

  const normalizedToMapName = useMemo(() => {
    const index = new Map<string, string>();
    mapNames.forEach((name) => {
      index.set(normalizeProvinceName(name), name);
    });
    return index;
  }, [mapNames]);

  const mapNameForProvince = (province: string): string => {
    const normalized = normalizeProvinceName(province);
    return normalizedToMapName.get(normalized) ?? province;
  };

  const provinceRisk = useMemo(() => {
    const map = new Map<string, number>();
    warnings.forEach((item) => {
      const mapName = mapNameForProvince(item.province);
      const score = warningScore(item.level);
      const prev = map.get(mapName) ?? 0;
      if (score > prev) map.set(mapName, score);
    });
    return map;
  }, [warnings, normalizedToMapName]);

  const highlightedName = focusProvince ? mapNameForProvince(focusProvince) : null;
  const mapSeriesData = useMemo(() => {
    const base = mapNames
      .filter((name) => name !== highlightedName)
      .map((name) => ({
        name,
        value: provinceRisk.get(name) ?? 0,
      }));
    if (!highlightedName) return base;
    return [
      ...base,
      {
        name: highlightedName,
        value: provinceRisk.get(highlightedName) ?? 0,
        itemStyle: {
          borderColor: FOCUS_EDGE_COLOR,
          borderWidth: 3,
          shadowBlur: 6,
          shadowColor: "rgba(0, 0, 0, 0.45)",
        },
      },
    ];
  }, [highlightedName, mapNames, provinceRisk]);

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (params: { name: string; value?: number }) => {
        const rawValue = provinceRisk.get(params.name) ?? 0;
        if (highlightedName === params.name) {
          const highlightLabel =
            rawValue >= 4 ? "红色" : rawValue === 3 ? "橙色" : rawValue === 2 ? "黄色" : rawValue === 1 ? "蓝色" : "无";
          return `${params.name}<br/>当前为边界高亮模式，风险填充保持原等级色<br/>风险等级：${highlightLabel}`;
        }
        const val = params.value ?? 0;
        if (val <= 0) return `${params.name}<br/>当前无预警数据`;
        const label = val >= 4 ? "红色" : val === 3 ? "橙色" : val === 2 ? "黄色" : "蓝色";
        return `${params.name}<br/>最高预警等级：${label}`;
      },
    },
    visualMap: {
      seriesIndex: 0,
      min: 0,
      max: 4,
      orient: "horizontal",
      left: "center",
      bottom: 6,
      text: ["高风险", "低风险"],
      pieces: [
        { value: 4, label: "红色", color: "#d90429" },
        { value: 3, label: "橙色", color: "#f77f00" },
        { value: 2, label: "黄色", color: "#fcbf49" },
        { value: 1, label: "蓝色", color: "#1d4ed8" },
        { value: 0, label: "无", color: "#d1d5db" },
      ],
    },
    series: [
      {
        name: "省级风险",
        type: "map",
        map: MAIN_MAP_NAME,
        selectedMode: false,
        roam: true,
        zoom: 1.2,
        scaleLimit: { min: 1.1, max: 6 },
        label: { show: true, fontSize: 10, color: "#111827", fontWeight: 600 },
        itemStyle: {
          borderColor: "rgba(255, 255, 255, 0.75)",
          borderWidth: 0.8,
          areaColor: "#d1d5db",
        },
        regions: [
          {
            name: "南海诸岛",
            itemStyle: {
              areaColor: "transparent",
              borderColor: "transparent",
            },
            label: { show: false },
          },
        ],
        emphasis: {
          label: { color: "#111827", fontWeight: "bold" },
          itemStyle: {
            borderColor: "#1f2937",
            borderWidth: 1.5,
          },
        },
        select: {
          disabled: true,
          itemStyle: {
            borderColor: FOCUS_EDGE_COLOR,
            borderWidth: 4,
          },
        },
        data: mapSeriesData,
      },
      {
        name: "当前位置",
        type: "scatter",
        coordinateSystem: "map",
        data: [[selectedLocation.lon, selectedLocation.lat]],
        symbol: "pin",
        symbolSize: 28,
        itemStyle: { color: "#ef4444" },
        label: {
          show: true,
          formatter: "我",
          color: "#fff",
          fontWeight: "bold",
          fontSize: 10,
        },
        tooltip: {
          formatter: () => `当前位置<br/>${selectedLocation.lat.toFixed(4)}, ${selectedLocation.lon.toFixed(4)}`,
        },
        zlevel: 20,
      },
    ],
  };

  const southSeaOption = {
    animation: false,
    tooltip: { show: false },
    series: [
      {
        type: "map",
        map: SOUTH_SEA_MAP_NAME,
        roam: false,
        label: { show: false },
        itemStyle: {
          areaColor: "rgba(148, 163, 184, 0.08)",
          borderColor: "#64748b",
          borderWidth: 1,
        },
        emphasis: {
          disabled: true,
        },
      },
    ],
  };

  const onEvents = {
    click: (params: { componentType?: string; seriesType?: string; name?: string; event?: { offsetX?: number; offsetY?: number } }) => {
      if (params.componentType !== "series" || params.seriesType !== "map") {
        return;
      }
      const clickedProvince = params.name ? normalizeProvinceName(params.name) : "";
      if (clickedProvince) {
        onProvinceFocus(clickedProvince);
      }
      if (!pickMode) {
        setMapMessage(`已切换到 ${clickedProvince || "当前"} 省份（已自动刷新）`);
        return;
      }
      const chart = chartRef.current?.getEchartsInstance();
      const x = params.event?.offsetX;
      const y = params.event?.offsetY;
      if (!chart || x === undefined || y === undefined) {
        setMapMessage("该区域无法取点，请重试。");
        return;
      }
      const result = chart.convertFromPixel({ seriesIndex: 0 }, [x, y]) as number[] | undefined;
      if (!result || result.length < 2 || Number.isNaN(result[0]) || Number.isNaN(result[1])) {
        setMapMessage("该区域无法取点，请点击省份区域。");
        return;
      }
      onMapPick({
        lon: result[0],
        lat: result[1],
        province: clickedProvince || undefined,
      });
      setMapMessage(`已回填坐标：${result[1].toFixed(4)}, ${result[0].toFixed(4)}（未自动刷新）`);
    },
  };

  return (
    <section className="card">
      <h3>全国省级预警地图</h3>
      <p className="meta focus-meta">
        当前省份：{focusProvince ?? "未指定"}（已边界高亮）
      </p>
      <p className="meta">
        当前位置图钉：{selectedLocation.lat.toFixed(4)}, {selectedLocation.lon.toFixed(4)}
      </p>
      <div className="map-toolbar">
        <button
          type="button"
          onClick={() => {
            setPickMode((prev) => !prev);
            setMapMessage((prev) => {
              if (prev.includes("已回填坐标")) return prev;
              return !pickMode ? "选点模式已开启，请点击省份区域回填坐标。" : "选点模式已关闭。";
            });
          }}
        >
          {pickMode ? "关闭地图自选位置" : "开启地图自选位置"}
        </button>
        <button
          type="button"
          onClick={() => {
            const chart = chartRef.current?.getEchartsInstance();
            if (!chart) return;
            chart.clear();
            chart.setOption(option, true);
          }}
        >
          一键还原视图
        </button>
      </div>
      {mapMessage && <p className="meta geo-msg">{mapMessage}</p>}
      <div className="china-map-wrap">
        <ReactECharts ref={chartRef} option={option} onEvents={onEvents} style={{ height: 520 }} />
        {southSeaGeoJson.features.length > 0 && (
          <div className="south-sea-inset">
            <p className="meta inset-title">南海诸岛</p>
            <ReactECharts option={southSeaOption} style={{ height: 110 }} />
          </div>
        )}
      </div>
      <div className="map-legend-custom map-legend-bottom" aria-label="地图边界高亮图例">
        <span className="legend-item">
          <span className="legend-swatch-outline" />
          当前省份（仅边界高亮）
        </span>
      </div>
    </section>
  );
}
