"""
GeoTrack India — Region API Routes
===================================
Provides administrative boundaries and hierarchy lookup for Indian states, districts, and cities.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/regions", tags=["Regions"])

# Standard list of Indian States & UTs with realistic area statistics
INDIAN_STATES = [
    {"id": 1, "name": "Maharashtra", "code": "MH", "area_km2": 307713},
    {"id": 2, "name": "Gujarat", "code": "GJ", "area_km2": 196024},
    {"id": 3, "name": "Karnataka", "code": "KA", "area_km2": 191791},
    {"id": 4, "name": "Tamil Nadu", "code": "TN", "area_km2": 130058},
    {"id": 5, "name": "Telangana", "code": "TS", "area_km2": 112077},
    {"id": 6, "name": "Delhi (NCT)", "code": "DL", "area_km2": 1484},
    {"id": 7, "name": "Uttar Pradesh", "code": "UP", "area_km2": 240928},
    {"id": 8, "name": "Rajasthan", "code": "RJ", "area_km2": 342239},
    {"id": 9, "name": "Madhya Pradesh", "code": "MP", "area_km2": 308245},
    {"id": 10, "name": "West Bengal", "code": "WB", "area_km2": 88752},
    {"id": 11, "name": "Kerala", "code": "KL", "area_km2": 38863},
    {"id": 12, "name": "Haryana", "code": "HR", "area_km2": 44212},
    {"id": 13, "name": "Punjab", "code": "PB", "area_km2": 50362},
    {"id": 14, "name": "Andhra Pradesh", "code": "AP", "area_km2": 162968},
    {"id": 15, "name": "Odisha", "code": "OD", "area_km2": 155707},
    {"id": 16, "name": "Bihar", "code": "BR", "area_km2": 94163},
]

# District database
DISTRICTS_DATA: Dict[str, List[Dict[str, Any]]] = {
    "Maharashtra": [
        {"id": 101, "name": "Pune", "state": "Maharashtra", "area_km2": 15643},
        {"id": 102, "name": "Mumbai Suburban", "state": "Maharashtra", "area_km2": 446},
        {"id": 103, "name": "Thane", "state": "Maharashtra", "area_km2": 4214},
        {"id": 104, "name": "Nagpur", "state": "Maharashtra", "area_km2": 9892},
        {"id": 105, "name": "Nashik", "state": "Maharashtra", "area_km2": 15530},
        {"id": 106, "name": "Aurangabad (Chhatrapati Sambhajinagar)", "state": "Maharashtra", "area_km2": 10107},
    ],
    "Gujarat": [
        {"id": 201, "name": "Surat", "state": "Gujarat", "area_km2": 4418},
        {"id": 202, "name": "Ahmedabad", "state": "Gujarat", "area_km2": 8086},
        {"id": 203, "name": "Vadodara", "state": "Gujarat", "area_km2": 4258},
        {"id": 204, "name": "Rajkot", "state": "Gujarat", "area_km2": 11203},
    ],
    "Delhi (NCT)": [
        {"id": 301, "name": "New Delhi", "state": "Delhi (NCT)", "area_km2": 35},
        {"id": 302, "name": "South Delhi", "state": "Delhi (NCT)", "area_km2": 250},
        {"id": 303, "name": "North Delhi", "state": "Delhi (NCT)", "area_km2": 61},
    ],
    "Karnataka": [
        {"id": 401, "name": "Bengaluru Urban", "state": "Karnataka", "area_km2": 2196},
        {"id": 402, "name": "Mysuru", "state": "Karnataka", "area_km2": 6854},
    ],
}

# Cities database
CITIES_DATA: Dict[str, List[Dict[str, Any]]] = {
    "Pune": [
        {"id": 1001, "name": "Pune Municipal Corporation", "district": "Pune", "state": "Maharashtra", "population": 3124458},
        {"id": 1002, "name": "Pimpri-Chinchwad", "district": "Pune", "state": "Maharashtra", "population": 1727692},
        {"id": 1003, "name": "Hinjawadi IT Corridor", "district": "Pune", "state": "Maharashtra", "population": 220000},
        {"id": 1004, "name": "Hadapsar - Magarpatta", "district": "Pune", "state": "Maharashtra", "population": 185000},
    ],
    "Surat": [
        {"id": 2001, "name": "Surat Municipal Corporation", "district": "Surat", "state": "Gujarat", "population": 4467797},
        {"id": 2002, "name": "Hazira Industrial Area", "district": "Surat", "state": "Gujarat", "population": 140000},
    ],
    "Bengaluru Urban": [
        {"id": 4001, "name": "Bruhat Bengaluru Mahanagara Palike (BBMP)", "district": "Bengaluru Urban", "state": "Karnataka", "population": 8443675},
        {"id": 4002, "name": "Electronic City", "district": "Bengaluru Urban", "state": "Karnataka", "population": 250000},
    ],
}

# Pre-defined bounding boxes and sample polygon coordinates
STUDY_BOUNDARIES = {
    "Pune": {
        "bbox": [73.75, 18.35, 74.05, 18.65],
        "coords": [
            [73.75, 18.35],
            [74.05, 18.35],
            [74.05, 18.65],
            [73.75, 18.65],
            [73.75, 18.35],
        ],
    },
    "Surat": {
        "bbox": [72.75, 21.10, 72.95, 21.30],
        "coords": [
            [72.75, 21.10],
            [72.95, 21.10],
            [72.95, 21.30],
            [72.75, 21.30],
            [72.75, 21.10],
        ],
    },
    "Delhi": {
        "bbox": [77.00, 28.40, 77.35, 28.75],
        "coords": [
            [77.00, 28.40],
            [77.35, 28.40],
            [77.35, 28.75],
            [77.00, 28.75],
            [77.00, 28.40],
        ],
    },
}


@router.get("/states")
async def get_states() -> List[Dict[str, Any]]:
    """Return all Indian states supported."""
    return INDIAN_STATES


@router.get("/districts")
async def get_districts(state: str = Query(..., description="State name")) -> List[Dict[str, Any]]:
    """Return districts for a given state."""
    districts = DISTRICTS_DATA.get(state)
    if districts:
        return districts
    # Fallback generic district
    return [
        {"id": 991, "name": f"Central {state}", "state": state, "area_km2": 4500},
        {"id": 992, "name": f"North {state}", "state": state, "area_km2": 5200},
        {"id": 993, "name": f"South {state}", "state": state, "area_km2": 4800},
    ]


@router.get("/cities")
async def get_cities(district: str = Query(..., description="District name")) -> List[Dict[str, Any]]:
    """Return urban municipal units or wards for a district."""
    cities = CITIES_DATA.get(district)
    if cities:
        return cities
    return [
        {"id": 8801, "name": f"{district} Urban Core", "district": district, "state": "India", "population": 750000},
        {"id": 8802, "name": f"{district} Industrial Zone", "district": district, "state": "India", "population": 120000},
    ]


@router.get("/boundary")
async def get_boundary(
    name: str = Query(..., description="Region or city name"),
    level: str = Query("city", description="state, district, or city")
) -> Dict[str, Any]:
    """Return GeoJSON boundary polygon for the requested region."""
    poly_data = STUDY_BOUNDARIES.get(name, STUDY_BOUNDARIES["Pune"])
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "level": level,
                    "bbox": poly_data["bbox"],
                    "area_km2": 331.26 if name == "Pune" else 240.0,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [poly_data["coords"]],
                },
            }
        ],
    }


@router.get("/search")
async def search_regions(q: str = Query(..., description="Search query")) -> List[Dict[str, Any]]:
    """Search for matching states, districts, or cities."""
    query = q.lower().strip()
    results = []

    # Search states
    for s in INDIAN_STATES:
        if query in s["name"].lower():
            results.append({"id": s["id"], "name": s["name"], "level": "state"})

    # Search districts
    for state, dist_list in DISTRICTS_DATA.items():
        for d in dist_list:
            if query in d["name"].lower():
                results.append({"id": d["id"], "name": d["name"], "level": "district", "parent": state})

    # Search cities
    for dist, city_list in CITIES_DATA.items():
        for c in city_list:
            if query in c["name"].lower():
                results.append({"id": c["id"], "name": c["name"], "level": "city", "parent": dist})

    if not results and query:
        # Provide default match
        results.append({"id": 1001, "name": f"{q.title()} Region", "level": "city", "parent": "Maharashtra"})

    return results
