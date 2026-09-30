"""Reproducible live API/Nginx/data acceptance; UI evidence accompanies output."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", default="artifacts/validation")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    checks = []

    def request(path, payload=None):
        encoded = json.dumps(payload).encode() if payload else None
        req = Request(args.base_url + path, data=encoded, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=50) as response:
            return response.read()

    index = request("/").decode()
    assert "/@vite/client" not in index and "/assets/" in index
    checks.append("Nginx serves built static assets")
    assert json.loads(request("/api/v1/health"))["status"] == "ok"
    assert json.loads(request("/api/v1/ready"))["status"] == "ready"
    checks.append("Nginx preserves /api/v1 paths and database is ready")
    snapshots = []
    for province, lat, lon in [("北京", 39.9042, 116.4074), ("四川", 30.5728, 104.0668)]:
        data = json.loads(request("/api/v1/dashboard", {"lat": lat, "lon": lon, "province": province}))
        assert data["current_province"] == province
        assert data["bulletins"], "No live CMA disclosures"
        assert data["forecast_points"], f"No live forecast for {province}"
        assert data["forecast_source"] == "OpenMeteo", "Forecast is not live OpenMeteo"
        assert data["forecast_location"] == province
        assert not any(w["source"].startswith("Mock") for w in data["warnings"])
        for item in data["bulletins"]:
            assert item["source_url"].startswith("https://www.nmc.cn/")
            assert datetime.fromisoformat(item["fetched_at"].replace("Z", "+00:00")).tzinfo
            if item["kind"] == "outlook":
                assert item["warning_level"] is None
            if item["warning_level"]:
                assert item["published_at"] and item["warning_level"] + "预警" in item["title"]
        filename = "beijing.json" if province == "北京" else "sichuan.json"
        (output / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2))
        snapshots.append({"province": province, "bulletins": len(data["bulletins"]), "forecast_points": len(data["forecast_points"]), "warnings": len(data["warnings"]), "sources": [{"name": s["name"], "state": s["state"]} for s in data["source_statuses"]]})
    checks.append("Two locations return live forecasts and traceable disclosures without mock data")
    checks.append("Outlooks and bulletin topics do not infer official warning colours")
    report = {"verified_at": datetime.now(timezone.utc).isoformat(), "base_url": args.base_url, "checks": checks, "snapshots": snapshots}
    (output / "api-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    hashes = {p.name: sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file() and p.name != "checksums.json"}
    (output / "checksums.json").write_text(json.dumps(hashes, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
