"""
Refresh the Charleston (CHS) demand data for Subway Builder.

The 1.0.0 demand (1185 points / 19301 pops, LODES-derived, with the author's
special demand) is kept as-is. What this recomputes is the commute layer:
driving distance, driving time, and the drivingPath geometry that depot 1.2.6+
writes and the current game renders. The original data has distances and
durations but no paths.

IGNORE_SCHEMA is on because the inherited special demand (ENT/UNI/AIR plus the
author's custom JBCS/JBCN/NPTC/NPTU/NWS/CGC codes) shipped without the
.railyard_map schema files, so there is nothing to validate against.

Run a single stage:   python CHS_demand.py <stage>
Stages: osrm | routes | config | all
"""
import json
import os
import shutil
import sys

from depot.demand import DemandData

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "CHS_demand")
FDEMAND = os.path.join(OUTDIR, "demand_data.json")
SOURCE_DEMAND = os.path.join(HERE, "source", "demand_data.json")
OSMPBF = os.path.join(HERE, "south-carolina-latest.osm.pbf")
BBOX = [-80.3018, 32.5526, -79.6701, 33.1133]

os.makedirs(OUTDIR, exist_ok=True)
if not os.path.exists(FDEMAND):
    shutil.copy(SOURCE_DEMAND, FDEMAND)
    print(f"seeded {FDEMAND} from the 1.0.0 release")

dd = DemandData(FDEMAND, map_code="CHS", bbox=BBOX,
                outputdir=OUTDIR, IGNORE_SCHEMA=True)


def stage_osrm():
    dd.prepare_osrm(OSMPBF, bbox=BBOX, port=5050, force_recreate=True)


def stage_routes():
    dd.print_stats()
    dd.calculate_routes(routing_method="osrm", osrm_port=5050,
                        recalculate_routes=True, include_driving_paths=True)
    dd.save()
    dd.print_stats()


def stage_config():
    dd.create_config(
        name="Charleston",
        bbox=BBOX,
        description="Revive the historic downtown of the oldest city in "
                    "South Carolina",
        creator="PSWBSF",
        version="1.1.0",
        country="US",
        initial_view_state=[-79.9381, 32.7885],
    )
    # create_config hardcodes zoom 12; the 1.0.0 map opened at 13, which is
    # the framing the registry listing also records. Keep the author's.
    fconfig = os.path.join(OUTDIR, "config.json")
    with open(fconfig) as f:
        config = json.load(f)
    config["initialViewState"]["zoom"] = 13
    with open(fconfig, "w") as f:
        json.dump(config, f, indent=4)
    print(f"set initialViewState.zoom to 13 in {fconfig}")


STAGES = {"osrm": stage_osrm, "routes": stage_routes, "config": stage_config}
STAGES["all"] = lambda: [s() for s in (stage_osrm, stage_routes, stage_config)]

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage not in STAGES:
        raise SystemExit(f"unknown stage {stage!r}; pick one of {', '.join(STAGES)}")
    print(f"===== CHS demand stage: {stage} =====", flush=True)
    STAGES[stage]()
    print(f"===== CHS demand stage {stage} complete =====", flush=True)
