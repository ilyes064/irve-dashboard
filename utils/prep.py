"""Cleaning, validation and feature engineering for the consolidated IRVE file.

The unit of observation is the *point de charge* (one connector position a car can plug
into). Every rule applied here is logged in a quality report that the app displays, so a
reader can see exactly how many rows each decision touched.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape

from utils.constants import (
    ACCESS_KEYS,
    FAST_THRESHOLD_KW,
    FRANCE_BBOXES,
    IMPLANTATION_KEYS,
    PIPELINE_VERSION,
    MAX_POWER_KW,
    MIN_POWER_KW,
    MIN_SERVICE_YEAR,
    POWER_BINS,
    POWER_LABELS,
    USECOLS,
    WATT_CONFUSION_THRESHOLD,
)

TRUE_VALUES = {"true", "vrai", "1", "oui", "yes", "t", "y"}
FALSE_VALUES = {"false", "faux", "0", "non", "no", "f", "n"}
BOOL_COLS = [
    "prise_type_ef",
    "prise_type_2",
    "prise_type_combo_ccs",
    "prise_type_chademo",
    "prise_type_autre",
    "gratuit",
    "paiement_cb",
    "station_deux_roues",
]
NEAREST_MAX_DEG = 0.05  # ≈ 4–5 km at French latitudes
LEGAL_SUFFIXES =re.compile(r"\b(sas|sasu|sa|sarl|eurl|sem|spl|gie|inc|ltd|gmbh|bv|france)\b\.?", re.I)


# --------------------------------------------------------------------------------------
# Small parsers
# --------------------------------------------------------------------------------------
def parse_bool(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.strip().str.lower()
    out = pd.Series(pd.NA, index=s.index, dtype="boolean")
    out[t.isin(TRUE_VALUES)] = True
    out[t.isin(FALSE_VALUES)] = False
    return out


def parse_number(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.strip().str.replace(",", ".", regex=False)
    t = t.str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(t, errors="coerce")


def parse_xy(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Parse the schema's ``coordonneesXY`` field: "[lon, lat]"."""
    parts = s.astype("string").str.extract(r"\[?\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]?")
    return pd.to_numeric(parts[0], errors="coerce"), pd.to_numeric(parts[1], errors="coerce")


def in_france(lon: pd.Series, lat: pd.Series) -> pd.Series:
    mask = pd.Series(False, index=lon.index)
    for lon_min, lon_max, lat_min, lat_max in FRANCE_BBOXES.values():
        mask |= lon.between(lon_min, lon_max) & lat.between(lat_min, lat_max)
    return mask


def _ascii_lower(s: pd.Series) -> pd.Series:
    return (s.astype("string").str.lower().str.normalize("NFKD")
            .str.encode("ascii", errors="ignore").str.decode("ascii").str.strip())


def map_category(s: pd.Series, keys: list[tuple[tuple[str, ...], str]]) -> pd.Series:
    """Map free-text schema values to labels by keywords, robust to case/accents/typos.

    `keys` is ordered: the first rule whose keywords all appear in the value wins.
    """
    t = _ascii_lower(s).fillna("")
    out = pd.Series("Not specified", index=s.index, dtype=object)
    done = pd.Series(False, index=s.index)
    for words, label in keys:
        hit = ~done
        for w in words:
            hit &= t.str.contains(w, regex=False)
        out[hit] = label
        done |= hit
    return out


def normalise_operator(s: pd.Series) -> pd.Series:
    """Group spelling variants of the same operator ("IZIVIA", "Izivia SAS", " izivia ")."""
    # The consolidation appends the eMI3 operator ID ("Freshmile | FR*FR1"): drop it.
    raw = s.astype("string").str.replace(r"\s*\|\s*[A-Z]{2}\*\w+\s*$", "", regex=True).str.strip()
    key = (
        raw.str.lower()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("ascii")
        .str.replace(LEGAL_SUFFIXES, "", regex=True)
        .str.replace(r"[^a-z0-9]+", " ", regex=True)
        .str.strip()
    )
    key = key.mask(key.isna() | (key == ""), "unknown")
    # Display name = most frequent original spelling within each key
    display = (
        pd.DataFrame({"key": key, "raw": raw.fillna("Unknown")})
        .groupby("key")["raw"]
        .agg(lambda x: x.value_counts().index[0])
    )
    display["unknown"] = "Unknown"
    return key.map(display)


# --------------------------------------------------------------------------------------
# Department assignment
# --------------------------------------------------------------------------------------
def assign_department(
    lon: pd.Series, lat: pd.Series, insee: pd.Series, geojson: dict, valid_codes: set[str]
) -> tuple[pd.Series, pd.Series]:
    """Point-in-polygon join on (unique) coordinates, falling back on the INSEE code.

    Returns (code_dept, method) where method ∈ {"coordinates", "insee_code", "unassigned"}.
    """
    codes = [f["properties"]["code"] for f in geojson["features"]]
    polys = [shape(f["geometry"]) for f in geojson["features"]]
    tree = shapely.STRtree(polys)

    coords = pd.DataFrame({"lon": lon, "lat": lat}).dropna()
    uniq = coords.drop_duplicates().reset_index(drop=True)
    pts = shapely.points(uniq["lon"].to_numpy(), uniq["lat"].to_numpy())
    pt_idx, poly_idx = tree.query(pts, predicate="intersects")
    found = pd.Series(np.array(codes, dtype=object)[poly_idx], index=pt_idx)
    found = found[~found.index.duplicated()]
    uniq["dept"] = found.reindex(range(len(uniq))).to_numpy()
    # Points just off a simplified coastline/border: snap to the nearest department ≤ ~5 km.
    miss = np.flatnonzero(uniq["dept"].isna().to_numpy())
    if len(miss):
        near_pt, near_poly = tree.query_nearest(pts[miss], max_distance=NEAREST_MAX_DEG)
        snapped = pd.Series(np.array(codes, dtype=object)[near_poly], index=miss[near_pt])
        snapped = snapped[~snapped.index.duplicated()]
        uniq.loc[snapped.index, "dept"] = snapped.to_numpy()
    lookup = uniq.set_index(["lon", "lat"])["dept"]

    dept = pd.Series(pd.NA, index=lon.index, dtype="string")
    has_xy = lon.notna() & lat.notna()
    keys = pd.MultiIndex.from_arrays([lon[has_xy], lat[has_xy]])
    dept[has_xy] = lookup.reindex(keys).to_numpy()

    method = pd.Series("unassigned", index=lon.index, dtype="string")
    method[dept.notna()] = "coordinates"

    code = insee.astype("string").str.strip().str.upper()
    from_insee = code.str[:3].where(code.str.startswith("97"), code.str[:2])
    from_insee = from_insee.where(from_insee.isin(valid_codes))
    fill = dept.isna() & from_insee.notna()
    dept[fill] = from_insee[fill]
    method[fill] = "insee_code"
    return dept, method


# --------------------------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------------------------
def clean(
    raw: pd.DataFrame,
    reference: pd.DataFrame,
    geojson: dict,
    snapshot: date | None = None,
    raw_sha256: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    df = raw.copy()
    n_raw = len(df)
    checks: list[dict] = []

    def log(name: str, description: str, rows: int, action: str) -> None:
        checks.append(
            {
                "check": name,
                "description": description,
                "rows": int(rows),
                "pct": round(100 * rows / max(n_raw, 1), 2),
                "action": action,
                "status": "pass" if rows == 0 else "handled",
            }
        )

    missingness = (df[USECOLS].isna().mean() * 100).round(2).sort_values(ascending=False)

    # 1. Exact duplicates ------------------------------------------------------------------
    dup_exact = df.duplicated()
    log("Exact duplicate rows", "Identical rows published twice", dup_exact.sum(), "Dropped")
    df = df[~dup_exact]

    # 2. Duplicate charge-point IDs (same point declared by several producers / versions)
    df["date_maj_dt"] = pd.to_datetime(df["date_maj"], errors="coerce", format="mixed")
    df = df.sort_values("date_maj_dt", ascending=False, na_position="last")
    has_id = df["id_pdc_itinerance"].notna() & (df["id_pdc_itinerance"].str.strip() != "")
    dup_id = has_id & df["id_pdc_itinerance"].str.strip().str.upper().duplicated()
    log(
        "Duplicate charge-point ID",
        "Same id_pdc_itinerance declared more than once",
        dup_id.sum(),
        "Kept the most recently updated record",
    )
    df = df[~dup_id]
    log("Missing charge-point ID", "id_pdc_itinerance empty", (~has_id[~dup_id]).sum(), "Kept (counted)")

    # 3. Booleans --------------------------------------------------------------------------
    for col in BOOL_COLS:
        df[col] = parse_bool(df[col])

    # 4. Power -------------------------------------------------------------------------------
    power = parse_number(df["puissance_nominale"])
    in_watts = power > WATT_CONFUSION_THRESHOLD
    log(
        "Power declared in W",
        f"puissance_nominale > {WATT_CONFUSION_THRESHOLD:,.0f} (kW expected)",
        in_watts.sum(),
        "Divided by 1,000",
    )
    power = power.where(~in_watts, power / 1000)
    zero = power == 0
    log("Power = 0", "Placeholder value meaning 'unknown'", zero.sum(), "Set to missing")
    power = power.mask(zero)
    implausible = power.notna() & ~power.between(MIN_POWER_KW, MAX_POWER_KW)
    log(
        "Implausible power",
        f"Outside {MIN_POWER_KW:g}–{MAX_POWER_KW:g} kW after unit fix",
        implausible.sum(),
        "Set to missing",
    )
    df["power_kw"] = power.mask(implausible)
    log("Missing power", "No usable nominal power", df["power_kw"].isna().sum(), "Kept; excluded from kW metrics")

    # 5. Coordinates -------------------------------------------------------------------------
    lon = parse_number(df["consolidated_longitude"])
    lat = parse_number(df["consolidated_latitude"])
    x2, y2 = parse_xy(df["coordonneesXY"])
    fallback = lon.isna() | lat.isna()
    lon, lat = lon.where(~fallback, x2), lat.where(~fallback, y2)
    ok = in_france(lon, lat)
    swapped = ~ok & in_france(lat, lon)
    log("Swapped lon/lat", "Coordinates valid only once inverted", swapped.sum(), "Swapped back")
    lon, lat = lon.where(~swapped, lat), lat.where(~swapped, lon)
    outside = (lon.notna() & lat.notna()) & ~in_france(lon, lat)
    log("Coordinates outside France", "Not in metropolitan France or the 5 DROM", outside.sum(), "Set to missing")
    df["lon"], df["lat"] = lon.mask(outside), lat.mask(outside)
    log("Missing coordinates", "No usable coordinates", (df["lon"].isna()).sum(), "Department from INSEE code if possible")

    # 6. Commissioning dates ---------------------------------------------------------------------
    if snapshot is None:
        snapshot = datetime.now(timezone.utc).date()
    # The data is only as recent as its latest update: use the last plausible date_maj
    # (≤ download date) as the reference "today" for "last 12 months" style figures.
    latest_update = df["date_maj_dt"][df["date_maj_dt"] <= pd.Timestamp(snapshot)].max()
    if pd.notna(latest_update):
        snapshot = min(snapshot, latest_update.date())
    service = pd.to_datetime(df["date_mise_en_service"], errors="coerce", format="mixed")
    unparsable = df["date_mise_en_service"].notna() & service.isna()
    log("Unparsable date", "date_mise_en_service not a date", unparsable.sum(), "Set to missing")
    too_old = service.dt.year < MIN_SERVICE_YEAR
    future = service > pd.Timestamp(snapshot)
    log("Date before 2010", f"Commissioned before {MIN_SERVICE_YEAR} (placeholder like 0001-01-01)", too_old.sum(), "Set to missing")
    log("Date in the future", f"Commissioning after snapshot ({snapshot})", future.sum(), "Set to missing")
    df["service_date"] = service.mask(too_old | future)
    log("Missing commissioning date", "Unknown date", df["service_date"].isna().sum(), "Kept; excluded from time charts")

    # 7. Department / region ------------------------------------------------------------------
    valid_codes = set(reference["code_dept"])
    df["code_dept"], df["dept_method"] = assign_department(
        df["lon"], df["lat"], df["code_insee_commune"], geojson, valid_codes
    )
    log("No department", "Neither coordinates nor INSEE code locate the point", df["code_dept"].isna().sum(), "Dropped from geo analyses")
    ref_cols = reference[["code_dept", "nom_dept", "code_region", "nom_region", "zone"]]
    df = df.merge(ref_cols, on="code_dept", how="left")

    # 8. Feature engineering ---------------------------------------------------------------------
    df["power_class"] = pd.cut(df["power_kw"], bins=POWER_BINS, labels=POWER_LABELS, right=True)
    df["is_fast"] = df["power_kw"] >= FAST_THRESHOLD_KW
    df["service_year"] = df["service_date"].dt.year.astype("Int64")
    df["operator"] = normalise_operator(df["nom_operateur"].fillna(df["nom_amenageur"]))
    df["implantation"] = map_category(df["implantation_station"], IMPLANTATION_KEYS)
    df["access"] = map_category(df["condition_acces"], ACCESS_KEYS)
    log("Unrecognised location type", "implantation_station empty or outside the schema list",
        (df["implantation"] == "Not specified").sum(), "Labelled 'Not specified'")
    log("Unrecognised access condition", "condition_acces empty or outside the schema list",
        (df["access"] == "Not specified").sum(), "Labelled 'Not specified'")
    df["station_id"] = df["id_station_itinerance"].astype("string").str.strip().str.upper()
    df["has_ccs"] = df["prise_type_combo_ccs"].fillna(False)

    keep = [
        "station_id", "nom_station", "operator", "implantation", "access",
        "power_kw", "power_class", "is_fast", "has_ccs", "prise_type_2", "prise_type_chademo",
        "gratuit", "paiement_cb", "service_date", "service_year",
        "lon", "lat", "code_dept", "nom_dept", "code_region", "nom_region", "zone", "dept_method",
    ]
    out = df[keep].reset_index(drop=True)
    for col in ["operator", "implantation", "access", "nom_dept", "nom_region", "zone", "dept_method", "code_dept", "code_region"]:
        out[col] = out[col].astype("category")

    report = {
        "raw_sha256": raw_sha256,
        "pipeline_version": PIPELINE_VERSION,
        "raw_rows": n_raw,
        "final_rows": len(out),
        "snapshot_date": str(snapshot),
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "missingness_pct": missingness.to_dict(),
        "checks": checks,
        "dept_method": out["dept_method"].value_counts().to_dict(),
    }
    return out, report


# --------------------------------------------------------------------------------------
# Aggregations used by several sections
# --------------------------------------------------------------------------------------
def by_department(df: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    g = (
        df.dropna(subset=["code_dept"])
        .groupby("code_dept", observed=True)
        .agg(
            points=("power_kw", "size"),
            stations=("station_id", "nunique"),
            power_mw=("power_kw", lambda s: s.sum() / 1000),
            fast_points=("is_fast", "sum"),
        )
        .reset_index()
    )
    g["code_dept"] = g["code_dept"].astype(str)
    out = reference.merge(g, on="code_dept", how="left")
    for c in ["points", "stations", "power_mw", "fast_points"]:
        out[c] = out[c].fillna(0)
    out["density_hab_km2"] = out["population"] / out["area_km2"]
    out["points_per_100k"] = out["points"] / out["population"] * 1e5
    out["kw_per_1k"] = out["power_mw"] * 1000 / out["population"] * 1e3
    out["fast_per_100k"] = out["fast_points"] / out["population"] * 1e5
    out["fast_share"] = np.where(out["points"] > 0, out["fast_points"] / out["points"] * 100, np.nan)
    out["hab_per_point"] = np.where(out["points"] > 0, out["population"] / out["points"], np.nan)
    return out


def cumulative_by_month(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["service_date"])
    m = (
        d.assign(month=d["service_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "power_class"], observed=False)
        .size()
        .rename("added")
        .reset_index()
    )
    m["cumulative"] = m.groupby("power_class", observed=False)["added"].cumsum()
    return m


def gini(values: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Gini coefficient of a per-capita indicator, population-weighted if weights given."""
    v = np.asarray(values, dtype=float)
    w = np.ones_like(v) if weights is None else np.asarray(weights, dtype=float)
    order = np.argsort(v)
    v, w = v[order], w[order]
    cw = np.cumsum(w) / w.sum()
    cv = np.cumsum(v * w) / (v * w).sum()
    cw, cv = np.insert(cw, 0, 0), np.insert(cv, 0, 0)
    return float(1 - np.sum((cw[1:] - cw[:-1]) * (cv[1:] + cv[:-1])))


def spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation without scipy: Pearson correlation of average ranks."""
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 3:
        return float("nan")
    return float(d["a"].rank().corr(d["b"].rank()))


def lorenz(values: np.ndarray, weights: np.ndarray) -> pd.DataFrame:
    order = np.argsort(values)
    v, w = np.asarray(values, float)[order], np.asarray(weights, float)[order]
    return pd.DataFrame(
        {
            "pop_share": np.insert(np.cumsum(w) / w.sum(), 0, 0) * 100,
            "points_share": np.insert(np.cumsum(v * w) / (v * w).sum(), 0, 0) * 100,
        }
    )
