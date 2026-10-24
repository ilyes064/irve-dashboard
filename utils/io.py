"""Data access: download with caching, reference tables, processed-data cache."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from utils.constants import (
    DATA_LICENSE,
    DATASET_PAGE,
    DATASET_TITLE,
    DEPT_GEOJSON,
    DEPT_REFERENCE_CSV,
    IRVE_CSV_URL,
    PIPELINE_VERSION,
    PROCESSED_PARQUET,
    QUALITY_JSON,
    RAW_CSV,
    RAW_MANIFEST,
    USECOLS,
)

CHUNK = 1 << 20  # 1 MiB


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def read_manifest() -> dict:
    if RAW_MANIFEST.exists():
        return json.loads(RAW_MANIFEST.read_text())
    return {}


def fetch_and_cache(url: str = IRVE_CSV_URL, force: bool = False, max_age_days: int | None = None) -> Path:
    """Download the consolidated IRVE CSV once and reuse the local copy afterwards.

    The download is streamed to a temporary file and only moved into place when complete,
    so an interrupted download never leaves a truncated CSV behind. A manifest records the
    URL, download time, size and SHA-256 so that every figure in the app can be traced back
    to an exact file.
    """
    if RAW_CSV.exists() and not force:
        manifest = read_manifest()
        if max_age_days is None or not manifest:
            return RAW_CSV
        downloaded = datetime.fromisoformat(manifest["downloaded_at"])
        if (datetime.now(timezone.utc) - downloaded).days < max_age_days:
            return RAW_CSV

    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = RAW_CSV.with_suffix(".part")
    with requests.get(url, stream=True, timeout=(15, 300)) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as f:
            for block in resp.iter_content(CHUNK):
                f.write(block)
    tmp.replace(RAW_CSV)

    manifest = {
        "dataset": DATASET_TITLE,
        "page": DATASET_PAGE,
        "url": url,
        "license": DATA_LICENSE,
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": RAW_CSV.stat().st_size,
        "sha256": _sha256(RAW_CSV),
    }
    RAW_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return RAW_CSV


def load_raw(path: Path = RAW_CSV) -> pd.DataFrame:
    """Read only the columns the app needs, everything as text (typed later in prep.py).

    Reading as ``str`` is deliberate: the consolidated file mixes producers, so booleans,
    numbers and dates come in several spellings that pandas would otherwise mis-infer.
    """
    df = pd.read_csv(
        path,
        usecols=lambda c: c in USECOLS,
        dtype=str,
        keep_default_na=True,
        na_values=["", "nan", "NaN", "None", "null", "NULL", "N/A"],
        low_memory=False,
        encoding="utf-8",
        on_bad_lines="warn",
    )
    for col in USECOLS:  # tolerate older/newer schema versions
        if col not in df.columns:
            df[col] = pd.NA
    return df[USECOLS]


def load_reference() -> pd.DataFrame:
    return pd.read_csv(DEPT_REFERENCE_CSV, dtype={"code_dept": str, "code_region": str})


def load_geojson() -> dict:
    return json.loads(DEPT_GEOJSON.read_text())


def load_processed(expected_sha: str | None) -> tuple[pd.DataFrame, dict] | None:
    """Return the processed table if it was built from the same raw file, else None."""
    if not (PROCESSED_PARQUET.exists() and QUALITY_JSON.exists()):
        return None
    report = json.loads(QUALITY_JSON.read_text())
    if expected_sha and report.get("raw_sha256") != expected_sha:
        return None
    if report.get("pipeline_version") != PIPELINE_VERSION:
        return None
    return pd.read_parquet(PROCESSED_PARQUET), report


def save_processed(df: pd.DataFrame, report: dict) -> None:
    PROCESSED_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED_PARQUET, index=False)
    QUALITY_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))


def build_or_load(raw_path: Path = RAW_CSV, force: bool = False) -> tuple[pd.DataFrame, dict]:
    """Return (clean dataframe, quality report), rebuilding only when the raw file changed."""
    from utils.prep import clean  # local import keeps io.py light for the download script

    manifest = read_manifest()
    sha = manifest.get("sha256") if raw_path == RAW_CSV and manifest else _sha256(raw_path)
    if not force:
        cached = load_processed(sha)
        if cached is not None:
            return cached

    if manifest.get("downloaded_at") and raw_path == RAW_CSV:
        snapshot = datetime.fromisoformat(manifest["downloaded_at"]).date()
    else:
        snapshot = datetime.fromtimestamp(raw_path.stat().st_mtime, tz=timezone.utc).date()

    df, report = clean(load_raw(raw_path), load_reference(), load_geojson(), snapshot=snapshot, raw_sha256=sha)
    report["source_url"] = manifest.get("url", IRVE_CSV_URL)
    report["downloaded_at"] = manifest.get("downloaded_at")
    save_processed(df, report)
    return df, report


LICENSE_TEXT = (
    f"Data: «{DATASET_TITLE}», {DATA_LICENSE}. Source: {DATASET_PAGE}. "
    "Population: INSEE populations légales (Licence Ouverte). "
    "Boundaries: IGN Admin Express (Licence Ouverte). Code: MIT."
)
