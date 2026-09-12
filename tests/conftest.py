"""Shared test fixtures for the DSDA test suite."""

import pytest
from dsda.gis_store import GisDatabase
from dsda.models import GisNode, Point2D, WGS84Point


@pytest.fixture
def poc_base_sig_dicts():
    """Exact test dataset from the prototype POC."""
    return [
        {
            "node_name": "Node P3 (Target)",
            "PK_marker": "PK34",
            "Gazetteer": "B. Khair",
            "Highway_Hierarchy": "RR27",
            "x": 500068.85,
            "y": 3700000,
            "WGS84_Coordinates": (33.881, 10.098),
        },
        {
            "node_name": "Node P1 (Bypass)",
            "PK_marker": "PK34",
            "Gazetteer": "B. K",
            "Highway_Hierarchy": "RR27",
            "x": 500126.69,
            "y": 3700000,
            "WGS84_Coordinates": (33.882, 10.099),
        },
        {
            "node_name": "Node P2 (Parallel)",
            "PK_marker": "PK34",
            "Gazetteer": "Beni",
            "Highway_Hierarchy": "RR43",
            "x": 500151.61,
            "y": 3700000,
            "WGS84_Coordinates": (33.884, 10.102),
        },
        {
            "node_name": "Node P4 (Local)",
            "PK_marker": "PK34",
            "Gazetteer": "Bir",
            "Highway_Hierarchy": "MC28",
            "x": 500232.76,
            "y": 3700000,
            "WGS84_Coordinates": (33.887, 10.105),
        },
    ]


@pytest.fixture
def poc_gis_database(poc_base_sig_dicts):
    """GisDatabase instance loaded with the POC test nodes."""
    return GisDatabase.from_records(poc_base_sig_dicts)


@pytest.fixture
def corridor_gis_db():
    """Multi-PK corridor database along RR27 and adjacent routes."""
    nodes = [
        # PK33 nodes
        GisNode(
            node_name="RR27_PK33_A",
            pk_marker="PK33",
            gazetteer=["Nabeul Nord", "Station Nabeul"],
            highway_hierarchy="RR27",
            coords=Point2D(500000.0, 3698500.0),
            wgs84=WGS84Point(33.870, 10.090),
        ),
        # PK34 nodes
        GisNode(
            node_name="RR27_PK34_Main",
            pk_marker="PK34",
            gazetteer=["Béni Khiar", "B. Khiar", "Centre Béni Khiar"],
            highway_hierarchy="RR27",
            coords=Point2D(500068.85, 3700000.0),
            wgs84=WGS84Point(33.881, 10.098),
        ),
        GisNode(
            node_name="RR27_PK34_Bypass",
            pk_marker="PK34",
            gazetteer=["B. K Deviateur"],
            highway_hierarchy="RR27",
            coords=Point2D(500126.69, 3700000.0),
            wgs84=WGS84Point(33.882, 10.099),
        ),
        GisNode(
            node_name="RR43_PK34_Cross",
            pk_marker="PK34",
            gazetteer=["Beni"],
            highway_hierarchy="RR43",
            coords=Point2D(500151.61, 3700000.0),
            wgs84=WGS84Point(33.884, 10.102),
        ),
        # PK35 nodes
        GisNode(
            node_name="RR27_PK35_Main",
            pk_marker="PK35",
            gazetteer=["Korba Sud", "Plage Korba"],
            highway_hierarchy="RR27",
            coords=Point2D(500200.0, 3701500.0),
            wgs84=WGS84Point(33.895, 10.110),
        ),
        # MC28 nodes (different route)
        GisNode(
            node_name="MC28_PK10",
            pk_marker="PK10",
            gazetteer=["Grombalia Centre"],
            highway_hierarchy="MC28",
            coords=Point2D(480000.0, 3720000.0),
            wgs84=WGS84Point(34.010, 9.950),
        ),
    ]
    return GisDatabase(nodes)
