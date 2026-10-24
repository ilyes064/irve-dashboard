"""Hook, context, audience and the questions the story answers."""
from __future__ import annotations

import streamlit as st

from utils.constants import AVERE_200K_DATE, TARGET_2030
from utils.context import Ctx
from utils.ui import fmt, kicker


def render(ctx: Ctx) -> None:
    # Compare metropolitan departments: overseas ones have so few points that a ratio
    # against them would be huge and meaningless (they get their own sentence).
    nat = ctx.dept_nat[ctx.dept_nat["points"] > 0]
    metro = nat[nat["zone"].astype(str) == "metro"]
    best = metro.loc[metro["points_per_100k"].idxmax()]
    worst = metro.loc[metro["points_per_100k"].idxmin()]
    ratio = best["points_per_100k"] / worst["points_per_100k"]
    drom = ctx.dept_nat[ctx.dept_nat["zone"].astype(str) == "drom"]
    drom_rate = drom["points"].sum() / drom["population"].sum() * 1e5 if len(drom) else float("nan")
    nat_rate = ctx.dept_nat["points"].sum() / ctx.dept_nat["population"].sum() * 1e5
    total = len(ctx.df_all)
    undated = ctx.df_all["service_date"].isna().mean() * 100

    kicker("EFREI Data Stories 2026 · Open data · data.gouv.fr")
    st.title("Plugged in or left out?", anchor="hook")
    st.markdown("#### France's public EV charging network — fast growth, uneven ground")

    st.markdown(
        f"""
France's national registry of public charging points now lists **{fmt(total)} charge points**.
The government's next milestone is **{fmt(TARGET_2030)} by 2030**. But a national total hides
a local reality: someone living in **{best['nom_dept']}** has
**{ratio:.1f}× more public charge points per inhabitant** than someone in **{worst['nom_dept']}** —
and overseas departments average only **{drom_rate:,.0f} points per 100,000 inhabitants**, against
{nat_rate:,.0f} nationally.

For the millions of households that cannot install a charger at home — flats, on-street parking —
**public charging is the precondition for going electric.** Where the network is thin, switching
is harder.
"""
    )

    c1, c2 = st.columns([1.15, 1])
    with c1:
        st.markdown(
            """
**Who this is for** — elected officials and planners in departments, regions and energy
syndicates (*syndicats d'énergie*) who decide where public money for chargers goes; and
curious EV drivers.

**The questions this dashboard answers**
1. How fast has the network grown — and is the 2030 target in reach?
2. Where are the chargers, relative to where people live?
3. Is access fair between dense cities and rural departments?
4. Is *fast* charging, the kind long trips need, spread as widely?
5. Who builds and runs the network?
6. Can we trust the open data itself?
"""
        )
    with c2:
        st.info(
            "**How to read this page**\n\n"
            "Scroll top to bottom: each section opens with a one-sentence finding in a blue box, "
            "computed live from the data. Use the **sidebar filters** to re-run the whole story for "
            "your region, a period, or a type of charger. Hover any chart for exact values; every chart "
            "has a data table you can download.",
            icon="🧭",
        )
        st.warning(
            "**Main caveats** — the registry only counts points that operators *declare*, so it can differ "
            f"from industry counts (the Avere-France barometer reported 200,045 points on {AVERE_200K_DATE}). "
            f"{undated:.0f}% of points have no usable commissioning date. Details in *Data quality*.",
            icon="⚠️",
        )
