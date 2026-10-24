"""Project-wide constants: data sources, thresholds, colours and narrative reference values.

Everything that a reviewer may want to tweak (URLs, validation bounds, targets) lives here,
so the cleaning and the charts stay deterministic and documented in one place.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"
ASSETS_DIR = ROOT / "assets"

RAW_CSV = RAW_DIR / "irve_statique_consolidated.csv"
RAW_MANIFEST = RAW_DIR / "manifest.json"
PROCESSED_PARQUET = PROCESSED_DIR / "irve_clean.parquet"
QUALITY_JSON = PROCESSED_DIR / "quality_report.json"
DEPT_REFERENCE_CSV = REFERENCE_DIR / "departements.csv"
DEPT_GEOJSON = ASSETS_DIR / "departements.geojson"

# --------------------------------------------------------------------------------------
# Data source (data.gouv.fr — "Fichier consolidé des Bornes de Recharge pour Véhicules
# Électriques", schema etalab/schema-irve-statique v2.3.x)
# --------------------------------------------------------------------------------------
DATASET_TITLE = "Fichier consolidé des Bornes de Recharge pour Véhicules Électriques (IRVE)"
DATASET_PAGE = (
    "https://www.data.gouv.fr/datasets/"
    "fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques/"
)
DATASET_REPLACEMENT_PAGE = (
    "https://transport.data.gouv.fr/datasets/"
    "fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques"
)
SCHEMA_DOC = "https://schema.data.gouv.fr/etalab/schema-irve-statique/latest.html"
# Stable data.gouv.fr resource URL of the consolidated CSV (latest schema version).
# Can be overridden without touching the code: IRVE_URL=... streamlit run app.py
IRVE_CSV_URL = os.environ.get(
    "IRVE_URL",
    "https://www.data.gouv.fr/api/1/datasets/r/eb76d20a-8501-400e-b336-d85724de5435",
)
DATA_LICENSE = "Licence Ouverte / Open Licence 2.0 (Etalab)"
PORTAL = "data.gouv.fr"

POPULATION_SOURCE = (
    "INSEE — populations légales en vigueur au 1er janvier 2026, via le paquet "
    "@etalab/decoupage-administratif 6.0.0 (Licence Ouverte)"
)
GEO_SOURCE = (
    "IGN Admin Express (Licence Ouverte), GeoJSON by github.com/gregoiredavid/france-geojson, "
    "re-simplified for this app"
)

# Columns actually used by the app (read with usecols to keep memory low on the cloud).
USECOLS = [
    "nom_amenageur",
    "nom_operateur",
    "nom_enseigne",
    "id_station_itinerance",
    "nom_station",
    "implantation_station",
    "code_insee_commune",
    "coordonneesXY",
    "nbre_pdc",
    "id_pdc_itinerance",
    "puissance_nominale",
    "prise_type_ef",
    "prise_type_2",
    "prise_type_combo_ccs",
    "prise_type_chademo",
    "prise_type_autre",
    "gratuit",
    "paiement_cb",
    "condition_acces",
    "accessibilite_pmr",
    "station_deux_roues",
    "date_mise_en_service",
    "date_maj",
    "consolidated_longitude",
    "consolidated_latitude",
    "consolidated_commune",
]

# --------------------------------------------------------------------------------------
# Validation rules (documented in the Data Quality section and the README)
# --------------------------------------------------------------------------------------
# Plausible commissioning window: the first public chargers in France date from ~2010.
MIN_SERVICE_YEAR = 2010
# Power: AC chargers start around 1.8–3.7 kW; the most powerful DC units sold today are
# rated 400–480 kW, so anything above 500 kW is treated as an entry error.
MIN_POWER_KW = 1.0
MAX_POWER_KW = 500.0
# Values above this are almost certainly declared in W instead of kW (e.g. 22000 → 22 kW).
WATT_CONFUSION_THRESHOLD = 1000.0

# Bounding boxes used to accept / repair coordinates (lon_min, lon_max, lat_min, lat_max).
FRANCE_BBOXES = {
    "Metropolitan France": (-5.5, 9.8, 41.2, 51.2),
    "Guadeloupe": (-61.9, -60.9, 15.8, 16.6),
    "Martinique": (-61.3, -60.7, 14.3, 14.9),
    "Guyane": (-54.7, -51.5, 2.0, 5.9),
    "La Réunion": (55.1, 55.9, -21.5, -20.8),
    "Mayotte": (44.9, 45.4, -13.1, -12.5),
}

# --------------------------------------------------------------------------------------
# Feature engineering
# --------------------------------------------------------------------------------------
# Power classes used by Avere-France / the AFIR regulation vocabulary.
POWER_BINS = [0, 7.4, 22, 50, 150, float("inf")]
POWER_LABELS = [
    "Slow ≤7.4 kW",
    "Normal 7.4–22 kW",
    "Fast 22–50 kW",
    "Rapid 50–150 kW",
    "Ultra-rapid ≥150 kW",
]
FAST_THRESHOLD_KW = 50.0  # "fast charging" for the KPIs / map metric

# Department indicators offered in the sidebar: key → (label, unit)
METRICS = {
    "points_per_100k": ("Charge points per 100,000 inhabitants", "points / 100k inh."),
    "fast_per_100k": ("Fast (≥50 kW) points per 100,000 inhabitants", "fast points / 100k inh."),
    "kw_per_1k": ("Installed power per 1,000 inhabitants", "kW / 1,000 inh."),
    "fast_share": ("Share of fast (≥50 kW) points", "% of points"),
    "points": ("Charge points (raw count)", "points"),
}

# Keyword rules (accent- and case-insensitive, first match wins) to map the schema's
# free-text values; producers spell them in many ways ("Accès libre", "acces libre", …).
IMPLANTATION_KEYS = [
    (("recharge rapide",), "Dedicated fast-charging station"),
    (("client",), "Customer-only car park"),
    (("prive",), "Private car park, public use"),
    (("parking",), "Public car park"),
    (("voirie",), "On-street"),
]
ACCESS_KEYS = [
    (("reserv",), "Restricted access"),
    (("libre",), "Open access"),
]

# --------------------------------------------------------------------------------------
# Narrative reference values (sourced in the README)
# --------------------------------------------------------------------------------------
TARGET_100K = 100_000  # Initial national target for end-2021, reached 5 May 2023 (Avere-France)
TARGET_2030 = 400_000  # Government target for 2030
AVERE_200K_DATE = "31 July 2026"  # Avere-France barometer: 200,045 public points

# Bump when cleaning rules change: cached processed data is rebuilt automatically.
PIPELINE_VERSION = 2

# Reproducibility: any random sampling (e.g. map point thinning) uses this seed.
SEED = 42
MAX_MAP_POINTS = 6_000

# --------------------------------------------------------------------------------------
# Colours — validated with a CVD/contrast checker (see README › Accessibility).
# Power classes are *ordered*, so they use one hue light→dark (ordinal ramp), never a
# rainbow. Categorical slots are used in this fixed order and never cycled.
# --------------------------------------------------------------------------------------
POWER_COLORS = {
    "Slow ≤7.4 kW": "#86b6ef",
    "Normal 7.4–22 kW": "#5598e7",
    "Fast 22–50 kW": "#2a78d6",
    "Rapid 50–150 kW": "#1c5cab",
    "Ultra-rapid ≥150 kW": "#104281",
}
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
OTHER_COLOR = "#b5b4ad"
ACCENT = "#2a78d6"
HIGHLIGHT = "#eb6834"
SEQUENTIAL_SCALE = [
    [0.0, "#cde2fb"], [0.17, "#9ec5f4"], [0.33, "#6da7ec"], [0.5, "#3987e5"],
    [0.67, "#256abf"], [0.83, "#184f95"], [1.0, "#0d366b"],
]
# Chart chrome
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
