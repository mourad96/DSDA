"""DSDA: Deterministic Spatial Disambiguation Algorithm for Linear Referencing.

Reproducibility framework and production-grade implementation of DSDA
(Formal Mathematical Specification Appendix A.1).
"""

from dsda.engine import DSDAEngine, dsda_algorithm_with_logs
from dsda.evaluation import AccuracyReport, ErrorSummary, compute_geocoding_accuracy, percentile_linear
from dsda.gis_store import GisDatabase
from dsda.metrics import (
    compute_composite_score,
    compute_proximity_similarity,
    compute_topology_similarity,
    compute_toponym_similarity,
    resolve_weights,
)
from dsda.models import (
    Anchor,
    AnchorType,
    CandidateEvaluation,
    CrashEvent,
    DSDAParameters,
    GeocodingResult,
    GeocodingStatus,
    GisNode,
    PKPost,
    Point2D,
    ResolutionMode,
    WGS84Point,
)
from dsda.text_utils import normalize_toponym, strip_accents

__all__ = [
    "DSDAEngine",
    "dsda_algorithm_with_logs",
    "GisDatabase",
    "PKPost",
    "ResolutionMode",
    "AccuracyReport",
    "ErrorSummary",
    "compute_geocoding_accuracy",
    "percentile_linear",
    "Point2D",
    "WGS84Point",
    "GisNode",
    "CrashEvent",
    "Anchor",
    "AnchorType",
    "CandidateEvaluation",
    "GeocodingResult",
    "GeocodingStatus",
    "DSDAParameters",
    "compute_composite_score",
    "compute_proximity_similarity",
    "compute_topology_similarity",
    "compute_toponym_similarity",
    "resolve_weights",
    "normalize_toponym",
    "strip_accents",
]
