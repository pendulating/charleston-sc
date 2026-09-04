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
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Charleston International. PSWBSF modelled 6,900 daily departing passengers
# and no arrivals, so the map had no inbound tourism at all. Mirroring that
# figure gives the arrival side; ~13.8k daily passengers both ways is in line
# with CHS's traffic. merge_within picks up the airport's own LODES workers,
# so total_capacity here is passengers only.
AIRPORT = [
    dict(type="airport", name="Charleston International Airport", code="CHS",
         location=[-80.0369, 32.8845], total_capacity=13800, pop_size=100,
         residential_split=0.50, merge_within=700),
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
# are added with only a tight merge radius.
MILITARY = [
    dict(type="military_base", name="Joint Base Charleston - Air Base", code="JBCS",
         location=[-80.0523, 32.8972], total_capacity=10600, pop_size=100,
         residential_split=0.208, merge_within=400),
    dict(type="military_base", name="Joint Base Charleston - Weapons Station", code="JBCN",
         location=[-80.0548, 32.9037], total_capacity=10600, pop_size=100,
         residential_split=0.208, merge_within=400),
    dict(type="military_base", name="Naval Weapons Station Charleston", code="NWS",
         location=[-79.9366, 32.9579], total_capacity=3500, pop_size=50,
         residential_split=0.20, merge_within=400),
    dict(type="military_base", name="Nuclear Power Training Unit", code="NPTU",
         location=[-79.9305, 32.9440], total_capacity=12000, pop_size=100,
         residential_split=0.0, merge_within=400),
    dict(type="military_base", name="Naval Nuclear Power Training Command", code="NPTC",
         location=[-79.9678, 32.9658], total_capacity=14200, pop_size=100,
         residential_split=0.211, merge_within=400),
    dict(type="military_base", name="US Coast Guard Base Charleston", code="CGC",
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
         merge_within=400),                                    # 94 beds
    dict(type="hospital", name="Roper St Francis Mount Pleasant Hospital", code="MP",
         location=[-79.7686, 32.8782], total_capacity=210, pop_size=25,
         merge_within=400),                                    # 85 beds
]

# Terminal employment is in LODES and arrives here through the merge, so
# capacity covers only the gate traffic on top of it -- drayage drivers whose
# LODES workplace is their trucking firm, not the terminal. Union Pier is the
# exception: cruise calls put arriving passengers on the pier, which is inbound
# tourism and nowhere in LODES, hence the residential split.
PORTS = [
    dict(type="port", name="Wando Welch Terminal", code="WW",
         location=[-79.8814, 32.8330], total_capacity=400, pop_size=25,
         merge_within=600),
    dict(type="port", name="North Charleston Terminal", code="NCT",
         location=[-79.9619, 32.9056], total_capacity=300, pop_size=25,
         merge_within=600),
    dict(type="port", name="Hugh K. Leatherman Terminal", code="HKL",
         location=[-79.9387, 32.8409], total_capacity=200, pop_size=25,
         merge_within=600),
    dict(type="port", name="Columbus Street Terminal", code="CST",
         location=[-79.9298, 32.7955], total_capacity=150, pop_size=25,
         merge_within=500),
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
         merge_within=300),
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
RESORTS = [
    dict(type="resort", name="Kiawah Island", code="KIAW",
         location=[-80.0848, 32.6082], total_capacity=3000, pop_size=50,
         residential_split=0.80),
    dict(type="resort", name="Wild Dunes, Isle of Palms", code="WD",
         location=[-79.7384, 32.8046], total_capacity=2500, pop_size=50,
         residential_split=0.80),
    dict(type="resort", name="Folly Beach", code="FOLLY",
         location=[-79.9408, 32.6555], total_capacity=2000, pop_size=50,
         residential_split=0.70),
    dict(type="resort", name="Seabrook Island", code="SEAB",
         location=[-80.1707, 32.5771], total_capacity=1200, pop_size=25,
         residential_split=0.80),
    dict(type="resort", name="Edisto Beach", code="EDIS",
         location=[-80.3348, 32.4794], total_capacity=800, pop_size=25,
         residential_split=0.80),
]


def schools():
    """
    Schools from the NCES Common Core of Data (public) and Private School
    Universe Survey (private), both 2021-22, filtered to the map bbox.

    Capacity is students plus staff. Staff is teacher FTE scaled by 1.9, the
    national ratio of total school employees to teachers. Note that those staff
    are already present in LODES as workers at the school's block and this
    deliberately does not merge them away, so school employment is counted
    twice by design.
    """
    raw = json.load(open(os.path.join(HERE, "schools.json")))
    out = []
    for s in raw:
        cap = s["students"] + s["staff"]
        if cap < 40:
            continue
        code = None
        out.append(dict(
            type="school", name=s["name"], location=[s["lon"], s["lat"]],
            total_capacity=cap,
            pop_size=max(10, min(100, cap // 25)),
            residential_split=0.0,
        ))
    return out


def all_pois():
    groups = [
        ("airport", AIRPORT), ("university", UNIVERSITIES), ("military", MILITARY),
        ("hospital", HOSPITALS), ("port", PORTS), ("shopping", SHOPPING),
        ("attraction", ATTRACTIONS), ("resort", RESORTS), ("school", schools()),
    ]
    pois = []
    for _name, g in groups:
        pois.extend(g)
    return pois


if __name__ == "__main__":
    groups = [
        ("airport", AIRPORT), ("university", UNIVERSITIES), ("military", MILITARY),
        ("hospital", HOSPITALS), ("port", PORTS), ("shopping", SHOPPING),
        ("attraction", ATTRACTIONS), ("resort", RESORTS), ("school", schools()),
    ]
    total = 0
    print(f"{'group':<14}{'points':>8}{'capacity':>12}{'residents':>11}{'jobs':>10}")
    for name, g in groups:
        cap = sum(p["total_capacity"] for p in g)
        res = sum(int(p["total_capacity"] * p.get("residential_split", 0.0)) for p in g)
        print(f"{name:<14}{len(g):>8}{cap:>12,}{res:>11,}{cap - res:>10,}")
        total += cap
    print(f"{'TOTAL':<14}{len(all_pois()):>8}{total:>12,}")
