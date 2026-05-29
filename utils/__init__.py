import os
import pandas as pd
import yaml

# Sheets to ignore
IGNORE_SHEETS = {
    "All Players 80 min Average",
    "Players by Match",
}

# Sheets we want to read
VALID_SHEETS = [
    "All Players Season",
    "Carries",
    "Kicks",
    "Tackles",
    "Ruck Entries",
    "Passes",
    "Lineout Throws",
    "Lineout Catch",
    "Turnover Conceded",
    "Turnover Won",
    "Restarts",
    "Pens Conceded",
]

# Columns that identify a player (must be kept from every sheet)
ID_COLS = ["Player Name", "Team Name", "Normal Position"]

def load_and_merge_players(folder_path="data"):
    all_players = None

    for file in os.listdir(folder_path):
        if not file.endswith(".xlsx"):
            continue

        path = os.path.join(folder_path, file)
        xls = pd.ExcelFile(path)

        # Extract league from filename
        filename = os.path.basename(file)
        parts = filename.split("_")
        league = parts[2]
        if len(parts) > 3 and not parts[3].isdigit():
            league = f"{parts[2]} {parts[3]}"
        league = league.replace("_", " ").replace("-", " ")

        # Start a dictionary of dataframes for this file
        sheet_frames = []

        for sheet in xls.sheet_names:
            if sheet in IGNORE_SHEETS:
                continue
            if sheet not in VALID_SHEETS:
                continue

            df = pd.read_excel(path, sheet_name=sheet, header=3)
            df = df.dropna(axis=1, how="all")

            # Clean column names
            df.columns = (
                df.columns.astype(str)
                .str.strip()
                .str.replace("\n", " ")
            )

            # Ensure ID columns exist
            if not all(col in df.columns for col in ID_COLS):
                continue

            # Add league
            df["league"] = league

            # Prefix metric columns with sheet name to avoid collisions
            metric_cols = [c for c in df.columns if c not in ID_COLS + ["league"]]
            df = df[ID_COLS + ["league"] + metric_cols]

            df = df.rename(columns={c: f"{sheet}__{c}" for c in metric_cols})

            sheet_frames.append(df)

        if not sheet_frames:
            continue

        # Merge all sheets horizontally for this file
        merged_file = sheet_frames[0]
        for df in sheet_frames[1:]:
            merged_file = pd.merge(
                merged_file,
                df,
                on=ID_COLS + ["league"],
                how="outer"
            )

        # Append to global dataset
        if all_players is None:
            all_players = merged_file
        else:
            all_players = pd.concat([all_players, merged_file], ignore_index=True)

    if all_players is None:
        return pd.DataFrame()

    # Final collapse: one row per player
    all_players = all_players.groupby(ID_COLS + ["league"], as_index=False).first()

    # Rename ID columns to match your Streamlit code
    all_players = all_players.rename(columns={
        "Player Name": "player",
        "Team Name": "team",
        "Normal Position": "position",
    })

    return all_players


def load_descriptors(path="config/descriptors.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_metrics_for_position(descriptors: dict, position: str):
    """
    Returns a FLAT list of metrics:
    - all universal metrics (flattened)
    - plus position‑specific metrics for the given position (flattened)
    """

    if not position:
        return []

    position = position.lower().strip()

    # 1) Flatten universal metrics
    universal_dict = descriptors.get("universal_metrics", {})
    universal_flat = [
        metric
        for section, metrics in universal_dict.items()
        for metric in metrics
    ]

    # 2) Find the matching position group
    pos_groups = descriptors.get("position_groups", {})
    pos_flat = []

    for group_name, group_data in pos_groups.items():
        positions = [p.lower() for p in group_data.get("positions", [])]

        if position in positions:
            metrics_dict = group_data.get("metrics", {})
            pos_flat = [
                metric
                for section, metrics in metrics_dict.items()
                for metric in metrics
            ]
            break

    # 3) Combine + dedupe
    combined = universal_flat + pos_flat
    combined = list(dict.fromkeys(combined))

    return combined
