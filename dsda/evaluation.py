"""Post-hoc positional accuracy of DSDA outputs (E_geo, median, P90, P95, RMSE).

Ground-truth coordinates (RTK-DGPS) are read only here, after the engine has
produced its decisions. Nothing in this module feeds back into dsda.engine.

Two populations are reported, as in Table 5 / Table C.1:
  - conditional: records accepted by the gate (Cs >= 0.85);
  - inclusive:   every record that had at least one candidate, using the
                 top-ranked candidate whether accepted or not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

from dsda.models import GeocodingResult, GeocodingStatus, Point2D


def percentile_linear(values: Sequence[float], q: float) -> float:
    """Percentile with linear interpolation between order statistics (numpy 'linear')."""
    if not values:
        raise ValueError("percentile of an empty sequence")
    if not 0.0 <= q <= 100.0:
        raise ValueError(f"q must be in [0, 100], got {q}")
    xs = sorted(values)
    pos = (len(xs) - 1) * q / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


@dataclass
class ErrorSummary:
    n: int
    mean: float
    median: float
    p90: float
    p95: float
    rmse: float
    max: float

    @classmethod
    def from_errors(cls, errors: Sequence[float]) -> Optional["ErrorSummary"]:
        if not errors:
            return None
        n = len(errors)
        return cls(
            n=n,
            mean=sum(errors) / n,
            median=percentile_linear(errors, 50),
            p90=percentile_linear(errors, 90),
            p95=percentile_linear(errors, 95),
            rmse=math.sqrt(sum(e * e for e in errors) / n),
            max=max(errors),
        )


@dataclass
class AccuracyReport:
    n_records: int
    n_accepted: int
    acceptance_rate: float
    conditional: Optional[ErrorSummary]
    inclusive: Optional[ErrorSummary]
    per_record: List[Dict[str, object]] = field(default_factory=list)
    missing_ground_truth: List[str] = field(default_factory=list)


def compute_geocoding_accuracy(
    results: Sequence[GeocodingResult],
    ground_truth: Mapping[str, Point2D],
) -> AccuracyReport:
    """Compare DSDA outputs with ground truth, after the fact.

    Args:
        results: Engine outputs (decisions already taken).
        ground_truth: event_id -> RTK-DGPS coordinate (same projected CRS).
    """
    per_record: List[Dict[str, object]] = []
    missing: List[str] = []
    cond: List[float] = []
    incl: List[float] = []
    n_accepted = 0

    for r in results:
        accepted = r.status == GeocodingStatus.AUTO_VALIDATED
        n_accepted += int(accepted)
        gt = ground_truth.get(r.event_id)
        e_geo: Optional[float] = None
        if r.selected_node is not None and gt is not None:
            e_geo = r.selected_node.coords.distance_to(gt)
            incl.append(e_geo)
            if accepted:
                cond.append(e_geo)
        elif r.selected_node is not None:
            missing.append(r.event_id)
        per_record.append({"event_id": r.event_id, "status": r.status.value, "cs": r.best_score, "e_geo": e_geo})

    n = len(results)
    return AccuracyReport(
        n_records=n,
        n_accepted=n_accepted,
        acceptance_rate=(n_accepted / n) if n else 0.0,
        conditional=ErrorSummary.from_errors(cond),
        inclusive=ErrorSummary.from_errors(incl),
        per_record=per_record,
        missing_ground_truth=missing,
    )
