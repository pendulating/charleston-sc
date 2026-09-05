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
| | (without embedded `drivingPath` geometry — see below) |
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
python simplify_ocean.py    # shrink the ocean depth index (see below)
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

Two traps are worth knowing before editing `special/pois.py`. Point ids are
built from a POI's `code`, falling back to its name, and a collision silently
merges two points into one — there are two Palmetto Christian Academies, so
schools carry their NCES id. And `merge_within` fails silently when it is
smaller than the distance to the nearest LODES block: the radius has to be
sized against real geography or the point quietly ends up with no employment
at all, which is what happened to the airport at 700 m against a 954 m gap.

`package.py` runs a preflight that refuses to build an archive with unrouted
pops, duplicate point ids, a stale or duplicated special-demand schema, or a
config population that disagrees with the demand. Every one of those checks
exists because that failure actually shipped.

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

#### Why schools don't use the gravity model

Every other category lets depot place its people by gravity: the weight of a
residential node is `residents / distance ** exponent`. For schools that breaks
down. The distances are in metres and the default school exponent is 2.5, so a
node 0.5 km from the school outweighs one at 5 km by 316×, and the entire
intake collapses onto the one or two closest nodes. In the 1.2.0 build that
left 172 residential nodes sending more children to school than they had
LODES residents — the worst at 3,990% — because `add_points` credits those
students back to the node as residents, so a node's population inflates to
match its own outbound student flow.

Schools are the one category whose destination has a legally defined
catchment, so they are placed explicitly instead. Every residential node inside
the attendance zone is passed as a `required_locs` entry, repeated in
proportion to its residents, which spreads intake across the zone the way
zoning actually works. Radii are 5 miles for primary, 8 for middle and 12 for
high schools — South Carolina districts are county-wide and rural zones run
long — growing further only when a zone cannot supply its school.

Two constraints keep it honest. Nodes are allocated whole pops only when they
have headroom for one, so quantisation cannot push a node past its cap; and
schools are placed largest-first against a running per-node budget, so a node
inside several overlapping catchments cannot be oversubscribed by the
combination. The budget is measured against each node's *LODES* residents, not
its current count — by the time schools are added, the other special demand has
already assigned workers to live at these nodes, and one node goes from 8 LODES
residents to 193.

Staff go through the same seat-capped allocation, but drawn metro-wide rather
than from the zone, since teachers are not zoned. Leaving them to depot's own
gravity draw was the last thing that could overload a node: that draw has no
notion of capacity, so a node with three residents picked by chance received a
whole pop. It also barred teachers from living anywhere in their own school's
attendance zone, because depot zeroes a point's required locations out of the
gravity pool — an artefact of the mechanism rather than a modelling choice,
and one that flattered the distance figures.

They are sampled rather than apportioned. Apportioning over a metro-wide pool
floors almost every share to zero and hands the pops to the highest-weight
candidates, which under a distance decay means the nearest ones: it becomes
"pick the closest N" and collapses the commute distribution to a 1.9 km
median. Pupils keep the apportionment, since they are confined to a zone and
weighted only by residents, with no distance term to bias it.

The result is **no node over 100%** — the worst now sends 75% of its residents
to school, against 3,990% before — a 95th percentile of 70% rather than 603%,
and a median school fed by 37 residential nodes rather than 7.

#### Calibrating the distance decay

depot places special demand by gravity, weighting a residential node by
`residents / distance ** exponent`, and ships a default exponent per type.
Those defaults are steep for a metro like this one. Charleston is not
transit-oriented — people drive a long way to work — and the base demand
already contains the evidence: the LODES commutes in it are real Charleston
journeys, at a 13.9 km median and 34.8 km 90th percentile.

Measured against that, the worker flows were all far too tight, so their
exponents are set explicitly rather than left at the default:

| flow | exponent | median commute | |
| --- | --- | --- | --- |
| School staff | 2.5 → 0.8 | 9.5 → 13.5 km | teachers are not zoned |
| Military personnel | 1.2 → 0.8 | 11.9 → 13.9 km | they commute from across the metro |
| Resort staff | 2.0 → 1.2 | 0.3 → 23 km | see below |

The resort figure was the clearest defect. At the default exponent of 2.0 the
median resort worker lived 300 metres from the resort, because the barrier
islands have almost no residents of their own and a steep decay hands the
entire staff to the handful that are there. Service staff on Kiawah and
Seabrook are priced off the islands and drive in from Johns Island and West
Ashley, which is what 1.2 reproduces.

Not every category was changed. Where a point's capacity is patients,
shoppers or visitors rather than staff — hospitals, malls, museums — the
shorter trips are correct, since non-work travel genuinely is shorter than
commuting, and those sites' actual employees arrive through `merge_within`
carrying their real LODES commutes. Pupils keep their short trips too, because
they are zoned.

#### Airport arrivals

Half of the airport's passengers are arrivals, and they are split two ways.
Thirty per cent disperse across the metro by gravity — residents coming home,
people staying with family, business trips to the North Charleston office
parks. The other 70% are visitors heading for a hotel, and 70% of those go to
the downtown peninsula. Weighting them by room count alone would send only 37%
downtown, because the airport strip and North Charleston hold a lot of rooms
serving business and Boeing traffic, but leisure visitors flying into
Charleston overwhelmingly stay on the peninsula.

That flow is written from the hotel end, not the airport end: each lodging
cluster carries `required_locs` entries pointing back at the airport, so those
pops take the airport as their residence and the hotel as their destination.
It has to be expressed that way because `required_locs` only shapes a point's
inbound job pops, never its outbound residents. It also means the airport must
be added in its own `add_points` call before the clusters — the function only
merges new points into the list when it returns, so a combined call would
silently bind those required locations to whatever base node sits nearest the
airport.

| Category | Points | Sizing |
| --- | --- | --- |
| Schools | 214 | NCES CCD 2022-23 (public) and PSS 2021-22 (private): real per-school enrollment, staff as teacher FTE × 1.9. Fully-virtual schools excluded. Pupils placed by 5/8/12-mile attendance zone, not gravity — see below |
| Military | 6 | Joint Base Charleston, the Navy nuclear training commands, Coast Guard. Active duty is largely absent from LODES |
| Universities | 5 | Student bodies carried from the 1.0.0 map |
| Airport | 1 | 6.1M passengers a year = 16,712/day, split evenly. Arrivals route to hotels, mostly downtown |
| Lodging | 67 | Overnight visitors where they sleep: OSM lodging, rooms × 70% occupancy × 1.9 guests, gridded into clusters |
| Resorts | 5 | Kiawah, Wild Dunes, Folly, Seabrook, Edisto — mostly residential, i.e. visitors |
| Hospitals | 8 | Patient and visitor trips at ~2.5 per licensed bed, beds from OSM |
| Ports | 5 | Gate traffic above terminal employment; Union Pier adds cruise arrivals |
| Retail and attractions | 9 | Malls, the aquarium, City Market, the forts, Patriots Point, IAAM, Amtrak |

### The ocean depth index needs simplifying after a rebuild

`ocean_depth_index.json.gz` comes out of depot as the largest thing the game
parses — 79 MB uncompressed, 98% of it polygon geometry. Almost all of that is
the shallowest band. depot patches −5 m with `water_gaps`, "everywhere OSM
says there is water but GEBCO left a gap", and GEBCO's global grid is about
450 m, so every tidal creek and marsh channel in the Lowcountry arrives as
hand-detailed shoreline: 81,134 polygons and 3.07M vertices for that one band.
Deep water is nothing by comparison — the −30 m band is 190 polygons.

That detail is far finer than anything consuming it. The index addresses water
through a grid of 0.0027° cells, about 250 m a side, so shoreline resolved to
a metre buys nothing.

```bash
python simplify_ocean.py          # after CHS.py pmtiles
```

Simplifies at ~9 m and rounds coordinates to ~1 m: 79.1 → 22.1 MB raw, 78%
fewer vertices, total water area down 0.53%. Every polygon and hole is kept,
so water stays water and no marsh becomes buildable land — only the outlines
get coarser, by well under half a grid cell.

It deliberately preserves polygon count and order. The `cells` array indexes
into `depths` by position, so dropping or reordering entries would silently
mis-address every cell referencing anything past the gap; `--check` verifies
no cell points out of range and no ring is degenerate.

### Pop granularity

The simulation cost scales with the number of pops, not the number of people,
so the generator is tuned to land in the same range as other US LODES maps
rather than at the finest granularity it will produce. Across the 50 US LODES
maps in the registry the median is 13.8 people per pop, with Tampa at 26.5;
this map sits at 17.7.

Two settings do the work. `DISTANCE_THRESHOLD_NONCBD` is 0.2 in
`us-demand/Charleston.json`, matching Tampa — at the 0.1 it was, the base
layer came out at 5.1 people per pop and 53,586 pops on its own. And
`CONSOLIDATE_POPS` merges the small ones. A finer `DISTANCE_THRESHOLD_CBD`
still applies downtown, so the peninsula keeps its detail.

`CHS_demand.py` then calls `merge_identical_commutes` after the special demand
is placed, because the allocators hand one residence node several pops bound
for the same school or hotel and those are one commute, not several, followed
by `enforce_max_pop_size` so nothing exceeds a trainload.

### Driving paths are deliberately not shipped

depot embeds the full polyline of every commute in `demand_data.json` when it
routes. At 43 vertices a pop that made the file 74 MB, 85% of it path
geometry — 1.1 KB per pop against a 0.18 KB median across 274 registry maps,
a 6× outlier and by far the most expensive thing in the map.

The game does not read them from there anyway. It asks for one path at a time
over `map://paths/{cityCode}/{popId}`, which Railyard's map loader intercepts
and serves. So `INCLUDE_DRIVING_PATHS` in `CHS_demand.py` is off, and
`drivingSeconds`/`drivingDistance`, which the simulation does need, are kept.
`python CHS_demand.py strip-paths` removes them from an already-routed file
without re-routing.

### Inputs

- OSM: `south-carolina-latest.osm.pbf` from [Geofabrik](https://download.geofabrik.de/north-america/us/south-carolina.html)
- Buildings: Overture Maps, fetched by depot
- Bathymetry: GEBCO 2026 sub-ice grid, via CEDA OPeNDAP
- Demand: LODES 2023 origin-destination pairs via the US Demand Generator
- Schools: NCES Common Core of Data and Private School Universe Survey
- Lodging: OSM `tourism=hotel/motel/guest_house/hostel/apartment` with room counts.
  Note OSM maps most hotels twice, once as a node and once as the building
  outline, so `fetch_lodging.py` collapses same-named lodging within 300 m —
  without it the room count, and therefore the whole tourism layer, roughly
  doubles.
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
