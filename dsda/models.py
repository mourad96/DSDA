"""Data models and type definitions for the DSDA algorithm."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass(frozen=True)
class Point2D:
    """Projected Cartesian coordinate (x, y) in metric units (e.g. UTM)."""
    x: float
    y: float

    def distance_to(self, other: Point2D) -> float:
        """Euclidean distance in meters to another 2D point."""
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass(frozen=True)
class WGS84Point:
    """WGS84 geographic coordinate (latitude, longitude)."""
    lat: float
    lon: float

    @classmethod
    def from_tuple(cls, coords: Tuple[float, float]) -> WGS84Point:
        return cls(lat=coords[0], lon=coords[1])

    def to_tuple(self) -> Tuple[float, float]:
        return (self.lat, self.lon)


@dataclass
class GisNode:
    """A centerline node in the GIS infrastructure database."""
    node_name: str
    pk_marker: str
    gazetteer: List[str]
    highway_hierarchy: str
    coords: Point2D
    wgs84: Optional[WGS84Point] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GisNode:
        """Construct a GisNode from a legacy dictionary."""
        gazetteer = data.get("Gazetteer", [])
        if isinstance(gazetteer, str):
            gazetteer = [gazetteer]

        wgs84_raw = data.get("WGS84_Coordinates")
        wgs84 = None
        if wgs84_raw:
            if isinstance(wgs84_raw, (tuple, list)) and len(wgs84_raw) == 2:
                wgs84 = WGS84Point(lat=float(wgs84_raw[0]), lon=float(wgs84_raw[1]))
            elif isinstance(wgs84_raw, WGS84Point):
                wgs84 = wgs84_raw

        coords = data.get("coords")
        if not coords:
            coords = Point2D(x=float(data["x"]), y=float(data["y"]))
        elif isinstance(coords, (tuple, list)):
            coords = Point2D(x=float(coords[0]), y=float(coords[1]))

        return cls(
            node_name=str(data.get("node_name", "")),
            pk_marker=str(data.get("PK_marker", "")),
            gazetteer=[str(g) for g in gazetteer],
            highway_hierarchy=str(data.get("Highway_Hierarchy", "")),
            coords=coords,
            wgs84=wgs84,
            extra={k: v for k, v in data.items() if k not in {
                "node_name", "PK_marker", "Gazetteer", "Highway_Hierarchy",
                "x", "y", "coords", "WGS84_Coordinates"
            }}
        )


class AnchorType(str, Enum):
    """Source classification of a spatial reference point.

    PK_POST is the only anchor used for proximity decay (primary LRS-anchored
    mode, Algorithm 1). MUNICIPALITY_CENTROID and PRIOR_EVENT are sector
    references, used only to resolve an omitted or ambiguous PK marker.
    """
    COLD_START = "COLD_START"
    PK_POST = "PK_POST"
    PRIOR_EVENT = "PRIOR_EVENT"
    MUNICIPALITY_CENTROID = "MUNICIPALITY_CENTROID"


class ResolutionMode(str, Enum):
    """Candidate generation mode of Algorithm 1 (step 2)."""
    LRS_ANCHORED = "LRS_ANCHORED"        # PK marker resolved: anchor = k_PK, buffer R_max
    SECTOR_FALLBACK = "SECTOR_FALLBACK"  # PK omitted/ambiguous: w2 = 0, sector query


@dataclass(frozen=True)
class Anchor:
    """Spatial reference point (k_PK, k_municipality or k_prev)."""
    coords: Point2D
    anchor_type: AnchorType
    source_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    route: Optional[str] = None


@dataclass(frozen=True)
class PKPost:
    """Nominal kilometric post (k_PK) on a route centerline."""
    route: str
    pk_marker: str
    coords: Point2D
    sector: Optional[str] = None


@dataclass
class CrashEvent:
    """A crash event requiring linear referencing disambiguation."""
    event_id: str
    route: str
    pk_marker: Optional[str]
    narrative_landmarks: List[str]
    timestamp: Optional[datetime] = None
    municipality_centroid: Optional[Point2D] = None
    intersection_descriptors: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)
    # NOTE: ground-truth coordinates are deliberately NOT part of the runtime
    # event. They are only used post hoc by dsda.evaluation (E_geo, P90, P95).

    def __post_init__(self) -> None:
        if isinstance(self.narrative_landmarks, str):
            self.narrative_landmarks = [self.narrative_landmarks]


@dataclass
class CandidateEvaluation:
    """Detailed multi-criteria evaluation metrics for a single GIS node."""
    node: GisNode
    distance_m: float
    s_toponym: float
    s_proximity: float
    s_topology: float
    cs_score: float


class GeocodingStatus(str, Enum):
    """Decision status of the DSDA disambiguation process."""
    AUTO_VALIDATED = "AUTO-VALIDATED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    NO_CANDIDATES = "REJECTED_NO_CANDIDATES"


@dataclass
class GeocodingResult:
    """Full disambiguation result for a crash event."""
    event_id: str
    status: GeocodingStatus
    selected_node: Optional[GisNode]
    best_score: float
    candidate_evaluations: List[CandidateEvaluation]
    weights_used: Dict[str, float]
    anchor_used: Optional[Anchor]
    mode: ResolutionMode = ResolutionMode.LRS_ANCHORED
    sector_reference: Optional[Anchor] = None
    is_safe_anchor: bool = False
    decision_message: str = ""

    def summary_table(self) -> str:
        """Formatted evaluation table for logging or CLI inspection."""
        lines = [
            f"Event ID: {self.event_id} | Status: {self.status.value} (Score: {self.best_score:.3f})",
            f"Weights: {self.weights_used}",
            f"Mode: {self.mode.value} | Proximity anchor: {self.anchor_used.anchor_type.value if self.anchor_used else 'None'}",
            f"{'-'*75}",
            f"{'Node':<22} | {'Route':<7} | {'Dist(m)':<8} | {'Toponym':<7} | {'Prox':<6} | {'Topo':<5} | {'Cs'}",
            f"{'-'*75}"
        ]
        for c in self.candidate_evaluations:
            lines.append(
                f"{c.node.node_name:<22} | {c.node.highway_hierarchy:<7} | "
                f"{c.distance_m:<8.2f} | {c.s_toponym:<7.3f} | {c.s_proximity:<6.3f} | "
                f"{c.s_topology:<5.1f} | {c.cs_score:.3f}"
            )
        lines.append(f"{'-'*75}")
        lines.append(f"Decision: {self.decision_message}")
        return "\n".join(lines)


@dataclass
class DSDAParameters:
    """Configurable weights, tolerances, and thresholds for the DSDA algorithm."""
    # Standard multi-criteria weights (Equation A1)
    w1: float = 0.500
    w2: float = 0.375
    w3: float = 0.125

    # Cold start weights (Rule 1: Proximity neutralized, w2 absorbed by w1)
    cold_start_w1: float = 0.875
    cold_start_w2: float = 0.000
    cold_start_w3: float = 0.125

    # Gaussian proximity bandwidth (Equation A3)
    sigma: float = 150.0

    # Auto-validation threshold (acceptance gate, Algorithm 1 step 5)
    validation_threshold: float = 0.85

    # Candidate search buffer around the nominal PK post k_PK (Algorithm 1 step 2)
    r_max: float = 500.0

    # Radius of the municipal sector queried in fallback mode (implementation
    # choice: Algorithm 1 does not fix it numerically)
    sector_radius: float = 5000.0

    # Chronological sector rule: Delta_t <= 24 h -> k_municipality
    simultaneous_window: timedelta = timedelta(hours=24)

    def __post_init__(self) -> None:
        std_sum = self.w1 + self.w2 + self.w3
        if not math.isclose(std_sum, 1.0, rel_tol=1e-3):
            raise ValueError(f"Standard weights must sum to 1.0, got {std_sum}")
        cold_sum = self.cold_start_w1 + self.cold_start_w2 + self.cold_start_w3
        if not math.isclose(cold_sum, 1.0, rel_tol=1e-3):
            raise ValueError(f"Cold start weights must sum to 1.0, got {cold_sum}")
        if self.sigma <= 0:
            raise ValueError(f"Bandwidth sigma must be strictly positive, got {self.sigma}")
        if not (0.0 <= self.validation_threshold <= 1.0):
            raise ValueError(f"Validation threshold must be in [0, 1], got {self.validation_threshold}")
        if self.r_max <= 0:
            raise ValueError(f"r_max must be strictly positive, got {self.r_max}")
        if self.sector_radius <= 0:
            raise ValueError(f"sector_radius must be strictly positive, got {self.sector_radius}")
