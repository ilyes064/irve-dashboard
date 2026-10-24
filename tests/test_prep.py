"""Unit tests for the cleaning rules — run with `pytest -q` (no download needed)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.constants import USECOLS  # noqa: E402
from utils.io import load_geojson, load_reference  # noqa: E402
from utils.prep import by_department, clean, gini, normalise_operator, parse_bool, spearman  # noqa: E402


def _row(**kw) -> dict:
    base = {c: None for c in USECOLS}
    base.update(
        nom_operateur="Izivia", id_station_itinerance="FRS1", id_pdc_itinerance="FRS1P1",
        implantation_station="Voirie", condition_acces="Accès libre", puissance_nominale="22",
        consolidated_longitude="2.35", consolidated_latitude="48.86",  # Paris
        date_mise_en_service="2023-05-01", date_maj="2024-01-01", prise_type_2="true",
    )
    base.update(kw)
    return base


@pytest.fixture(scope="module")
def ref_geo():
    return load_reference(), load_geojson()


def run(rows, ref_geo):
    ref, geo = ref_geo
    return clean(pd.DataFrame(rows), ref, geo, snapshot=date(2026, 6, 30))


def test_reference_tables_are_complete(ref_geo):
    ref, geo = ref_geo
    assert len(ref) == 101
    assert ref["population"].gt(0).all()
    assert {f["properties"]["code"] for f in geo["features"]} == set(ref["code_dept"])


def test_duplicates_removed_keeping_latest(ref_geo):
    rows = [_row(), _row(), _row(date_maj="2025-01-01", puissance_nominale="50")]
    out, rep = run(rows, ref_geo)
    assert len(out) == 1
    assert out["power_kw"].iloc[0] == 50  # most recent version kept
    checks = {c["check"]: c["rows"] for c in rep["checks"]}
    assert checks["Exact duplicate rows"] == 1 and checks["Duplicate charge-point ID"] == 1


def test_power_units_and_bounds(ref_geo):
    rows = [_row(id_pdc_itinerance=f"P{i}", puissance_nominale=p) for i, p in enumerate(["22000", "0", "7,4", "900"])]
    out, _ = run(rows, ref_geo)
    assert out["power_kw"].tolist()[0] == 22
    assert out["power_kw"].isna().sum() == 2  # 0 kW placeholder and 900 kW outlier
    assert 7.4 in out["power_kw"].dropna().tolist()


def test_swapped_and_invalid_coordinates(ref_geo):
    rows = [
        _row(id_pdc_itinerance="A", consolidated_longitude="48.86", consolidated_latitude="2.35"),  # swapped
        _row(id_pdc_itinerance="B", consolidated_longitude="0", consolidated_latitude="0", code_insee_commune="69123"),
        _row(id_pdc_itinerance="C", consolidated_longitude=None, consolidated_latitude=None,
             coordonneesXY="[-1.55, 47.22]"),  # Nantes via fallback field
    ]
    out, _ = run(rows, ref_geo)
    assert set(out["code_dept"].astype(str)) == {"75", "69", "44"}  # Paris, Rhône (INSEE fallback), Loire-Atlantique
    assert (out["dept_method"].astype(str) == "insee_code").sum() == 1


def test_dates(ref_geo):
    rows = [
        _row(id_pdc_itinerance="A", date_mise_en_service="0001-01-01"),
        _row(id_pdc_itinerance="B", date_mise_en_service="2030-01-01"),
        _row(id_pdc_itinerance="C", date_mise_en_service="pas une date"),
        _row(id_pdc_itinerance="D", date_mise_en_service="2021-03-15"),
    ]
    out, _ = run(rows, ref_geo)
    assert out["service_year"].dropna().tolist() == [2021]


def test_booleans_and_operator_normalisation():
    s = pd.Series(["TRUE", "false", "Oui", "0", "maybe", None])
    assert parse_bool(s).tolist()[:4] == [True, False, True, False]
    assert parse_bool(s).isna().sum() == 2
    ops = normalise_operator(pd.Series(["IZIVIA", "Izivia SAS", " izivia ", "Freshmile | FR*FR1", "Freshmile"]))
    assert ops.nunique() == 2


def test_gini_bounds():
    assert gini(np.array([1, 1, 1]), np.array([1, 1, 1])) == pytest.approx(0, abs=1e-9)
    assert 0 < gini(np.array([0, 0, 10]), np.array([1, 1, 1])) < 1


def test_by_department_per_capita(ref_geo):
    ref, geo = ref_geo
    out, _ = run([_row(id_pdc_itinerance=f"P{i}") for i in range(10)], ref_geo)
    d = by_department(out, ref)
    paris = d[d["code_dept"] == "75"].iloc[0]
    assert paris["points"] == 10
    assert paris["points_per_100k"] == pytest.approx(10 / paris["population"] * 1e5)


def test_spearman_matches_definition():
    a = pd.Series([1, 2, 3, 4, 5]); b = pd.Series([5, 6, 7, 8, 7])
    assert spearman(a, a ** 3) == pytest.approx(1)
    assert spearman(a, -a) == pytest.approx(-1)
    assert -1 <= spearman(a, b) <= 1


def test_category_mapping_is_robust():
    from utils.constants import ACCESS_KEYS, IMPLANTATION_KEYS
    from utils.prep import map_category
    acc = map_category(pd.Series(["Accès libre", "acces libre ", "ACCÈS RÉSERVÉ", None, "autre"]), ACCESS_KEYS)
    assert acc.tolist() == ["Open access", "Open access", "Restricted access", "Not specified", "Not specified"]
    imp = map_category(pd.Series(["Parking privé à usage public", "Parking privé réservé à la clientèle",
                                  "parking public", "Voirie", "Station dédiée à la recharge rapide"]),
                       IMPLANTATION_KEYS)
    assert imp.tolist() == ["Private car park, public use", "Customer-only car park", "Public car park",
                            "On-street", "Dedicated fast-charging station"]
