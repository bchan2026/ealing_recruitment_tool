import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

from utils import (
    load_and_merge_players,
    load_descriptors,
    get_metrics_for_position,
)

# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

# IMPORTANT: use the *display* names (after strip_prefix)
LOWER_IS_BETTER = [
    "Penalty Conceded",
    "Scrum Offence",
    "Total Turnovers",
    "Handling Error",
    "Yellow Card",
    "Red Card",
    "Percent Unforced",
]

# ---------------------------------------------------------
# PAGE + THEME
# ---------------------------------------------------------

st.set_page_config(page_title="Trailfinders Player Comparison Tool", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Garamond', serif;
    font-weight: 600;
    color: #FAFAFA;
:root {
    --primary: #006400;   /* Dark Green */
}

body { background-color: var(--bg-dark); }
.block-container { padding-top: 1.5rem; }
.neon-card {
    background: var(--bg-card);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.15);
:root {
    --primary: #006400;   /* Dark Green */
}

hr { border: 1px solid rgba(255,255,255,0.15); }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def strip_prefix(metric: str) -> str:
    return metric.split("__", 1)[1] if "__" in metric else metric

def is_percentage_metric(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    return ("percent" in n) or ("%" in n) or ("rate" in n)

def format_raw_value(metric: str, v):
    if pd.isna(v):
        return ""
    # Convert decimal percentages to whole numbers
    if is_percentage_metric(metric):
        try:
            v = float(v)
            if v < 1:
                v = v * 100
            return str(int(round(v)))
        except:
            return ""
    try:
        v = float(v)
        if v.is_integer():
            return str(int(v))
        return f"{v:.1f}"
    except:
        return str(v)

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

@st.cache_data
def get_data():
    players = load_and_merge_players("data")
    descriptors = load_descriptors("config/descriptors.yaml")
    return players, descriptors

players, descriptors = get_data()

universal_dict = descriptors.get("universal_metrics", {})
universal_metrics = [
    m for section, metrics in universal_dict.items() for m in metrics
]

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown("<h1 class='neon-title'>Trailfinders Player COMPARISON</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------
# FILTERS (SAFE + PERSISTENT)
# ---------------------------------------------------------

with st.container():
    st.markdown("<div class='neon-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    if "league_choice" not in st.session_state:
        st.session_state.league_choice = "All leagues"
    if "team_choice" not in st.session_state:
        st.session_state.team_choice = "All teams"
    if "pos_choice" not in st.session_state:
        st.session_state.pos_choice = "All positions"

    # LEAGUE
    leagues = sorted(players["league"].dropna().unique())
    if st.session_state.league_choice not in (["All leagues"] + leagues):
        st.session_state.league_choice = "All leagues"

    st.session_state.league_choice = c1.selectbox(
        "League",
        ["All leagues"] + leagues,
        index=(["All leagues"] + leagues).index(st.session_state.league_choice),
    )

    filtered = players.copy()
    if st.session_state.league_choice != "All leagues":
        filtered = filtered[filtered["league"] == st.session_state.league_choice]

    # TEAM
    teams = sorted(filtered["team"].dropna().unique())
    if st.session_state.team_choice not in (["All teams"] + teams):
        st.session_state.team_choice = "All teams"

    st.session_state.team_choice = c2.selectbox(
        "Team",
        ["All teams"] + teams,
        index=(["All teams"] + teams).index(st.session_state.team_choice),
    )

    if st.session_state.team_choice != "All teams":
        filtered = filtered[filtered["team"] == st.session_state.team_choice]

    # POSITION
    positions = sorted(filtered["position"].dropna().unique())
    if st.session_state.pos_choice not in (["All positions"] + positions):
        st.session_state.pos_choice = "All positions"

    st.session_state.pos_choice = c3.selectbox(
        "Position",
        ["All positions"] + positions,
        index=(["All positions"] + positions).index(st.session_state.pos_choice),
    )

    if st.session_state.pos_choice != "All positions":
        filtered = filtered[filtered["position"] == st.session_state.pos_choice]

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PLAYER SELECTION
# ---------------------------------------------------------

st.subheader("Select Players (2–6)")

if "compare_players" not in st.session_state:
    st.session_state.compare_players = ["None"] * 6

player_options = ["None"] + sorted(filtered["player"].dropna().unique())
cols = st.columns(6)
new_sel = []

for i in range(6):
    current = st.session_state.compare_players[i]
    opts = player_options if current in player_options else player_options + [current]
    new_val = cols[i].selectbox(
        f"Player {i+1}",
        opts,
        index=opts.index(current) if current in opts else 0,
        key=f"sel_{i}",
    )
    new_sel.append(new_val)

st.session_state.compare_players = new_sel
selected = [p for p in new_sel if p != "None"]

if len(selected) < 2:
    st.info("Select at least two players.")
    st.stop()

df_sel = players[players["player"].isin(selected)].set_index("player")

# ---------------------------------------------------------
# RADAR CHART (THEME‑ADAPTIVE + SAFE)
# ---------------------------------------------------------

st.subheader("Radar Chart")

# -------------------------------
# THEME-AWARE COLOR SYSTEM
# -------------------------------
def get_theme_colors():
    base = st.get_option("theme.base")  # "light" or "dark"

    if base == "dark":
        return {
            "bg": "#0E1117",
            "card": "#111318",
            "text": "#FFFFFF",
            "muted": "#A0A4B8",
            "grid": "#2A2D3A",
            "legend_bg": "#111318",
        }
    else:
        return {
            "bg": "#FFFFFF",
            "card": "#FFFFFF",
            "text": "#000000",
            "muted": "#444444",
            "grid": "#CCCCCC",
            "legend_bg": "#FFFFFF",
        }

ui = get_theme_colors()

# -------------------------------
# BUILD RADAR METRIC LIST
# -------------------------------
radar_metrics = list(universal_metrics)
for name in selected:
    pos = df_sel.loc[name].get("position")
    pos_metrics = get_metrics_for_position(descriptors, pos)
    for m in pos_metrics:
        if m not in radar_metrics:
            radar_metrics.append(m)

labels = [strip_prefix(m) for m in radar_metrics]

# -------------------------------
# CALCULATE PERCENTILES
# -------------------------------
fig = go.Figure()

# High‑contrast palette (works in both themes)
player_palette = [
    "#1E90FF", "#FFA500", "#32CD32",
    "#FF6347", "#8A2BE2", "#00CED1"
]

for idx, name in enumerate(selected):
    row = df_sel.loc[name]
    pos = row.get("position")
    league = row.get("league")
    group = players[(players["league"] == league) & (players["position"] == pos)]

    pct_list = []
    for metric in radar_metrics:
        if metric not in row or metric not in group:
            pct_list.append(0)
            continue

        series = group[metric].dropna()
        if series.empty:
            pct_list.append(0)
            continue

        val = row[metric]
        pct = (series < val).mean() * 100
        pct_list.append(pct)

    # SAFETY: ensure r-values are valid
    pct_list = [0 if pd.isna(v) else float(v) for v in pct_list]

    fig.add_trace(go.Scatterpolar(
        r=pct_list,
        theta=labels,
        fill="toself",
        name=name,
        line=dict(color=player_palette[idx % len(player_palette)], width=3),
        opacity=0.55,
    ))

# League average
fig.add_trace(go.Scatterpolar(
    r=[50] * len(labels),
    theta=labels,
    fill="toself",
    name="League Avg",
    line=dict(color=ui["muted"], width=2, dash="dot"),
    opacity=0.35,
))

# -------------------------------
# APPLY THEME-AWARE STYLING
# -------------------------------
fig.update_layout(
    polar=dict(
        bgcolor=ui["card"],
        radialaxis=dict(
            visible=True,
            range=[0, 100],
            gridcolor=ui["grid"],
            tickfont=dict(color=ui["muted"], family="Garamond"),
        ),
        angularaxis=dict(
            tickfont=dict(color=ui["muted"], family="Garamond"),
        ),
    ),
    showlegend=True,
    legend=dict(
        bgcolor=ui["legend_bg"],
        bordercolor=ui["grid"],
        borderwidth=1,
        font=dict(color=ui["text"], family="Garamond", size=12),
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="right",
        x=1,
    ),
    paper_bgcolor=ui["card"],
    plot_bgcolor=ui["card"],
    font=dict(color=ui["text"], family="Garamond"),
    height=700,
    margin=dict(l=40, r=40, t=60, b=40),
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# COMPARISON TABLE (Raw or Per‑80 + Highlighting)
# ---------------------------------------------------------

st.subheader("Comparison Table")

# Base data for comparison (raw from selection)
base_df = df_sel.copy()

# --- Per‑80 toggle UI ---
with st.container():
    st.markdown("<div class='neon-card'>", unsafe_allow_html=True)
    per80_toggle = st.toggle("Show metrics per 80 minutes played", value=False)
    st.markdown("</div>", unsafe_allow_html=True)

# Start with raw data
df_comp = base_df.copy()

# Detect minutes column
minutes_col = None
for c in df_comp.columns:
    if "minute" in c.lower():
        minutes_col = c
        break

# ---------------------------------------------------------
# APPLY PER‑80 TRANSFORMATION (Appearances + Minutes untouched)
# ---------------------------------------------------------
if per80_toggle and minutes_col is not None:

    mins = df_comp[minutes_col].replace(0, np.nan)

    for col in df_comp.columns:

        # IGNORE RULE — these must NEVER change
        if col in ["Appearances", "Minutes Played"]:
            continue

        # Skip raw minutes column, ID fields, etc.
        if col in [
            minutes_col,
            "Games Played",
            "player", "league", "team", "position"
        ]:
            continue

        # Skip percentage metrics
        if is_percentage_metric(col):
            continue

        # Apply per‑80 formula
        try:
            df_comp[col] = (df_comp[col] / mins) * 80
        except:
            pass

# ---------------------------------------------------------
# BUILD METRIC LIST
# ---------------------------------------------------------
all_metrics = list(universal_metrics)
for name in selected:
    pos = df_comp.loc[name].get("position")
    pos_metrics = get_metrics_for_position(descriptors, pos)
    for m in pos_metrics:
        if m not in all_metrics:
            all_metrics.append(m)

# ---------------------------------------------------------
# REMOVE APPEARANCES FROM METRIC LIST WHEN TOGGLE IS ON
# ---------------------------------------------------------
if per80_toggle:
    all_metrics = [m for m in all_metrics if strip_prefix(m) != "Appearances"]

# index uses *display* names
display_index = [strip_prefix(m) for m in all_metrics]
table = pd.DataFrame(index=display_index)

# ---------------------------------------------------------
# FILL TABLE WITH FORMATTED VALUES
# ---------------------------------------------------------
for name in selected:
    table[name] = [
        format_raw_value(strip_prefix(metric), df_comp.loc[name].get(metric, np.nan))
        for metric in all_metrics
    ]

# ---------------------------------------------------------
# HIGHLIGHTING LOGIC
# ---------------------------------------------------------
style_map = pd.DataFrame("", index=table.index, columns=table.columns)
green_count = {name: 0 for name in selected}

for display_name, raw_metric in zip(table.index, all_metrics):

    values = {}
    for name in selected:
        raw_val = df_comp.loc[name].get(raw_metric, np.nan)

        # Convert decimal percentages to whole numbers for ranking
        if pd.notna(raw_val) and is_percentage_metric(raw_metric) and raw_val < 1:
            raw_val = raw_val * 100

        if pd.notna(raw_val):
            try:
                values[name] = float(raw_val)
            except:
                continue

    if len(values) < 2:
        continue

    # LOWER IS BETTER?
    if display_name in LOWER_IS_BETTER:
        ranked = sorted(values.items(), key=lambda x: x[1])
    else:
        ranked = sorted(values.items(), key=lambda x: x[1], reverse=True)

    # Apply colours
    if len(ranked) >= 1:
        best = ranked[0][0]
        style_map.loc[display_name, best] = "color:#2ecc71; font-weight:700;"
        green_count[best] += 1

    if len(ranked) >= 2:
        second = ranked[1][0]
        style_map.loc[display_name, second] = "color:#e67e22; font-weight:700;"

    if len(ranked) >= 3:
        third = ranked[2][0]
        style_map.loc[display_name, third] = "color:#e74c3c; font-weight:700;"

# ---------------------------------------------------------
# ADD 🌟 TO BEST OVERALL
# ---------------------------------------------------------
max_greens = max(green_count.values()) if green_count else 0
for name in list(table.columns):
    base_name = name.replace("🌟 ", "")
    if green_count.get(base_name, 0) == max_greens and max_greens > 0:
        if not name.startswith("🌟 "):
            table.rename(columns={name: f"🌟 {base_name}"}, inplace=True)
            style_map.rename(columns={name: f"🌟 {base_name}"}, inplace=True)

# ---------------------------------------------------------
# RENDER TABLE
# ---------------------------------------------------------
st.dataframe(
    table.style.apply(lambda row: style_map.loc[row.name], axis=1),
    use_container_width=True,
)

