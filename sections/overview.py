"""KPI header + section 1: how fast is the network growing?"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.constants import FAST_THRESHOLD_KW, POWER_LABELS, TARGET_100K
from utils.context import Ctx
from utils.prep import cumulative_by_month
from utils.ui import chart, data_table, fmt, headline
from utils.viz import growth_chart, yearly_additions


def _kpis(ctx: Ctx) -> None:
    df, snap = ctx.df, ctx.snapshot
    last12 = df["service_date"].between(snap - pd.DateOffset(years=1), snap)
    prev12 = df["service_date"].between(snap - pd.DateOffset(years=2), snap - pd.DateOffset(years=1), inclusive="left")
    n, n12, p12 = len(df), int(last12.sum()), int(prev12.sum())
    per100k = n / ctx.population * 1e5
    nat_per100k = len(ctx.df_all) / ctx.ref["population"].sum() * 1e5
    fast_share = df["is_fast"].mean() * 100
    fast_share_12 = df.loc[last12, "is_fast"].mean() * 100 if n12 else float("nan")

    st.header("Key figures", anchor="kpis")
    st.caption(f"For the current selection — {ctx.filters.describe()}. Deltas compare the last 12 months "
               f"to the 12 months before (snapshot {snap:%d %b %Y}).")
    c = st.columns(5)
    c[0].metric("Public charge points", fmt(n),
                delta=f"+{fmt(n12)} in last 12 months" if n12 else None,
                help="Rows in the registry after de-duplication. Delta = points commissioned in the last 12 months "
                     "(dated points only).")
    c[1].metric("Charging stations", fmt(df["station_id"].nunique()),
                help="Distinct id_station_itinerance. A station groups several charge points.")
    c[2].metric("Installed power", f"{df['power_kw'].sum() / 1000:,.0f} MW",
                help="Sum of nominal power of points with a valid power value.")
    c[3].metric("Points per 100,000 inhabitants", f"{per100k:,.0f}",
                delta=f"{per100k - nat_per100k:+,.0f} vs France" if not ctx.filters.all_regions else None,
                delta_color="off",
                help="Population: INSEE populations légales (in force 1 Jan 2026) of the regions in scope.")
    c[4].metric(f"Fast (≥{FAST_THRESHOLD_KW:.0f} kW) share", f"{fast_share:.1f}%",
                delta=(f"{fast_share_12 - fast_share:+.1f} pts among last-12-month additions"
                       if n12 >= 100 else None),
                help="Share of points whose nominal power is at least 50 kW (DC fast charging).")
    if p12:
        growth = (n12 / p12 - 1) * 100
        st.caption(f"Pace: {fmt(n12)} points commissioned in the last 12 months vs {fmt(p12)} the year before "
                   f"({growth:+.0f}%).")


def render(ctx: Ctx) -> None:
    _kpis(ctx)
    df, snap = ctx.df, ctx.snapshot

    st.header("1 · How fast is the network growing?", anchor="growth")
    monthly = cumulative_by_month(df)
    dated = df["service_date"].notna()
    if monthly.empty:
        st.info("No dated charge points in this selection.")
        return

    total_series = monthly.groupby("month")["added"].sum().cumsum()
    ref_date = snap - pd.DateOffset(years=3)
    before = total_series[total_series.index <= ref_date]
    then = int(before.iloc[-1]) if len(before) else 0
    now = int(total_series.iloc[-1])
    last12 = df["service_date"].between(snap - pd.DateOffset(years=1), snap)
    rapid12 = df.loc[last12, "is_fast"].mean() * 100 if last12.any() else 0
    stock_fast = df["is_fast"].mean() * 100
    prev12 = df["service_date"].between(snap - pd.DateOffset(years=2), snap - pd.DateOffset(years=1),
                                        inclusive="left").sum()
    if then:
        text = (f"The dated network grew <b>{now / then:.1f}×</b> in three years ({fmt(then)} → {fmt(now)} points "
                f"since {ref_date:%b %Y}).")
        if prev12 >= 100:
            change = (last12.sum() / prev12 - 1) * 100
            text += (f" But the pace is <b>{'slowing' if change < -5 else 'rising' if change > 5 else 'stable'}</b>: "
                     f"{fmt(last12.sum())} points commissioned in the last 12 months vs {fmt(prev12)} the year "
                     f"before ({change:+.0f}%, partly a publication lag).")
        if last12.any():
            text += (f" {rapid12:.0f}% of the newest points are fast (≥{FAST_THRESHOLD_KW:.0f} kW), "
                     f"{'more' if rapid12 > stock_fast + 1 else 'less' if rapid12 < stock_fast - 1 else 'about as much'}"
                     f" than in the existing network ({stock_fast:.0f}%).")
        headline(text)
    else:
        headline(f"{fmt(now)} dated charge points in this selection; {rapid12:.0f}% of the last 12 months' additions are fast.")

    show_targets = ctx.filters.all_regions and ctx.filters.full_scope
    targets = {"100,000 — national target for end-2021, reached 5 May 2023 (Avere-France)":
               (pd.Timestamp("2023-05-05"), TARGET_100K)} if show_targets else None
    fig = growth_chart(monthly, total_now=len(df), snapshot=snap, targets=targets)
    chart(fig, alt=(
        f"Stacked area chart of the cumulative number of public charge points by month of commissioning, split by "
        f"five power classes from slow to ultra-rapid. The total of dated points reaches {fmt(now)}; the orange dot "
        f"at the right shows the {fmt(len(df))} points in the file including undated ones."
        + (" A dashed line marks the 100,000 target and a dotted vertical line the date it was officially reached." if show_targets else "")
    ), key="growth")
    st.caption(
        f"Only points with a valid commissioning date ({dated.mean() * 100:.0f}% of the selection) can be placed on the "
        "timeline — the black line therefore under-states the stock; the orange dot is the full count today. "
        + ("" if show_targets else "National targets are hidden because the selection is not the whole country.")
    )

    st.subheader("New points per year, by power class")
    yearly = (
        df.dropna(subset=["service_year"])
        .groupby(["service_year", "power_class"], observed=False).size().rename("added").reset_index()
    )
    yearly = yearly[yearly["power_class"].isin(POWER_LABELS)]
    chart(yearly_additions(yearly), alt=(
        "Stacked bar chart of charge points commissioned each year, split by power class. Each year's bar shows "
        "how many slow, normal, fast, rapid and ultra-rapid points were added."
    ), key="yearly")
    st.caption(f"{snap.year} is a partial year (up to {snap:%d %b}).")
    data_table(
        yearly.pivot(index="service_year", columns="power_class", values="added").fillna(0).astype(int)
        .reset_index().rename(columns={"service_year": "year"}),
        label="Show the data behind yearly",
    )
