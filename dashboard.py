from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Sodexo Nikos Traffic Dashboard", layout="wide")
st.title("Sodexo Nikos — Daily Traffic Dashboard")

# -----------------------------
# Paths
# -----------------------------
ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "combined_output.xlsx"

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Settings")
TOP_PEAK_PCT = st.sidebar.slider("Peak threshold (Top %)", 1, 30, 10) / 100.0
BOTTOM_SLOW_PCT = st.sidebar.slider("Slow threshold (Bottom %)", 1, 50, 20) / 100.0

# -----------------------------
# Helpers
# -----------------------------
def parse_times(time_series: pd.Series) -> pd.Series:
    """
    Parse times like '11:45:00AM' into datetime.
    Returns a datetime series (NaT for non-time rows like 'Total').
    """
    s = time_series.astype(str).str.strip()
    t = pd.to_datetime(s, format="%I:%M:%S%p", errors="coerce")
    if t.isna().all():
        t = pd.to_datetime(s, format="%I:%M%p", errors="coerce")
    return t

def load_day_sheet(xls: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    """
    Reads one day sheet and returns clean df with columns:
    Day, Time (HH:MM), Total (numeric), where only real time rows are kept.
    This removes the 'Total' summary row so daily totals aren't double-counted.
    """
    # Most of your sheets: data table starts around row 16
    df = pd.read_excel(xls, sheet_name=sheet_name, skiprows=15)

    # Fallback: scan for header row containing 'Total' if needed
    if "Total" not in df.columns:
        raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        header_row = None
        for i in range(min(len(raw), 60)):
            row = raw.iloc[i].astype(str).tolist()
            if any(cell.strip().lower() == "total" for cell in row):
                header_row = i
                break
        if header_row is None:
            return pd.DataFrame(columns=["Day", "Time", "Total"])
        df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)

    time_col = "Unnamed: 0" if "Unnamed: 0" in df.columns else df.columns[0]
    clean = df[[time_col, "Total"]].copy()
    clean.columns = ["Time_raw", "Total"]

    # Make Total numeric
    clean["Total"] = pd.to_numeric(clean["Total"], errors="coerce")

    # ✅ KEY FIX: keep ONLY rows where Time parses successfully (removes 'Total' row)
    t = parse_times(clean["Time_raw"])
    clean = clean[t.notna()].copy()

    # Format time as HH:MM
    clean["Time"] = t[t.notna()].dt.strftime("%H:%M")

    # Drop NaN totals
    clean = clean.dropna(subset=["Total"])

    clean["Day"] = sheet_name
    return clean[["Day", "Time", "Total"]]

@st.cache_data
def load_all_days(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    xls = pd.ExcelFile(path)
    all_rows = []
    daily_rows = []

    for day in xls.sheet_names:
        day_df = load_day_sheet(xls, day)
        if day_df.empty:
            continue

        all_rows.append(day_df)

        avg = day_df["Total"].mean()
        std = day_df["Total"].std(ddof=1)
        cv = (std / avg) if avg else None

        daily_rows.append({
            "Day": day,
            "Slots": int(len(day_df)),
            "Total_Traffic": float(day_df["Total"].sum()),   # ✅ now correct
            "Avg_per_Slot": float(avg),
            "Max_Slot": float(day_df["Total"].max()),        # ✅ now correct
            "Min_Slot": float(day_df["Total"].min()),
            "Std_Dev": float(std) if pd.notna(std) else None,
            "CV_(Std/Avg)": float(cv) if cv is not None and pd.notna(cv) else None,
        })

    all_df = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    daily_df = pd.DataFrame(daily_rows).sort_values("Day") if daily_rows else pd.DataFrame()
    return all_df, daily_df

# -----------------------------
# Load data
# -----------------------------
if not INPUT_FILE.exists():
    st.error(f"Could not find {INPUT_FILE}. Put combined_output.xlsx in the project root.")
    st.stop()

all_df, daily_df = load_all_days(str(INPUT_FILE))

if all_df.empty or daily_df.empty:
    st.error("No usable data found (could not locate the time/Total table in sheets).")
    st.stop()

# -----------------------------
# Global KPIs
# -----------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Days", int(daily_df.shape[0]))
col2.metric("Total Traffic (all days)", f"{all_df['Total'].sum():,.0f}")
col3.metric("Avg per 15-min slot (all days)", f"{all_df['Total'].mean():.2f}")
col4.metric("Max single slot (all days)", f"{all_df['Total'].max():,.0f}")

# -----------------------------
# Daily summary + chart
# -----------------------------
left, right = st.columns([1.2, 1])

with left:
    st.subheader("Daily Summary")
    st.dataframe(daily_df, width="stretch")

with right:
    st.subheader("Total Traffic by Day")
    fig = px.bar(daily_df, x="Day", y="Total_Traffic")
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Day drill-down
# -----------------------------
st.divider()
day_choice = st.selectbox("Select a day to drill down", daily_df["Day"].tolist())
day_data = all_df[all_df["Day"] == day_choice].copy()

peak_thresh = day_data["Total"].quantile(1 - TOP_PEAK_PCT)
slow_thresh = day_data["Total"].quantile(BOTTOM_SLOW_PCT)

peaks = day_data[day_data["Total"] >= peak_thresh].sort_values("Total", ascending=False)
slows = day_data[day_data["Total"] <= slow_thresh].sort_values("Total", ascending=True)

k1, k2, k3 = st.columns(3)
k1.metric("Peak threshold (Top %)", f"{(1 - TOP_PEAK_PCT) * 100:.0f}th pct → {peak_thresh:.2f}")
k2.metric("Slow threshold (Bottom %)", f"{BOTTOM_SLOW_PCT * 100:.0f}th pct → {slow_thresh:.2f}")
k3.metric("Day total traffic", f"{day_data['Total'].sum():,.0f}")

st.subheader(f"Traffic Trend — {day_choice}")
fig_line = px.line(day_data.sort_values("Time"), x="Time", y="Total")
st.plotly_chart(fig_line, use_container_width=True)

# -----------------------------
# Peak / Slow tables
# -----------------------------
c1, c2 = st.columns(2)
with c1:
    st.subheader(f"Peak Slots (Top {int(TOP_PEAK_PCT * 100)}%)")
    st.dataframe(peaks[["Time", "Total"]], width="stretch", height=320)

with c2:
    st.subheader(f"Slow Slots (Bottom {int(BOTTOM_SLOW_PCT * 100)}%)")
    st.dataframe(slows[["Time", "Total"]], width="stretch", height=320)

# -----------------------------
# Cross-day insights
# -----------------------------
st.divider()
st.subheader("Across All Days")

avg_by_time = (
    all_df.groupby("Time", as_index=False)["Total"]
    .mean()
    .rename(columns={"Total": "Avg_Traffic"})
    .sort_values("Time")
)

c3, c4 = st.columns([1, 1.2])
with c3:
    st.write("Average traffic by time-of-day (all days)")
    fig_avg = px.line(avg_by_time, x="Time", y="Avg_Traffic")
    st.plotly_chart(fig_avg, use_container_width=True)

with c4:
    st.write("Heatmap (Day × Time)")
    heatmap = all_df.pivot_table(index="Day", columns="Time", values="Total", aggfunc="mean").sort_index()
    fig_hm = px.imshow(heatmap, aspect="auto")
    st.plotly_chart(fig_hm, use_container_width=True)

# -----------------------------
# Staffing labels (simple)
# -----------------------------
st.divider()
st.subheader("Overview (Selected Day)")
labeled = day_data.copy()
labeled["Label"] = "Normal"
labeled.loc[labeled["Total"] >= peak_thresh, "Label"] = "Peak"
labeled.loc[labeled["Total"] <= slow_thresh, "Label"] = "Slow"

st.dataframe(labeled.sort_values("Time")[["Time", "Total", "Label"]], width="stretch")
