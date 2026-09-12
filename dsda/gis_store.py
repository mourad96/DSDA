"""GIS Centerline database and spatial indexing for DSDA."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from dsda.models import GisNode, Point2D


class GisDatabase:
    """In-memory spatial repository indexed by PK marker for corridor centerline nodes."""

    def __init__(self, nodes: Optional[Iterable[Union[GisNode, Dict[str, Any]]]] = None) -> None:
        self._nodes_by_pk: Dict[str, List[GisNode]] = defaultdict(list)
        self._all_nodes: List[GisNode] = []
        if nodes:
            for node in nodes:
                self.add_node(node)

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

    def query_by_pk(self, pk_marker: str) -> List[GisNode]:
        """Query all candidate centerline nodes matching a given PK marker."""
        normalized_pk = self._normalize_pk(pk_marker)
        return list(self._nodes_by_pk.get(normalized_pk, []))

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
    def from_records(cls, records: Iterable[Union[GisNode, Dict[str, Any]]]) -> GisDatabase:
        """Factory method to construct a GisDatabase from an iterable of records."""
        return cls(nodes=records)
