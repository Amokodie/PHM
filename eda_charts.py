"""Plotly/Matplotlib helpers for C-MAPSS exploratory analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def sensor_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("sensor_")]


def non_constant_sensors(df: pd.DataFrame, eps: float = 1e-9) -> list[str]:
    cols = sensor_columns(df)
    out = []
    for c in cols:
        if float(df[c].std()) > eps:
            out.append(c)
    return out


def fig_correlation_heatmap(df: pd.DataFrame, title: str) -> go.Figure:
    cols = non_constant_sensors(df)
    if len(cols) < 2:
        fig = go.Figure()
        fig.update_layout(title=title, annotations=[dict(text="Not enough varying sensors", showarrow=False)])
        return fig
    sub = df[cols].astype(float)
    corr = sub.corr()
    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=[c.replace("sensor_", "s") for c in cols],
            y=[c.replace("sensor_", "s") for c in cols],
            colorscale="RdBu",
            zmid=0,
            colorbar=dict(title="r"),
        )
    )
    fig.update_layout(
        title=title,
        height=560,
        margin=dict(l=60, r=20, t=50, b=60),
        xaxis=dict(tickangle=-45),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def fig_max_cycle_per_unit(df: pd.DataFrame, title: str) -> go.Figure:
    g = df.groupby("unit")["cycle"].max().sort_values(ascending=True)
    fig = go.Figure(
        data=go.Bar(x=g.values, y=[str(u) for u in g.index], orientation="h", marker_color="#3b6ea5")
    )
    fig.update_layout(
        title=title,
        height=min(800, max(400, 12 * len(g))),
        xaxis_title="Last observed cycle",
        yaxis_title="Engine unit",
        margin=dict(l=80, r=20, t=50, b=40),
    )
    return fig


def fig_settings_2d(df: pd.DataFrame, title: str) -> go.Figure:
    sample = df if len(df) <= 8000 else df.sample(8000, random_state=0)
    fig = go.Figure(
        data=go.Scatter(
            x=sample["setting_1"],
            y=sample["setting_2"],
            mode="markers",
            marker=dict(size=4, color=sample["cycle"], colorscale="Viridis", opacity=0.5),
            text=sample["unit"],
            hovertemplate="setting1=%{x:.4f}<br>setting2=%{y:.4f}<br>cycle=%{marker.color:.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Operational setting 1",
        yaxis_title="Operational setting 2",
        height=420,
        margin=dict(l=50, r=20, t=50, b=40),
    )
    return fig


def fig_sensor_std_bar(df: pd.DataFrame, title: str) -> go.Figure:
    cols = sensor_columns(df)
    stds = [float(df[c].std()) for c in cols]
    fig = go.Figure(
        data=go.Bar(x=[c.replace("sensor_", "s") for c in cols], y=stds, marker_color="#c44e52")
    )
    fig.update_layout(
        title=title,
        xaxis_title="Sensor",
        yaxis_title="Std dev (full table)",
        height=400,
        margin=dict(l=50, r=20, t=50, b=80),
        xaxis=dict(tickangle=-45),
    )
    return fig


def fig_run_length_histogram(df: pd.DataFrame, title: str) -> go.Figure:
    mx = df.groupby("unit")["cycle"].max()
    fig = go.Figure(data=go.Histogram(x=mx.values, nbinsx=25, marker_color="#457b9d"))
    fig.update_layout(
        title=title,
        xaxis_title="Last observed cycle (engine life in dataset)",
        yaxis_title="Number of engines",
        height=380,
        margin=dict(l=50, r=20, t=50, b=40),
    )
    return fig


def fig_rul_histogram(rul: np.ndarray, title: str) -> go.Figure:
    fig = go.Figure(data=go.Histogram(x=rul, nbinsx=30, marker_color="#6a994e"))
    fig.update_layout(
        title=title,
        xaxis_title="True RUL (cycles)",
        yaxis_title="Count (engines)",
        height=400,
        margin=dict(l=50, r=20, t=50, b=40),
    )
    return fig


def fig_normalized_ensemble(
    df: pd.DataFrame,
    sensor_cols: list[str],
    title: str,
) -> go.Figure:
    """Mean sensor vs normalized engine life (cycle / max_cycle per unit)."""
    if not sensor_cols:
        fig = go.Figure()
        fig.update_layout(title=title, annotations=[dict(text="No sensors", showarrow=False)])
        return fig
    rows = []
    for u, g in df.groupby("unit"):
        m = float(g["cycle"].max())
        if m < 1:
            continue
        gg = g.copy()
        gg["life"] = gg["cycle"] / m
        rows.append(gg)
    if not rows:
        fig = go.Figure()
        fig.update_layout(title=title, annotations=[dict(text="No data", showarrow=False)])
        return fig
    long = pd.concat(rows, ignore_index=True)
    # Bin life for stable mean
    long["life_bin"] = (long["life"] * 99).round().astype(int).clip(0, 99)
    use_cols = sensor_cols[:3]
    nrows = len(use_cols)
    fig = make_subplots(
        rows=nrows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=use_cols,
    )
    for i, s in enumerate(use_cols):
        agg = long.groupby("life_bin")[s].mean()
        x = (agg.index.astype(float) + 0.5) / 100.0
        r = i + 1
        fig.add_trace(
            go.Scatter(x=x, y=agg.values, mode="lines", name=s, showlegend=False),
            row=r,
            col=1,
        )
        fig.update_yaxes(title_text=s.replace("sensor_", "s"), row=r, col=1)
    fig.update_layout(height=200 * nrows + 60, title=title, margin=dict(l=50, r=20, t=60, b=40))
    fig.update_xaxes(title_text="Normalized life (0=start, 1=last cycle)", row=nrows, col=1)
    return fig


def fig_pair_sensors_last_snapshot(df: pd.DataFrame, s1: str, s2: str, title: str) -> go.Figure:
    """Last-cycle snapshot per engine: useful for spread / fault mixing."""
    last = df.sort_values(["unit", "cycle"]).groupby("unit", as_index=False).tail(1)
    fig = go.Figure(
        data=go.Scatter(
            x=last[s1],
            y=last[s2],
            mode="markers",
            marker=dict(size=8, color=last["unit"], colorscale="Turbo", opacity=0.75),
            text=last["unit"],
            hovertemplate=f"{s1}=%{{x:.4f}}<br>{s2}=%{{y:.4f}}<br>unit=%{{text}}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=s1,
        yaxis_title=s2,
        height=440,
        margin=dict(l=50, r=20, t=50, b=40),
    )
    return fig
