"""DSDA engine: implementation of Algorithm 1 (Appendix A.2), stateless.

Step 1  Sector reference: sector_ref <- k_municipality (no state carried
        between records; results do not depend on processing order).
Step 2  Candidate generation:
        PK marker resolved on the route       -> primary LRS-anchored mode:
            active anchor = nominal PK post k_PK, candidates = all nodes
            (all routes) within R_max = 500 m, base weights (0.500, 0.375, 0.125).
        otherwise                             -> fallback mode:
            no proximity anchor, route nodes in the municipal sector,
            weights (0.875, 0.000, 0.125).
Step 3  Gaussian proximity decay to k_PK (sigma = 150 m).
Step 4  Intersection pass: w1 <- w1 + w3, w3 <- 0.
        Deterministic tie-breaking: highest Cs, then smallest distance d to
        the active anchor (d = 0 for every candidate in fallback mode), then
        lexicographic Node_ID (node_name).
Step 5  Acceptance gate Cs >= 0.85; otherwise manual review.

Ground-truth coordinates are never used here. Positional accuracy
(E_geo, P90, P95) is computed post hoc in dsda.evaluation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

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
    ResolutionMode,
)


class DSDAEngine:
    """Deterministic Spatial Disambiguation Algorithm (Algorithm 1)."""

    def __init__(self, parameters: Optional[DSDAParameters] = None) -> None:
        self.params = parameters or DSDAParameters()

    # ------------------------------------------------------------------
    # Steps 3 to 5 for one event, given its candidates and anchor
    # ------------------------------------------------------------------
    def evaluate_event(
        self,
        event: CrashEvent,
        candidates: Sequence[GisNode],
        pk_anchor: Optional[Anchor] = None,
        mode: Optional[ResolutionMode] = None,
        sector_reference: Optional[Anchor] = None,
    ) -> GeocodingResult:
        """Score candidates and apply the acceptance gate.

        Args:
            event: Crash event (route, PK, landmarks, intersection flag).
            candidates: Candidate centerline nodes (from step 2).
            pk_anchor: Nominal PK post k_PK (None in fallback mode).
            mode: Resolution mode; inferred from pk_anchor when omitted.
            sector_reference: Sector reference used in step 1 (for traceability).
        """
        if mode is None:
            mode = ResolutionMode.LRS_ANCHORED if pk_anchor is not None else ResolutionMode.SECTOR_FALLBACK
        weights = resolve_weights(
            is_fallback=(pk_anchor is None),
            params=self.params,
            intersection=event.intersection_descriptors,
        )

        if pk_anchor is None and self.params.fallback_policy == "reject":
            return GeocodingResult(
                event_id=event.event_id,
                status=GeocodingStatus.MANUAL_REVIEW_REQUIRED,
                selected_node=None,
                best_score=0.0,
                candidate_evaluations=[],
                weights_used=weights,
                anchor_used=None,
                mode=mode,
                sector_reference=sector_reference,
                accepted=False,
                decision_message="REJECTED: Manual Review Required (no resolvable PK marker)",
            )

        if not candidates:
            return GeocodingResult(
                event_id=event.event_id,
                status=GeocodingStatus.NO_CANDIDATES,
                selected_node=None,
                best_score=0.0,
                candidate_evaluations=[],
                weights_used=weights,
                anchor_used=pk_anchor,
                mode=mode,
                sector_reference=sector_reference,
                accepted=False,
                decision_message=f"REJECTED: No candidates found for marker {event.pk_marker}",
            )

        anchor_point = pk_anchor.coords if pk_anchor is not None else None
        evaluations: List[CandidateEvaluation] = []

        for node in candidates:
            s_toponym = compute_toponym_similarity(
                extracted_landmarks=event.narrative_landmarks,
                candidate_gazetteer=node.gazetteer,
                use_normalization=True,
            )
            if anchor_point is None or weights["w2"] == 0.0:
                s_proximity = 0.0
                # d is still measured to k_PK when it exists (tie-breaking);
                # in fallback mode there is no anchor and d = 0 for all nodes.
                dist_m = node.coords.distance_to(anchor_point) if anchor_point is not None else 0.0
            else:
                s_proximity, dist_m = compute_proximity_similarity(
                    candidate_coords=node.coords,
                    anchor_coords=anchor_point,
                    sigma=self.params.sigma,
                )
            s_topology = compute_topology_similarity(
                candidate_hierarchy=node.highway_hierarchy,
                target_route=event.route,
            )
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

        # Deterministic tie-breaking: highest Cs, then smallest d, then Node_ID.
        # Equivalent to the loop of Algorithm 1 and independent of the order
        # in which candidates are returned by the GIS query.
        evaluations.sort(key=_ranking_key)
        best_candidate = evaluations[0].node
        best_score = evaluations[0].cs_score

        # Step 5: acceptance gate, based on Cs only
        accepted = best_candidate is not None and best_score >= self.params.validation_threshold
        if accepted:
            coords_desc = (
                f"{best_candidate.wgs84.to_tuple()}"
                if best_candidate.wgs84
                else f"({best_candidate.coords.x}, {best_candidate.coords.y})"
            )
            status = GeocodingStatus.AUTO_VALIDATED
            decision = f"AUTO-VALIDATED: {best_candidate.node_name} -> {coords_desc}"
        else:
            status = GeocodingStatus.MANUAL_REVIEW_REQUIRED
            decision = (
                "REJECTED: Manual Review Required "
                f"(Low Confidence Score, Cs {best_score:.3f} < {self.params.validation_threshold})"
            )

        return GeocodingResult(
            event_id=event.event_id,
            status=status,
            selected_node=best_candidate,
            best_score=best_score,
            candidate_evaluations=evaluations,
            weights_used=weights,
            anchor_used=pk_anchor,
            mode=mode,
            sector_reference=sector_reference,
            accepted=accepted,
            decision_message=decision,
        )

    # ------------------------------------------------------------------
    # Steps 1 and 2
    # ------------------------------------------------------------------
    @staticmethod
    def sector_reference(event: CrashEvent) -> Optional[Anchor]:
        """Step 1 (stateless): sector_ref <- k_municipality."""
        if event.municipality_centroid is None:
            return None
        return Anchor(
            coords=event.municipality_centroid,
            anchor_type=AnchorType.MUNICIPALITY_CENTROID,
            source_id=f"Centroid for {event.event_id}",
            route=event.route,
        )

    def resolve_event(self, event: CrashEvent, gis_db: GisDatabase) -> GeocodingResult:
        """Steps 1 to 5 for one event (no dependence on other records)."""
        sector_ref = self.sector_reference(event)
        sector_point = sector_ref.coords if sector_ref is not None else None

        post = gis_db.resolve_pk_post(event.route, event.pk_marker, sector_point)
        if post is not None:
            pk_anchor = Anchor(
                coords=post.coords,
                anchor_type=AnchorType.PK_POST,
                source_id=f"{post.route} {post.pk_marker}",
                route=post.route,
            )
            candidates = gis_db.query_within_radius(post.coords, self.params.r_max)
            mode = ResolutionMode.LRS_ANCHORED
        else:
            pk_anchor = None
            candidates = gis_db.query_in_sector(event.route, sector_point, self.params.sector_radius)
            mode = ResolutionMode.SECTOR_FALLBACK

        return self.evaluate_event(
            event,
            candidates,
            pk_anchor=pk_anchor,
            mode=mode,
            sector_reference=sector_ref,
        )

    def process_corridor(
        self,
        events: Sequence[CrashEvent],
        gis_db: GisDatabase,
    ) -> List[GeocodingResult]:
        """Process a corridor record by record (stateless, results in input order)."""
        return [self.resolve_event(event, gis_db) for event in events]


def _ranking_key(c: CandidateEvaluation):
    return (-c.cs_score, c.distance_m, c.node.node_name)


def _norm(route: Optional[str]) -> str:
    return "".join((route or "").split()).upper()


def dsda_algorithm_with_logs(
    pk_marker: str,
    t_rep: Union[str, Sequence[str]],
    target_route: str,
    k_pk: Optional[Union[Dict[str, Any], Point2D, Anchor]],
    gis_database: Union[GisDatabase, Sequence[Dict[str, Any]]],
    sigma: float = 150.0,
    threshold: float = 0.85,
    r_max: float = 500.0,
    intersection_descriptors: bool = False,
) -> Dict[str, Any]:
    """Single-event entry point (prototype signature, updated to Algorithm 1).

    Args:
        pk_marker: Extracted linear marker (e.g. 'PK34').
        t_rep: Landmark string or list of landmark strings.
        target_route: Highway route identifier (e.g. 'RR27').
        k_pk: Nominal coordinate of the PK post (dict {'x','y'}, Point2D or
            Anchor). None means the post is unknown: fallback mode, candidates
            are the nodes indexed under pk_marker, w2 = 0.
        gis_database: List of node dictionaries or a GisDatabase instance.
        sigma: Proximity bandwidth in meters.
        threshold: Acceptance threshold on Cs.
        r_max: Candidate buffer around k_PK in meters.
        intersection_descriptors: Intersection flag extracted by the MLLM.

    Returns:
        {'Decision': ..., 'Weights_Used': ..., 'Mode': ..., 'Logs': [...]}
    """
    params = DSDAParameters(sigma=sigma, validation_threshold=threshold, r_max=r_max)
    engine = DSDAEngine(params)
    db = gis_database if isinstance(gis_database, GisDatabase) else GisDatabase.from_records(gis_database)

    anchor: Optional[Anchor] = None
    if k_pk is not None:
        if isinstance(k_pk, Anchor):
            anchor = k_pk
        elif isinstance(k_pk, Point2D):
            anchor = Anchor(coords=k_pk, anchor_type=AnchorType.PK_POST, route=target_route)
        elif isinstance(k_pk, dict):
            anchor = Anchor(
                coords=Point2D(x=float(k_pk["x"]), y=float(k_pk["y"])),
                anchor_type=AnchorType.PK_POST,
                route=target_route,
            )

    landmarks = [t_rep] if isinstance(t_rep, str) else list(t_rep)
    event = CrashEvent(
        event_id="POC_EVENT",
        route=target_route,
        pk_marker=pk_marker,
        narrative_landmarks=landmarks,
        intersection_descriptors=intersection_descriptors,
    )

    if anchor is not None:
        candidates = db.query_within_radius(anchor.coords, params.r_max)
        mode = ResolutionMode.LRS_ANCHORED
    else:
        candidates = db.query_by_pk(pk_marker)
        mode = ResolutionMode.SECTOR_FALLBACK
    result = engine.evaluate_event(event, candidates, pk_anchor=anchor, mode=mode)

    logs = [
        {
            "Node": c.node.node_name,
            "Route": c.node.highway_hierarchy,
            "Distance_m": round(c.distance_m, 2),
            "S_Toponym": round(c.s_toponym, 3),
            "S_Proximity": round(c.s_proximity, 3),
            "S_Topology": c.s_topology,
            "Cs_Score": round(c.cs_score, 3),
        }
        for c in result.candidate_evaluations
    ]
    return {
        "Decision": result.decision_message,
        "Weights_Used": result.weights_used,
        "Mode": result.mode.value,
        "Logs": logs,
    }
