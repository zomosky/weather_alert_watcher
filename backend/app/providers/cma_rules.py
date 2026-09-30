"""Conservative rules for explicit NMC publication statements and forecast areas."""
from datetime import datetime, timedelta, timezone
import re

from app.services.province import PROVINCES

CST = timezone(timedelta(hours=8))
COLOUR = r"红色|橙色|黄色|蓝色"
HAZARDS = [
    ("台风", ("台风", "热带风暴")), ("暴雨", ("暴雨",)),
    ("降水", ("大雨", "强降水", "降雨")), ("暴雪", ("暴雪",)),
    ("降雪", ("降雪", "雨夹雪", "大雪")), ("大风", ("大风", "雷雨强风")),
    ("沙尘", ("沙尘", "扬沙", "浮尘")), ("冰雹", ("冰雹",)),
    ("强对流", ("强对流",)), ("雷电", ("雷电", "雷暴")),
    ("高温", ("高温",)), ("寒潮", ("寒潮",)), ("低温", ("低温", "降温")),
    ("大雾", ("大雾",)), ("干旱", ("干旱",)),
    ("冰冻", ("冰冻", "冻雨", "冰粒")), ("道路结冰", ("道路结冰",)),
    ("霜冻", ("霜冻",)), ("霾", ("霾",)),
    ("山洪", ("山洪",)), ("地质灾害", ("地质灾害", "滑坡", "泥石流")),
    ("河流洪水", ("河流洪水",)), ("渍涝", ("渍涝", "内涝")),
    ("森林火险", ("森林火险",)), ("草原火险", ("草原火险",)),
]
RISK_HAZARDS = {"山洪", "地质灾害", "河流洪水", "渍涝"}
PROVINCE_ALIASES = {"四川": ("川西", "川东", "川南", "川北"), "陕西": ("陕北", "陕南", "关中"), "内蒙古": ("内蒙",)}


def extract_provinces(text: str) -> list[str]:
    return [p.name for p in PROVINCES if
            (bool(re.search(r"(?<!青)海南", text)) if p.name == "海南" else p.name in text)
            or any(alias in text for alias in PROVINCE_ALIASES.get(p.name, ()))]


def title_hazard(title: str) -> str | None:
    matches = [(len(word), name) for name, words in HAZARDS for word in words if word in title]
    return max(matches, default=(0, None), key=lambda item: item[0])[1]


def warning_statement(title: str, body: str) -> tuple[str, str | None, str | None]:
    lead = re.sub(r"\s+", "", body.splitlines()[0] if body else "").split("：")[0][:240]
    official_lead = bool(re.match(r"(?:中央气象台|水利部|自然资源部|中国气象局)", lead))
    statement = lead if official_lead and re.search(r"发布|解除|取消|停止", lead) and "预警" in lead else title
    if "预警" in statement and any(word in statement for word in ("解除", "停止", "取消")):
        return "cancelled_warning", None, statement
    colour = re.search(rf"({COLOUR})[\u4e00-\u9fff]{{0,24}}预警", statement)
    if colour:
        return "official_warning", colour.group(1), statement
    if official_lead and "发布" in statement and "预警" in statement:
        regions = coloured_regions(body.split("防御指南")[0])
        if regions:
            score = {"蓝色": 1, "黄色": 2, "橙色": 3, "红色": 4}
            return "official_warning", max((level for _, level, _ in regions), key=score.get), statement
    return "bulletin", None, None


TIME_RANGE = re.compile(
    r"(?:(?P<y1>20\d{2})年)?(?P<m1>\d{1,2})月(?P<d1>\d{1,2})日(?P<h1>\d{1,2})时(?:(?P<min1>\d{1,2})分)?"
    r"(?:至|到|—|–|-)(?:(?P<y2>20\d{2})年)?(?:(?P<m2>\d{1,2})月)?(?P<d2>\d{1,2})日(?P<h2>\d{1,2})时(?:(?P<min2>\d{1,2})分)?"
)


def forecast_periods(text: str, published: datetime) -> list[tuple[str, datetime]]:
    """Return region text plus its explicitly stated end, with month/year rollover."""
    compact = re.sub(r"\s+", "", text)
    matches = list(TIME_RANGE.finditer(compact))
    result = []
    local = published.astimezone(CST)
    for index, match in enumerate(matches):
        values = match.groupdict()
        try:
            years = [int(values["y1"])] if values["y1"] else [local.year - 1, local.year, local.year + 1]
            starts = []
            for year_candidate in years:
                try:
                    starts.append(datetime(year_candidate, int(values["m1"]), int(values["d1"]), int(values["h1"]), int(values["min1"] or 0), tzinfo=CST))
                except ValueError:
                    continue
            if not starts:
                continue
            start = min(starts, key=lambda item: abs(item - local))
            month = int(values["m2"] or start.month)
            year = int(values["y2"] or start.year)
            if not values["m2"] and int(values["d2"]) < start.day:
                month = start.month % 12 + 1
                year += start.month == 12
            elif values["m2"] and month < start.month and not values["y2"]:
                year += 1
            end = datetime(year, month, int(values["d2"]), int(values["h2"]), int(values["min2"] or 0), tzinfo=CST)
            if not start < end <= start + timedelta(days=14):
                continue
            segment = compact[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(compact)]
            result.append((segment, end.astimezone(timezone.utc)))
        except ValueError:
            continue
    return result


def coloured_regions(text: str) -> list[tuple[str, str, str]]:
    result = []
    for match in re.finditer(rf"([^。；\n（）()]+)[（(]({COLOUR})预警[）)]", text):
        region, colour = match.groups()
        for province in extract_provinces(region):
            result.append((province, colour, region))
    return result
