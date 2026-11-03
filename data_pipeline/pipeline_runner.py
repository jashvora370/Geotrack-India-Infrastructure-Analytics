"""
GeoTrack India — Pipeline Runner
=================================
Orchestrates end-to-end data collection, preprocessing, change detection,
and analytical synthesis for a target Indian region.

Usage:
    python pipeline_runner.py --region "Pune" --state "Maharashtra" --level city --skip-gee
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Tuple

# Set up paths
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR.parent / "backend"))

from collectors.osm_collector import OsmCollector
from collectors.ghsl_collector import GhslCollector
from processors.road_network_processor import RoadNetworkProcessor
from processors.change_detector import ChangeDetector
from processors.width_estimator import WidthEstimator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("pipeline_runner")

# Default study area coordinates: Pune Metropolitan Region
PUNE_BBOX = (73.75, 18.35, 74.05, 18.65)  # min_lon, min_lat, max_lon, max_lat


def parse_args():
    parser = argparse.ArgumentParser(description="GeoTrack India Data Pipeline Runner")
    parser.add_argument("--region", type=str, default="Pune", help="Region name")
    parser.add_argument("--state", type=str, default="Maharashtra", help="State name")
    parser.add_argument("--level", type=str, default="city", choices=["state", "district", "city", "ward", "custom"])
    parser.add_argument("--bbox", type=str, default="73.75,18.35,74.05,18.65", help="min_lon,min_lat,max_lon,max_lat")
    parser.add_argument("--years", nargs="+", type=int, default=[2016, 2021, 2026], help="Target years")
    parser.add_argument("--skip-gee", action="store_true", default=True, help="Skip Google Earth Engine calls")
    parser.add_argument("--output-dir", type=str, default="./data/processed", help="Output directory")
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        coords = [float(x.strip()) for x in args.bbox.split(",")]
        bbox: Tuple[float, float, float, float] = (coords[0], coords[1], coords[2], coords[3])
    except Exception as exc:
        logger.error("Invalid bbox: %s. Defaulting to Pune.", exc)
        bbox = PUNE_BBOX

    logger.info("=================================================================")
    logger.info("   GEOTRACK INDIA: DATA PIPELINE INITIALISING")
    logger.info("=================================================================")
    logger.info("Region: %s, %s (%s)", args.region, args.state, args.level)
    logger.info("Bounding box: %s", bbox)
    logger.info("Target years: %s", args.years)

    # 1. Collectors
    osm_col = OsmCollector(cache_dir=str(CURRENT_DIR / "cache"))
    width_est = WidthEstimator()
    rnp = RoadNetworkProcessor()
    detector = ChangeDetector()

    year_gdfs = {}

    # 2. Collect & Process Road Networks
    for yr in args.years:
        logger.info("--> Collecting OSM snapshot for year %d...", yr)
        raw_gdf = osm_col.collect_historical_snapshot(bbox=bbox, year=yr)
        if raw_gdf.empty:
            logger.warning("Empty or fallback snapshot for year %d.", yr)
        
        proc_gdf = rnp.process_raw_network(raw_gdf)
        proc_gdf = width_est.process_network(proc_gdf)
        year_gdfs[yr] = proc_gdf

        # Export GeoJSON
        geojson_path = out_dir / f"roads_{args.region.lower()}_{yr}.geojson"
        try:
            if not proc_gdf.empty:
                proc_gdf.to_file(str(geojson_path), driver="GeoJSON")
                logger.info("Saved %s (%d segments)", geojson_path.name, len(proc_gdf))
        except Exception as exc:
            logger.warning("Could not write GeoJSON file: %s", exc)

    # 3. Change Detection (2016 vs 2026)
    if 2016 in year_gdfs and 2026 in year_gdfs:
        logger.info("--> Executing 10-year road network change detection (2016 -> 2026)...")
        gdf_16 = year_gdfs[2016]
        gdf_26 = year_gdfs[2026]
        change_report = detector.generate_change_report(gdf_16, gdf_26)

        report_file = out_dir / f"change_detection_{args.region.lower()}_2016_2026.json"
        with open(report_file, "w") as f:
            json.dump(change_report, f, indent=2)
        logger.info("Change detection report saved to %s", report_file)

    # 4. GHSL Built-Up Data
    logger.info("--> Processing GHSL built-up indicators...")
    try:
        ghsl_col = GhslCollector(data_dir=str(CURRENT_DIR / "data" / "ghsl"))
        ghsl_summary = ghsl_col.get_built_up_summary(bbox)
        ghsl_file = out_dir / f"builtup_{args.region.lower()}.json"
        with open(ghsl_file, "w") as f:
            json.dump(ghsl_summary, f, indent=2)
        logger.info("GHSL summary saved to %s", ghsl_file)
    except Exception as exc:
        logger.warning("GHSL processing skipped/fallback: %s", exc)

    logger.info("=================================================================")
    logger.info("   GEOTRACK INDIA PIPELINE EXECUTION COMPLETED")
    logger.info("=================================================================")


if __name__ == "__main__":
    main()
