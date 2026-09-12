"""DSDA Engine implementing the deterministic multi-criteria disambiguation and anchor state machine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

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
    Point2D,
)


class DSDAEngine:
    """Deterministic Spatial Disambiguation Algorithm (DSDA) Engine.

    Implements Equation A1, A2, A3 and the three Anchor Initialization Rules:
      Rule 1: Cold Start (route transition or uninitialized anchor).
      Rule 2: Simultaneous Events (<=24h temporal window uses regional municipality centroid).
      Rule 3: Anchor Independence (rejects Cs < 0.85 or E_geo > 50m to break error cascades).
    """

    def __init__(self, parameters: Optional[DSDAParameters] = None) -> None:
        self.params = parameters or DSDAParameters()

    def evaluate_event(
        self,
        event: CrashEvent,
        anchor: Optional[Anchor],
        candidates: Sequence[GisNode],
    ) -> GeocodingResult:
        """Evaluate candidate nodes for a single crash event against an anchor.

        Args:
            event: The crash event to geocode.
            anchor: Spatial anchor k_prev (None for Cold Start).
            candidates: List of candidate GIS centerline nodes at event's PK marker.

        Returns:
            GeocodingResult containing scores, status, and candidate logs.
        """
        if not candidates:
            return GeocodingResult(
                event_id=event.event_id,
                status=GeocodingStatus.NO_CANDIDATES,
                selected_node=None,
                best_score=0.0,
                candidate_evaluations=[],
                weights_used=resolve_weights(is_cold_start=(anchor is None), params=self.params),
                anchor_used=anchor,
                is_safe_anchor=False,
                decision_message=f"REJECTED: No candidates found for marker {event.pk_marker}",
            )

        is_cold_start = anchor is None
        weights = resolve_weights(is_cold_start=is_cold_start, params=self.params)
        anchor_point = anchor.coords if anchor is not None else None

        evaluations: List[CandidateEvaluation] = []
        best_candidate: Optional[GisNode] = None
        best_score = -1.0

        for node in candidates:
            # A. ToponymMatch (Equation A2)
            s_toponym = compute_toponym_similarity(
                extracted_landmarks=event.narrative_landmarks,
                candidate_gazetteer=node.gazetteer,
                use_normalization=True,
            )

            # B. ProximityMatch (Equation A3)
            s_proximity, dist_m = compute_proximity_similarity(
                candidate_coords=node.coords,
                anchor_coords=anchor_point,
                sigma=self.params.sigma,
            )

            # C. TopologicalMatch (Binary infrastructure filter)
            s_topology = compute_topology_similarity(
                candidate_hierarchy=node.highway_hierarchy,
                target_route=event.route,
            )

            # D. Contextual Compatibility Score Cs (Equation A1)
            cs_score = compute_composite_score(
                s_toponym=s_toponym,
                s_proximity=s_proximity,
                s_topology=s_topology,
                weights=weights,
            )

            evaluations.append(
                CandidateEvaluation(
                    node=node,
                    distance_m=dist_m,
                    s_toponym=s_toponym,
                    s_proximity=s_proximity,
                    s_topology=s_topology,
                    cs_score=cs_score,
                )
            )

            if cs_score > best_score:
                best_score = cs_score
                best_candidate = node

        # Sort candidates descending by Cs score
        evaluations.sort(key=lambda x: x.cs_score, reverse=True)

        # Spatial accuracy check E_geo if ground truth is available
        e_geo: Optional[float] = None
        e_geo_passed = True
        if best_candidate and event.ground_truth_coords is not None:
            e_geo = best_candidate.coords.distance_to(event.ground_truth_coords)
            if e_geo > self.params.e_geo_tolerance:
                e_geo_passed = False

        # Rule 3 validation threshold check
        threshold_passed = best_score >= self.params.validation_threshold
        is_validated = threshold_passed and e_geo_passed

        if is_validated and best_candidate:
            status = GeocodingStatus.AUTO_VALIDATED
            coords_desc = (
                f"{best_candidate.wgs84.to_tuple()}"
                if best_candidate.wgs84
                else f"({best_candidate.coords.x}, {best_candidate.coords.y})"
            )
            decision = f"AUTO-VALIDATED: {best_candidate.node_name} -> {coords_desc}"
        else:
            status = GeocodingStatus.MANUAL_REVIEW_REQUIRED
            reason_parts = []
            if not threshold_passed:
                reason_parts.append(f"Max score {best_score:.3f} < {self.params.validation_threshold}")
            if not e_geo_passed and e_geo is not None:
                reason_parts.append(f"E_geo {e_geo:.1f}m > {self.params.e_geo_tolerance}m tolerance")
            decision = f"REJECTED: Manual Review Required ({', '.join(reason_parts)})"

        return GeocodingResult(
            event_id=event.event_id,
            status=status,
            selected_node=best_candidate,
            best_score=best_score,
            candidate_evaluations=evaluations,
            weights_used=weights,
            anchor_used=anchor,
            e_geo=e_geo,
            is_safe_anchor=is_validated,
            decision_message=decision,
        )

    def process_corridor(
        self,
        events: Sequence[CrashEvent],
        gis_db: GisDatabase,
        sort_chronologically: bool = True,
    ) -> List[GeocodingResult]:
        """Process a sequence of crash events along a corridor applying all 3 anchor rules.

        Args:
            events: Sequence of crash events.
            gis_db: Spatial GIS centerline database.
            sort_chronologically: If True and timestamps are present, sort events by time.

        Returns:
            List of GeocodingResult objects for each event.
        """
        if not events:
            return []

        processed_events = list(events)
        if sort_chronologically and all(e.timestamp is not None for e in processed_events):
            processed_events.sort(key=lambda e: e.timestamp)  # type: ignore[arg-type]

        results: List[GeocodingResult] = []
        current_route: Optional[str] = None
        last_safe_anchor: Optional[Anchor] = None
        last_event_time: Optional[datetime] = None

        for event in processed_events:
            # Query candidate centerline nodes for the event's PK
            candidates = gis_db.query_by_pk(event.pk_marker)

            # Determine anchor using the three initialization rules:
            # Rule 1: Cold Start (route switch or first event)
            is_route_switch = (current_route is not None and current_route.strip().upper() != event.route.strip().upper())
            if last_safe_anchor is None or is_route_switch:
                anchor_for_event = None
                current_route = event.route
            else:
                # Rule 2: Simultaneous Events (tight temporal window <= 24h)
                is_simultaneous = False
                if (
                    event.timestamp is not None
                    and last_event_time is not None
                    and (event.timestamp - last_event_time) <= self.params.simultaneous_window
                ):
                    is_simultaneous = True

                if is_simultaneous and event.municipality_centroid is not None:
                    anchor_for_event = Anchor(
                        coords=event.municipality_centroid,
                        anchor_type=AnchorType.MUNICIPALITY_CENTROID,
                        source_id=f"Centroid for {event.event_id}",
                        timestamp=event.timestamp,
                    )
                else:
                    anchor_for_event = last_safe_anchor

            # Evaluate the event
            result = self.evaluate_event(event=event, anchor=anchor_for_event, candidates=candidates)
            results.append(result)

            # Rule 3: Anchor Independence
            # If auto-validated and passes tolerance, update the safe anchor;
            # otherwise reject as anchor, reverting to last_safe_anchor.
            if result.is_safe_anchor and result.selected_node is not None:
                last_safe_anchor = Anchor(
                    coords=result.selected_node.coords,
                    anchor_type=AnchorType.PRIOR_EVENT,
                    source_id=event.event_id,
                    timestamp=event.timestamp,
                )

            if event.timestamp is not None:
                last_event_time = event.timestamp

        return results


def dsda_algorithm_with_logs(
    pk_marker: str,
    t_rep: Union[str, Sequence[str]],
    target_route: str,
    k_prev: Optional[Union[Dict[str, Any], Point2D, Anchor]],
    gis_database: Union[GisDatabase, Sequence[Dict[str, Any]]],
    sigma: float = 150.0,
    threshold: float = 0.85,
) -> Dict[str, Any]:
    """Backward-compatible function matching the prototype DSDA signature.

    Args:
        pk_marker: Extracted linear marker (e.g. 'PK34').
        t_rep: Landmark narrative string or list of landmark strings.
        target_route: Highway route identifier (e.g. 'RR27').
        k_prev: Previous anchor coordinates dict {'x': ..., 'y': ...}, Point2D, or None.
        gis_database: List of node dictionaries or a GisDatabase instance.
        sigma: Proximity bandwidth in meters.
        threshold: Auto-validation threshold.

    Returns:
        Dict matching the original prototype structure:
        {'Decision': ..., 'Weights_Used': ..., 'Logs': ...}
    """
    params = DSDAParameters(sigma=sigma, validation_threshold=threshold)
    engine = DSDAEngine(params)

    # Normalize GIS database
    if isinstance(gis_database, GisDatabase):
        db = gis_database
    else:
        db = GisDatabase.from_records(gis_database)

    # Normalize anchor
    anchor: Optional[Anchor] = None
    if k_prev is not None:
        if isinstance(k_prev, Anchor):
            anchor = k_prev
        elif isinstance(k_prev, Point2D):
            anchor = Anchor(coords=k_prev, anchor_type=AnchorType.PRIOR_EVENT)
        elif isinstance(k_prev, dict):
            anchor = Anchor(
                coords=Point2D(x=float(k_prev["x"]), y=float(k_prev["y"])),
                anchor_type=AnchorType.PRIOR_EVENT,
            )

    landmarks = [t_rep] if isinstance(t_rep, str) else list(t_rep)
    event = CrashEvent(
        event_id="POC_EVENT",
        route=target_route,
        pk_marker=pk_marker,
        narrative_landmarks=landmarks,
    )

    candidates = db.query_by_pk(pk_marker)
    result = engine.evaluate_event(event, anchor, candidates)

    logs = []
    for c in result.candidate_evaluations:
        logs.append({
            "Node": c.node.node_name,
            "Route": c.node.highway_hierarchy,
            "Distance_m": round(c.distance_m, 2),
            "S_Toponym": round(c.s_toponym, 3),
            "S_Proximity": round(c.s_proximity, 3),
            "S_Topology": c.s_topology,
            "Cs_Score": round(c.cs_score, 3),
        })

    return {
        "Decision": result.decision_message,
        "Weights_Used": result.weights_used,
        "Logs": logs,
    }
