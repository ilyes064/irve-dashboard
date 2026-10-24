"""Loading, filtering and shared aggregates for the Streamlit app (all cached)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from utils.constants import POWER_LABELS, RAW_CSV
from utils.io import build_or_load, fetch_and_cache, load_geojson, load_reference
from utils.prep import by_department


@st.cache_data(show_spinner=False)
def get_data() -> tuple[pd.DataFrame, dict, pd.DataFrame, dict]:
    """Clean table + quality report + department reference + boundaries.

    On a fresh checkout (e.g. Streamlit Community Cloud) the raw file is downloaded once,
    processed, and both versions are reused on later runs.
    """
    if not RAW_CSV.exists():
        fetch_and_cache()
    df, report = build_or_load()
    return df, report, load_reference(), load_geojson()


@dataclass(frozen=True)
class Filters:
    regions: tuple[str, ...]
    years: tuple[int, int]
    include_undated: bool
    power: tuple[str, ...]
    access: tuple[str, ...]
    implantation: tuple[str, ...]
    all_regions: bool = True
    full_scope: bool = True  # True when nothing but the region filter is narrowed

    def describe(self) -> str:
        parts = []
        if not self.all_regions:
            parts.append(", ".join(self.regions) if len(self.regions) <= 3 else f"{len(self.regions)} regions")
        parts.append(f"commissioned {self.years[0]}–{self.years[1]}" + (" + undated" if self.include_undated else ""))
        if len(self.power) < len(POWER_LABELS):
            parts.append(f"{len(self.power)} power class(es)")
        if not self.full_scope and len(self.access) == 1:
            parts.append(self.access[0].lower())
        return " · ".join(parts)


@st.cache_data(show_spinner=False)
def apply_filters(_df: pd.DataFrame, f: Filters, data_key: str) -> pd.DataFrame:
    """`_df` is not hashed (it's large and constant); `data_key` (raw SHA) invalidates the cache."""
    df = _df
    m = df["nom_region"].astype(str).isin(f.regions)
    in_years = df["service_year"].between(f.years[0], f.years[1]).fillna(False).astype(bool)
    m &= in_years | (df["service_year"].isna() & f.include_undated)
    m &= df["power_class"].astype(str).isin(f.power) | (df["power_class"].isna() & (len(f.power) == len(POWER_LABELS)))
    m &= df["access"].astype(str).isin(f.access)
    m &= df["implantation"].astype(str).isin(f.implantation)
    return df[m]


@st.cache_data(show_spinner=False)
def dept_table(_df: pd.DataFrame, reference: pd.DataFrame, regions: tuple[str, ...], key: str) -> pd.DataFrame:
    ref = reference[reference["nom_region"].isin(regions)]
    return by_department(_df, ref)


@dataclass
class Ctx:
    df_all: pd.DataFrame
    df: pd.DataFrame
    report: dict
    ref: pd.DataFrame
    geo: dict
    filters: Filters
    dept: pd.DataFrame          # department table for the current filters
    dept_nat: pd.DataFrame      # department table for the whole country, no filter
    snapshot: pd.Timestamp
    population: int             # population of the regions in scope
    extras: dict = field(default_factory=dict)
