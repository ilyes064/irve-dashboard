"""Plugged in or left out? — France's public EV charging network, told with open data.

Run:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from sections import conclusions, deep_dives, intro, overview, quality, whatif
from utils.constants import DATA_LICENSE, DATASET_PAGE, DATASET_TITLE, METRICS, POWER_LABELS, PORTAL
from utils.context import Ctx, Filters, apply_filters, dept_table, get_data

st.set_page_config(
    page_title="Plugged in or left out? — EV charging in France",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """<style>
    .block-container {max-width: 1250px; padding-top: 4rem;}
    [data-testid="stMetricValue"] {font-size: 1.9rem;}
    .headline {font-size: 1.15rem; color: #0b0b0b; border-left: 4px solid #2a78d6;
               padding: .35rem .8rem; margin: .4rem 0 1rem 0; background: #f3f7fd;}
    .kicker {color:#52514e; text-transform: uppercase; letter-spacing: .06em; font-size: .78rem; font-weight: 600;}
    </style>""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ data
try:
    with st.spinner("Loading the national charge-point registry (first run downloads ~90 MB, then it is cached)…"):
        df_all, report, ref, geo = get_data()
except Exception as exc:  # noqa: BLE001 — show a useful message instead of a stack trace
    st.error(
        "The dataset could not be downloaded or processed.\n\n"
        f"**Error:** `{exc}`\n\n"
        "Run `python scripts/download_data.py` (or `make data`) with an internet connection, "
        "or pass a local copy with `python scripts/download_data.py --from-file irve.csv`."
    )
    st.stop()

snapshot = pd.Timestamp(report["snapshot_date"])
data_key = report.get("raw_sha256") or report["processed_at"]

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Filters")
    st.caption("Every chart, KPI and headline below updates with these filters.")

    all_regions = (
        ref.drop_duplicates("nom_region")
        .assign(order=lambda d: (d["zone"] != "metro").astype(int))
        .sort_values(["order", "nom_region"])["nom_region"]
        .tolist()
    )
    regions = st.multiselect(
        "Region", all_regions, default=[], placeholder="All of France",
        help="Leave empty for the whole country (13 metropolitan regions + 5 overseas).",
    )

    years_avail = df_all["service_year"].dropna().astype(int)
    y_min, y_max = int(years_avail.min()), int(years_avail.max())
    years = st.slider("Commissioning year", y_min, y_max, (y_min, y_max),
                      help="Year the charge point was put into service (date_mise_en_service).")
    full_years = years == (y_min, y_max)
    include_undated = st.checkbox(
        "Include points with no valid date", value=True, disabled=not full_years,
        help="About a third of points have no usable commissioning date. They can only be "
             "included when the full year range is selected.",
    )

    power = st.multiselect("Power class", POWER_LABELS, default=POWER_LABELS,
                           help="Nominal power of the charge point. Rapid/ultra-rapid (≥50 kW) is what "
                                "long-distance trips rely on.")
    access_opts = sorted(df_all["access"].astype(str).unique())
    access = st.multiselect("Access", access_opts, default=access_opts)
    impl_opts = sorted(df_all["implantation"].astype(str).unique())
    implantation = st.multiselect("Location type", impl_opts, default=impl_opts)

    st.divider()
    metric_key = st.selectbox(
        "Indicator for map & ranking", list(METRICS), format_func=lambda k: METRICS[k][0],
        help="Per-capita indicators are fairer than raw counts: big departments naturally have more chargers.",
    )
    st.divider()
    st.markdown(
        "**Jump to**\n\n"
        "- [The question](#hook)\n- [Key figures](#kpis)\n- [1 · Growth](#growth)\n"
        "- [2 · Geography](#geography)\n- [3 · Urban vs rural](#density)\n"
        "- [4 · Fast charging](#fast)\n- [5 · Who builds it](#operators)\n"
        "- [6 · Zoom on a department](#zoom)\n- [7 · What if…](#whatif)\n"
        "- [Data quality](#quality)\n- [Takeaways](#takeaways)"
    )
    st.divider()
    st.caption(f"Data snapshot: **{snapshot:%d %b %Y}**")

if not power or not access or not implantation:
    st.warning("Select at least one power class, access type and location type in the sidebar.")
    st.stop()

filters = Filters(
    regions=tuple(regions or all_regions),
    years=years,
    include_undated=include_undated and full_years,
    power=tuple(power),
    access=tuple(access),
    implantation=tuple(implantation),
    all_regions=not regions,
    full_scope=(len(power) == len(POWER_LABELS) and set(access) == set(access_opts)
                and set(implantation) == set(impl_opts) and full_years and include_undated),
)
df = apply_filters(df_all, filters, data_key)
if df.empty:
    st.warning("No charge point matches these filters — widen the selection in the sidebar.")
    st.stop()

ctx = Ctx(
    df_all=df_all,
    df=df,
    report=report,
    ref=ref,
    geo=geo,
    filters=filters,
    dept=dept_table(df, ref, filters.regions, f"{data_key}|{filters}"),
    dept_nat=dept_table(df_all, ref, tuple(all_regions), f"{data_key}|national"),
    snapshot=snapshot,
    population=int(ref[ref["nom_region"].isin(filters.regions)]["population"].sum()),
    extras={"metric": metric_key},
)

# ------------------------------------------------------------------ story
intro.render(ctx)
overview.render(ctx)
deep_dives.render(ctx)
whatif.render(ctx)
quality.render(ctx)
conclusions.render(ctx)

st.divider()
st.caption(
    f"Source: «{DATASET_TITLE}» — {PORTAL} ([dataset page]({DATASET_PAGE})) — {DATA_LICENSE}. "
    f"Data as of {snapshot:%d %B %Y}. Population: INSEE populations légales; boundaries: IGN Admin Express "
    "(Licence Ouverte). Code: MIT licence. Built for #EFREIDataStories2026."
)
