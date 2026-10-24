"""Data quality, validation checks, provenance and ethics."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.constants import DATA_LICENSE, DATASET_PAGE, DATASET_REPLACEMENT_PAGE, SCHEMA_DOC
from utils.context import Ctx
from utils.ui import chart, fmt, headline
from utils.viz import missingness_bar


def render(ctx: Ctx) -> None:
    r = ctx.report
    st.header("Data quality & limitations", anchor="quality")
    checks = pd.DataFrame(r["checks"])
    miss = pd.Series(r["missingness_pct"]).sort_values(ascending=False)
    undated = ctx.df_all["service_date"].isna().mean() * 100
    fixed = checks.loc[checks["action"].str.startswith(("Dropped", "Divided", "Swapped", "Set", "Kept the")), "rows"].sum()
    headline(
        f"{fmt(r['raw_rows'])} raw rows → <b>{fmt(r['final_rows'])}</b> unique charge points. "
        f"{fmt(fixed)} values were corrected or removed by automatic checks; the biggest blind spot is the "
        f"commissioning date, unusable for <b>{undated:.0f}%</b> of points."
    )

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.subheader("Validation checks")
        view = checks.assign(
            status=checks["rows"].map(lambda n: "✅ pass" if n == 0 else "🛠 handled"),
        )[["status", "check", "description", "rows", "pct", "action"]]
        st.dataframe(
            view, hide_index=True, height=35 * (len(view) + 1) + 3,
            column_config={
                "status": st.column_config.TextColumn("Status", width="small"),
                "check": "Check", "description": "Rule",
                "rows": st.column_config.NumberColumn("Rows", format="%d"),
                "pct": st.column_config.NumberColumn("% of raw", format="%.2f%%"),
                "action": "Action taken",
            },
        )
        method = pd.Series(r["dept_method"])
        st.markdown(
            "**Locating each point in a department** — "
            + ", ".join(f"{k.replace('_', ' ')}: {fmt(v)}" for k, v in method.items())
            + ". Points are matched to department boundaries by their coordinates (point-in-polygon, snapping "
              "≤5 km for points just off a simplified coastline); the INSEE commune code is the fallback."
        )
    with c2:
        st.subheader("Missing values in the raw file")
        chart(missingness_bar(miss), alt=(
            "Horizontal bar chart of the percentage of missing values for each raw column used by the app; "
            f"columns above 20% are highlighted in orange. Highest: {miss.index[0]} ({miss.iloc[0]:.0f}%)."
        ), key="missing")

    st.subheader("What this data can and cannot say")
    a, b = st.columns(2)
    with a:
        st.markdown(
            """
- **Declarations, not a census.** Operators must publish their public charge points, but compliance is uneven;
  totals differ from the Avere-France barometer. Missing operators bias some departments downwards.
- **Stock, not usage.** The file says a charger exists, not whether it works, is busy, or is affordable
  (real-time status is a separate dataset, *IRVE dynamique*).
- **No closures.** Decommissioned points may linger; points without a date cannot be placed in time.
- **Per-capita is a lens, not a verdict.** Through-traffic, tourism, second homes and home-charging rates
  differ strongly between departments.
"""
        )
    with b:
        manifest_url = r.get("source_url") or DATASET_PAGE
        st.markdown(
            f"""
- **Source**: data.gouv.fr consolidated file, schema [etalab/schema-irve-statique]({SCHEMA_DOC});
  {DATA_LICENSE}. The data.gouv.fr dataset is being migrated to
  [transport.data.gouv.fr]({DATASET_REPLACEMENT_PAGE}) — the download URL is configurable (`IRVE_URL`).
- **This snapshot**: downloaded {r.get('downloaded_at') or 'locally'} from `{manifest_url}`,
  SHA-256 `{(r.get('raw_sha256') or 'n/a')[:16]}…`; processed {r['processed_at']}.
- **Privacy**: no personal data is used. Operator contact e-mails and phone numbers present in the file
  are deliberately not loaded; all charts aggregate to stations, departments or regions.
- **Reproducibility**: every rule above lives in `utils/prep.py` and `utils/constants.py`; re-running
  `make data` on the same file gives identical results.
"""
        )
