import streamlit as st
import pandas as pd
import math
import os
from utils import load_and_merge_players, load_descriptors

# ---------------------------------------------------------
# PAGE + THEME (Dark Mode + Garamond)
# ---------------------------------------------------------

st.set_page_config(
    page_title="Player Profiles – Oval Trailfinders Recruitment Tool",
    layout="wide",
)

st.markdown("""
<style>

html, body, [class*="css"]  {
    font-family: 'Garamond', serif;
    font-weight: 600;
    color: #FAFAFA;
}

:root {
    --primary: #006400;   /* Dark Green */
}


body {
    background-color: var(--bg-dark);
    color: var(--text-light);
}

section.main > div {
    background: var(--bg-dark);
}

.block-container {
    padding-top: 1.5rem;
}

.neon-card {
    background: var(--bg-card);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.15);
}

h1.neon-title {
    text-align: center;
    letter-spacing: 1px;
    color: var(--primary);
}

[data-testid="stMetricValue"] {
    color: var(--primary) !important;
    font-weight: 700;
}

div[data-testid="stMetricLabel"] {
    color: var(--text-light);
}

hr {
    border: 1px solid rgba(255,255,255,0.15);
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# FORMATTING HELPERS
# ---------------------------------------------------------

def format_number(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        v = float(value)
        if v.is_integer():
            return str(int(v))
        return f"{v:.1f}"
    except:
        return str(value)

def format_percentage(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        v = float(value)
        if v > 1:
            v = v / 100.0
        pct = v * 100.0
        if pct.is_integer():
            return f"{int(pct)}%"
        return f"{pct:.1f}%"
    except:
        return ""

def is_percentage_metric(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    return "%" in n or "percent" in n or "rate" in n

def strip_prefix(metric_name: str) -> str:
    if "__" in metric_name:
        return metric_name.split("__", 1)[1]
    return metric_name

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

@st.cache_data
def get_data():
    players = load_and_merge_players("data")
    descriptors = load_descriptors("config/descriptors.yaml")
    return players, descriptors

players, descriptors = get_data()

if players.empty:
    st.error("No player data loaded. Add Excel files to /data.")
    st.stop()

universal_metrics = descriptors.get("universal_metrics", {})
position_groups = descriptors.get("position_groups", {})

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

col_logo_left, col_title, col_logo_right = st.columns([1, 5, 1])

logo_left_path = "images/Ealing_Trailfinders_logo.jpg"
logo_right_path = "images/Stats_Perform_logo.jpg"

with col_logo_left:
    if os.path.exists(logo_left_path):
        st.image(logo_left_path, width=120)

with col_title:
    st.markdown(
        "<h1 class='neon-title' style='font-size:48px; text-align:center;'>TRAILFINDERS OVAL RECRUITMENT TOOL</h1>",
        unsafe_allow_html=True,
    )

with col_logo_right:
    if os.path.exists(logo_right_path):
        st.image(logo_right_path, width=120)

st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------
# FILTERS — NON-RESETTING
# ---------------------------------------------------------

with st.container():
    st.markdown("<div class='neon-card'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    leagues = sorted(players["league"].dropna().unique())
    league_choice = c1.selectbox("League", ["All leagues"] + leagues)

    filtered = players.copy()
    if league_choice != "All leagues":
        filtered = filtered[filtered["league"] == league_choice]

    teams = sorted(filtered["team"].dropna().unique())
    team_choice = c2.selectbox("Team", ["All teams"] + teams)

    if team_choice != "All teams":
        filtered = filtered[filtered["team"] == team_choice]

    positions = sorted(filtered["position"].dropna().unique())
    pos_choice = c3.selectbox("Position", ["All positions"] + positions)

    if pos_choice != "All positions":
        filtered = filtered[filtered["position"] == pos_choice]

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PLAYER SELECTION — PERSISTENT
# ---------------------------------------------------------

st.subheader("🎯 Select Players")

if "selected_players" not in st.session_state:
    st.session_state.selected_players = ["None"] * 4

player_options = ["None"] + sorted(filtered["player"].dropna().unique())

cols = st.columns(4)
new_selections = []

for i in range(4):
    current_value = st.session_state.selected_players[i]
    if current_value not in player_options:
        options = player_options + [current_value]
    else:
        options = player_options

    new_value = cols[i].selectbox(
        f"Player {i+1}",
        options,
        index=options.index(current_value) if current_value in options else 0,
        key=f"profile_select_{i}"
    )
    new_selections.append(new_value)

st.session_state.selected_players = new_selections
selected_players = [p for p in new_selections if p != "None"]

if not selected_players:
    st.info("Select at least one player.")
    st.stop()

df_selected = players[players["player"].isin(selected_players)].set_index("player")

st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PROFILE SECTIONS (TABS PER PLAYER)
# ---------------------------------------------------------

PROFILE_SECTIONS = [
    "General",
    "Attack",
    "Defence",
    "Discipline",
    "Set Piece",
    "Breakdown",
    "Kicking",
    "Error Rate",
]

st.subheader("📇 Player Profiles")

for name in selected_players:
    row = df_selected.loc[name]
    position = row.get("position", "")

    with st.expander(f"{name} – {position}", expanded=True):

        st.markdown("<div class='neon-card'>", unsafe_allow_html=True)

        st.write(f"**Team:** {row.get('team', '')}")
        st.write(f"**League:** {row.get('league', '')}")
        st.write(f"**Position:** {position}")

        # Find position group key
        pos_key = None
        for key, group in position_groups.items():
            if position and position.lower() in [p.lower() for p in group.get("positions", [])]:
                pos_key = key
                break

        tabs = st.tabs(PROFILE_SECTIONS)

        for tab, section in zip(tabs, PROFILE_SECTIONS):
            with tab:
                st.markdown(f"### {section}")

                metrics = []

                # Universal metrics for this section
                if section in universal_metrics:
                    metrics.extend(universal_metrics[section])

                # Position-specific metrics for this section
                if pos_key and section in position_groups[pos_key].get("metrics", {}):
                    metrics.extend(position_groups[pos_key]["metrics"][section])

                # Remove duplicates
                metrics = list(dict.fromkeys(metrics))

                cols_tab = st.columns(4)
                idx = 0

                for metric in metrics:
                    if metric in row.index and pd.notna(row.get(metric)):
                        val = row.get(metric)

                        if is_percentage_metric(metric):
                            value = format_percentage(val)
                        else:
                            value = format_number(val)

                        cols_tab[idx % 4].metric(strip_prefix(metric), value)
                        idx += 1

        st.markdown("</div>", unsafe_allow_html=True)
