from dataclasses import dataclass


@dataclass(frozen=True)
class ProvinceMeta:
    name: str
    pinyin_initial: str


PROVINCES = [
    ProvinceMeta("安徽", "A"), ProvinceMeta("北京", "B"), ProvinceMeta("重庆", "C"), ProvinceMeta("福建", "F"),
    ProvinceMeta("甘肃", "G"), ProvinceMeta("广东", "G"), ProvinceMeta("广西", "G"), ProvinceMeta("贵州", "G"),
    ProvinceMeta("海南", "H"), ProvinceMeta("河北", "H"), ProvinceMeta("黑龙江", "H"), ProvinceMeta("河南", "H"),
    ProvinceMeta("湖北", "H"), ProvinceMeta("湖南", "H"), ProvinceMeta("江苏", "J"), ProvinceMeta("江西", "J"),
    ProvinceMeta("吉林", "J"), ProvinceMeta("辽宁", "L"), ProvinceMeta("内蒙古", "N"), ProvinceMeta("宁夏", "N"),
    ProvinceMeta("青海", "Q"), ProvinceMeta("山东", "S"), ProvinceMeta("上海", "S"), ProvinceMeta("山西", "S"),
    ProvinceMeta("陕西", "S"), ProvinceMeta("四川", "S"), ProvinceMeta("天津", "T"), ProvinceMeta("西藏", "X"),
    ProvinceMeta("新疆", "X"), ProvinceMeta("云南", "Y"), ProvinceMeta("浙江", "Z"), ProvinceMeta("香港", "X"),
    ProvinceMeta("澳门", "A"), ProvinceMeta("台湾", "T"),
]

PROVINCE_LOOKUP = {item.name: item for item in PROVINCES}


def sorted_provinces(current_province: str | None) -> list[ProvinceMeta]:
    provinces = sorted(PROVINCES, key=lambda p: (p.pinyin_initial, p.name))
    if current_province and current_province in PROVINCE_LOOKUP:
        current = PROVINCE_LOOKUP[current_province]
        provinces = [current] + [p for p in provinces if p.name != current.name]
    return provinces
