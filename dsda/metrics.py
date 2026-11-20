"""Mathematical implementations of the DSDA similarity components (Appendix A.1)."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import jellyfish

from dsda.models import DSDAParameters, Point2D
from dsda.text_utils import normalize_toponym


def compute_toponym_similarity(
    extracted_landmarks: Sequence[str],
    candidate_gazetteer: Sequence[str],
    use_normalization: bool = True,
) -> float:
    """Compute ToponymMatch S_toponym (Equation A2).

    S_toponym(m_k) = max_{m in T_rep, g in T_gis(k)} [ d_jw(m, g) ]

    Args:
        extracted_landmarks: Narrative landmarks T_rep extracted from crash description.
        candidate_gazetteer: GIS centerline node attributes T_gis(k).
        use_normalization: Whether to also compare normalized strings to handle
            accents, case variations, and punctuation differences.

    Returns:
        Maximum Jaro-Winkler similarity in [0.0, 1.0].
    """
    if not extracted_landmarks or not candidate_gazetteer:
        return 0.0

    best_sim = 0.0

    for m in extracted_landmarks:
        if not m or not m.strip():
            continue
        m_str = m.strip()
        m_norm = normalize_toponym(m_str) if use_normalization else ""

        for g in candidate_gazetteer:
            if not g or not g.strip():
                continue
            g_str = g.strip()

            # Raw string similarity
            sim = jellyfish.jaro_winkler_similarity(m_str, g_str)
            if sim > best_sim:
                best_sim = sim

            # Normalized string similarity if enabled
            if use_normalization and m_norm:
                g_norm = normalize_toponym(g_str)
                if g_norm:
                    norm_sim = jellyfish.jaro_winkler_similarity(m_norm, g_norm)
                    if norm_sim > best_sim:
                        best_sim = norm_sim

    return min(1.0, max(0.0, best_sim))


def compute_proximity_similarity(
    candidate_coords: Point2D,
    anchor_coords: Optional[Point2D],
    sigma: float = 150.0,
) -> Tuple[float, float]:
    """Compute ProximityMatch S_proximity (Equation A3).

    S_proximity(l_k) = exp( - d(k, k_PK)^2 / (2 * sigma^2) )

    Args:
        candidate_coords: Spatial coordinates of candidate node k.
        anchor_coords: Nominal PK post coordinate k_PK (None in fallback mode).
        sigma: Structural bandwidth in meters (default 150.0 m).

    Returns:
        Tuple of (S_proximity, distance_in_meters).
        If anchor_coords is None, returns (0.0, 0.0).
    """
    if anchor_coords is None:
        return 0.0, 0.0

    if sigma <= 0:
        raise ValueError(f"Bandwidth sigma must be > 0, got {sigma}")

    distance = candidate_coords.distance_to(anchor_coords)
    s_proximity = math.exp(-(distance**2) / (2.0 * (sigma**2)))
    return s_proximity, distance


def compute_topology_similarity(
    candidate_hierarchy: str,
    target_route: str,
) -> float:
    """Compute TopologyMatch S_topology (Binary infrastructure filter).

    Returns 1.0 if candidate k connects directly to the designated highway hierarchy,
    else 0.0. Corridors are modeled as bidirectional single-carriageways.

    Args:
        candidate_hierarchy: Route / highway classification of candidate node k.
        target_route: Designated route identifier of the crash event.

    Returns:
        1.0 if match, 0.0 otherwise.
    """
    if not candidate_hierarchy or not target_route:
        return 0.0

    # Normalization for case-insensitive matching and whitespace
    cand_norm = candidate_hierarchy.strip().upper()
    target_norm = target_route.strip().upper()

    return 1.0 if cand_norm == target_norm else 0.0


def resolve_weights(
    is_fallback: bool,
    params: DSDAParameters,
    intersection: bool = False,
) -> Dict[str, float]:
    """Determine multi-criteria weights (Algorithm 1, steps 2 and 4).

    Primary LRS-anchored mode: base weights (w1, w2, w3), by default
    (0.500, 0.375, 0.125). Fallback mode (no k_PK anchor): w2 = 0 and its
    weight is transferred to toponymy, by default (0.875, 0.000, 0.125)
    (see DSDAParameters.fallback_weights).

    Adaptive intersection pass: when the MLLM flags intersection_descriptors,
    w1 absorbs w3 and w3 is set to 0.

    Args:
        is_fallback: True when no proximity anchor k_PK is available.
        params: Configured DSDA parameters.
        intersection: Value of the intersection_descriptors flag.

    Returns:
        Dictionary with keys 'w1', 'w2', 'w3'.
    """
    if is_fallback:
        w = params.fallback_weights()
    else:
        w = {"w1": params.w1, "w2": params.w2, "w3": params.w3}
    if intersection:
        w = {"w1": w["w1"] + w["w3"], "w2": w["w2"], "w3": 0.0}
    return w


def compute_composite_score(
    s_toponym: float,
    s_proximity: float,
    s_topology: float,
    weights: Dict[str, float],
) -> float:
    """Compute the Contextual Compatibility Score Cs (Equation A1).

    Cs_k = w1 * S_toponym(m_k) + w2 * S_proximity(l_k) + w3 * S_topology(t_k)
    """
    return (
        weights["w1"] * s_toponym
        + weights["w2"] * s_proximity
        + weights["w3"] * s_topology
    )
