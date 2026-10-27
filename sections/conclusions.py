"""Takeaways, implications and next steps — computed from the national data, not hard-coded."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from utils.constants import FAST_THRESHOLD_KW, TARGET_2030
from utils.context import Ctx
from utils.prep import gini, spearman
from utils.ui import fmt


def render(ctx: Ctx) -> None:
    df, nat, snap = ctx.df_all, ctx.dept_nat, ctx.snapshot
    nat = nat[nat["points"] > 0]
    dated = df["service_date"].notna()
    scale = len(df) / max(dated.sum(), 1)
    last12 = df["service_date"].between(snap - pd.DateOffset(years=1), snap)
    pace = df["service_date"].between(snap - pd.DateOffset(years=2), snap).sum() / 2 * scale
    needed = max(TARGET_2030 - len(df), 0) / ((pd.Timestamp("2030-12-31") - snap).days / 365.25)
    g = gini(nat["points_per_100k"].to_numpy(), nat["population"].to_numpy())
    q = nat["points_per_100k"].quantile([0.1, 0.9])
    rho = spearman(nat["density_hab_km2"], nat["points_per_100k"])
    fast_new = df.loc[last12, "is_fast"].mean() * 100 if last12.any() else np.nan
    fast_all = df["is_fast"].mean() * 100
    low_fast = nat.nsmallest(5, "fast_per_100k")["nom_dept"].astype(str).tolist()
    undated = (~dated).mean() * 100

    st.header("Takeaways & next steps", anchor="takeaways")
    st.caption("Computed on the whole country, independently of the sidebar filters.")

    density_txt = (
        f"Population density explains little of it (ρ = {rho:+.2f}): departments of similar density sit far "
        "apart on the scatter plot." if abs(rho) < 0.3 else
        f"Population density explains part of it (ρ = {rho:+.2f}), but not all."
    )
    trend_txt = (
        f"and the newest points are no faster ({fast_new:.0f}% of last year's additions)"
        if fast_new <= fast_all + 1 else f"although the newest points are faster ({fast_new:.0f}% of last year's additions)"
    )
    st.success(
        f"""
**1 · The network is growing, but not fast enough for 2030.** {fmt(len(df))} points are registered; the recent
pace (~{fmt(pace)}/year) must reach ~{fmt(needed)}/year to hit {fmt(TARGET_2030)} by end-2030
({needed / pace:.1f}× today's pace).

**2 · Access is unequal.** The best-equipped 10% of departments have at least {q[0.9]:,.0f} points per 100k
inhabitants, the least-equipped 10% at most {q[0.1]:,.0f} (Gini {g:.2f}). {density_txt}

**3 · Fast charging is the real divide.** Only {fast_all:.0f}% of points are ≥{FAST_THRESHOLD_KW:.0f} kW, {trend_txt}.
Departments with the fewest fast points per inhabitant: {', '.join(low_fast)}.
""",
        icon="💡",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
**Implications for decision-makers**
- Use **per-capita and per-kW indicators**, not raw counts, to allocate public subsidies (e.g. the
  *Advenir* programme) — raw counts reward big departments.
- Target **the bottom decile first**: they are where an EV is hardest to own without a home charger.
- Plan **fast-charging corridors** in departments that are well covered in AC but thin in DC.
- **Enforce publication**: {undated:.0f}% of records lack a commissioning date and some operators are absent —
  the open data itself is a policy lever.
"""
        )
    with c2:
        st.markdown(
            f"""
**Next steps for the analysis**
- Join **EV registrations per commune** (SDES) to measure *vehicles per charger*, the indicator used by
  the EU AFIR regulation (kW of public charging per registered EV).
- Add **IRVE dynamique** (real-time status) to measure availability and failure rates, not just stock.
- Move from departments to **communes / 15-minute access areas** to find true charging deserts.
- Re-run monthly: the pipeline is cached and reproducible, so the story updates itself.

*Limitation reminder: {undated:.0f}% undated points; declared, not audited, data; correlation ≠ causation.*
"""
        )
