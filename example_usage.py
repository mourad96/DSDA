"""Example: Algorithm 1 on the Figure 3 case and on a short synthetic corridor."""

from datetime import datetime

from dsda import (
    CrashEvent,
    DSDAEngine,
    GisDatabase,
    GisNode,
    PKPost,
    Point2D,
    WGS84Point,
    compute_geocoding_accuracy,
    dsda_algorithm_with_logs,
)

FIG3_NODES = [
    {"node_name": "Node P3 (Bridge)",  "PK_marker": "PK34", "Gazetteer": "Hydraulic bridge",  "Highway_Hierarchy": "RR27", "x": 500068.85, "y": 3700000},
    {"node_name": "Node P1 (Culvert)", "PK_marker": "PK34", "Gazetteer": "Hydraulic culvert", "Highway_Hierarchy": "RR27", "x": 500126.69, "y": 3700000},
    {"node_name": "Node P2 (RR43)",    "PK_marker": "PK34", "Gazetteer": "RR43 junction",     "Highway_Hierarchy": "RR43", "x": 500151.61, "y": 3700000},
    {"node_name": "Node P4 (MC28)",    "PK_marker": "PK34", "Gazetteer": "Farm track",        "Highway_Hierarchy": "MC28", "x": 500232.76, "y": 3700000},
]
PK34_POST = Point2D(500000.0, 3700000.0)


def main() -> None:
    print("[1] Figure 3 example (anchor = nominal PK 34 post)")
    res = dsda_algorithm_with_logs(
        pk_marker="PK34",
        t_rep="Hydraulic bridge (PK 34)",
        target_route="RR27",
        k_pk={"x": PK34_POST.x, "y": PK34_POST.y},
        gis_database=FIG3_NODES,
    )
    print(f"Mode: {res['Mode']} | Weights: {res['Weights_Used']}")
    for log in res["Logs"]:
        print(f"  {log['Node']:<18} d={log['Distance_m']:>7.2f} m  S_top={log['S_Toponym']:.3f}  "
              f"S_prox={log['S_Proximity']:.3f}  S_topo={log['S_Topology']:.1f}  Cs={log['Cs_Score']:.3f}")
    print(f"Decision: {res['Decision']}")

    print("\n[2] Synthetic corridor")
    db = GisDatabase.from_records(FIG3_NODES, pk_posts=[
        PKPost("RR27", "PK33", Point2D(500000.0, 3698500.0)),
        PKPost("RR27", "PK34", PK34_POST),
        PKPost("RR27", "PK35", Point2D(500200.0, 3701500.0)),
    ])
    db.add_node(GisNode("Node PK33", "PK33", ["Maamoura Sud"], "RR27", Point2D(500000.0, 3698500.0), WGS84Point(33.870, 10.090)))
    db.add_node(GisNode("Node PK35", "PK35", ["El Mazraa Nord"], "RR27", Point2D(500200.0, 3701500.0), WGS84Point(33.895, 10.110)))

    events = [
        CrashEvent("CRASH_001", "RR27", "PK33", ["Maamoura Sud"], datetime(2025, 6, 1, 8, 30)),
        CrashEvent("CRASH_002", "RR27", "PK34", ["Hydraulic bridge"], datetime(2025, 6, 1, 10, 30)),
        CrashEvent("CRASH_003", "RR27", "PK34", ["Unrecognized Station 99"], datetime(2025, 6, 3, 9, 0)),
        CrashEvent("CRASH_004", "RR27", None, ["El Mazraa Nord"], datetime(2025, 6, 5, 14, 0)),  # PK omitted
    ]
    results = DSDAEngine().process_corridor(events, db)
    for r in results:
        print("\n" + r.summary_table())

    # Post-hoc accuracy (illustrative ground truth)
    gt = {
        "CRASH_001": Point2D(500010.0, 3698505.0),
        "CRASH_002": Point2D(500075.0, 3700004.0),
        "CRASH_003": Point2D(500090.0, 3700000.0),
        "CRASH_004": Point2D(500195.0, 3701510.0),
    }
    rep = compute_geocoding_accuracy(results, gt)
    print(f"\nAccepted: {rep.n_accepted}/{rep.n_records}")
    print(f"Conditional: {rep.conditional}")
    print(f"Inclusive:   {rep.inclusive}")


if __name__ == "__main__":
    main()
