"""
Assemble the Charleston.zip release archive from the depot build outputs.

The file set follows what depot's own author ships for depot-built maps
(TPA/JAX/DCA in the Railyard registry): both buildings-index forms, the
foundations PMTiles, and the gzipped ocean depth index. Everything is written
flat -- Railyard requires a ZIP with no nested folders, and this builds the
archive entry by entry so no __MACOSX sidecars can sneak in (the 1.0.0 release
shipped one).
"""
import hashlib
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CITY = "CHS"
MAPDIR = os.path.join(HERE, CITY)
DEMANDDIR = os.path.join(HERE, CITY + "_demand")
OUT = os.path.join(HERE, "dist", "Charleston.zip")

# (source path, name inside the zip, required?)
CONTENTS = [
    (os.path.join(DEMANDDIR, "config.json"), "config.json", True),
    (os.path.join(DEMANDDIR, "demand_data.json"), "demand_data.json", True),
    (os.path.join(MAPDIR, f"{CITY}.pmtiles"), f"{CITY}.pmtiles", True),
    (os.path.join(MAPDIR, f"{CITY}_foundations.pmtiles"), f"{CITY}_foundations.pmtiles", False),
    (os.path.join(MAPDIR, "buildings_index.bin.gz"), "buildings_index.bin.gz", True),
    (os.path.join(MAPDIR, "buildings_index.json.gz"), "buildings_index.json.gz", True),
    (os.path.join(MAPDIR, "ocean_depth_index.json.gz"), "ocean_depth_index.json.gz", False),
    (os.path.join(MAPDIR, "ocean_depth_index_contours.json.gz"), "ocean_depth_index_contours.json.gz", False),
    (os.path.join(MAPDIR, "roads.geojson"), "roads.geojson", True),
    (os.path.join(MAPDIR, "runways_taxiways.geojson"), "runways_taxiways.geojson", True),
]


def main():
    missing = [n for src, n, req in CONTENTS if req and not os.path.exists(src)]
    if missing:
        raise SystemExit("missing required build outputs: " + ", ".join(missing))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    included, skipped = [], []
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for src, name, _req in CONTENTS:
            if not os.path.exists(src):
                skipped.append(name)
                continue
            z.write(src, arcname=name)
            included.append((name, os.path.getsize(src)))

    print(f"wrote {OUT}")
    for name, size in included:
        print(f"  {size / 1048576:9.2f} MB  {name}")
    if skipped:
        print("  not produced by this build: " + ", ".join(skipped))

    zsize = os.path.getsize(OUT)
    digest = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print(f"\narchive: {zsize / 1048576:.2f} MB")
    print(f"sha256 : {digest}")


if __name__ == "__main__":
    sys.exit(main())
