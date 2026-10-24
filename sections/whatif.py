"""Section 7: what-if projection to the 2030 target, with documented assumptions."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from utils.constants import AVERE_200K_DATE, TARGET_2030
from utils.context import Ctx
from utils.ui import chart, fmt, headline
from utils.viz import projection_chart

TARGET_DATE = pd.Timestamp("2030-12-31")
AVERE_COUNT, AVERE_DATE = 200_045, pd.Timestamp("2026-07-31")


def _project(start_value: float, start_date: pd.Timestamp, annual: float, growth: float) -> pd.DataFrame:
    """Year-end stock if `annual` points are added in year 1, then additions change by `growth`/yr."""
    dates = [start_date] + list(pd.date_range(f"{start_date.year}-12-31", TARGET_DATE, freq="YE"))
    dates = sorted(set(d for d in dates if d >= start_date))
    out, value, prev = [], start_value, start_date
    for i, d in enumerate(dates):
        if i:
            years_elapsed = (d - start_date).days / 365.25
            rate = annual * (1 + growth) ** max(np.floor(years_elapsed - 1e-9), 0)
            value += rate * (d - prev).days / 365.25
        out.append((d, value))
        prev = d
    return pd.DataFrame(out, columns=["date", "points"])


def _reach_date(start_value: float, start_date: pd.Timestamp, annual: float, growth: float, target: float) -> str:
    if start_value >= target:
        return "already reached"
    value, d = start_value, start_date
    for _ in range(12 * 40):  # monthly steps, up to 40 years
        years_elapsed = (d - start_date).days / 365.25
        value += annual * (1 + growth) ** np.floor(years_elapsed) / 12
        d += pd.DateOffset(months=1)
        if value >= target:
            return f"{d:%b %Y}"
    return "not before 2066"


def render(ctx: Ctx) -> None:
    df, snap = ctx.df, ctx.snapshot
    st.header("7 · What if… will 2030 be reached?", anchor="whatif")

    national = ctx.filters.all_regions
    pop_share = ctx.population / ctx.ref["population"].sum()
    target = TARGET_2030 * pop_share
    target_label = ("400,000 — national target for 2030" if national
                    else f"{fmt(target)} — this selection's population share ({pop_share:.1%}) of the 400,000 target")

    dated = df["service_date"].notna()
    if dated.sum() < 50:
        st.info("Not enough dated charge points in this selection to estimate a pace.")
        return
    scale = len(df) / dated.sum()
    last24 = df["service_date"].between(snap - pd.DateOffset(years=2), snap).sum()
    pace = last24 / 2 * scale

    c1, c2 = st.columns([1, 1.6])
    with c1:
        use_avere = False
        if national and ctx.filters.full_scope:
            use_avere = st.toggle(
                f"Start from the Avere-France count ({fmt(AVERE_COUNT)} on {AVERE_200K_DATE})",
                value=False, help="The industry barometer counts more points than operators declare to the open registry.",
            )
        start_value, start_date = (AVERE_COUNT, AVERE_DATE) if use_avere else (len(df), snap)
        years_left = (TARGET_DATE - start_date).days / 365.25
        needed = max(target - start_value, 0) / years_left

        annual = st.slider("New charge points per year (your scenario)", 0, int(max(needed, pace) * 2.2 // 1000 * 1000 + 1000),
                           int(round(pace, -2)), step=500,
                           help=f"Default = recent pace: {fmt(pace)} per year (last 24 months, scaled for undated points).")
        growth = st.slider("Yearly change in that pace (%)", -20, 30, 0, step=5,
                           help="0% = constant number of new points each year; +10% = each year adds 10% more than the last.") / 100

    scenarios = pd.concat([
        _project(start_value, start_date, pace, 0.0).assign(scenario=f"Recent pace ({fmt(pace)}/yr)"),
        _project(start_value, start_date, annual, growth).assign(
            scenario=f"Your scenario ({fmt(annual)}/yr, {growth:+.0%}/yr)"),
        _project(start_value, start_date, needed, 0.0).assign(scenario=f"Pace needed ({fmt(needed)}/yr)"),
    ])

    dated_df = df[dated]
    hist_years = range(max(2016, int(dated_df["service_year"].min())), snap.year)
    hist = pd.Series(
        {pd.Timestamp(f"{y}-12-31"): (dated_df["service_date"] <= pd.Timestamp(f"{y}-12-31")).sum() * scale
         for y in hist_years}
    )
    hist[snap] = len(df)

    reach_now = _reach_date(start_value, start_date, pace, 0.0, target)
    reach_you = _reach_date(start_value, start_date, annual, growth, target)
    end_you = scenarios[scenarios["scenario"].str.startswith("Your")]["points"].iloc[-1]

    with c1:
        headline(
            f"At the recent pace of <b>{fmt(pace)} points a year</b>, the target is reached in <b>{reach_now}</b>. "
            f"Meeting it by end-2030 takes <b>{fmt(needed)} a year</b> "
            f"({needed / pace:.1f}× the recent pace)." if pace else "No recent additions in this selection."
        )
        st.metric("Your scenario: target reached", reach_you,
                  delta=f"{fmt(end_you)} points at end-2030 ({end_you / target:.0%} of target)", delta_color="off")
    with c2:
        chart(projection_chart(hist, scenarios, target, target_label), alt=(
            f"Line chart of the estimated stock of charge points since {hist_years.start} and three projections to "
            f"end-2030: recent pace ({fmt(pace)} per year), the user's scenario, and the pace needed "
            f"({fmt(needed)} per year) to reach {fmt(target)} points."
        ), key="projection")

    with st.expander("Assumptions behind this projection (read before quoting a number)"):
        st.markdown(
            f"""
- **Starting stock**: {'the Avere-France barometer count' if use_avere else 'all charge points in the registry for this selection'}
  ({fmt(start_value)} on {start_date:%d %b %Y}).
- **Recent pace**: points commissioned in the 24 months before the snapshot, ÷ 2, multiplied by
  {scale:.2f} because {1 / scale:.0%} of points carry a valid date — i.e. *undated points are assumed to
  follow the same timing as dated ones*.
- **Historical line**: same scaling applied to year-end cumulative counts — an estimate, not an observation.
- **Regional targets**: when you filter regions, the 400,000 target is split by population share. This is a
  fairness benchmark, not an official regional objective.
- **What is ignored**: decommissioned chargers (the registry does not record closures), declaration lag
  (recent points may be published months later), and the shift towards fewer but more powerful chargers —
  the 2030 objective is about points, while drivers increasingly care about kW.
"""
        )
