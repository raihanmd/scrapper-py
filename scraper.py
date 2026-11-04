#!/usr/bin/env python3
"""Ambil data usaha jasa wedding sekitar Ciamis dari Google Maps, simpan ke JSON."""

import argparse
import json
from pathlib import Path

from crawler import crawl

OUTPUT_NAME = "wedding-organizer-ciamis.json"


def save(records, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / OUTPUT_NAME
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser(description="Crawler Google Maps: usaha jasa wedding sekitar Ciamis.")
    parser.add_argument("--config", type=Path, default=Path("gmaps-config.json"),
                        help="file konfigurasi kata kunci & pusat pencarian")
    parser.add_argument("--keywords", default=None,
                        help="daftar kata kunci pisah koma, mengalahkan isi config")
    parser.add_argument("--region", default=None, help="label wilayah untuk laporan")
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--no-pin", action="store_true",
                        help="jangan paku pencarian ke koordinat pusat Ciamis")
    args = parser.parse_args()

    config_path = args.config if args.config.exists() else None
    conf = (json.loads(config_path.read_text(encoding="utf-8"))
            if config_path else {"keywords": [], "center": {"lat": -7.3261, "lon": 108.3534}, "zoom": 12})

    keywords = [k.strip() for k in (args.keywords.split(",") if args.keywords else conf.get("keywords", [])) if k.strip()]
    if not keywords:
        raise SystemExit("Tidak ada kata kunci. Isi gmaps-config.json atau pakai --keywords.")

    center = conf.get("center", {})
    lat = None if args.no_pin else center.get("lat")
    lon = None if args.no_pin else center.get("lon")
    region_label = args.region or conf.get("region", "Ciamis")

    print(f"Mencari jasa wedding sekitar {region_label} dengan {len(keywords)} kata kunci ...")
    records = crawl(keywords, lat=lat, lon=lon, zoom=conf.get("zoom", 12))
    out = save(records, args.output_dir)
    print(f"Tersimpan {len(records)} bisnis unik -> {out}")


if __name__ == "__main__":
    main()