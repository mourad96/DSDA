"""Shared test fixtures for the DSDA test suite.

The single-event example (PK 34 on RR27) is the illustrative case drawn in
Figure 3 of the manuscript: four synthetic candidate nodes around the nominal
PK 34 post k_PK = (500000, 3700000), landmark "Hydraulic bridge (PK 34)".
"""

import pytest
from dsda.gis_store import GisDatabase
from dsda.models import GisNode, PKPost, Point2D, WGS84Point

PK34_POST = Point2D(500000.0, 3700000.0)


@pytest.fixture
def poc_base_sig_dicts():
    """Figure 3 example: candidate nodes around the PK 34 post."""
    return [
        {
            "node_name": "Node P3 (Bridge)",
            "PK_marker": "PK34",
            "Gazetteer": "Hydraulic bridge",
            "Highway_Hierarchy": "RR27",
            "x": 500068.85,
            "y": 3700000,
            "WGS84_Coordinates": (33.881, 10.098),
        },
        {
            "node_name": "Node P1 (Culvert)",
            "PK_marker": "PK34",
            "Gazetteer": "Hydraulic culvert",
            "Highway_Hierarchy": "RR27",
            "x": 500126.69,
            "y": 3700000,
            "WGS84_Coordinates": (33.882, 10.099),
        },
        {
            "node_name": "Node P2 (RR43)",
            "PK_marker": "PK34",
            "Gazetteer": "RR43 junction",
            "Highway_Hierarchy": "RR43",
            "x": 500151.61,
            "y": 3700000,
            "WGS84_Coordinates": (33.884, 10.102),
        },
        {
            "node_name": "Node P4 (MC28)",
            "PK_marker": "PK34",
            "Gazetteer": "Farm track",
            "Highway_Hierarchy": "MC28",
            "x": 500232.76,
            "y": 3700000,
            "WGS84_Coordinates": (33.887, 10.105),
        },
    ]


@pytest.fixture
def pk34_post():
    return PK34_POST


@pytest.fixture
def poc_gis_database(poc_base_sig_dicts):
    """GisDatabase with the Figure 3 nodes and the PK 34 post."""
    return GisDatabase.from_records(
        poc_base_sig_dicts,
        pk_posts=[PKPost(route="RR27", pk_marker="PK34", coords=PK34_POST)],
    )


@pytest.fixture
def corridor_gis_db():
    """Multi-PK synthetic corridor along RR27 (posts every 1.5 km) plus MC28."""
    nodes = [
        GisNode(
            node_name="RR27_PK33_A",
            pk_marker="PK33",
            gazetteer=["Maamoura Sud"],
            highway_hierarchy="RR27",
            coords=Point2D(500000.0, 3698500.0),
            wgs84=WGS84Point(33.870, 10.090),
        ),
        GisNode(
            node_name="RR27_PK34_Bridge",
            pk_marker="PK34",
            gazetteer=["Hydraulic bridge", "Pont hydraulique"],
            highway_hierarchy="RR27",
            coords=Point2D(500068.85, 3700000.0),
            wgs84=WGS84Point(33.881, 10.098),
        ),
        GisNode(
            node_name="RR27_PK34_Culvert",
            pk_marker="PK34",
            gazetteer=["Hydraulic culvert"],
            highway_hierarchy="RR27",
            coords=Point2D(500126.69, 3700000.0),
            wgs84=WGS84Point(33.882, 10.099),
        ),
        GisNode(
            node_name="RR43_PK34_Cross",
            pk_marker="PK34",
            gazetteer=["RR43 junction"],
            highway_hierarchy="RR43",
            coords=Point2D(500151.61, 3700000.0),
            wgs84=WGS84Point(33.884, 10.102),
        ),
        GisNode(
            node_name="RR27_PK35_Main",
            pk_marker="PK35",
            gazetteer=["El Mazraa Nord"],
            highway_hierarchy="RR27",
            coords=Point2D(500200.0, 3701500.0),
            wgs84=WGS84Point(33.895, 10.110),
        ),
        GisNode(
            node_name="MC28_PK10",
            pk_marker="PK10",
            gazetteer=["Grombalia Centre"],
            highway_hierarchy="MC28",
            coords=Point2D(480000.0, 3720000.0),
            wgs84=WGS84Point(34.010, 9.950),
        ),
    ]
    posts = [
        PKPost(route="RR27", pk_marker="PK33", coords=Point2D(500000.0, 3698500.0)),
        PKPost(route="RR27", pk_marker="PK34", coords=PK34_POST),
        PKPost(route="RR27", pk_marker="PK35", coords=Point2D(500200.0, 3701500.0)),
        PKPost(route="MC28", pk_marker="PK10", coords=Point2D(480000.0, 3720000.0)),
    ]
    return GisDatabase(nodes, pk_posts=posts)
