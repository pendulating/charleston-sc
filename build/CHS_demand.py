"""
Build the Charleston (CHS) demand data for Subway Builder.

Base demand comes from slurry's US Demand Generator over LODES 2023 for the
tri-county bbox (see ../us-demand/Charleston.json), which is regenerated
whenever the map bbox changes. This script layers the special demand on top
with depot, recomputes commutes through a local OSRM server, and writes
config.json.

Special demand lives in special/pois.py. Adding it through depot rather than
by hand is what produces the .railyard_map/special_demand_*.json schema files,
which the 1.0.0 and 1.1.0 maps never shipped -- without them the game has no
type information for these points.

Run a single stage:   python CHS_demand.py <stage>
Stages: seed | special | osrm | routes | config | all
"""
import json
import os
import shutil
import sys

from depot.demand import DemandData

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from special import pois as POIS

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "CHS_demand")
FDEMAND = os.path.join(OUTDIR, "demand_data.json")
BASE_DEMAND = os.path.join(HERE, os.pardir, "us-demand", "demand_data",
                           "Charleston", "demand_data.json")
OSMPBF = os.path.join(HERE, "south-carolina-latest.osm.pbf")
BBOX = [-80.68, 32.47, -79.43, 33.43]
OSRM_PORT = 5050

os.makedirs(OUTDIR, exist_ok=True)


def stage_seed():
    """Copy the generator's LODES output in as the starting point."""
    shutil.copy(BASE_DEMAND, FDEMAND)
    d = json.load(open(FDEMAND))
    print(f"seeded from {BASE_DEMAND}")
    print(f"  {len(d['points']):,} points  {len(d['pops']):,} pops  "
          f"{sum(p['size'] for p in d['pops']):,} commuters")


def _load():
    return DemandData(FDEMAND, map_code="CHS", bbox=BBOX, outputdir=OUTDIR)


def stage_special():
    dd = _load()
    before_pts, before_pops = len(dd["points"]), len(dd["pops"])
    before_size = sum(p["size"] for p in dd["pops"])

    pois = POIS.all_pois()
    print(f"adding {len(pois)} special demand points")
    dd.add_points(pois)
    dd.save()

    after_size = sum(p["size"] for p in dd["pops"])
    print(f"\npoints {before_pts:,} -> {len(dd['points']):,}"
          f"   pops {before_pops:,} -> {len(dd['pops']):,}"
          f"   people {before_size:,} -> {after_size:,}")


def stage_osrm():
    """
    depot's prepare_osrm publishes -p <port>:<port>, but osrm-routed listens on
    5000 inside the container, so only the default port ever connects. Do the
    extract and preprocessing through depot, then start the router by hand.
    """
    dd = _load()
    dd.prepare_osrm(OSMPBF, bbox=BBOX, port=OSRM_PORT, force_recreate=True)


def stage_routes():
    dd = _load()
    dd.print_stats()
    dd.calculate_routes(routing_method="osrm", osrm_port=OSRM_PORT,
                        recalculate_routes=True, include_driving_paths=True)
    dd.save()
    dd.print_stats()


def stage_config():
    dd = _load()
    dd.create_config(
        name="Charleston",
        bbox=BBOX,
        description="Revive the historic downtown of the oldest city in "
                    "South Carolina",
        creator="PSWBSF",
        version="1.2.0",
        country="US",
        initial_view_state=[-79.9381, 32.7885],
    )
    # create_config hardcodes zoom 12; the 1.0.0 map opened at 13, which is
    # the framing the registry listing also records. Keep the author's.
    fconfig = os.path.join(OUTDIR, "config.json")
    config = json.load(open(fconfig))
    config["initialViewState"]["zoom"] = 13
    json.dump(config, open(fconfig, "w"), indent=4)
    print(f"set initialViewState.zoom to 13 in {fconfig}")


STAGES = {"seed": stage_seed, "special": stage_special, "osrm": stage_osrm,
          "routes": stage_routes, "config": stage_config}
STAGES["all"] = lambda: [s() for s in (stage_seed, stage_special, stage_osrm,
                                       stage_routes, stage_config)]

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage not in STAGES:
        raise SystemExit(f"unknown stage {stage!r}; pick one of {', '.join(STAGES)}")
    print(f"===== CHS demand stage: {stage} =====", flush=True)
    STAGES[stage]()
    print(f"===== CHS demand stage {stage} complete =====", flush=True)
