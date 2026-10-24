"""Build the small reference tables bundled with the app (run once, outputs are committed).

Outputs
-------
data/reference/departements.csv
    code_dept, nom_dept, code_region, nom_region, zone, population, area_km2
assets/departements.geojson
    Department boundaries (metropole + 5 DROM), simplified to keep the file light.

Sources
-------
* Population: INSEE populations légales (in force 1 Jan 2026), shipped in the npm package
  @etalab/decoupage-administratif 6.0.0 (Licence Ouverte).
* Boundaries: IGN Admin Express via github.com/gregoiredavid/france-geojson.

Usage
-----
    python scripts/build_reference.py                 # downloads both sources
    python scripts/build_reference.py --pkg-dir DIR --geojson FILE   # offline, local copies
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import shapely
from shapely.geometry import mapping, shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.constants import DEPT_GEOJSON, DEPT_REFERENCE_CSV  # noqa: E402

NPM_TARBALL = "https://registry.npmjs.org/@etalab/decoupage-administratif/-/decoupage-administratif-6.0.0.tgz"
GEOJSON_URL = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/"
    "departements-avec-outre-mer.geojson"
)
EARTH_RADIUS_KM = 6371.0088
SIMPLIFY_TOLERANCE_DEG = 0.008


def _load_package(pkg_dir: Path | None) -> dict[str, list]:
    names = ["communes", "departements", "regions"]
    if pkg_dir:
        return {n: json.loads((pkg_dir / "data" / f"{n}.json").read_text()) for n in names}
    resp = requests.get(NPM_TARBALL, timeout=120)
    resp.raise_for_status()
    out = {}
    with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
        for n in names:
            member = tar.extractfile(f"package/data/{n}.json")
            out[n] = json.load(member)
    return out


def _equal_area_km2(geom) -> float:
    """Area in km² using a sinusoidal (equal-area) projection centred on the geometry."""
    lon0 = geom.centroid.x

    def project(coords: np.ndarray) -> np.ndarray:
        lam = np.radians(coords[:, 0] - lon0)
        phi = np.radians(coords[:, 1])
        return np.column_stack([EARTH_RADIUS_KM * lam * np.cos(phi), EARTH_RADIUS_KM * phi])

    return shapely.transform(geom, project).area


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pkg-dir", type=Path, help="Local extracted npm package directory")
    parser.add_argument("--geojson", type=Path, help="Local departements-avec-outre-mer.geojson")
    args = parser.parse_args()

    pkg = _load_package(args.pkg_dir)
    communes = pd.DataFrame(pkg["communes"])
    communes = communes[communes["type"] == "commune-actuelle"]
    pop = communes.groupby("departement", as_index=False)["population"].sum()
    pop = pop.rename(columns={"departement": "code_dept"})

    depts = pd.DataFrame(pkg["departements"])[["code", "nom", "region", "zone"]]
    depts = depts.rename(columns={"code": "code_dept", "nom": "nom_dept", "region": "code_region"})
    regions = pd.DataFrame(pkg["regions"])[["code", "nom"]].rename(
        columns={"code": "code_region", "nom": "nom_region"}
    )
    ref = depts.merge(regions, on="code_region", how="left").merge(pop, on="code_dept", how="left")

    if args.geojson:
        gj = json.loads(args.geojson.read_text())
    else:
        r = requests.get(GEOJSON_URL, timeout=120)
        r.raise_for_status()
        gj = r.json()

    features, areas = [], {}
    for feat in gj["features"]:
        code = feat["properties"]["code"]
        geom = shape(feat["geometry"])
        areas[code] = _equal_area_km2(geom)
        simple = geom.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
        geo = json.loads(json.dumps(mapping(simple)), parse_float=lambda x: round(float(x), 4))
        features.append(
            {"type": "Feature", "id": code, "properties": {"code": code, "nom": feat["properties"]["nom"]}, "geometry": geo}
        )

    ref["area_km2"] = ref["code_dept"].map(areas).round(1)
    # Keep the 101 departments that have boundaries (drops COM / Clipperton without IGN geometry)
    ref = ref[ref["code_dept"].isin(areas)].sort_values("code_dept").reset_index(drop=True)
    ref["population"] = ref["population"].astype(int)

    DEPT_REFERENCE_CSV.parent.mkdir(parents=True, exist_ok=True)
    ref.to_csv(DEPT_REFERENCE_CSV, index=False)
    DEPT_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    DEPT_GEOJSON.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")))

    print(f"{len(ref)} departments, population {ref['population'].sum():,}")
    print(f"Wrote {DEPT_REFERENCE_CSV} and {DEPT_GEOJSON} ({DEPT_GEOJSON.stat().st_size/1e3:.0f} kB)")


if __name__ == "__main__":
    main()
