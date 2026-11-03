# app/services/osm_service.py
"""
OpenStreetMap / ohsome data-fetching service for GeoTrack India.

This module provides async wrappers around:
    1. **osmnx** – for current (latest) road network retrieval.
    2. **ohsome API** – for historical road network snapshots and time-series.

OSM Completeness Caveat
-----------------------
OSM is a volunteer-contributed dataset.  Coverage in India has grown
dramatically since 2015, meaning that apparent road "growth" between an
older snapshot (e.g. 2016) and a recent one (e.g. 2026) is a mixture of:
    a) genuine new road construction, and
    b) mapping backfill – roads that existed in 2016 but were only
       added to OSM later.

The :func:`ohsome_road_stats` function returns a ``data_quality_note``
flag whenever the year-over-year growth in a region is implausibly high
(> 30 % in a single year), suggesting that mapping activity, not road
construction, dominates the change signal.

ohsome API Reference
--------------------
Base URL : https://api.ohsome.org/v1
Endpoints used:
    POST /elements/length   – total road length per time step
    POST /elements/geometry – GeoJSON snapshot at a point in time

Authentication: none required for public endpoints.
Rate limits   : apply reasonable back-off (ohsome is a public research API).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, shape
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

OHSOME_BASE_URL = "https://api.ohsome.org/v1"

# IRC standard widths (metres) keyed by OSM highway tag value.
IRC_WIDTHS: Dict[str, float] = {
    "motorway": 26.5,
    "motorway_link": 9.0,
    "trunk": 18.5,
    "trunk_link": 9.0,
    "primary": 12.0,
    "primary_link": 7.5,
    "secondary": 9.0,
    "secondary_link": 7.5,
    "tertiary": 7.5,
    "tertiary_link": 5.5,
    "unclassified": 5.5,
    "residential": 5.5,
    "service": 4.0,
    "living_street": 4.0,
    "track": 3.5,
    "path": 2.0,
    "footway": 2.0,
    "cycleway": 2.0,
    "road": 5.5,
}


# ─────────────────────────────────────────────────────────────────────────────
# Road classification helpers
# ─────────────────────────────────────────────────────────────────────────────

def classify_road(highway_tag: Optional[str]) -> str:
    """
    Map an OSM ``highway`` tag to an Indian road classification string.

    The classification follows the Indian road hierarchy:
        NH (National Highway), SH (State Highway), MDR (Major District Road),
        ODR (Other District Road), VR (Village Road), Service / Access road.

    Args:
        highway_tag: The value of the OSM ``highway`` key (e.g. ``"primary"``).

    Returns:
        A human-readable road classification label.
    """
    mapping = {
        "motorway": "National Highway / Expressway",
        "motorway_link": "National Highway / Expressway (Link)",
        "trunk": "National Highway",
        "trunk_link": "National Highway (Link)",
        "primary": "State Highway",
        "primary_link": "State Highway (Link)",
        "secondary": "Major District Road",
        "secondary_link": "Major District Road (Link)",
        "tertiary": "Other District Road",
        "tertiary_link": "Other District Road (Link)",
        "unclassified": "Village Road",
        "residential": "Residential / Urban Local Road",
        "service": "Service / Access Road",
        "living_street": "Living Street",
        "track": "Farm / Forest Track",
        "path": "Footpath",
        "footway": "Footway",
        "cycleway": "Cycleway",
        "road": "Unclassified Road",
    }
    return mapping.get(str(highway_tag).lower(), "Other / Unknown")


def estimate_road_width(
    highway_tag: Optional[str],
    lanes: Optional[int] = None,
    width_attr: Optional[float] = None,
) -> Tuple[float, float, str]:
    """
    Estimate road carriageway width in metres.

    Resolution order:
        1. Use the explicit ``width`` OSM attribute if available.
        2. Derive from ``lanes`` × IRC standard lane width (3.5 m) + shoulders.
        3. Fall back to IRC standards for the ``highway`` tag.

    Args:
        highway_tag:  OSM ``highway`` tag value.
        lanes:        Number of lanes from OSM ``lanes`` tag (may be None).
        width_attr:   Explicit ``width`` attribute in metres (may be None).

    Returns:
        Tuple of (width_m, confidence, method_used) where confidence is in [0, 1].
    """
    if width_attr is not None and width_attr > 0:
        return float(width_attr), 0.95, "osm_explicit"

    if lanes is not None and int(lanes) > 0:
        lane_width = 3.5  # IRC standard lane width
        shoulder = 2.5 if int(lanes) >= 2 else 1.5
        width = int(lanes) * lane_width + shoulder
        return width, 0.70, "lane_count_derived"

    tag = str(highway_tag).lower() if highway_tag else "road"
    width = IRC_WIDTHS.get(tag, 5.5)
    return width, 0.40, "irc_standard"


# ─────────────────────────────────────────────────────────────────────────────
# Network metric helpers
# ─────────────────────────────────────────────────────────────────────────────

def calculate_network_metrics(G: nx.MultiDiGraph) -> Dict[str, Any]:
    """
    Compute graph-theoretic road network metrics from a NetworkX MultiDiGraph.

    For large graphs, betweenness centrality is computed on a random sample
    of 500 nodes to keep computation tractable.

    Args:
        G: OSMnx-derived (or compatible) MultiDiGraph where edges have a
           ``length`` attribute in metres.

    Returns:
        Dictionary with keys:
            total_length_km, node_count, edge_count, avg_degree,
            avg_betweenness, avg_clustering, density, connected_components.
    """
    if len(G) == 0:
        return {
            "total_length_km": 0.0,
            "node_count": 0,
            "edge_count": 0,
            "avg_degree": 0.0,
            "avg_betweenness": 0.0,
            "avg_clustering": 0.0,
            "density": 0.0,
            "connected_components": 0,
        }

    total_length_m: float = sum(
        data.get("length", 0) for _, _, data in G.edges(data=True)
    )
    total_length_km = total_length_m / 1000.0

    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    avg_degree = (2 * edge_count / node_count) if node_count > 0 else 0.0

    # Betweenness centrality – sampled for large graphs
    sample_size = min(500, node_count)
    bc_dict = nx.betweenness_centrality(
        G, k=sample_size, normalized=True, seed=42
    )
    avg_betweenness = float(np.mean(list(bc_dict.values())))

    # Clustering – convert to undirected for clustering coefficient
    G_und = G.to_undirected()
    clustering = nx.average_clustering(G_und)

    graph_density = nx.density(G)

    undirected = G.to_undirected()
    connected_components = nx.number_connected_components(undirected)

    return {
        "total_length_km": round(total_length_km, 3),
        "node_count": node_count,
        "edge_count": edge_count,
        "avg_degree": round(avg_degree, 4),
        "avg_betweenness": round(avg_betweenness, 6),
        "avg_clustering": round(clustering, 4),
        "density": round(graph_density, 6),
        "connected_components": connected_components,
    }


# ─────────────────────────────────────────────────────────────────────────────
# OSMnx – current network
# ─────────────────────────────────────────────────────────────────────────────

def fetch_current_network(
    bbox: Tuple[float, float, float, float],
    network_type: str = "drive",
) -> Tuple[nx.MultiDiGraph, gpd.GeoDataFrame]:
    """
    Fetch the current (latest) OSM road network for a bounding box.

    Uses the ``osmnx`` library which queries the Overpass API internally.

    Args:
        bbox:         Bounding box as (west, south, east, north) in WGS-84 degrees.
        network_type: OSMnx network type string: ``"drive"``, ``"all"``,
                      ``"walk"``, ``"bike"``.  Defaults to ``"drive"``
                      to retrieve driveable roads only.

    Returns:
        Tuple of (G, gdf_edges) where ``G`` is the NetworkX graph and
        ``gdf_edges`` is a GeoDataFrame of road edges with OSM attributes.

    Raises:
        ValueError: If the bounding box is invalid.
        RuntimeError: If the Overpass API query fails.
    """
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError(f"Invalid bounding box: {bbox}")

    logger.info(
        "Fetching current OSM network for bbox=%s network_type=%s",
        bbox,
        network_type,
    )
    try:
        G = ox.graph_from_bbox(
            north=north,
            south=south,
            east=east,
            west=west,
            network_type=network_type,
            retain_all=False,
            simplify=True,
        )
        G = ox.add_edge_speeds(G)
        G = ox.add_edge_travel_times(G)

        _, gdf_edges = ox.graph_to_gdfs(G)
        gdf_edges = gdf_edges.reset_index()

        logger.info(
            "Fetched current network: %d nodes, %d edges",
            G.number_of_nodes(),
            G.number_of_edges(),
        )
        return G, gdf_edges
    except Exception as exc:
        logger.error("Failed to fetch current OSM network: %s", exc)
        raise RuntimeError(f"OSM network fetch failed: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# ohsome API – historical network
# ─────────────────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _post_ohsome(
    endpoint: str,
    payload: Dict[str, str],
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Make an authenticated POST request to the ohsome API.

    The ohsome API is a public REST API maintained by HeiGIT that exposes
    historical OpenStreetMap data.  No API key is required.

    Args:
        endpoint: API path starting with ``/``, e.g. ``/elements/length``.
        payload:  Form-encoded body parameters.
        timeout:  Request timeout in seconds.

    Returns:
        Parsed JSON response as a dictionary.

    Raises:
        aiohttp.ClientResponseError: On HTTP 4xx / 5xx responses.
        asyncio.TimeoutError: If the request exceeds ``timeout`` seconds.
    """
    url = f"{OHSOME_BASE_URL}{endpoint}"
    logger.debug("ohsome POST %s payload=%s", url, payload)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            data=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            resp.raise_for_status()
            return await resp.json()


async def fetch_historical_network(
    bbox: Tuple[float, float, float, float],
    year: int,
    month: int = 6,
) -> gpd.GeoDataFrame:
    """
    Fetch a historical road network snapshot from the ohsome API.

    The ohsome API (https://api.ohsome.org/v1) exposes OSM element geometries
    at any past timestamp.  We query the ``/elements/geometry`` endpoint with
    a ``time`` parameter of ``{year}-{month:02d}-01`` to obtain all OSM ways
    tagged ``highway=*`` that existed on that date.

    Note on OSM completeness
    ~~~~~~~~~~~~~~~~~~~~~~~~
    A snapshot from 2016 will only contain roads that were mapped in OSM by
    that date.  Rural and peri-urban roads in India were often added to OSM
    significantly later.  Callers should apply
    :func:`apply_osm_completeness_correction` to the derived statistics.

    Args:
        bbox:  (west, south, east, north) in WGS-84 degrees.
        year:  Snapshot year (e.g. 2016).
        month: Snapshot month (default 6 = June, mid-year).

    Returns:
        GeoDataFrame of road geometries with OSM tag columns.

    Raises:
        RuntimeError: On ohsome API failure after retries.
    """
    west, south, east, north = bbox
    bboxes_str = f"{west},{south},{east},{north}"
    timestamp = f"{year}-{month:02d}-01"

    payload = {
        "bboxes": bboxes_str,
        "filter": "highway=* and type:way",
        "time": timestamp,
        "format": "geojson",
        "properties": "tags",
    }

    logger.info("Fetching ohsome historical network: %s at %s", bboxes_str, timestamp)
    try:
        data = await _post_ohsome("/elements/geometry", payload)
    except Exception as exc:
        logger.error("ohsome /elements/geometry failed: %s", exc)
        raise RuntimeError(f"ohsome geometry fetch failed for {year}: {exc}") from exc

    features = data.get("features", [])
    if not features:
        logger.warning("No features returned from ohsome for %s at %s", bboxes_str, timestamp)
        return gpd.GeoDataFrame(
            columns=["geometry", "highway", "name", "lanes", "width", "@osmId"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    rows = []
    for feat in features:
        props = feat.get("properties", {})
        geom_dict = feat.get("geometry")
        if geom_dict is None:
            continue
        try:
            geom = shape(geom_dict)
        except Exception:
            continue
        rows.append(
            {
                "geometry": geom,
                "osm_id": props.get("@osmId", ""),
                "highway": props.get("highway"),
                "name": props.get("name"),
                "lanes": props.get("lanes"),
                "width": props.get("width"),
                "surface": props.get("surface"),
                "maxspeed": props.get("maxspeed"),
            }
        )

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    logger.info("ohsome returned %d road features for year=%d", len(gdf), year)
    return gdf


async def ohsome_road_stats(
    bbox: Tuple[float, float, float, float],
    year_from: int = 2016,
    year_to: int = 2026,
) -> Dict[str, Any]:
    """
    Retrieve year-by-year total road length from the ohsome API.

    Uses the ``POST /elements/length`` endpoint with an annual interval
    time string (``{year_from}-01-01/{year_to}-01-01/P1Y``) to obtain the
    total length of all ``highway=*`` ways for each year in the range.

    Args:
        bbox:       (west, south, east, north) in WGS-84 degrees.
        year_from:  Start year (inclusive).
        year_to:    End year (inclusive, one extra year added to the ohsome
                    range string to capture the final year).

    Returns:
        Dictionary with keys:
            ``timeseries``    – list of {year, length_km} dicts
            ``data_quality_note`` – warning string if anomalous growth detected
            ``total_growth_pct``  – percentage growth from first to last year
    """
    west, south, east, north = bbox
    bboxes_str = f"{west},{south},{east},{north}"
    time_str = f"{year_from}-01-01/{year_to + 1}-01-01/P1Y"

    payload = {
        "bboxes": bboxes_str,
        "filter": "highway=* and type:way",
        "time": time_str,
        "format": "json",
    }

    logger.info("Fetching ohsome road stats for bbox=%s time=%s", bboxes_str, time_str)
    try:
        data = await _post_ohsome("/elements/length", payload)
    except Exception as exc:
        logger.error("ohsome /elements/length failed: %s", exc)
        raise RuntimeError(f"ohsome length stats failed: {exc}") from exc

    results = data.get("result", [])
    timeseries: List[Dict[str, Any]] = []
    for entry in results:
        ts = entry.get("timestamp", "")
        year = int(ts[:4]) if ts else None
        if year is None:
            continue
        length_m = entry.get("value", 0) or 0
        timeseries.append({"year": year, "length_km": round(length_m / 1000, 3)})

    # Detect implausible growth (> 30% single-year jump → likely mapping backfill)
    data_quality_note = ""
    for i in range(1, len(timeseries)):
        prev = timeseries[i - 1]["length_km"]
        curr = timeseries[i]["length_km"]
        if prev > 0:
            yoy_pct = (curr - prev) / prev * 100
            if yoy_pct > 30:
                data_quality_note = (
                    f"Anomalous single-year growth of {yoy_pct:.1f}% detected between "
                    f"{timeseries[i-1]['year']} and {timeseries[i]['year']}. "
                    "This likely reflects OSM mapping backfill rather than actual road "
                    "construction. Treat absolute change figures with caution."
                )
                break

    total_growth_pct: Optional[float] = None
    if timeseries and timeseries[0]["length_km"] > 0:
        total_growth_pct = round(
            (timeseries[-1]["length_km"] - timeseries[0]["length_km"])
            / timeseries[0]["length_km"]
            * 100,
            2,
        )

    return {
        "timeseries": timeseries,
        "data_quality_note": data_quality_note,
        "total_growth_pct": total_growth_pct,
    }


def apply_osm_completeness_correction(
    stats: Dict[str, Any],
    region: str,
) -> Dict[str, Any]:
    """
    Annotate change statistics with an OSM completeness caveat.

    Appends a data quality note to ``stats`` when the apparent road growth
    exceeds a threshold that is plausible for genuine road construction,
    indicating that OSM mapping activity is likely a contributing factor.

    Args:
        stats:   Dictionary of change statistics (mutated in place).
        region:  Human-readable region name for the note string.

    Returns:
        The same ``stats`` dictionary with an updated ``data_quality_note``.
    """
    pct = stats.get("pct_growth", 0) or 0
    existing_note = stats.get("data_quality_note", "") or ""

    if pct > 50:
        caveat = (
            f"[OSM Completeness Warning] The {pct:.1f}% growth figure for "
            f"{region} exceeds typical road construction rates and is likely "
            "partly attributable to retrospective OSM data addition. "
            "Ground-truth validation against Bhuvan or NRSC imagery is strongly recommended."
        )
        stats["data_quality_note"] = f"{existing_note} {caveat}".strip()
    elif pct > 20:
        caveat = (
            f"[Data Quality Note] The {pct:.1f}% growth figure for {region} "
            "may include OSM mapping backfill. Values should be interpreted "
            "as an upper bound on actual road construction."
        )
        stats["data_quality_note"] = f"{existing_note} {caveat}".strip()

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Class wrapper for OsmService
# ─────────────────────────────────────────────────────────────────────────────

class OsmService:
    """
    OpenStreetMap & ohsome API data-fetching service.
    Exposes network retrieval, road classification, width estimation,
    and topological metric calculation.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir

    @staticmethod
    def classify_road(highway_tag: Optional[str]) -> str:
        return classify_road(highway_tag)

    @staticmethod
    def estimate_road_width(
        highway_tag: Optional[str],
        lanes: Optional[int] = None,
        width_attr: Optional[float] = None,
    ) -> Tuple[float, float]:
        return estimate_road_width(highway_tag, lanes, width_attr)

    @staticmethod
    def calculate_network_metrics(G: nx.MultiDiGraph) -> Dict[str, Any]:
        return calculate_network_metrics(G)

    @staticmethod
    def fetch_current_network(
        bbox: Tuple[float, float, float, float],
        network_type: str = "all",
    ) -> gpd.GeoDataFrame:
        return fetch_current_network(bbox, network_type)

    @staticmethod
    async def fetch_historical_network(
        bbox: Tuple[float, float, float, float],
        year: int,
        month: int = 6,
    ) -> gpd.GeoDataFrame:
        return await fetch_historical_network(bbox, year, month)

    @staticmethod
    async def ohsome_road_stats(
        bbox: Tuple[float, float, float, float],
        year: int,
    ) -> Dict[str, Any]:
        return await ohsome_road_stats(bbox, year)

    @staticmethod
    def apply_osm_completeness_correction(
        stats: Dict[str, Any],
        region: str,
    ) -> Dict[str, Any]:
        return apply_osm_completeness_correction(stats, region)

