NMC_WARNING_PATHS = (
    "wind", "strong_convection", "downpour", "typhoon", "megatemperature", "fog",
    "dust", "blizzard", "cold", "frozen", "drought", "low-temperature",
)
NMC_ADDITIONAL_PATHS = (
    "mountainflood.html", "geohazard.html", "waterlogging.html", "swdz/zxhlhsqxyj.html",
    "bulletin/swpc.html", "environment/forestfire-doc.html",
)
DEFAULT_WARNING_URLS = ",".join(
    [f"https://www.nmc.cn/publish/country/warning/{name}.html" for name in NMC_WARNING_PATHS]
    + [f"https://www.nmc.cn/publish/{path}" for path in NMC_ADDITIONAL_PATHS]
)
