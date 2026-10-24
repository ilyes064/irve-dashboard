"""Small Streamlit helpers shared by all sections (consistent headlines, accessible charts)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.viz import PLOTLY_CONFIG


def kicker(text: str) -> None:
    st.markdown(f'<div class="kicker">{text}</div>', unsafe_allow_html=True)


def headline(text: str) -> None:
    """One-sentence takeaway that opens each section (computed from the filtered data)."""
    st.markdown(f'<div class="headline">{text}</div>', unsafe_allow_html=True)


def chart(fig: go.Figure, alt: str, key: str | None = None, **kwargs):
    """Render a Plotly figure with alt text for screen readers and a visible description."""
    out = st.plotly_chart(fig, theme=None, config=PLOTLY_CONFIG, alt=alt, key=key, **kwargs)
    st.caption(f"Chart description: {alt}")
    return out


def data_table(df: pd.DataFrame, label: str = "Show the data behind this chart", **kwargs) -> None:
    with st.expander(label):
        st.dataframe(df, hide_index=True, **kwargs)
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name=f"{label.split()[-1].lower()}.csv", mime="text/csv",
                           key=f"dl_{label}_{len(df)}")


def fmt(n: float, digits: int = 0) -> str:
    """French-style thin-space thousands separator, readable in both languages."""
    return f"{n:,.{digits}f}".replace(",", " ")
