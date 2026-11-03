# app/services/network_analysis.py
"""
NetworkX-based road network analysis service for GeoTrack India.

Provides graph construction, connectivity metric computation, and comparative
analysis between two road network snapshots.

Metrics produced:
    - Average node degree
    - Local clustering coefficient
    - Betweenness centrality (sampled)
    - Graph density
    - Number of connected components
    - Intersection density (intersections per km²)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiLineString, Point

logger = logging.getLogger(__name__)

# UTM 43N – metric CRS for India
INDIA_UTM_CRS = "EPSG:32643"


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────────────

def build_graph_from_gdf(gdf: gpd.GeoDataFrame) -> nx.MultiDiGraph:
    """
    Convert a road-edge GeoDataFrame into a NetworkX MultiDiGraph.

    Each road LineString becomes a directed edge (both directions for
    undivided roads).  Endpoints of each LineString are used as nodes,
    snapped to a 1 m grid to merge nearby intersections.

    Args:
        gdf: GeoDataFrame of road segments with a ``geometry`` column
             (LineString or MultiLineString).  Should be in a projected CRS
             so that ``length`` attributes are in metres.

    Returns:
        A NetworkX MultiDiGraph suitable for network metric computation.
        Edge attributes include ``length`` (metres), ``highway``, and
        ``name``.
    """
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    if not gdf.crs.is_projected:
        gdf = gdf.to_crs(INDIA_UTM_CRS)

    G: nx.MultiDiGraph = nx.MultiDiGraph()

    def _snap(coord: Tuple[float, float], grid: float = 1.0) -> Tuple[float, float]:
        """Snap coordinate to grid to merge nearby nodes."""
        return (round(coord[0] / grid) * grid, round(coord[1] / grid) * grid)

    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        lines: List[LineString] = []
        if isinstance(geom, LineString):
            lines = [geom]
        elif isinstance(geom, MultiLineString):
            lines = list(geom.geoms)
        else:
            continue

        for line in lines:
            coords = list(line.coords)
            if len(coords) < 2:
                continue
            u = _snap(coords[0])
            v = _snap(coords[-1])

            if not G.has_node(u):
                G.add_node(u, x=u[0], y=u[1])
            if not G.has_node(v):
                G.add_node(v, x=v[0], y=v[1])

            attrs = {
                "geometry": line,
                "length": line.length,
                "highway": row.get("highway", None),
                "name": row.get("name", None),
                "osm_id": row.get("osm_id", idx),
            }
            G.add_edge(u, v, **attrs)
            G.add_edge(v, u, **attrs)  # bidirectional for undivided roads

    logger.info(
        "Built graph: %d nodes, %d edges from %d GDF rows",
        G.number_of_nodes(),
        G.number_of_edges(),
        len(gdf),
    )
    return G


# ─────────────────────────────────────────────────────────────────────────────
# Connectivity metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_connectivity_metrics(G: nx.MultiDiGraph) -> Dict[str, Any]:
    """
    Compute road network connectivity metrics from a MultiDiGraph.

    For performance on large graphs:
        - Betweenness centrality is approximated using a random sample of
          k = min(500, node_count) pivot nodes.
        - Clustering coefficient uses the undirected projection.

    Args:
        G: NetworkX MultiDiGraph (typically built by :func:`build_graph_from_gdf`).

    Returns:
        Dictionary with keys:
            node_count, edge_count, avg_degree, avg_clustering,
            avg_betweenness, graph_density, connected_components,
            total_length_km.
    """
    if G.number_of_nodes() == 0:
        return {
            "node_count": 0,
            "edge_count": 0,
            "avg_degree": 0.0,
            "avg_clustering": 0.0,
            "avg_betweenness": 0.0,
            "graph_density": 0.0,
            "connected_components": 0,
            "total_length_km": 0.0,
        }

    n = G.number_of_nodes()
    e = G.number_of_edges()

    # Degree (out-degree in directed graph)
    degrees = [deg for _, deg in G.degree()]
    avg_degree = float(np.mean(degrees)) if degrees else 0.0

    # Betweenness centrality – sampled
    k = min(500, n)
    bc = nx.betweenness_centrality(G, k=k, normalized=True, seed=42)
    avg_betweenness = float(np.mean(list(bc.values())))

    # Clustering coefficient – undirected projection
    G_und = G.to_undirected(as_view=False)
    avg_clustering = nx.average_clustering(G_und)

    # Graph density
    graph_density = nx.density(G)

    # Connected components (undirected)
    connected_components = nx.number_connected_components(G_und)

    # Total edge length
    total_length_m = sum(
        data.get("length", 0) for _, _, data in G.edges(data=True)
    )
    total_length_km = total_length_m / 1000.0

    return {
        "node_count": n,
        "edge_count": e,
        "avg_degree": round(avg_degree, 4),
        "avg_clustering": round(avg_clustering, 4),
        "avg_betweenness": round(avg_betweenness, 6),
        "graph_density": round(graph_density, 6),
        "connected_components": connected_components,
        "total_length_km": round(total_length_km, 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Intersection density
# ─────────────────────────────────────────────────────────────────────────────

def compute_intersection_density(
    G: nx.MultiDiGraph,
    area_km2: float,
) -> float:
    """
    Compute intersection density in intersections per square kilometre.

    An intersection is defined as a graph node with degree ≥ 3 (i.e. three
    or more connecting road segments), which corresponds to a genuine
    road crossing point.

    Args:
        G:        Road network graph.
        area_km2: Study area in km².

    Returns:
        Intersection density (intersections / km²).  Returns 0.0 if the
        graph is empty or the area is zero.
    """
    if G.number_of_nodes() == 0 or area_km2 <= 0:
        return 0.0

    intersection_count = sum(
        1 for _, deg in G.degree() if deg >= 3
    )
    return round(intersection_count / area_km2, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Network comparison
# ─────────────────────────────────────────────────────────────────────────────

def compare_networks(
    G_from: nx.MultiDiGraph,
    G_to: nx.MultiDiGraph,
    area_km2: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Structured comparison of two road network graphs.

    Computes connectivity metrics for both graphs and returns a comparison
    dictionary suitable for JSON serialisation and dashboard display.

    Args:
        G_from:   Road network graph for the earlier year.
        G_to:     Road network graph for the later year.
        area_km2: Study area in km² (used for intersection density if provided).

    Returns:
        Dictionary with sub-keys ``from``, ``to``, and ``delta`` (absolute
        and percentage change for each metric).
    """
    m_from = compute_connectivity_metrics(G_from)
    m_to = compute_connectivity_metrics(G_to)

    delta: Dict[str, Any] = {}
    for key in m_from:
        v_from = m_from[key]
        v_to = m_to[key]
        if isinstance(v_from, (int, float)) and isinstance(v_to, (int, float)):
            abs_delta = round(v_to - v_from, 4)
            pct_delta = (
                round(abs_delta / v_from * 100, 2) if v_from != 0 else None
            )
            delta[key] = {"abs": abs_delta, "pct": pct_delta}

    result: Dict[str, Any] = {
        "from": m_from,
        "to": m_to,
        "delta": delta,
    }

    if area_km2 and area_km2 > 0:
        result["intersection_density_from"] = compute_intersection_density(
            G_from, area_km2
        )
        result["intersection_density_to"] = compute_intersection_density(
            G_to, area_km2
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# High-betweenness nodes
# ─────────────────────────────────────────────────────────────────────────────

def find_most_connected_nodes(
    G: nx.MultiDiGraph,
    top_n: int = 10,
) -> gpd.GeoDataFrame:
    """
    Identify the highest-betweenness (most critical) nodes in the network.

    These nodes represent key junctions whose removal would most disrupt
    network connectivity.

    Args:
        G:     Road network graph.  Node attributes must include ``x`` and ``y``
               coordinates in the graph's native CRS.
        top_n: Number of top nodes to return.

    Returns:
        GeoDataFrame of top-N nodes with columns:
            node_id, x, y, betweenness, degree, geometry (Point).
        The GeoDataFrame is in EPSG:4326 if the input graph uses UTM 43N,
        otherwise it retains the graph CRS.
    """
    if G.number_of_nodes() == 0:
        return gpd.GeoDataFrame(
            columns=["node_id", "x", "y", "betweenness", "degree", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    k = min(500, G.number_of_nodes())
    bc = nx.betweenness_centrality(G, k=k, normalized=True, seed=42)

    top_nodes = sorted(bc.items(), key=lambda kv: kv[1], reverse=True)[:top_n]

    rows = []
    for node_id, bc_val in top_nodes:
        node_data = G.nodes[node_id]
        x = node_data.get("x", node_id[0] if isinstance(node_id, tuple) else 0)
        y = node_data.get("y", node_id[1] if isinstance(node_id, tuple) else 0)
        rows.append(
            {
                "node_id": str(node_id),
                "x": x,
                "y": y,
                "betweenness": round(bc_val, 6),
                "degree": G.degree(node_id),
                "geometry": Point(x, y),
            }
        )

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=INDIA_UTM_CRS)
    try:
        gdf = gdf.to_crs("EPSG:4326")
    except Exception:
        pass  # Leave in UTM if reprojection fails

    return gdf
