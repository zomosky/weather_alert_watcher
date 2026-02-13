from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

from app.models import ForecastPoint, WarningRecord
from app.providers.base import IngestionContext


class MockWeatherProvider:
    """Mock provider for local development and fallback."""

    def fetch_warnings(self, context: IngestionContext) -> list[WarningRecord]:
        now = datetime.now(timezone.utc)
        scenarios = [
            ("台风红色预警（演示）", "红色", "台风", "福建", 15, 10, "沿海风力可达13级以上，注意海上作业安全。"),
            ("暴雨橙色预警（演示）", "橙色", "暴雨", "广东", 25, 12, "部分地区小时雨强较大，低洼路段有内涝风险。"),
            ("高温红色预警（演示）", "红色", "高温", "新疆", 40, 18, "白天气温可超过40°C，建议减少午后户外活动。"),
            ("强对流黄色预警（演示）", "黄色", "强对流", "湖北", 35, 9, "局地短时强降水、雷暴大风和冰雹概率升高。"),
            ("雷电黄色预警（演示）", "黄色", "雷电", "江苏", 30, 8, "午后到夜间雷电活动频繁，注意临时搭建物安全。"),
            ("沙尘蓝色预警（演示）", "蓝色", "沙尘", "内蒙古", 45, 14, "局地有扬沙或浮尘天气，能见度下降。"),
            ("寒潮蓝色预警（演示）", "蓝色", "寒潮", "黑龙江", 55, 16, "未来48小时降温显著，请提前做好保暖防冻。"),
            ("大风橙色预警（演示）", "橙色", "大风", "北京", 20, 7, "阵风较强，部分高空设施有坠落风险。"),
            ("暴雪黄色预警（演示）", "黄色", "暴雪", "青海", 65, 15, "山区降雪增强，道路湿滑结冰风险提高。"),
            ("干旱蓝色预警（演示）", "蓝色", "干旱", "云南", 75, 20, "部分区域降水持续偏少，农业用水压力上升。"),
        ]

        warnings: list[WarningRecord] = []
        for title, level, hazard_type, province, minutes_ago, duration_hours, summary in scenarios:
            warnings.append(
                WarningRecord(
                    source="MockScenario",
                    title=title,
                    level=level,
                    hazard_type=hazard_type,
                    province=province,
                    issue_time=now - timedelta(minutes=minutes_ago),
                    expires_at=now + timedelta(hours=duration_hours),
                    detail_url="https://www.nmc.cn/publish/weather-bulletin/index.htm",
                    summary=summary,
                    confidence=1.0,
                )
            )

        # Keep the current province always visible in demos.
        warnings.append(
            WarningRecord(
                source="MockScenario",
                title=f"{context.province}地区综合风险提示（演示）",
                level="黄色",
                hazard_type="综合风险",
                province=context.province,
                issue_time=now - timedelta(minutes=10),
                expires_at=now + timedelta(hours=6),
                detail_url="https://www.nmc.cn/publish/weatherperday/index.htm",
                summary="该提示用于演示当前省份高亮与预警联动效果。",
                confidence=0.95,
            )
        )
        return warnings

    def fetch_forecast(self, context: IngestionContext) -> list[ForecastPoint]:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        points: list[ForecastPoint] = []
        for h in range(0, 24 * 7, 3):
            t = now + timedelta(hours=h)
            daily_phase = (h % 24) / 24
            temperature = 22 + 8 * math.sin(2 * math.pi * daily_phase)
            humidity = 65 + 20 * math.cos(2 * math.pi * daily_phase)
            points.append(
                ForecastPoint(
                    lat=round(context.lat, 4),
                    lon=round(context.lon, 4),
                    location_label=context.label,
                    province=context.province,
                    forecast_time=t,
                    temperature_c=round(temperature, 1),
                    humidity_pct=max(15.0, min(100.0, round(humidity, 1))),
                    source="MockForecast",
                )
            )
        return points
