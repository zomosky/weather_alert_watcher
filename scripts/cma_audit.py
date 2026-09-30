"""Reproducible official-page audit. Run with PYTHONPATH=backend uv run python."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.providers.cma_bulletins import HEADERS, parse_bulletin
from app.providers.cma_local_signals import CmaLocalSignalProvider
from app.providers.cma_provider import warnings_from_bulletins


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", help="Replay the original before.json/raw capture")
    parser.add_argument("--as-of", help="Explicit UTC ISO time for offline replay")
    parser.add_argument("--output", default="artifacts/cma-audit/live")
    args = parser.parse_args()
    output = Path(args.output)
    (output / "raw").mkdir(parents=True, exist_ok=True)
    now = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc)
    if now.tzinfo is None:
        parser.error("--as-of must include timezone")
    settings = get_settings()

    def collect(url):
        entry = {"url": url}
        try:
            if urlparse(url).hostname not in {"nmc.cn", "www.nmc.cn"}:
                raise ValueError("Unverified source domain")
            response = httpx.get(url, headers=HEADERS, timeout=settings.http_timeout_seconds, follow_redirects=True)
            response.raise_for_status()
            if response.url.host not in {"nmc.cn", "www.nmc.cn"}:
                raise ValueError("Unverified redirected source")
            filename = sha256(url.encode()).hexdigest()[:12] + ".html"
            (output / "raw" / filename).write_text(response.text)
            entry["html"] = response.text
            entry["raw_file"] = filename
        except Exception as exc:
            entry["fetch_error"] = type(exc).__name__
        return entry

    if args.offline:
        root = Path(args.offline)
        inputs = [{"url": item["url"], "html": (root / "raw" / item["filename"]).read_text(),
                   "raw_file": item["filename"], "old_parser": item.get("old_parser")}
                  for item in json.loads((root / "before.json").read_text()) if item.get("writing")]
    else:
        with ThreadPoolExecutor(max_workers=5) as pool:
            inputs = list(pool.map(collect, settings.cma_source_urls_list))
    report = []
    for item in inputs:
        entry = {key: value for key, value in item.items() if key != "html"}
        try:
            record = parse_bulletin(item["html"], item["url"], now)
            rows = warnings_from_bulletins([record], now=now)
            assert record.kind not in {"cancelled_warning", "outlook"} or not rows
            entry.update(title=record.title, kind=record.kind, level=record.warning_level,
                         published_at=record.published_at.isoformat() if record.published_at else None,
                         source_sha256=sha256(item["html"].encode()).hexdigest(),
                         regions=[{"province": w.province, "hazard": w.hazard_type, "level": w.level,
                                   "forecast_until": w.expires_at.isoformat() if w.expires_at else None} for w in rows])
        except Exception as exc:
            entry["parse_error"] = type(exc).__name__
        report.append(entry)
    local = None
    if not args.offline and settings.cma_local_signals_enabled:
        try:
            rows = CmaLocalSignalProvider(settings).fetch()
            local = {"records": len(rows), "unique_ids": len({b.id for b in rows}),
                     "provinces": sorted({p for b in rows for p in b.provinces}),
                     "note": "Complete website pagination; not an atomic or lifecycle-authoritative snapshot"}
        except Exception as exc:
            local = {"error": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}
    result = {"verified_at": datetime.now(timezone.utc).isoformat(), "sample_as_of": now.isoformat(),
              "mode": "offline" if args.offline else "live", "products": report, "local_index": local}
    (output / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"products": len(report), "recognised": sum("parse_error" not in r for r in report),
                      "warning_regions": sum(len(r.get("regions", [])) for r in report), "local_index": local}, ensure_ascii=False))
    if any("parse_error" in r or "fetch_error" in r for r in report) or local and "error" in local:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
