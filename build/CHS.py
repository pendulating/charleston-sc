"""
Rebuild of the Charleston, SC map (CHS) for Subway Builder using depot.

Bounding box matches the original 1.0.0 release's PMTiles bounds so existing
networks stay aligned:  -80.3018, 32.5526 -> -79.6701, 33.1133

Run a single stage:   python CHS.py <stage>
Stages: extract | labels | buildings | roads | pmtiles | addlabels | all
"""
import os
import sys

from depot.maps import MapGen

HERE = os.path.dirname(os.path.abspath(__file__))
OSMPBF = os.path.join(HERE, "south-carolina-latest.osm.pbf")

obj = MapGen(
    city="CHS",
    bbox=[-80.3018, 32.5526, -79.6701, 33.1133],
    osmpbf=OSMPBF,
    outputdir=HERE,
    # Charleston is a mid-size, low-rise metro: keep small buildings so the
    # historic peninsula stays dense, at defaults for filtering/simplification.
    building_index_filter_size=40,
    building_tile_filter_size=None,
    building_index_simplification=1,
    building_tile_simplification=1,
    # The 1.4+ gameplay layers the original 1.0.0 map predates.
    create_building_foundations=True,
    create_ocean_foundations=True,
    # US label preset from the depot README, plus 'island': the Charleston
    # area names 46 of them (James, Daniel, Sullivan's, Folly, Wadmalaw...)
    # and they read as places here, not just landforms.
    cities=["city", "borough", "town"],
    suburbs=["suburb", "village"],
    neighborhoods=["neighbourhood", "hamlet", "quarter", "locality", "island"],
    maxzoom=15,
    ncores=10,
    RAM=8,
    cleanup_files=False,
    verb=True,
)

STAGES = {
    "extract": obj.extract_base_data,
    "labels": obj.check_labels,
    "buildings": obj.process_buildings,
    "roads": obj.process_roads_and_aeroways,
    "pmtiles": obj.generate_pmtiles,
    "addlabels": obj.add_labels,
    "all": obj.run_all,
}

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage not in STAGES:
        raise SystemExit(f"unknown stage {stage!r}; pick one of {', '.join(STAGES)}")
    print(f"===== CHS stage: {stage} =====", flush=True)
    STAGES[stage]()
    print(f"===== CHS stage {stage} complete =====", flush=True)
