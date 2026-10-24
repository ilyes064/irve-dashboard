"""Sections 2–6: geography, urban/rural equity, fast charging, operators, department zoom."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from utils.constants import FAST_THRESHOLD_KW, MAX_MAP_POINTS, METRICS, POWER_LABELS, SEED
from utils.context import Ctx
from utils.prep import gini, lorenz, spearman
from utils.ui import chart, data_table, fmt, headline
from utils.viz import (
    choropleth,
    density_scatter,
    lorenz_chart,
    operator_bar,
    power_mix_by_region,
    ranking_bar,
    small_multiples,
    station_map,
)

FOCUS_KEY = "focus_dept"


def _scope_value(ctx: Ctx, metric: str) -> float:
    """Indicator for the whole selection (ratio of sums, not mean of ratios)."""
    d = ctx.dept
    pop, pts = d["population"].sum(), d["points"].sum()
    return {
        "points_per_100k": pts / pop * 1e5,
        "fast_per_100k": d["fast_points"].sum() / pop * 1e5,
        "kw_per_1k": d["power_mw"].sum() * 1e3 / pop * 1e3,
        "fast_share": d["fast_points"].sum() / pts * 100 if pts else np.nan,
        "points": pts / max(len(d), 1),
    }[metric]


# --------------------------------------------------------------------------------------
def _geography(ctx: Ctx) -> None:
    metric = ctx.extras["metric"]
    label, unit = METRICS[metric]
    d = ctx.dept[ctx.dept["population"] > 0]
    ranked = d.dropna(subset=[metric]).sort_values(metric, ascending=False)
    scope_val = _scope_value(ctx, metric)
    ref_label = "France" if ctx.filters.all_regions else "Selection"

    st.header("2 · Where are the chargers?", anchor="geography")
    is_metro = ranked["zone"].astype(str) == "metro"
    comp = ranked[is_metro] if is_metro.sum() >= 2 else ranked  # overseas get their own sentence
    best, worst = comp.iloc[0], comp.iloc[-1]
    below_half = (ranked[metric] < scope_val / 2).sum() if metric != "points" else None
    gap = best[metric] / worst[metric] if worst[metric] else np.inf
    where = " among metropolitan departments" if comp is not ranked else ""
    text = (f"On <b>{label.lower()}</b>{where}, <b>{best['nom_dept']}</b> leads with {best[metric]:,.1f} and "
            f"<b>{worst['nom_dept']}</b> trails with {worst[metric]:,.1f}")
    text += f" — a <b>{gap:.1f}×</b> gap." if np.isfinite(gap) else "."
    if comp is not ranked and (~is_metro).any():
        o = ranked[~is_metro]
        text += (f" The {len(o)} overseas department(s) range from {o[metric].min():,.1f} to "
                 f"{o[metric].max():,.1f}.")
    if below_half:
        text += f" {below_half} of {len(ranked)} departments are below half the {'French' if ref_label == 'France' else 'selection'} level."
    headline(text)

    left, right = st.columns([1.35, 1])
    with left:
        st.markdown(f"**{label}, by department** — click a department to zoom on it in section 6.")
        focus = st.session_state.get(FOCUS_KEY)
        fig = choropleth(d, ctx.geo, metric, label, unit, highlight=focus)
        event = chart(fig, alt=(
            f"Map of French departments coloured by {label.lower()}, from light blue (low) to dark blue (high). "
            f"Highest: {best['nom_dept']} ({best[metric]:,.1f} {unit}); lowest: {worst['nom_dept']} "
            f"({worst[metric]:,.1f} {unit})."
        ), key="choropleth", on_select="rerun", selection_mode="points")
        try:
            pts = event.selection.points if event else []
            code = pts[0].get("location") if pts else None
            # Act only on a *new* click, so a later choice in the selectbox is not overridden.
            if code and code != st.session_state.get("_last_map_click"):
                st.session_state["_last_map_click"] = code
                st.session_state[FOCUS_KEY] = code
                st.rerun()
        except AttributeError:
            pass
        if any(d["zone"].astype(str) == "drom"):
            st.caption("The map is framed on metropolitan France; the five overseas departments (DROM) appear in "
                       "the ranking and the data table. Colour scale capped at the 2nd–98th percentile of "
                       "metropolitan values — hover for exact figures.")
    with right:
        n = st.slider("Departments shown at each end", 3, 15, 8, key="rank_n")
        chart(ranking_bar(ranked, metric, unit, n, scope_val, ref_label), alt=(
            f"Horizontal bar chart of the {n} best and {n} least equipped departments on {label.lower()}, "
            f"with a dashed line at the {'national' if ref_label == 'France' else 'selection'} value of {scope_val:,.1f}."
        ), key="ranking")

    data_table(
        ranked[["code_dept", "nom_dept", "nom_region", "population", "points", "stations", "fast_points",
                "power_mw", "points_per_100k", "fast_per_100k", "kw_per_1k", "fast_share"]].round(2),
        label="Show the data behind departments",
    )


# --------------------------------------------------------------------------------------
def _density(ctx: Ctx) -> None:
    metric = ctx.extras["metric"]
    if metric == "points":
        metric = "points_per_100k"
    label, unit = METRICS[metric]
    d = ctx.dept[(ctx.dept["points"] > 0)]

    st.header("3 · Cities vs countryside: who is better served?", anchor="density")
    rho = spearman(d["density_hab_km2"], d[metric]) if len(d) > 4 else np.nan
    g = gini(d["points_per_100k"].to_numpy(), d["population"].to_numpy()) if len(d) > 2 else np.nan

    if np.isnan(rho):
        headline("Select more departments to compare dense and rural areas.")
    else:
        strength = "weak" if abs(rho) < 0.3 else "moderate" if abs(rho) < 0.6 else "strong"
        direction = ("denser departments tend to be <b>better</b> equipped per inhabitant" if rho > 0
                     else "denser departments tend to be <b>less</b> equipped per inhabitant")
        headline(
            f"The link between population density and {label.lower()} is {strength} (Spearman ρ = {rho:+.2f}): "
            f"{direction}. Distribution of charge points vs population across departments: Gini = {g:.2f} "
            "(0 = perfectly proportional to population)."
        )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Density vs {label.lower()}** (bubble size = population)")
        chart(density_scatter(d, metric, unit, highlight=st.session_state.get(FOCUS_KEY)), alt=(
            f"Scatter plot with one bubble per department: population density on a log scale on the x-axis and "
            f"{label.lower()} on the y-axis, with a dashed linear trend. Spearman correlation {rho:+.2f}."
        ), key="scatter")
    with c2:
        st.markdown("**How evenly are charge points shared?** (Lorenz curve)")
        chart(lorenz_chart(lorenz(d["points_per_100k"].to_numpy(), d["population"].to_numpy()), g), alt=(
            f"Lorenz curve: departments are sorted from least to best equipped per inhabitant; the curve shows the "
            f"cumulative share of charge points against the cumulative share of population. Gini coefficient {g:.2f}."
        ), key="lorenz")
    st.caption(
        "Reading tip — a correlation describes a pattern, not a cause. Rural departments crossed by motorways host "
        "many fast-charging hubs used by through-traffic, while dense cities rely on on-street AC charging; "
        "per-capita figures do not capture who actually uses each charger."
    )


# --------------------------------------------------------------------------------------
def _fast(ctx: Ctx) -> None:
    df = ctx.df
    st.header("4 · Fast charging is the new frontier", anchor="fast")
    mix = (
        df.dropna(subset=["power_class", "nom_region"])
        .groupby(["nom_region", "power_class"], observed=True).size().rename("points").reset_index()
    )
    mix["nom_region"] = mix["nom_region"].astype(str)
    mix["power_class"] = mix["power_class"].astype(str)
    mix["share"] = mix["points"] / mix.groupby("nom_region")["points"].transform("sum") * 100
    fast_by_reg = (mix[mix["power_class"].isin(POWER_LABELS[3:])].groupby("nom_region")["share"].sum()
                   .reindex(mix["nom_region"].unique()).fillna(0).sort_values())
    mix["nom_region"] = pd.Categorical(mix["nom_region"], categories=fast_by_reg.index, ordered=True)
    mix = mix.sort_values("nom_region")

    if len(fast_by_reg) >= 2:
        headline(
            f"The share of fast points (≥{FAST_THRESHOLD_KW:.0f} kW) ranges from <b>{fast_by_reg.iloc[0]:.0f}%</b> in "
            f"{fast_by_reg.index[0]} to <b>{fast_by_reg.iloc[-1]:.0f}%</b> in {fast_by_reg.index[-1]}: "
            "the same number of chargers can mean very different service for long trips."
        )
    chart(power_mix_by_region(mix), alt=(
        "100% stacked horizontal bars, one per region, showing the share of charge points in each power class, "
        f"sorted by share of fast points. Lowest: {fast_by_reg.index[0]}; highest: {fast_by_reg.index[-1]}."
    ), key="mix")

    st.subheader("Fast points per 100,000 inhabitants over time — one panel per region")
    pop_reg = ctx.ref.groupby("nom_region")["population"].sum()
    fast = df[df["is_fast"].fillna(False) & df["service_year"].notna()]
    yrs = range(max(2015, int(ctx.filters.years[0])), int(ctx.snapshot.year) + 1)
    sm = (fast.groupby(["nom_region", "service_year"], observed=True).size().rename("n").reset_index())
    sm["nom_region"] = sm["nom_region"].astype(str)
    grid = pd.MultiIndex.from_product([sm["nom_region"].unique(), yrs], names=["nom_region", "year"])
    sm = (sm.rename(columns={"service_year": "year"}).set_index(["nom_region", "year"])["n"]
          .reindex(grid, fill_value=0).groupby(level=0).cumsum().reset_index())
    sm["value"] = sm["n"] / sm["nom_region"].map(pop_reg) * 1e5
    nat_fast = ctx.df_all[ctx.df_all["is_fast"].fillna(False) & ctx.df_all["service_year"].notna()]
    nat = nat_fast.groupby("service_year").size().reindex(yrs, fill_value=0).cumsum()
    nat = pd.DataFrame({"year": list(yrs), "value": nat.values / ctx.ref["population"].sum() * 1e5})
    if sm.empty:
        st.info("No dated fast-charging points in this selection.")
        return
    chart(small_multiples(sm, "value", "fast pts / 100k inh.", national=nat), alt=(
        "Small multiples: one line chart per region showing the cumulative number of dated fast charge points per "
        "100,000 inhabitants since 2015, on a shared scale, with the national curve repeated in grey in every panel."
    ), key="smallmult")
    st.caption("Panels sorted from highest to lowest current value; shared y-axis so heights compare directly. "
               "Dated points only.")


# --------------------------------------------------------------------------------------
def _operators(ctx: Ctx) -> None:
    df = ctx.df
    st.header("5 · Who builds the network?", anchor="operators")
    counts = df["operator"].astype(str).value_counts()
    counts = counts[counts.index != "Unknown"]
    share = counts / counts.sum() * 100
    top = share.head(10)
    ops = pd.DataFrame({"operator": top.index, "share": top.values, "points": counts.head(10).values})
    rest = pd.DataFrame({"operator": ["All other operators"], "share": [100 - top.sum()],
                         "points": [counts.iloc[10:].sum()]})
    ops = pd.concat([ops, rest], ignore_index=True)
    hhi = float((share ** 2).sum())
    level = "unconcentrated" if hhi < 1000 else "moderately concentrated" if hhi < 1800 else "highly concentrated"
    headline(
        f"<b>{len(counts):,}</b> operators run the points in this selection; the top 5 hold <b>{share.head(5).sum():.0f}%</b>. "
        f"Herfindahl index {hhi:,.0f} → {'an' if level[0] == 'u' else 'a'} {level} market (competition-authority thresholds 1,000 / 1,800)."
    )
    c1, c2 = st.columns([1.3, 1])
    with c1:
        chart(operator_bar(ops), alt=(
            f"Horizontal bar chart of the ten operators with the most charge points and a grey bar for all others. "
            f"Largest: {ops.iloc[0]['operator']} with {ops.iloc[0]['share']:.1f}%."
        ), key="operators")
    with c2:
        by_type = (df.groupby("implantation", observed=True)
                   .agg(points=("power_kw", "size"), fast_share=("is_fast", "mean")).reset_index())
        by_type["share"] = by_type["points"] / by_type["points"].sum() * 100
        by_type["fast_share"] = by_type["fast_share"] * 100
        st.markdown("**Where chargers are installed**")
        st.dataframe(
            by_type.sort_values("points", ascending=False)[["implantation", "points", "share", "fast_share"]],
            hide_index=True,
            column_config={
                "implantation": "Location type",
                "points": st.column_config.NumberColumn("Points", format="%d"),
                "share": st.column_config.ProgressColumn("Share of points", format="%.1f%%", min_value=0, max_value=100),
                "fast_share": st.column_config.NumberColumn("Fast share", format="%.0f%%"),
            },
        )
        st.caption("Operator names are normalised (case, accents, legal suffixes, eMI3 IDs) so that "
                   "\"IZIVIA\" and \"Izivia SAS\" count once.")


# --------------------------------------------------------------------------------------
def _zoom(ctx: Ctx) -> None:
    st.header("6 · Zoom on a department", anchor="zoom")
    d = ctx.dept[ctx.dept["points"] > 0].sort_values("nom_dept")
    if d.empty:
        return
    codes = d["code_dept"].tolist()
    names = dict(zip(d["code_dept"], d["nom_dept"].astype(str) + " (" + d["code_dept"] + ")"))
    if st.session_state.get(FOCUS_KEY) not in codes:
        st.session_state[FOCUS_KEY] = d.sort_values("population", ascending=False).iloc[0]["code_dept"]
    code = st.selectbox("Department", codes, format_func=names.get, key=FOCUS_KEY,
                        help="You can also click a department on the map in section 2.")
    row = d[d["code_dept"] == code].iloc[0]
    nat = ctx.dept_nat
    nat_rate = nat["points"].sum() / nat["population"].sum() * 1e5
    rank = int((ctx.dept_nat["points_per_100k"] > row["points_per_100k"]).sum()) + 1

    headline(
        f"<b>{row['nom_dept']}</b>: {fmt(row['points'])} points for {fmt(row['population'])} inhabitants — "
        f"{row['points_per_100k']:,.0f} per 100k ({'above' if row['points_per_100k'] >= nat_rate else 'below'} the "
        f"national {nat_rate:,.0f}), ranked <b>{rank}</b> of {len(ctx.dept_nat)} departments."
    )
    c = st.columns(4)
    c[0].metric("Charge points", fmt(row["points"]))
    c[1].metric("Per 100k inhabitants", f"{row['points_per_100k']:,.0f}", delta=f"{row['points_per_100k'] - nat_rate:+,.0f} vs France",
                delta_color="normal")
    c[2].metric("Fast share", f"{row['fast_share']:.0f}%")
    c[3].metric("Inhabitants per point", fmt(row["hab_per_point"]))

    pts = ctx.df[ctx.df["code_dept"].astype(str) == code].dropna(subset=["lat", "lon"])
    key = pts["station_id"].fillna(pts["lat"].round(5).astype(str) + "," + pts["lon"].round(5).astype(str))
    stations = (pts.assign(key=key).groupby("key", observed=True)
                .agg(lat=("lat", "mean"), lon=("lon", "mean"), points=("power_kw", "size"), max_kw=("power_kw", "max"),
                     nom_station=("nom_station", "first"), operator=("operator", "first"))
                .reset_index())
    stations["max_kw"] = stations["max_kw"].astype(float)
    stations["power_class"] = pd.cut(stations["max_kw"], bins=[0, 7.4, 22, 50, 150, np.inf], labels=POWER_LABELS)
    if len(stations) > MAX_MAP_POINTS:
        stations = stations.sample(MAX_MAP_POINTS, random_state=SEED)
        st.caption(f"Map shows a random sample of {MAX_MAP_POINTS:,} stations (seed {SEED}) for speed.")
    if stations.empty:
        st.info("No geolocated stations for this department in the current selection.")
        return
    span = max(stations["lat"].max() - stations["lat"].min(), stations["lon"].max() - stations["lon"].min(), 0.05)
    zoom = float(np.clip(8.6 - np.log2(span / 0.6), 5, 12))
    chart(station_map(stations, (stations["lat"].median(), stations["lon"].median()), zoom), alt=(
        f"Street map of {row['nom_dept']} with one dot per charging station ({len(stations):,} stations), coloured by "
        "the maximum power available, darker meaning faster; dot size grows with the number of charge points."
    ), key="stationmap")
    st.caption("Dot colour = most powerful charge point at the station; size = number of points. Basemap © CARTO, © OpenStreetMap contributors.")


def render(ctx: Ctx) -> None:
    _geography(ctx)
    _density(ctx)
    _fast(ctx)
    _operators(ctx)
    _zoom(ctx)
