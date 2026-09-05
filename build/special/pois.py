"""
Special demand definitions for the Charleston (CHS) map.

Every entry is a depot `DemandData.add_points` POI. Two conventions matter here:

`merge_within` (metres) folds the nearby LODES block points into the special
point. Use it wherever the site is a workplace LODES already counts -- a
hospital, a port terminal, a mall, a campus -- otherwise its staff get counted
twice, once in the block point and once here. Skip it where the special demand
is people LODES never saw: airport passengers, resort visitors, schoolchildren.

`residential_split` is the share of capacity that *lives* at the point and
travels out, rather than travelling in. It is how inbound tourism is modelled:
an arriving air passenger or a guest in a beach rental is a resident of that
point for the day.

Coordinates are from OpenStreetMap unless they carry over from PSWBSF's
original 1.0.0 map, which spot-checks clean against OSM.
"""
import json
import math
import os
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# The map extent. POIs are written with real coordinates and filtered against
# this rather than hand-pruned, so changing the bbox cannot silently leave a
# point sitting off the edge of the map -- depot would place it, the game would
# never reach it, and nothing would report the problem.
BBOX = [-80.3018, 32.5526, -79.6701, 33.1133]


def in_bbox(location):
    return (BBOX[0] <= location[0] <= BBOX[2]
            and BBOX[1] <= location[1] <= BBOX[3])

# Charleston International served 6.1M passengers in 2023, which is 16,712 a
# day across both directions, so ~8,350 arriving and ~8,350 departing. PSWBSF
# modelled 6,900 departing and no arrivals at all, so the map had a tourist
# city with no inbound tourism. merge_within picks up the airport's own LODES
# workers, so total_capacity here is passengers only.
AIRPORT_LOC = [-80.0369, 32.8845]
DAILY_PASSENGERS = 16700          # 6.1M a year, both directions
ARRIVALS = DAILY_PASSENGERS // 2
# Share of arriving passengers who are visitors heading for a hotel. The rest
# -- residents coming home, people staying with family, business trips to the
# North Charleston office parks -- disperse across the metro by gravity.
ARRIVALS_TO_LODGING = 0.70
# Of those hotel-bound visitors, the share going to the downtown peninsula.
# Weighting purely by room count would send only 37% there, because the airport
# strip and North Charleston hold a lot of rooms serving business and Boeing
# traffic. Leisure visitors flying into Charleston overwhelmingly stay on the
# peninsula, so that is where the arrivals go.
PENINSULA_SHARE = 0.70
PENINSULA_BBOX = (-79.97, 32.76, -79.90, 32.82)

_lodging_bound = int(ARRIVALS * ARRIVALS_TO_LODGING)
_dispersing = ARRIVALS - _lodging_bound
_departures = DAILY_PASSENGERS - ARRIVALS

# total_capacity is departures plus the dispersing arrivals. The hotel-bound
# arrivals hang off the lodging clusters instead, via required_locs pointing
# back here, so they still land as residents of the airport.
AIRPORT = [
    dict(type="airport", name="Charleston International Airport", code="CHS",
         location=AIRPORT_LOC,
         total_capacity=_departures + _dispersing,
         pop_size=100,
         residential_split=_dispersing / (_departures + _dispersing),
         merge_within=1100),
]

# Student bodies carried over from the 1.0.0 map, which are plausible for these
# institutions. merge_within absorbs campus staff from LODES.
UNIVERSITIES = [
    dict(type="university", name="College of Charleston", code="COC",
         location=[-79.9370, 32.7834], total_capacity=5100, pop_size=100,
         residential_split=0.37, merge_within=600),
    dict(type="university", name="The Citadel", code="CIT",
         location=[-79.9609, 32.7971], total_capacity=1300, pop_size=50,
         residential_split=0.69, merge_within=600),
    dict(type="university", name="Medical University of South Carolina", code="MUSC",
         location=[-79.9486, 32.7847], total_capacity=1300, pop_size=50,
         residential_split=0.15, merge_within=400),
    dict(type="university", name="Charleston Southern University", code="CSU",
         location=[-80.0711, 32.9826], total_capacity=1600, pop_size=50,
         residential_split=0.375, merge_within=600),
    dict(type="university", name="Trident Technical College", code="TTC",
         location=[-80.0305, 32.9256], total_capacity=5600, pop_size=100,
         residential_split=0.0, merge_within=600),
]

# Joint Base Charleston and the Navy's nuclear training pipeline are the
# region's largest employers. Active-duty personnel are largely absent from
# LODES, which counts jobs covered by state unemployment insurance, so these
# are added on top. The merge radius is deliberately tight and in practice
# never fires -- the nearest blocks are 540 m or more out -- which is the
# intended outcome here: the bases should not swallow neighbouring housing.
#
# exponent 0.8 rather than depot's 1.2 default: personnel commute in from
# across the metro, and 0.8 reproduces the LODES median of 13.9 km exactly,
# where the default gave 11.9.
MIL_EXPONENT = 0.8
MILITARY = [
    dict(type="military_base", name="Joint Base Charleston - Air Base", code="JBCS", exponent=MIL_EXPONENT,
         location=[-80.0523, 32.8972], total_capacity=10600, pop_size=100,
         residential_split=0.208, merge_within=400),
    dict(type="military_base", name="Joint Base Charleston - Weapons Station", code="JBCN", exponent=MIL_EXPONENT,
         location=[-80.0548, 32.9037], total_capacity=10600, pop_size=100,
         residential_split=0.208, merge_within=400),
    dict(type="military_base", name="Naval Weapons Station Charleston", code="NWS", exponent=MIL_EXPONENT,
         location=[-79.9366, 32.9579], total_capacity=3500, pop_size=50,
         residential_split=0.20, merge_within=400),
    dict(type="military_base", name="Nuclear Power Training Unit", code="NPTU", exponent=MIL_EXPONENT,
         location=[-79.9305, 32.9440], total_capacity=12000, pop_size=100,
         residential_split=0.0, merge_within=400),
    dict(type="military_base", name="Naval Nuclear Power Training Command", code="NPTC", exponent=MIL_EXPONENT,
         location=[-79.9678, 32.9658], total_capacity=14200, pop_size=100,
         residential_split=0.211, merge_within=400),
    dict(type="military_base", name="US Coast Guard Base Charleston", code="CGC", exponent=MIL_EXPONENT,
         location=[-79.9376, 32.8475], total_capacity=7000, pop_size=100,
         residential_split=0.20, merge_within=400),
]

# Hospital staff are already in LODES, and merge_within pulls that block point
# into this one, so capacity here is only the trips LODES never sees: patients
# and visitors, at ~2.5 daily arrivals per licensed bed. Bed counts are OSM
# `beds` tags; sites marked est. carry no tag and use the published count.
HOSPITALS = [
    dict(type="hospital", name="MUSC Health Medical Center", code="MUSC",
         location=[-79.9473, 32.7846], total_capacity=1800, pop_size=50,
         merge_within=400),                                    # 713 beds
    dict(type="hospital", name="Roper Hospital", code="ROPER",
         location=[-79.9493, 32.7832], total_capacity=920, pop_size=50,
         merge_within=400),                                    # 368 beds
    dict(type="hospital", name="Trident Medical Center", code="TRID",
         location=[-80.0730, 32.9764], total_capacity=750, pop_size=25,
         merge_within=400),                                    # ~300 beds, est.
    dict(type="hospital", name="Ralph H. Johnson VA Medical Center", code="VA",
         location=[-79.9539, 32.7836], total_capacity=600, pop_size=25,
         merge_within=400),                                    # est.
    dict(type="hospital", name="Bon Secours St Francis Hospital", code="BSF",
         location=[-80.0417, 32.8090], total_capacity=510, pop_size=25,
         merge_within=400),                                    # 204 beds
    dict(type="hospital", name="East Cooper Medical Center", code="EC",
         location=[-79.8504, 32.8205], total_capacity=350, pop_size=25,
         merge_within=400),                                    # ~140 beds, est.
    dict(type="hospital", name="Summerville Medical Center", code="SUMM",
         location=[-80.1575, 32.9662], total_capacity=235, pop_size=25,
         merge_within=500),                                    # 94 beds
    dict(type="hospital", name="Roper St Francis Mount Pleasant Hospital", code="MP",
         location=[-79.7686, 32.8782], total_capacity=210, pop_size=25,
         merge_within=400),                                    # 85 beds
]

# Terminal employment is in LODES and arrives here through the merge, so
# capacity covers only the gate traffic on top of it -- drayage drivers whose
# LODES workplace is their trucking firm, not the terminal. Radii are sized to
# reach each terminal's nearest block; at 500-600 m three of them never fired.
# Union Pier is the exception: cruise calls put arriving passengers on the
# pier, which is inbound tourism and nowhere in LODES, hence the split.
PORTS = [
    dict(type="port", name="Wando Welch Terminal", code="WW",
         location=[-79.8814, 32.8330], total_capacity=400, pop_size=25,
         merge_within=600),
    dict(type="port", name="North Charleston Terminal", code="NCT",
         location=[-79.9619, 32.9056], total_capacity=300, pop_size=25,
         merge_within=800),
    dict(type="port", name="Hugh K. Leatherman Terminal", code="HKL",
         location=[-79.9387, 32.8409], total_capacity=200, pop_size=25,
         merge_within=700),
    dict(type="port", name="Columbus Street Terminal", code="CST",
         location=[-79.9298, 32.7955], total_capacity=150, pop_size=25,
         merge_within=600),
    dict(type="port", name="Union Pier Cruise Terminal", code="UP",
         location=[-79.9259, 32.7832], total_capacity=400, pop_size=25,
         residential_split=0.5, merge_within=300),
]

# Retail. Sizes carried over from the 1.0.0 map's ENT points, now typed as
# shopping centres rather than lumped under a generic entertainment code.
SHOPPING = [
    dict(type="shopping_center", name="Tanger Outlets Charleston", code="TANG",
         location=[-80.0185, 32.8712], total_capacity=2000, pop_size=50,
         merge_within=400),
    dict(type="shopping_center", name="Citadel Mall", code="CITM",
         location=[-80.0316, 32.7982], total_capacity=1900, pop_size=50,
         merge_within=400),
    dict(type="shopping_center", name="Northwoods Mall", code="NORM",
         location=[-80.0445, 32.9441], total_capacity=1700, pop_size=50,
         merge_within=400),
]

# Visitor attractions. The 1.0.0 map had these as generic ENT points; typing
# them lets the game label them correctly and gives each a sensible decay.
ATTRACTIONS = [
    dict(type="aquarium", name="South Carolina Aquarium", code="SCAQ",
         location=[-79.9254, 32.7910], total_capacity=1500, pop_size=50,
         merge_within=200),
    dict(type="heritage_site", name="Charleston City Market", code="MKT",
         location=[-79.9293, 32.7809], total_capacity=1500, pop_size=50,
         merge_within=150),
    dict(type="museum", name="Patriots Point Naval and Maritime Museum", code="PPT",
         location=[-79.9061, 32.7905], total_capacity=800, pop_size=25,
         merge_within=400),
    dict(type="heritage_site", name="Fort Sumter Visitor Center", code="SUM",
         location=[-79.9252, 32.7905], total_capacity=700, pop_size=25,
         merge_within=150),
    dict(type="heritage_site", name="Fort Moultrie", code="MOUL",
         location=[-79.8576, 32.7604], total_capacity=700, pop_size=25,
         merge_within=300),
    dict(type="museum", name="International African American Museum", code="IAAM",
         location=[-79.9258, 32.7887], total_capacity=600, pop_size=25,
         merge_within=150),
    dict(type="outside_connection", name="Charleston Amtrak Station", code="AMTK",
         location=[-79.9982, 32.8753], total_capacity=200, pop_size=25,
         residential_split=0.5, merge_within=200),
]

# Barrier-island resorts. Guests staying in a rental are residents of the
# island for the day and travel out of it, so these skew heavily residential.
# No merge: these are real towns whose own residents are already in LODES and
# should stay as their own points.
#
# exponent 1.2 rather than depot's 2.0 default for resorts. At 2.0 the median
# resort worker lived 0.3 km from the resort, because the islands have almost
# no residents of their own and a steep decay hands everything to the handful
# that are there. Service staff on Kiawah and Seabrook are priced off the
# islands entirely and drive in from Johns Island and West Ashley; 1.2 puts
# them at a 23 km median, which is what that commute really looks like.
RST_EXPONENT = 1.2
RESORTS = [
    dict(type="resort", name="Kiawah Island", code="KIAW", exponent=RST_EXPONENT,
         location=[-80.0848, 32.6082], total_capacity=3000, pop_size=50,
         residential_split=0.80),
    dict(type="resort", name="Wild Dunes, Isle of Palms", code="WD", exponent=RST_EXPONENT,
         location=[-79.7384, 32.8046], total_capacity=2500, pop_size=50,
         residential_split=0.80),
    dict(type="resort", name="Folly Beach", code="FOLLY", exponent=RST_EXPONENT,
         location=[-79.9408, 32.6555], total_capacity=2000, pop_size=50,
         residential_split=0.70),
    dict(type="resort", name="Seabrook Island", code="SEAB", exponent=RST_EXPONENT,
         location=[-80.1707, 32.5771], total_capacity=1200, pop_size=25,
         residential_split=0.80),
    dict(type="resort", name="Edisto Beach", code="EDIS", exponent=RST_EXPONENT,
         location=[-80.3348, 32.4794], total_capacity=800, pop_size=25,
         residential_split=0.80),
]


# Attendance-zone radius by NCES school level. Schools are the one category
# where the destination has a legally defined catchment, and pupils come from
# inside it in rough proportion to how many people live there. South Carolina
# districts are county-wide and rural zones run long, so these are generous:
# 5, 8 and 12 miles.
MILE_M = 1609.344
CATCHMENT_M = {1: round(5 * MILE_M), 2: round(8 * MILE_M), 3: round(12 * MILE_M)}
CATCHMENT_DEFAULT_M = round(8 * MILE_M)     # ungraded, private, "other"
# One pop size for everyone a school pulls in. required_locs takes a single
# pop size per point, and both pupils and staff go through it now, so they
# have to share one.
SCHOOL_POP_SIZE = 15
# Teachers are not zoned and Charleston is not transit-oriented -- people drive
# a long way to work here. Calibrated against the LODES commutes in the base
# demand, which are the real thing: this puts staff at a 14.0 km median
# against the real 13.9.
#
# Note this is calibrated for a pool where every node is eligible. depot's own
# gravity draw zeroes out a point's required_locs, which for a school means
# teachers are barred from living anywhere in their own attendance zone -- an
# artefact of the mechanism rather than a modelling choice, and one that
# flattered the distance figures. Staff are allocated here instead, over the
# whole metro, so the exponent has to be gentler to reach the same median.
STAFF_EXPONENT = 0.8
# Ceiling on the share of a residential node's LODES residents that may be
# sent to school. LODES counts workers, not people, and school-age children
# are roughly half a metro's worker count, so anything approaching 1.0 is a
# node sending more children than it plausibly houses.
NODE_CAP = 0.75


def _haversine_m(lon, lat, lons, lats):
    r = 6371008.8
    p1 = math.radians(lat)
    p2 = np.radians(lats)
    dphi = p2 - p1
    dlam = np.radians(lons - lon)
    h = np.sin(dphi / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dlam / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(h))


def _largest_remainder(weights, total):
    """Apportion `total` whole pops across `weights` without drift."""
    exact = weights * total
    alloc = np.floor(exact).astype(int)
    short = total - int(alloc.sum())
    if short > 0:
        for k in np.argsort(-(exact - alloc))[:short]:
            alloc[k] += 1
    return alloc


def _weighted_seat_sample(weights, seats, npops, seed):
    """
    Draw `npops` pops at random in proportion to `weights`, never exceeding a
    candidate's `seats`.

    Sampling rather than apportioning, because apportionment degenerates here.
    `_largest_remainder` over a metro-wide pool floors almost every share to
    zero and then hands the pops to the highest-weight candidates, which under
    a distance decay means the nearest ones -- it turns into "pick the closest
    N" and collapses the commute distribution. That is fine for pupils, who are
    confined to a zone and weighted only by residents, but not for staff.

    Seeded so a rebuild is reproducible.
    """
    rng = np.random.default_rng(seed)
    w = np.asarray(weights, dtype=float).copy()
    room = np.asarray(seats, dtype=int).copy()
    w[room <= 0] = 0.0
    alloc = np.zeros(w.size, dtype=int)
    for _ in range(int(npops)):
        total = w.sum()
        if total <= 0:
            break
        i = int(rng.choice(w.size, p=w / total))
        alloc[i] += 1
        if alloc[i] >= room[i]:
            w[i] = 0.0
    return alloc


def _seat_alloc(weights, seats, npops):
    """
    Hand out `npops` whole pops across candidates in proportion to `weights`,
    never giving a candidate more than its `seats`. Overflow is redistributed
    to whoever still has room, which is what keeps a three-resident node from
    being handed a whole pop it cannot possibly house.
    """
    npops = min(int(npops), int(seats.sum()))
    alloc = np.zeros(weights.size, dtype=int)
    left = npops
    while left > 0:
        room = seats - alloc
        open_ = room > 0
        if not open_.any():
            break
        w = weights * open_
        if w.sum() <= 0:
            break
        give = np.minimum(_largest_remainder(w / w.sum(), left), room)
        if give.sum() == 0:                 # rounding stalled; fill directly
            give[np.flatnonzero(open_)[:left]] = 1
        alloc += give
        left -= int(give.sum())
    return alloc


def lodging():
    """
    Overnight visitors, clustered by where they sleep (special/lodging.json,
    built by fetch_lodging.py from OSM).

    The airport only accounts for a slice of Charleston's tourism -- most
    visitors drive in -- so modelling arrivals alone still leaves the city
    emptier than it is. These are pure origin points: a visitor lives at their
    hotel for the day and travels out to the peninsula, the beaches and the
    forts, so the split is fully residential. Hotel staff are already in LODES
    at their own block and are deliberately not merged in here, because a
    cluster spans a whole district and merging would swallow unrelated demand.
    """
    clusters = json.load(open(os.path.join(HERE, "lodging.json")))

    def on_peninsula(c):
        x0, y0, x1, y1 = PENINSULA_BBOX
        return x0 <= c["lon"] <= x1 and y0 <= c["lat"] <= y1

    downtown = [c for c in clusters if on_peninsula(c)]
    elsewhere = [c for c in clusters if not on_peninsula(c)]
    downtown_pool = int(_lodging_bound * PENINSULA_SHARE)
    arrivals = {}
    for group, pool in ((downtown, downtown_pool),
                        (elsewhere, _lodging_bound - downtown_pool)):
        total = sum(c["visitors"] for c in group) or 1
        for c in group:
            arrivals[c["code"]] = int(pool * c["visitors"] / total)

    # Apportion whole pops rather than truncating per cluster: `int(pool*share)`
    # followed by `// arrival_pop` on each of 60-odd clusters lost 11% of the
    # arrivals outright.
    arrival_pop = 25
    codes = [c["code"] for c in clusters]
    weights = np.array([max(arrivals.get(k, 0), 0) for k in codes], dtype=float)
    npops = int(round(sum(arrivals.values()) / arrival_pop))
    pops_by_code = dict(zip(codes, _largest_remainder(weights / weights.sum(), npops))) \
        if weights.sum() > 0 and npops > 0 else {k: 0 for k in codes}

    out = []
    for c in clusters:
        if not in_bbox([c["lon"], c["lat"]]):
            continue
        nreq = int(pops_by_code.get(c["code"], 0))
        capacity = c["visitors"] + nreq * arrival_pop
        out.append(dict(
            type="resort", name=f"Charleston lodging {c['code']}", code=c["code"],
            location=[c["lon"], c["lat"]],
            total_capacity=capacity,
            required_locs=[list(AIRPORT_LOC)] * nreq,
            pop_size=25,
            pop_size_req=arrival_pop,
            pop_size_remain=25,
            residential_split=(c["visitors"] / capacity) if capacity else 0.0,
            exponent=1.5,
        ))
    return out


def schools(base_points, resident_baseline=None):
    """
    Schools from the NCES Common Core of Data (public) and Private School
    Universe Survey (private), both 2021-22, filtered to the map bbox.

    Pupils are placed by attendance zone rather than by depot's gravity model.
    The gravity weight is residents / distance**exponent, and at the default
    school exponent of 2.5 over metres a node 0.5 km out outweighs one at 5 km
    by 316x, so the whole school collapses onto its one or two closest
    residential nodes -- which then ship more children than they have
    residents. Instead every residential node inside the catchment is passed as
    a `required_locs` entry, repeated in proportion to its residents, so the
    intake spreads across the zone the way school zoning actually works.

    Schools are taken largest first against a running per-node capacity, so a
    node inside several overlapping catchments cannot be oversubscribed by the
    combination. Where a zone cannot supply its school the radius grows until
    it can.

    Staff are drawn metro-wide instead of from the zone, since teachers are
    not zoned, but through the same seat-capped allocation rather than depot's
    own gravity draw. That draw has no notion of capacity: weighted only by
    residents over distance, it would occasionally pick a node with three
    residents and hand it a whole pop, which was the last thing overloading
    nodes here. The gravity *weighting* is kept, and calibrated against the
    real LODES commute distances -- see STAFF_EXPONENT.

    `resident_baseline` maps point id to its LODES resident count. It matters
    because by the time schools are added, the other special demand has already
    assigned workers to live at these nodes -- one node here goes from 8 LODES
    residents to 193 -- and sizing a catchment against that inflated figure
    lets a school claim people the neighbourhood does not have. Falls back to
    the point's current residents when a node is missing from the baseline.

    Capacity is students plus staff, staff being teacher FTE scaled by 1.9 --
    the national ratio of school employees to teachers. Those staff are already
    in LODES as workers at the school's block, and this deliberately does not
    merge them away, so school employment is counted twice by design.
    """
    entries = [s for s in json.load(open(os.path.join(HERE, "schools.json")))
               if s["students"] + s["staff"] >= 40 and in_bbox([s["lon"], s["lat"]])]

    resident_baseline = resident_baseline or {}
    locs = np.array([p["location"] for p in base_points], dtype=float)
    residents = np.array(
        [float(resident_baseline.get(p["id"], p["residents"])) for p in base_points],
        dtype=float)
    remaining = residents * NODE_CAP

    out = []
    for s in sorted(entries, key=lambda x: (-x["students"], x.get("code") or x["name"])):
        students, staff = s["students"], s["staff"]
        seed_key = str(s.get("code") or s["name"])
        level = s.get("level")
        radius = CATCHMENT_M.get(level if level in CATCHMENT_M else None,
                                 CATCHMENT_DEFAULT_M)

        psize = SCHOOL_POP_SIZE
        dist = _haversine_m(s["lon"], s["lat"], locs[:, 0], locs[:, 1])
        dist = np.where(dist == 0, 1e9, dist)
        required_locs = []

        # --- pupils: inside the attendance zone, in proportion to residents.
        # Only nodes with room for a whole pop are eligible, so quantisation
        # cannot push one past its cap. Grow the zone until enough exist.
        npops = max(2, round(students / psize))
        mask = None
        for mult in (1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0):
            mask = (dist <= radius * mult) & (remaining >= psize)
            if int((remaining[mask] // psize).sum()) >= npops:
                break
        idx = np.flatnonzero(mask)
        n_pupil_pops = 0
        if idx.size:
            seats = (remaining[idx] // psize).astype(int)
            alloc = _seat_alloc(remaining[idx], seats, npops)
            n_pupil_pops = int(alloc.sum())
            for i, n in zip(idx, alloc):
                required_locs.extend([[float(locs[i][0]), float(locs[i][1])]] * int(n))
            remaining[idx] = np.maximum(0.0, remaining[idx] - alloc * psize)

        # --- staff: metro-wide, gravity-weighted, but seat-capped the same
        # way. Left to depot's own gravity draw they were the last thing that
        # could overload a node: the draw has no notion of capacity, so a
        # three-resident node picked by chance received a whole pop.
        nstaff = int(round(staff / psize))
        if nstaff:
            sidx = np.flatnonzero(remaining >= psize)
            if sidx.size:
                w = residents[sidx] / dist[sidx] ** STAFF_EXPONENT
                w = np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)
                w[dist[sidx] > 200000] = 0.0
                if w.sum() > 0:
                    seats = (remaining[sidx] // psize).astype(int)
                    # crc32, not hash(): str hashing is salted per process, so
                    # hash() made every rebuild produce different allocations.
                    alloc = _weighted_seat_sample(
                        w, seats, nstaff, seed=zlib.crc32(seed_key.encode()))
                    for i, n in zip(sidx, alloc):
                        required_locs.extend([[float(locs[i][0]), float(locs[i][1])]] * int(n))
                    remaining[sidx] = np.maximum(0.0, remaining[sidx] - alloc * psize)

        if not required_locs:
            continue

        out.append(dict(
            type="school", name=s["name"], location=[s["lon"], s["lat"]],
            # School names are not unique -- there are two Palmetto Christian
            # Academies -- and depot builds the point id from the code, falling
            # back to the name. Without a code the second campus overwrites the
            # first and sanitize silently merges their demand onto one point.
            code=s.get("code"),
            # QA only, ignored by depot: required_locs is pupils then staff,
            # and nothing downstream can tell them apart once placed.
            _n_pupil_pops=n_pupil_pops,
            total_capacity=psize * len(required_locs),
            required_locs=required_locs,
            pop_size=psize,
            pop_size_req=psize,
            pop_size_remain=psize,
            exponent=STAFF_EXPONENT,
            residential_split=0.0,
        ))
    return out


# Everything except the airport, lodging and schools. These are applied first:
# several carry merge_within, which deletes the LODES points they absorb, and
# school catchments must be computed against the point list that survives that.
# The airport goes in on its own beforehand and lodging afterwards, because
# lodging's required_locs have to resolve to an AIR_CHS that already exists.
def non_school_pois():
    # Hospitals before universities on purpose. Whichever POI is processed
    # first wins the merge, and MUSC is both: with universities first, the
    # 10.5k-job medical-centre block was absorbed by UNI_MUSC and the hospital
    # point kept only its patients.
    pois = []
    for g in (HOSPITALS, UNIVERSITIES, MILITARY, PORTS, SHOPPING,
              ATTRACTIONS, RESORTS):
        pois.extend(p for p in g if in_bbox(p["location"]))
    return pois


if __name__ == "__main__":
    import sys
    demand = sys.argv[1] if len(sys.argv) > 1 else "CHS_demand/demand_data.json"
    pts = [p for p in json.load(open(demand))["points"] if p["id"].startswith("merged")]
    groups = [
        ("airport", AIRPORT), ("university", UNIVERSITIES), ("military", MILITARY),
        ("hospital", HOSPITALS), ("port", PORTS), ("shopping", SHOPPING),
        ("attraction", ATTRACTIONS), ("resort", RESORTS), ("lodging", lodging()),
        ("school", schools(pts)),
    ]
    print(f"{'group':<14}{'points':>8}{'capacity':>12}{'residents':>11}{'jobs':>10}")
    total = 0
    for name, g in groups:
        cap = sum(p["total_capacity"] for p in g)
        res = sum(int(p["total_capacity"] * p.get("residential_split", 0.0)) for p in g)
        print(f"{name:<14}{len(g):>8}{cap:>12,}{res:>11,}{cap - res:>10,}")
        total += cap
    print(f"{'TOTAL':<14}{sum(len(g) for _, g in groups):>8}{total:>12,}")
