"""GIS Centerline database and spatial indexing for DSDA."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from dsda.models import GisNode, PKPost, Point2D


class GisDatabase:
    """In-memory spatial repository indexed by PK marker for corridor centerline nodes."""

    def __init__(
        self,
        nodes: Optional[Iterable[Union[GisNode, Dict[str, Any]]]] = None,
        pk_posts: Optional[Iterable[PKPost]] = None,
    ) -> None:
        self._nodes_by_pk: Dict[str, List[GisNode]] = defaultdict(list)
        self._all_nodes: List[GisNode] = []
        self._pk_posts: Dict[tuple, List[PKPost]] = defaultdict(list)
        if nodes:
            for node in nodes:
                self.add_node(node)
        if pk_posts:
            for post in pk_posts:
                self.add_pk_post(post)

    def add_node(self, node: Union[GisNode, Dict[str, Any]]) -> GisNode:
        """Add a GIS node to the database."""
        if isinstance(node, dict):
            gis_node = GisNode.from_dict(node)
        elif isinstance(node, GisNode):
            gis_node = node
        else:
            raise TypeError(f"Expected GisNode or dict, got {type(node)}")

        normalized_pk = self._normalize_pk(gis_node.pk_marker)
        self._nodes_by_pk[normalized_pk].append(gis_node)
        self._all_nodes.append(gis_node)
        return gis_node

    @staticmethod
    def _normalize_pk(pk: str) -> str:
        """Normalize PK marker format (e.g. 'PK 34' -> 'PK34', case-insensitive)."""
        return "".join(pk.split()).upper()

    @staticmethod
    def _normalize_route(route: str) -> str:
        return "".join(route.split()).upper()

    def query_by_pk(self, pk_marker: str) -> List[GisNode]:
        """Query all centerline nodes indexed under a given PK marker (legacy lookup)."""
        normalized_pk = self._normalize_pk(pk_marker)
        return list(self._nodes_by_pk.get(normalized_pk, []))

    # ------------------------------------------------------------------
    # Nominal kilometric posts k_PK (Algorithm 1, step 2)
    # ------------------------------------------------------------------
    def add_pk_post(self, post: PKPost) -> PKPost:
        """Register the nominal coordinate of a kilometric post on a route."""
        key = (self._normalize_route(post.route), self._normalize_pk(post.pk_marker))
        self._pk_posts[key].append(post)
        return post

    def get_pk_posts(self, route: str, pk_marker: str) -> List[PKPost]:
        """All registered posts carrying this PK label on this route."""
        key = (self._normalize_route(route), self._normalize_pk(pk_marker))
        return list(self._pk_posts.get(key, []))

    def resolve_pk_post(
        self,
        route: str,
        pk_marker: Optional[str],
        sector_ref: Optional[Point2D] = None,
    ) -> Optional[PKPost]:
        """Get_Nominal_LRS_Post_Coordinate(PK_marker, Route_ID, sector_ref).

        Returns the unique post for (route, PK). When several posts share the
        same label (e.g. local and national chainages), the one nearest to the
        sector reference is returned; without a sector reference the marker is
        ambiguous and None is returned (fallback mode).
        """
        if not pk_marker or not pk_marker.strip():
            return None
        posts = self.get_pk_posts(route, pk_marker)
        if not posts:
            return None
        if len(posts) == 1:
            return posts[0]
        if sector_ref is None:
            return None
        return min(posts, key=lambda p: p.coords.distance_to(sector_ref))

    # ------------------------------------------------------------------
    # Candidate generation
    # ------------------------------------------------------------------
    def query_within_radius(self, center: Point2D, radius: float) -> List[GisNode]:
        """Query_GIS_Nodes_Within_Radius: every node (any route) with d <= radius.

        Nodes of other routes are kept on purpose: their topology score is 0,
        which is what penalizes parallel or crossing roads.
        """
        found = [n for n in self._all_nodes if n.coords.distance_to(center) <= radius]
        return sorted(found, key=lambda n: n.coords.distance_to(center))

    def query_in_sector(
        self,
        route: str,
        sector_ref: Optional[Point2D],
        radius: float,
    ) -> List[GisNode]:
        """Query_GIS_Nodes_In_Sector: route nodes within `radius` of the sector reference.

        Without a sector reference, all nodes of the route are returned.
        """
        norm_route = self._normalize_route(route)
        nodes = [n for n in self._all_nodes if self._normalize_route(n.highway_hierarchy) == norm_route]
        if sector_ref is None:
            return nodes
        return [n for n in nodes if n.coords.distance_to(sector_ref) <= radius]

    def find_nearest_node(
        self,
        point: Point2D,
        route: Optional[str] = None,
    ) -> Optional[GisNode]:
        """Find the spatially nearest node in the database, optionally filtering by route."""
        candidates = self._all_nodes
        if route is not None:
            norm_route = route.strip().upper()
            candidates = [n for n in candidates if n.highway_hierarchy.strip().upper() == norm_route]

        if not candidates:
            return None

        return min(candidates, key=lambda n: n.coords.distance_to(point))

    def __len__(self) -> int:
        return len(self._all_nodes)

    def __iter__(self):
        return iter(self._all_nodes)

    @classmethod
    def from_records(
        cls,
        records: Iterable[Union[GisNode, Dict[str, Any]]],
        pk_posts: Optional[Iterable[PKPost]] = None,
    ) -> GisDatabase:
        """Factory method to construct a GisDatabase from an iterable of records."""
        return cls(nodes=records, pk_posts=pk_posts)
