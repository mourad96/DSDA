"""Example script demonstrating the DSDA algorithm capabilities."""

from datetime import datetime
from dsda import (
    Anchor,
    AnchorType,
    CrashEvent,
    DSDAParameters,
    DSDAEngine,
    GisDatabase,
    GisNode,
    Point2D,
    WGS84Point,
    dsda_algorithm_with_logs,
)


def main():
    print("=" * 80)
    print(" DSDA (Deterministic Spatial Disambiguation Algorithm) Demo")
    print("=" * 80)

    # 1. Backward-compatible POC demonstration
    print("\n[1] Running Backward-Compatible POC Call:")
    base_sig_test = [
        {"node_name": "Node P3 (Target)", "PK_marker": "PK34", "Gazetteer": "B. Khair", "Highway_Hierarchy": "RR27", "x": 500068.85, "y": 3700000, "WGS84_Coordinates": (33.881, 10.098)},
        {"node_name": "Node P1 (Bypass)", "PK_marker": "PK34", "Gazetteer": "B. K",     "Highway_Hierarchy": "RR27", "x": 500126.69, "y": 3700000, "WGS84_Coordinates": (33.882, 10.099)},
        {"node_name": "Node P2 (Parallel)","PK_marker": "PK34", "Gazetteer": "Beni",     "Highway_Hierarchy": "RR43", "x": 500151.61, "y": 3700000, "WGS84_Coordinates": (33.884, 10.102)},
        {"node_name": "Node P4 (Local)",  "PK_marker": "PK34", "Gazetteer": "Bir",      "Highway_Hierarchy": "MC28", "x": 500232.76, "y": 3700000, "WGS84_Coordinates": (33.887, 10.105)}
    ]

    poc_result = dsda_algorithm_with_logs(
        pk_marker="PK34",
        t_rep="B. Khiar",
        target_route="RR27",
        k_prev={"x": 500000, "y": 3700000},
        gis_database=base_sig_test,
    )
    print(f"Decision: {poc_result['Decision']}")
    print(f"Weights: {poc_result['Weights_Used']}")
    print("Ranked Candidates:")
    for log in poc_result["Logs"]:
        print(f"  * {log['Node']:<20} | Dist: {log['Distance_m']:<7.2f}m | S_Top: {log['S_Toponym']} | S_Prox: {log['S_Proximity']} | S_Topo: {log['S_Topology']} | Cs: {log['Cs_Score']}")

    # 2. Modern Engine & Multi-Event Corridor Sequence
    print("\n" + "=" * 80)
    print("[2] Modern Object-Oriented Corridor Processing (Demonstrating Rules 1, 2, & 3)")
    print("=" * 80)

    gis_db = GisDatabase()
    for record in base_sig_test:
        gis_db.add_node(record)

    # Add extra nodes along RR27 corridor
    gis_db.add_node(GisNode(
        node_name="Node PK33",
        pk_marker="PK33",
        gazetteer=["Nabeul Nord", "Station Nabeul"],
        highway_hierarchy="RR27",
        coords=Point2D(500000.0, 3698500.0),
        wgs84=WGS84Point(33.870, 10.090)
    ))
    gis_db.add_node(GisNode(
        node_name="Node PK35",
        pk_marker="PK35",
        gazetteer=["Korba Sud", "Plage Korba"],
        highway_hierarchy="RR27",
        coords=Point2D(500200.0, 3701500.0),
        wgs84=WGS84Point(33.895, 10.110)
    ))

    events = [
        # Event 1: Initial event -> Triggers Rule 1 (Cold Start)
        CrashEvent(
            event_id="CRASH_001",
            route="RR27",
            pk_marker="PK33",
            narrative_landmarks=["Station Nabeul"],
            timestamp=datetime(2025, 6, 1, 8, 30),
        ),
        # Event 2: Occurs 2 hours later (<24h) -> Triggers Rule 2 (Regional Municipality Centroid fallback)
        CrashEvent(
            event_id="CRASH_002",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["B. Khiar"],
            timestamp=datetime(2025, 6, 1, 10, 30),
            municipality_centroid=Point2D(500050.0, 3700020.0),
        ),
        # Event 3: Ambiguous event with erroneous landmark -> Rejected for manual review
        CrashEvent(
            event_id="CRASH_003_AMBIGUOUS",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["Unrecognized Station 99"],
            timestamp=datetime(2025, 6, 3, 9, 0),
        ),
        # Event 4: Valid event 2 days later -> Triggers Rule 3 (Anchor Independence: skips CRASH_003, reverts to CRASH_002)
        CrashEvent(
            event_id="CRASH_004",
            route="RR27",
            pk_marker="PK35",
            narrative_landmarks=["Korba Sud"],
            timestamp=datetime(2025, 6, 5, 14, 0),
        ),
    ]

    engine = DSDAEngine()
    corridor_results = engine.process_corridor(events, gis_db)

    for res in corridor_results:
        print("\n" + res.summary_table())


if __name__ == "__main__":
    main()
