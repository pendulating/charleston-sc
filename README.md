# Charleston, SC — Subway Builder map

Map of Charleston, South Carolina for [Subway Builder](https://subwaybuildermodded.com).
Originally built by **PSWBSF** (Map Patcher + US Demand Generator); this fork
rebuilds the map data with [depot](https://github.com/Subway-Builder-Modded/depot)
so it carries the layers the game has expected since 1.4.

The playable area is unchanged — `-80.3018, 32.5526 → -79.6701, 33.1133` — so
networks built on 1.0.0 still line up.

## What ships

Release assets are a flat `Charleston.zip` plus a `manifest.json` sidecar
(Railyard reads the sidecar to resolve game compatibility without downloading
the archive).

| File | Purpose |
| --- | --- |
| `CHS.pmtiles` | Basemap tiles: water, landuse, roads, buildings, ocean foundations |
| `CHS_foundations.pmtiles` | Building foundations layer |
| `buildings_index.bin.gz` | Packed building collision index |
| `buildings_index.json.gz` | JSON form of the same index |
| `roads.geojson` | Road network |
| `runways_taxiways.geojson` | Aeroway geometry |
| `ocean_depth_index.json.gz` | Bathymetry — gates underwater track building |
| `ocean_depth_index_contours.json.gz` | Depth contours |
| `demand_data.json` | Population, jobs, and commutes |
| `config.json` | Map metadata |

## Building it

`depot/` is vendored in as its own checkout and is gitignored. The scripts in
`build/` drive it:

```bash
cd build
python CHS.py all           # extract → buildings → roads → pmtiles → labels
python CHS_demand.py all    # OSRM server → recompute commutes → config.json
python package.py           # assemble dist/Charleston.zip
```

Each script also takes a single stage name if you want to re-run one step —
`python CHS.py pmtiles`, `python CHS_demand.py routes`, and so on.

### Toolchain

depot needs `node`, `mapshaper`, `osmium`, `java`, `tippecanoe`, `tile-join`,
`sqlite3`, `jq`, `pmtiles`, `planetiler.jar` on `PATH`, plus `ogr2ogr` (GDAL),
which depot uses but does not check for. Docker is needed only for the demand
step's local OSRM server.

On macOS:

```bash
brew install osmium-tool tippecanoe pmtiles jq gdal openjdk@21
npm install -g mapshaper
curl -L -o ~/.local/bin/planetiler.jar \
  https://github.com/onthegomap/planetiler/releases/download/v0.10.2/planetiler.jar
export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"   # openjdk@21 is keg-only
```

Python 3.13 with depot's dependencies. Note that depot's `environment.yml` is
missing two packages it imports — install them alongside it:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python \
  geopandas==1.1.1 mapbox-vector-tile==2.2.0 numpy==2.3.5 pandas==2.3.3 \
  duckdb==1.5.3 shapely==2.1.2 osmnx==2.1.0 tqdm==4.68.2 xarray==2026.4.0 \
  netCDF4==1.7.4 'httpx[http2]==0.28.1' mercantile==1.2.1 matplotlib==3.10.9 \
  scipy==1.17.1 Unidecode==1.4.0 inflect==7.5.0 scikit-learn
uv pip install --python .venv/bin/python ../depot
```

`scikit-learn` is imported by `depot.demand`; the `h2` extra on `httpx` is
needed by the Overture buildings fetch.

### Inputs

- OSM: `south-carolina-latest.osm.pbf` from [Geofabrik](https://download.geofabrik.de/north-america/us/south-carolina.html)
- Buildings: Overture Maps, fetched by depot
- Bathymetry: GEBCO 2026 sub-ice grid, via CEDA OPeNDAP
- Demand: inherited from the 1.0.0 release (2023 LODES), commutes recomputed

### OSRM port

`DemandData.prepare_osrm` publishes `-p <port>:<port>`, but `osrm-routed`
listens on 5000 inside the container, so a non-default port never reaches it.
On macOS the AirPlay Receiver holds port 5000, so `build/CHS_demand.py` expects
the router to be started by hand:

```bash
docker run --name CHS -d -p 5050:5000 \
  -v "$PWD/CHS_demand:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-routed --algorithm ch /data/CHS.osrm
```

## Credits

Map by PSWBSF. Demand from the
[US Demand Generator](https://github.com/rslurry/subwaybuilder-US-demand-data)
by slurry. Rebuilt with [depot](https://github.com/Subway-Builder-Modded/depot).
Map data © OpenStreetMap contributors, Overture Maps Foundation, and GEBCO.
