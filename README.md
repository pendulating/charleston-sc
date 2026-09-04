# Charleston, SC — Subway Builder map

Map of Charleston, South Carolina for [Subway Builder](https://subwaybuildermodded.com).
Originally built by **PSWBSF** (Map Patcher + US Demand Generator); this fork
rebuilds the map data with [depot](https://github.com/Subway-Builder-Modded/depot)
so it carries the layers the game has expected since 1.4, and extends it to the
whole populated tri-county area.

The playable area is `-80.68, 32.47 → -79.43, 33.43` — 117 × 106 km, covering
Charleston, Berkeley and Dorchester counties. It was derived rather than
eyeballed: it holds all 27 incorporated places in the three counties, 99.3% of
tri-county LODES activity by block group, and every barrier-island resort,
while trimming the empty Cape Romain marsh and the deepest Francis Marion
forest. Through 1.1.0 the map covered only the inner 3,663 km², which left
Moncks Corner and St. George outside the boundary.

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
| `.railyard_map/special_demand_*.json` | Special demand type and point schema |

## Building it

`depot/` is vendored in as its own checkout and is gitignored. The scripts in
`build/` drive it:

```bash
cd us-demand                            # base LODES demand for the bbox
python create_US_demand_file.py Charleston.json

cd ../build
python CHS.py all           # extract → buildings → roads → pmtiles → labels
python CHS_demand.py all    # seed → special demand → OSRM → commutes → config
python package.py           # assemble dist/Charleston.zip
```

`us-demand/` is [slurry's US Demand Generator](https://github.com/rslurry/subwaybuilder-US-demand-data),
cloned in and gitignored. It turns LODES origin-destination pairs into the base
demand; depot only edits an existing demand file, so it cannot produce this
part. Re-run it whenever the bbox changes, or the new area will have no demand.

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

### Special demand

`build/special/pois.py` defines every special demand point and is applied
through depot's `add_points`, which is also what emits the
`.railyard_map/special_demand_*.json` schema the 1.0.0 and 1.1.0 maps shipped
without.

Two conventions govern the numbers there. `merge_within` folds the nearby LODES
block point into the special point, and belongs anywhere the site is a
workplace LODES already counts — a hospital, terminal, mall or campus —
otherwise its staff are counted twice. `residential_split` is the share that
*lives* at the point and travels out, which is how inbound tourism is modelled:
an arriving air passenger or a beach-rental guest is a resident of that point
for the day.

So a point's capacity should be the trips LODES never sees. Airports carry
passengers, not airport workers; universities carry students, not faculty;
hospitals carry patients and visitors, not nurses. Schools are the deliberate
exception — they carry students *and* staff without merging, so school
employment is double-counted by choice.

| Category | Points | Sizing |
| --- | --- | --- |
| Schools | 215 | NCES CCD (public) and PSS (private), 2021-22: real per-school enrollment, staff as teacher FTE × 1.9 |
| Military | 6 | Joint Base Charleston, the Navy nuclear training commands, Coast Guard. Active duty is largely absent from LODES |
| Universities | 5 | Student bodies carried from the 1.0.0 map |
| Airport | 1 | Daily passengers, split evenly between departures and arrivals |
| Resorts | 5 | Kiawah, Wild Dunes, Folly, Seabrook, Edisto — mostly residential, i.e. visitors |
| Hospitals | 8 | Patient and visitor trips at ~2.5 per licensed bed, beds from OSM |
| Ports | 5 | Gate traffic above terminal employment; Union Pier adds cruise arrivals |
| Retail and attractions | 9 | Malls, the aquarium, City Market, the forts, Patriots Point, IAAM, Amtrak |

### Inputs

- OSM: `south-carolina-latest.osm.pbf` from [Geofabrik](https://download.geofabrik.de/north-america/us/south-carolina.html)
- Buildings: Overture Maps, fetched by depot
- Bathymetry: GEBCO 2026 sub-ice grid, via CEDA OPeNDAP
- Demand: LODES 2023 origin-destination pairs via the US Demand Generator
- Schools: NCES Common Core of Data and Private School Universe Survey
- Boundaries: Census TIGER counties and block groups, for deriving the bbox

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
