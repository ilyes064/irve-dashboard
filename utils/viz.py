"""Chart builders. One place for styling so every chart shares fonts, grid, units and colours."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from utils.constants import (
    ACCENT,
    AXIS,
    CATEGORICAL,
    FONT,
    GRID,
    HIGHLIGHT,
    INK,
    INK_2,
    MUTED,
    OTHER_COLOR,
    POWER_COLORS,
    POWER_LABELS,
    SEQUENTIAL_SCALE,
    SURFACE,
)

PLOTLY_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _style(fig: go.Figure, title: str | None = None, height: int = 420, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK), x=0, xanchor="left") if title else None,
        font=dict(family=FONT, size=13, color=INK_2),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        height=height,
        margin=dict(l=10, r=20, t=50 if title else 20, b=10),
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, size=13, color=INK), bordercolor=AXIS),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text="",
                    font=dict(size=12, color=INK_2)),
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickcolor=AXIS, ticks="outside", automargin=True,
                     title_font=dict(size=12, color=INK_2), tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, gridwidth=1, zeroline=False, linecolor=AXIS, automargin=True,
                     title_font=dict(size=12, color=INK_2), tickfont=dict(color=MUTED))
    return fig


def _fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ")


# --------------------------------------------------------------------------------------
# 1. Growth over time
# --------------------------------------------------------------------------------------
def growth_chart(monthly: pd.DataFrame, total_now: int, snapshot: pd.Timestamp,
                 targets: dict[str, tuple[pd.Timestamp | None, int]] | None = None) -> go.Figure:
    """Stacked cumulative area by power class + annotated national milestones."""
    fig = go.Figure()
    for label in POWER_LABELS:
        d = monthly[monthly["power_class"] == label]
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d["month"], y=d["cumulative"], name=label, mode="lines", stackgroup="one",
            line=dict(width=0.8, color=SURFACE), fillcolor=POWER_COLORS[label],
            hovertemplate=f"<b>{label}</b><br>%{{x|%b %Y}}: %{{y:,.0f}} points<extra></extra>",
        ))
    dated_total = monthly.groupby("month")["added"].sum().cumsum()
    if not dated_total.empty:
        fig.add_trace(go.Scatter(
            x=dated_total.index, y=dated_total.values, name="All dated points", mode="lines",
            line=dict(color=INK, width=2),
            hovertemplate="<b>Total (dated)</b><br>%{x|%b %Y}: %{y:,.0f} points<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=[snapshot], y=[total_now], mode="markers+text", name="Total incl. undated",
        marker=dict(size=10, color=HIGHLIGHT, line=dict(color=SURFACE, width=2)),
        text=[f"{_fmt(total_now)} today"], textposition="middle left", textfont=dict(color=INK, size=12),
        hovertemplate="<b>All points in the file</b><br>incl. those without a date: %{y:,.0f}<extra></extra>",
    ))
    for label, (when, value) in (targets or {}).items():
        fig.add_hline(y=value, line=dict(color=MUTED, width=1.2, dash="dash"))
        fig.add_annotation(x=0, xref="paper", y=value, text=label, showarrow=False, xanchor="left",
                           yanchor="bottom", font=dict(size=11, color=INK_2), bgcolor="rgba(252,252,251,0.85)")
        if when is not None:
            fig.add_vline(x=when, line=dict(color=MUTED, width=1, dash="dot"))
    fig.update_yaxes(title_text="Cumulative public charge points", tickformat=",")
    fig.update_xaxes(title_text="Commissioning month")
    return _style(fig, height=460)


def yearly_additions(df_year: pd.DataFrame) -> go.Figure:
    """New points per year, stacked by power class (ordinal ramp)."""
    fig = go.Figure()
    for label in POWER_LABELS:
        d = df_year[df_year["power_class"] == label]
        fig.add_trace(go.Bar(
            x=d["service_year"], y=d["added"], name=label, marker_color=POWER_COLORS[label],
            marker_line=dict(color=SURFACE, width=1),
            hovertemplate=f"<b>{label}</b><br>%{{x}}: %{{y:,.0f}} new points<extra></extra>",
        ))
    fig.update_layout(barmode="stack", bargap=0.25)
    fig.update_yaxes(title_text="New charge points commissioned", tickformat=",")
    fig.update_xaxes(title_text="Year of commissioning", dtick=1)
    return _style(fig, height=380)


# --------------------------------------------------------------------------------------
# 2. Geography
# --------------------------------------------------------------------------------------
def choropleth(dept: pd.DataFrame, geojson: dict, metric: str, metric_label: str, unit: str,
               highlight: str | None = None) -> go.Figure:
    """Department choropleth (SVG, no tile server). Framed on metropolitan France; DROM are in the ranking."""
    d = dept.copy()
    d["value"] = d[metric]
    # Colour range from metropolitan values (2nd–98th pct) so a few overseas or extreme
    # departments do not wash out the contrast for everyone else.
    metro = d.loc[d["zone"].astype(str) == "metro", "value"].dropna()
    rng = metro if len(metro) > 5 else d["value"].dropna()
    zmin, zmax = float(rng.quantile(0.02)), float(rng.quantile(0.98))
    fig = go.Figure(go.Choropleth(
        geojson=geojson, locations=d["code_dept"], z=d["value"], featureidkey="properties.code",
        colorscale=SEQUENTIAL_SCALE, marker_line=dict(color=SURFACE, width=0.7), zmin=zmin, zmax=zmax,
        colorbar=dict(title=dict(text=unit, font=dict(size=11, color=INK_2)), thickness=12, len=0.7,
                      tickfont=dict(color=MUTED, size=11), outlinewidth=0),
        customdata=np.stack([d["nom_dept"], d["code_dept"], d["points"], d["population"]], axis=-1),
        hovertemplate=(
            "<b>%{customdata[0]} (%{customdata[1]})</b><br>"
            f"{metric_label}: %{{z:,.1f}} {unit}<br>"
            "Charge points: %{customdata[2]:,.0f}<br>Population: %{customdata[3]:,.0f}<extra></extra>"
        ),
    ))
    if highlight is not None and highlight in set(d["code_dept"]):
        h = d[d["code_dept"] == highlight]
        fig.add_trace(go.Choropleth(
            geojson=geojson, locations=h["code_dept"], z=[1], featureidkey="properties.code",
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
            marker_line=dict(color=HIGHLIGHT, width=3), hoverinfo="skip",
        ))
    fig.update_geos(visible=False, bgcolor=SURFACE, projection_type="mercator",
                    lonaxis_range=[-5.3, 9.8], lataxis_range=[41.2, 51.2])
    fig = _style(fig, height=560, legend=False)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    return fig


def ranking_bar(dept: pd.DataFrame, metric: str, unit: str, n: int, national: float,
                ref_label: str = "France") -> go.Figure:
    """Top-n and bottom-n departments side by side in one sorted bar chart."""
    d = dept.dropna(subset=[metric]).sort_values(metric, ascending=False)
    top, bottom = d.head(n), d.tail(n)
    sel = pd.concat([top.assign(group="Best served"), bottom.assign(group="Least served")]).drop_duplicates("code_dept")
    sel = sel.iloc[::-1]
    labels = sel["nom_dept"].astype(str) + " (" + sel["code_dept"].astype(str) + ")"
    colors = np.where(sel["group"] == "Best served", ACCENT, HIGHLIGHT)
    fig = go.Figure(go.Bar(
        x=sel[metric], y=labels, orientation="h", marker_color=colors,
        marker_line=dict(color=SURFACE, width=1),
        text=sel[metric].map(lambda v: f"{v:,.0f}" if v >= 10 else f"{v:,.1f}"),
        textposition="outside", textfont=dict(color=INK_2, size=11), cliponaxis=False,
        customdata=sel["group"],
        hovertemplate="<b>%{y}</b><br>%{x:,.1f} " + unit + "<br>%{customdata}<extra></extra>",
    ))
    fig.add_vline(x=national, line=dict(color=INK, width=1.2, dash="dash"))
    fig.add_annotation(x=national, y=1.0, yref="paper", text=f"{ref_label}: {national:,.1f}" if national < 10 else f"{ref_label}: {national:,.0f}", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=11, color=INK))
    fig.update_xaxes(title_text=unit, showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return _style(fig, height=max(360, 26 * len(sel) + 80), legend=False)


def density_scatter(dept: pd.DataFrame, metric: str, unit: str, highlight: str | None = None) -> go.Figure:
    """Population density (log) vs equipment per capita: is the network urban-biased?"""
    d = dept[(dept["points"] > 0) & dept[metric].notna()].copy()
    is_drom = d["zone"].astype(str) == "drom"
    fig = go.Figure()
    for flag, name, color, symbol in [(False, "Metropolitan France", ACCENT, "circle"),
                                      (True, "Overseas (DROM)", HIGHLIGHT, "diamond")]:
        s = d[is_drom == flag]
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s["density_hab_km2"], y=s[metric], mode="markers", name=name,
            marker=dict(size=np.clip(np.sqrt(s["population"]) / 45, 8, 40), color=color, opacity=0.75,
                        symbol=symbol, line=dict(color=SURFACE, width=1.5)),
            customdata=np.stack([s["nom_dept"], s["code_dept"], s["population"]], axis=-1),
            hovertemplate=("<b>%{customdata[0]} (%{customdata[1]})</b><br>Density: %{x:,.0f} inh./km²<br>"
                           f"%{{y:,.1f}} {unit}<br>Population: %{{customdata[2]:,.0f}}<extra></extra>"),
        ))
    # Least-squares fit on log10(density) — descriptive only
    x, y = np.log10(d["density_hab_km2"].to_numpy(float)), d[metric].to_numpy(float)
    if len(d) > 3:
        b, a = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        fig.add_trace(go.Scatter(x=10 ** xs, y=a + b * xs, mode="lines", name="Linear fit (log density)",
                                 line=dict(color=MUTED, width=2, dash="dash"), hoverinfo="skip"))
    if highlight is not None:
        h = d[d["code_dept"] == highlight]
        for _, r in h.iterrows():
            fig.add_annotation(x=np.log10(r["density_hab_km2"]), y=r[metric], text=str(r["nom_dept"]),
                               showarrow=True, arrowcolor=INK, font=dict(color=INK, size=12), ax=30, ay=-30)
    fig.update_xaxes(type="log", title_text="Population density (inhabitants per km², log scale)")
    fig.update_yaxes(title_text=unit, range=[min(0, float(d[metric].min())), float(d[metric].max()) * 1.12])
    return _style(fig, height=460)


def lorenz_chart(curve: pd.DataFrame, g: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", name="Perfect equality",
                             line=dict(color=MUTED, dash="dash", width=1.5), hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=curve["pop_share"], y=curve["points_share"], mode="lines", name="Observed (departments)",
        line=dict(color=ACCENT, width=2.5), fill="tonexty", fillcolor="rgba(42,120,214,0.12)",
        hovertemplate="Least-equipped %{x:.0f}% of the population<br>share %{y:.1f}% of charge points<extra></extra>",
    ))
    fig.add_annotation(x=62, y=30, text=f"Gini = {g:.2f}", showarrow=False, font=dict(size=14, color=INK))
    fig.update_xaxes(title_text="Cumulative share of population (%), least → best equipped",
                     range=[0, 100])
    fig.update_yaxes(title_text="Cumulative share of charge points (%)", range=[0, 100])
    return _style(fig, height=420)


# --------------------------------------------------------------------------------------
# 3. Small multiples & composition
# --------------------------------------------------------------------------------------
def power_mix_by_region(mix: pd.DataFrame) -> go.Figure:
    """100% stacked horizontal bars: power mix per region (sorted by share ≥50 kW)."""
    fig = go.Figure()
    for label in POWER_LABELS:
        d = mix[mix["power_class"] == label]
        fig.add_trace(go.Bar(
            y=d["nom_region"], x=d["share"], name=label, orientation="h", marker_color=POWER_COLORS[label],
            marker_line=dict(color=SURFACE, width=1), customdata=d["points"],
            hovertemplate=f"<b>%{{y}}</b><br>{label}: %{{x:.1f}}% (%{{customdata:,.0f}} points)<extra></extra>",
        ))
    fig.update_layout(barmode="stack", bargap=0.3)
    order = list(mix["nom_region"].cat.categories) if hasattr(mix["nom_region"], "cat") else None
    if order:  # first category is drawn at the bottom → highest fast share ends up on top
        fig.update_yaxes(categoryorder="array", categoryarray=order)
    fig.update_xaxes(title_text="Share of charge points (%)", range=[0, 100], ticksuffix="%")
    fig.update_yaxes(showgrid=False)
    return _style(fig, height=max(380, 30 * mix["nom_region"].nunique() + 120))


def small_multiples(series: pd.DataFrame, value: str, unit: str, national: pd.DataFrame | None = None,
                    wrap: int = 6) -> go.Figure:
    """One small panel per region, same y-scale, national curve repeated in grey for reference."""
    from plotly.subplots import make_subplots

    regions = list(series.sort_values(value, ascending=False).drop_duplicates("nom_region")["nom_region"])
    rows = int(np.ceil(len(regions) / wrap))
    fig = make_subplots(rows=rows, cols=wrap, shared_xaxes=True, shared_yaxes=True,
                        subplot_titles=[r if len(r) < 24 else r[:22] + "…" for r in regions],
                        horizontal_spacing=0.02, vertical_spacing=0.12)
    for i, reg in enumerate(regions):
        r, c = i // wrap + 1, i % wrap + 1
        if national is not None:
            fig.add_trace(go.Scatter(x=national["year"], y=national[value], mode="lines", name="France",
                                     line=dict(color=OTHER_COLOR, width=1.5), showlegend=(i == 0),
                                     hovertemplate="France %{x}: %{y:,.1f} " + unit + "<extra></extra>"), row=r, col=c)
        d = series[series["nom_region"] == reg]
        fig.add_trace(go.Scatter(x=d["year"], y=d[value], mode="lines", name="Region",
                                 line=dict(color=ACCENT, width=2), showlegend=(i == 0),
                                 hovertemplate=f"<b>{reg}</b> %{{x}}: %{{y:,.1f}} {unit}<extra></extra>"),
                      row=r, col=c)
    fig.update_annotations(font=dict(size=11, color=INK_2))
    fig = _style(fig, height=190 * rows + 110)
    fig.update_layout(margin=dict(t=80), legend=dict(y=0.995, yanchor="top", yref="container", x=0))
    fig.update_yaxes(matches="y")
    fig.update_xaxes(dtick=3, tickfont=dict(size=10))
    fig.update_yaxes(tickfont=dict(size=10))
    fig.update_yaxes(title_text=unit, row=1, col=1, title_font=dict(size=11))
    return fig


def operator_bar(ops: pd.DataFrame) -> go.Figure:
    d = ops.iloc[::-1]
    colors = [OTHER_COLOR if o == "All other operators" else ACCENT for o in d["operator"]]
    fig = go.Figure(go.Bar(
        x=d["share"], y=d["operator"], orientation="h", marker_color=colors,
        text=d["share"].map(lambda v: f"{v:.1f}%"), textposition="outside", cliponaxis=False,
        textfont=dict(color=INK_2, size=11), customdata=d["points"],
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% of points (%{customdata:,.0f})<extra></extra>",
    ))
    fig.update_xaxes(title_text="Share of charge points (%)", ticksuffix="%", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return _style(fig, height=420, legend=False)


def station_map(points: pd.DataFrame, center: tuple[float, float], zoom: float) -> go.Figure:
    fig = go.Figure()
    for label in POWER_LABELS:
        d = points[points["power_class"] == label]
        if d.empty:
            continue
        fig.add_trace(go.Scattermap(
            lat=d["lat"], lon=d["lon"], mode="markers", name=label,
            marker=dict(size=np.clip(np.sqrt(d["points"]) * 5, 6, 22), color=POWER_COLORS[label], opacity=0.85),
            customdata=np.stack([d["nom_station"].astype(str), d["operator"].astype(str), d["points"],
                                 d["max_kw"]], axis=-1),
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[2]} charge point(s), "
                           "max %{customdata[3]:.0f} kW<extra></extra>"),
        ))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=center[0], lon=center[1]), zoom=zoom))
    fig = _style(fig, height=520)
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
    return fig


# --------------------------------------------------------------------------------------
# 4. What-if projection
# --------------------------------------------------------------------------------------
def projection_chart(hist: pd.Series, proj: pd.DataFrame, target: float, target_label: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist.values, mode="lines+markers", name="Observed (estimated stock)",
                             line=dict(color=INK, width=2), marker=dict(size=8),
                             hovertemplate="%{x|%b %Y}: %{y:,.0f} points<extra></extra>"))
    for i, (name, d) in enumerate(proj.groupby("scenario", sort=False)):
        fig.add_trace(go.Scatter(x=d["date"], y=d["points"], mode="lines+markers", name=name,
                                 line=dict(color=CATEGORICAL[i], width=2, dash="dot" if i else "solid"),
                                 marker=dict(size=8),
                                 hovertemplate=f"<b>{name}</b><br>%{{x|%b %Y}}: %{{y:,.0f}} points<extra></extra>"))
    fig.add_hline(y=target, line=dict(color=MUTED, dash="dash", width=1.2))
    fig.add_annotation(x=0, xref="paper", y=target, text=target_label, showarrow=False, xanchor="left",
                       yanchor="bottom", font=dict(size=11, color=INK_2))
    fig.update_xaxes(title_text="Date", dtick="M24", tickformat="%Y", tickangle=0)
    fig.update_yaxes(title_text="Public charge points", tickformat=",", rangemode="tozero")
    return _style(fig, height=440)


# --------------------------------------------------------------------------------------
# 5. Data quality
# --------------------------------------------------------------------------------------
def missingness_bar(miss: pd.Series) -> go.Figure:
    d = miss.sort_values()
    colors = [HIGHLIGHT if v >= 20 else ACCENT for v in d.values]
    fig = go.Figure(go.Bar(
        x=d.values, y=d.index, orientation="h", marker_color=colors,
        text=[f"{v:.1f}%" for v in d.values], textposition="outside", cliponaxis=False,
        textfont=dict(color=INK_2, size=11),
        hovertemplate="<b>%{y}</b><br>%{x:.2f}% missing<extra></extra>",
    ))
    fig.add_vline(x=20, line=dict(color=MUTED, dash="dot"))
    fig.update_xaxes(title_text="Missing values in the raw file (%)", ticksuffix="%", showgrid=True,
                     gridcolor=GRID, range=[0, max(100, d.max() * 1.1)])
    fig.update_yaxes(showgrid=False, tickfont=dict(family="ui-monospace, monospace", size=11, color=INK_2))
    return _style(fig, height=max(360, 22 * len(d) + 80), legend=False)
