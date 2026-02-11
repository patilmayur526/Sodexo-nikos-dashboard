from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="Sales Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Sales Dashboard — Daily & Weekly Analysis")

# -----------------------------
# File path
# -----------------------------
ROOT = Path(__file__).resolve().parent
DEFAULT_FILE = ROOT / "combined_sales_data.xlsx"

st.sidebar.header("⚙️ Configuration")
file_path_str = st.sidebar.text_input("Excel file path", str(DEFAULT_FILE))

TOP_PEAK_PCT = st.sidebar.slider("Peak slots (Top %)", 1, 30, 10) / 100.0
BOTTOM_SLOW_PCT = st.sidebar.slider("Slow slots (Bottom %)", 1, 50, 20) / 100.0

# -----------------------------
# Helper functions
# -----------------------------
def to_num(x):
    return pd.to_numeric(x, errors="coerce")


def get_sales_week(date_obj):
    """
    Calculate sales week number where week runs Thursday-Wednesday.
    Returns (year, week_number, week_start_date)
    """
    # Find the Thursday of this week (or before)
    days_since_thursday = (date_obj.weekday() - 3) % 7
    week_start = date_obj - timedelta(days=days_since_thursday)
    
    # Week number is based on first Thursday of the year
    year = week_start.year
    jan_1 = datetime(year, 1, 1)
    days_since_jan_thursday = (jan_1.weekday() - 3) % 7
    first_thursday = jan_1 - timedelta(days=days_since_jan_thursday)
    
    if week_start < first_thursday:
        # Part of previous year's last week
        year -= 1
        week_num = 52
    else:
        week_num = ((week_start - first_thursday).days // 7) + 1
    
    return year, week_num, week_start


def extract_date_info(raw_df: pd.DataFrame) -> dict:
    """Extract date and day from the top of the sheet"""
    info = {}
    if raw_df.shape[1] < 2:
        return info
    
    col0 = raw_df.columns[0]
    col1 = raw_df.columns[1]
    
    for _, row in raw_df.iterrows():
        k = str(row[col0]).strip() if pd.notna(row[col0]) else ""
        if not k:
            continue
        
        k_lower = k.lower()
        if k_lower == "date":
            info["date"] = str(row[col1]).strip()
        elif k_lower == "day":
            info["day_name"] = str(row[col1]).strip()
        
        # Stop when we hit financial section
        if "run financial" in k_lower:
            break
    
    return info


def extract_financial_metrics(raw_df: pd.DataFrame) -> dict:
    """Extract financial metrics from the control section"""
    metrics = {}
    if raw_df.shape[1] < 2:
        return metrics

    col0 = raw_df.columns[0]
    col1 = raw_df.columns[1]

    in_control_section = False
    for _, row in raw_df.iterrows():
        k = str(row[col0]).strip() if pd.notna(row[col0]) else ""
        if not k:
            continue

        k_lower = k.lower()
        
        if "run financial control report" in k_lower:
            in_control_section = True
            continue
        
        if "day part summary" in k_lower:
            break
        
        if in_control_section and k_lower not in ("name", ""):
            v = row[col1]
            v_num = to_num(v)
            if pd.notna(v_num):
                metrics[k] = float(v_num)

    return metrics


def find_table_start_row(raw_df: pd.DataFrame) -> int | None:
    """Find the row where the time slot table begins"""
    first_col = raw_df.columns[0]
    for i, val in enumerate(raw_df[first_col].astype(str).fillna("").tolist()):
        if val.strip().lower() in ("time_slots", "time slots"):
            return i
    return None


def extract_timeslot_table(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Extract time slot sales data"""
    start = find_table_start_row(raw_df)
    if start is None:
        return pd.DataFrame(columns=["Time_slot", "Sales", "Transactions"])

    header = raw_df.iloc[start].tolist()
    df = raw_df.iloc[start + 1:].copy()
    df.columns = header

    cols = {str(c).strip().lower(): c for c in df.columns}

    time_col = None
    sales_col = None
    txn_col = None

    for k, original in cols.items():
        if k in ("time_slots", "time slots"):
            time_col = original
        elif "sales net vat" in k or "after discount" in k or k == "sales":
            sales_col = original
        elif "transaction" in k or "checks" in k or "count" in k:
            txn_col = original

    if time_col is None or sales_col is None:
        return pd.DataFrame(columns=["Time_slot", "Sales", "Transactions"])

    out = pd.DataFrame()
    out["Time_slot"] = df[time_col].astype(str).str.strip()
    out["Sales"] = to_num(df[sales_col]).fillna(0)

    if txn_col is not None:
        out["Transactions"] = to_num(df[txn_col]).fillna(0)
    else:
        out["Transactions"] = 0

    out = out[out["Time_slot"].ne("") & out["Time_slot"].ne("nan")].copy()
    out = out[~out["Time_slot"].str.lower().isin(["total"])].copy()
    out["Avg_Ticket"] = np.where(out["Transactions"] > 0, out["Sales"] / out["Transactions"], 0.0)

    return out.reset_index(drop=True)


# -----------------------------
# Load all sheets
# -----------------------------
@st.cache_data
def load_workbook(file_path: str):
    xls = pd.ExcelFile(file_path)
    days_data = []
    days_slots = []

    for sheet in xls.sheet_names:
        raw = pd.read_excel(xls, sheet_name=sheet, header=0)
        
        # Extract date info
        date_info = extract_date_info(raw)
        
        # Extract financial metrics
        fin = extract_financial_metrics(raw)
        
        # Combine
        fin_row = {
            "Sheet": sheet,
            "Date": date_info.get("date", sheet),
            "Day_Name": date_info.get("day_name", ""),
            **fin
        }
        days_data.append(fin_row)

        # Extract time slots
        slots = extract_timeslot_table(raw)
        if not slots.empty:
            slots["Sheet"] = sheet
            slots["Date"] = date_info.get("date", sheet)
            slots["Day_Name"] = date_info.get("day_name", "")
            days_slots.append(slots)

    fin_df = pd.DataFrame(days_data)
    
    # Parse dates and add week information
    fin_df["Date_Parsed"] = pd.to_datetime(fin_df["Date"], errors="coerce")
    fin_df = fin_df.dropna(subset=["Date_Parsed"])
    fin_df = fin_df.sort_values("Date_Parsed")
    
    # Add week information
    week_info = fin_df["Date_Parsed"].apply(lambda x: get_sales_week(x))
    fin_df["Week_Year"] = week_info.apply(lambda x: x[0])
    fin_df["Week_Number"] = week_info.apply(lambda x: x[1])
    fin_df["Week_Start"] = week_info.apply(lambda x: x[2])
    fin_df["Week_Label"] = fin_df.apply(
        lambda row: f"W{row['Week_Number']:02d} ({row['Week_Start'].strftime('%b %d')})", 
        axis=1
    )
    
    slots_df = pd.concat(days_slots, ignore_index=True) if days_slots else pd.DataFrame(
        columns=["Sheet", "Date", "Day_Name", "Time_slot", "Sales", "Transactions", "Avg_Ticket"]
    )
    
    if not slots_df.empty:
        slots_df["Date_Parsed"] = pd.to_datetime(slots_df["Date"], errors="coerce")
        slots_df = slots_df.dropna(subset=["Date_Parsed"])
        
        # Add week info to slots
        week_info_slots = slots_df["Date_Parsed"].apply(lambda x: get_sales_week(x))
        slots_df["Week_Year"] = week_info_slots.apply(lambda x: x[0])
        slots_df["Week_Number"] = week_info_slots.apply(lambda x: x[1])
        slots_df["Week_Start"] = week_info_slots.apply(lambda x: x[2])
        slots_df["Week_Label"] = slots_df.apply(
            lambda row: f"W{row['Week_Number']:02d} ({row['Week_Start'].strftime('%b %d')})", 
            axis=1
        )
        
        # Daily aggregates from slot table
        daily_from_slots = (
            slots_df.groupby("Date", as_index=False)
            .agg(
                Slot_Sales_Total=("Sales", "sum"),
                Slot_Transactions_Total=("Transactions", "sum"),
            )
        )
        daily_from_slots["Avg_Ticket_Day"] = daily_from_slots["Slot_Sales_Total"] / daily_from_slots["Slot_Transactions_Total"].replace(0, np.nan)
        
        fin_df = fin_df.merge(daily_from_slots, on="Date", how="left")

    return fin_df, slots_df


# -----------------------------
# Validate file
# -----------------------------
file_path = Path(file_path_str)
if not file_path.exists():
    st.error("❌ File not found. Please provide the correct Excel path.")
    st.stop()

fin_df, slots_df = load_workbook(str(file_path))

if fin_df.empty:
    st.error("❌ No data extracted. Check the file format.")
    st.stop()

# -----------------------------
# Global KPIs
# -----------------------------
st.subheader("📈 Overall Performance")

# Helper function to get metric values
def metric_value(df, col):
    return df[col].sum() if col in df.columns else None

# Financial metrics
gross_before = metric_value(fin_df, "Gross Sales Before Discounts")
total_discounts = metric_value(fin_df, "Total Discounts")
gross_after = metric_value(fin_df, "Gross Sales After Discounts")
net_vat = metric_value(fin_df, "Sales Net VAT")

# Transaction metrics
total_sales = slots_df["Sales"].sum() if not slots_df.empty else 0
total_txns = slots_df["Transactions"].sum() if not slots_df.empty else 0
avg_ticket = total_sales / max(total_txns, 1)
num_days = fin_df["Date"].nunique()
avg_daily_sales = total_sales / max(num_days, 1)

# Display main KPIs
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📅 Days", f"{num_days}")
col2.metric("💰 Total Sales", f"${total_sales:,.2f}")
col3.metric("🛒 Transactions", f"{total_txns:,.0f}")
col4.metric("🎫 Avg Ticket", f"${avg_ticket:.2f}")
col5.metric("📊 Avg Daily Sales", f"${avg_daily_sales:,.2f}")

# Financial Control Metrics (from your original dashboard)
st.caption("**Financial Control Totals**")
fc1, fc2, fc3, fc4 = st.columns(4)
fc1.metric("Gross Sales (Before Disc.)", f"${gross_before:,.2f}" if gross_before else "—")
fc2.metric("Total Discounts", f"${total_discounts:,.2f}" if total_discounts else "—", 
          delta=f"-{(total_discounts/gross_before*100):.1f}%" if gross_before and total_discounts else None,
          delta_color="inverse")
fc3.metric("Gross Sales (After Disc.)", f"${gross_after:,.2f}" if gross_after else "—")
fc4.metric("Sales Net VAT", f"${net_vat:,.2f}" if net_vat else "—")

# Discount rate indicator
if gross_before and total_discounts:
    discount_rate = (total_discounts / gross_before) * 100
    st.info(f"💡 Overall discount rate: **{discount_rate:.2f}%** of gross sales")

# -----------------------------
# Weekly Analysis
# -----------------------------
st.divider()
st.subheader("📅 Weekly Performance Analysis (Thursday - Wednesday)")

if not slots_df.empty:
    # Calculate weekly stats with financial metrics
    weekly_stats_slots = (
        slots_df.groupby("Week_Label", as_index=False)
        .agg(
            Week_Sales=("Sales", "sum"),
            Week_Transactions=("Transactions", "sum"),
            Days_in_Week=("Date", "nunique"),
            Week_Start=("Week_Start", "first")
        )
    )
    
    # Get weekly financial metrics
    weekly_fin = (
        fin_df.groupby("Week_Label", as_index=False)
        .agg(
            Gross_Before=("Gross Sales Before Discounts", "sum"),
            Discounts=("Total Discounts", "sum"),
            Gross_After=("Gross Sales After Discounts", "sum"),
            Week_Start_Fin=("Week_Start", "first")
        )
    )
    
    # Merge
    weekly_stats = weekly_stats_slots.merge(weekly_fin, on="Week_Label", how="left")
    weekly_stats["Avg_Ticket"] = weekly_stats["Week_Sales"] / weekly_stats["Week_Transactions"].replace(0, np.nan)
    weekly_stats["Avg_Daily_Sales"] = weekly_stats["Week_Sales"] / weekly_stats["Days_in_Week"]
    weekly_stats["Discount_Rate"] = (weekly_stats["Discounts"] / weekly_stats["Gross_Before"].replace(0, np.nan)) * 100
    weekly_stats = weekly_stats.sort_values("Week_Start")
    
    # Week-over-week growth
    weekly_stats["WoW_Sales_Growth"] = weekly_stats["Week_Sales"].pct_change() * 100
    weekly_stats["WoW_Txn_Growth"] = weekly_stats["Week_Transactions"].pct_change() * 100
    
    # Display weekly metrics
    col1, col2 = st.columns([1.3, 1.2])
    
    with col1:
        # Weekly sales trend with discounts
        fig_weekly = go.Figure()
        
        fig_weekly.add_trace(go.Bar(
            x=weekly_stats["Week_Label"],
            y=weekly_stats["Gross_Before"],
            name="Gross (Before Disc.)",
            marker_color="lightblue",
            text=weekly_stats["Gross_Before"],
            texttemplate='$%{text:,.0f}',
            textposition='outside'
        ))
        
        fig_weekly.add_trace(go.Bar(
            x=weekly_stats["Week_Label"],
            y=weekly_stats["Discounts"],
            name="Discounts",
            marker_color="salmon",
            text=weekly_stats["Discounts"],
            texttemplate='$%{text:,.0f}',
            textposition='inside'
        ))
        
        fig_weekly.add_trace(go.Scatter(
            x=weekly_stats["Week_Label"],
            y=weekly_stats["Avg_Daily_Sales"],
            name="Avg Daily Sales",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="orange", width=3),
            marker=dict(size=8)
        ))
        
        fig_weekly.update_layout(
            title="Weekly Sales with Discounts",
            yaxis=dict(title="Sales ($)"),
            yaxis2=dict(title="Avg Daily Sales ($)", overlaying="y", side="right"),
            barmode='stack',
            hovermode="x unified",
            height=400
        )
        st.plotly_chart(fig_weekly, use_container_width=True)
    
    with col2:
        # Display weekly table with financial details
        display_weekly = weekly_stats[[
            "Week_Label", "Week_Sales", "Discounts", "Discount_Rate",
            "Week_Transactions", "Avg_Ticket", "WoW_Sales_Growth"
        ]].copy()
        display_weekly.columns = ["Week", "Net Sales", "Discounts", "Disc %", "Txns", "Avg Ticket", "WoW Growth"]
        
        st.dataframe(
            display_weekly.style.format({
                "Net Sales": "${:,.2f}",
                "Discounts": "${:,.2f}",
                "Disc %": "{:.1f}%",
                "Txns": "{:,.0f}",
                "Avg Ticket": "${:.2f}",
                "WoW Growth": "{:+.1f}%"
            }).background_gradient(subset=["WoW Growth"], cmap="RdYlGn", vmin=-20, vmax=20),
            height=400,
            use_container_width=True
        )

    # Week-over-week growth visualization
    st.subheader("📈 Week-over-Week Performance")
    
    fig_wow = go.Figure()
    
    # Sales growth bars
    colors = ['green' if x > 0 else 'red' for x in weekly_stats["WoW_Sales_Growth"]]
    fig_wow.add_trace(go.Bar(
        x=weekly_stats["Week_Label"],
        y=weekly_stats["WoW_Sales_Growth"],
        name="Sales Growth %",
        marker_color=colors,
        text=weekly_stats["WoW_Sales_Growth"],
        texttemplate='%{text:+.1f}%',
        textposition='outside'
    ))
    
    # Add discount rate as line
    fig_wow.add_trace(go.Scatter(
        x=weekly_stats["Week_Label"],
        y=weekly_stats["Discount_Rate"],
        name="Discount Rate %",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="purple", width=2, dash="dash"),
        marker=dict(size=8)
    ))
    
    fig_wow.update_layout(
        title="Week-over-Week Growth & Discount Rate",
        yaxis_title="Sales Growth %",
        yaxis2=dict(title="Discount Rate %", overlaying="y", side="right"),
        hovermode="x unified",
        height=400
    )
    st.plotly_chart(fig_wow, use_container_width=True)

# -----------------------------
# Day of Week Analysis
# -----------------------------
st.divider()
st.subheader("📊 Day of Week Performance")

if not slots_df.empty:
    # Merge financial data with slots data
    day_financial = (
        fin_df.groupby("Day_Name", as_index=False)
        .agg(
            Gross_Before_Day=("Gross Sales Before Discounts", "sum"),
            Discounts_Day=("Total Discounts", "sum"),
            Num_Days=("Date", "nunique")
        )
    )
    
    dow_stats = (
        slots_df.groupby("Day_Name", as_index=False)
        .agg(
            Total_Sales=("Sales", "sum"),
            Total_Transactions=("Transactions", "sum"),
        )
    )
    
    dow_stats = dow_stats.merge(day_financial, on="Day_Name", how="left")
    dow_stats["Avg_Sales_Per_Day"] = dow_stats["Total_Sales"] / dow_stats["Num_Days"]
    dow_stats["Avg_Discounts_Per_Day"] = dow_stats["Discounts_Day"] / dow_stats["Num_Days"]
    dow_stats["Avg_Ticket"] = dow_stats["Total_Sales"] / dow_stats["Total_Transactions"].replace(0, np.nan)
    dow_stats["Discount_Rate"] = (dow_stats["Discounts_Day"] / dow_stats["Gross_Before_Day"].replace(0, np.nan)) * 100
    
    # Order by day of week
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_stats["Day_Order"] = dow_stats["Day_Name"].apply(lambda x: day_order.index(x) if x in day_order else 999)
    dow_stats = dow_stats.sort_values("Day_Order")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sales with discounts
        fig_dow = go.Figure()
        
        fig_dow.add_trace(go.Bar(
            x=dow_stats["Day_Name"],
            y=dow_stats["Avg_Sales_Per_Day"],
            name="Avg Net Sales",
            marker_color="lightblue",
            text=dow_stats["Avg_Sales_Per_Day"],
            texttemplate='$%{text:,.0f}',
            textposition='outside'
        ))
        
        fig_dow.add_trace(go.Bar(
            x=dow_stats["Day_Name"],
            y=dow_stats["Avg_Discounts_Per_Day"],
            name="Avg Discounts",
            marker_color="salmon",
            text=dow_stats["Avg_Discounts_Per_Day"],
            texttemplate='$%{text:,.0f}',
            textposition='inside'
        ))
        
        fig_dow.update_layout(
            title="Average Sales & Discounts by Day",
            yaxis_title="Amount ($)",
            barmode='stack',
            height=400
        )
        st.plotly_chart(fig_dow, use_container_width=True)
    
    with col2:
        # Avg ticket and discount rate
        fig_dow_metrics = go.Figure()
        
        fig_dow_metrics.add_trace(go.Bar(
            x=dow_stats["Day_Name"],
            y=dow_stats["Avg_Ticket"],
            name="Avg Ticket",
            marker_color="steelblue",
            text=dow_stats["Avg_Ticket"],
            texttemplate='$%{text:.2f}',
            textposition='outside'
        ))
        
        fig_dow_metrics.add_trace(go.Scatter(
            x=dow_stats["Day_Name"],
            y=dow_stats["Discount_Rate"],
            name="Discount Rate %",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="purple", width=2),
            marker=dict(size=10)
        ))
        
        fig_dow_metrics.update_layout(
            title="Average Ticket & Discount Rate by Day",
            yaxis_title="Avg Ticket ($)",
            yaxis2=dict(title="Discount Rate %", overlaying="y", side="right"),
            height=400
        )
        st.plotly_chart(fig_dow_metrics, use_container_width=True)

# -----------------------------
# Daily overview
# -----------------------------
st.divider()
st.subheader("📅 Daily Performance Details")

# Prepare daily data with financial metrics
display_daily = fin_df[[
    "Date", "Day_Name", "Week_Label", 
    "Gross Sales Before Discounts", "Total Discounts", 
    "Slot_Sales_Total", "Slot_Transactions_Total", "Avg_Ticket_Day"
]].copy()

# Calculate discount rate for each day
display_daily["Discount_Rate"] = (display_daily["Total Discounts"] / display_daily["Gross Sales Before Discounts"].replace(0, np.nan)) * 100

display_daily.columns = ["Date", "Day", "Week", "Gross Sales", "Discounts", "Net Sales", "Transactions", "Avg Ticket", "Disc %"]

col1, col2 = st.columns([1.2, 1])

with col1:
    st.dataframe(
        display_daily.style.format({
            "Gross Sales": "${:,.2f}",
            "Discounts": "${:,.2f}",
            "Net Sales": "${:,.2f}",
            "Transactions": "{:,.0f}",
            "Avg Ticket": "${:.2f}",
            "Disc %": "{:.1f}%"
        }).background_gradient(subset=["Disc %"], cmap="YlOrRd", vmin=0, vmax=50),
        height=450,
        use_container_width=True
    )

with col2:
    # Daily sales trend with gross and net
    fig_daily = go.Figure()
    
    fig_daily.add_trace(go.Scatter(
        x=fin_df["Date_Parsed"],
        y=fin_df["Gross Sales Before Discounts"],
        name="Gross Sales",
        mode="lines+markers",
        line=dict(color="lightblue", width=2),
        fill='tonexty'
    ))
    
    fig_daily.add_trace(go.Scatter(
        x=fin_df["Date_Parsed"],
        y=fin_df["Slot_Sales_Total"],
        name="Net Sales",
        mode="lines+markers",
        line=dict(color="steelblue", width=2),
        marker=dict(size=8)
    ))
    
    fig_daily.update_layout(
        title="Daily Sales Trend (Gross vs Net)",
        xaxis_title="Date",
        yaxis_title="Sales ($)",
        hovermode="x unified",
        height=450
    )
    st.plotly_chart(fig_daily, use_container_width=True)

# -----------------------------
# Time Slot Analysis (Day Drill-Down)
# -----------------------------
st.divider()
st.subheader("🕐 Time Slot Analysis by Day")

day_choice = st.selectbox("Select Date for Time Slot Details", fin_df["Date"].tolist())
day_slots = slots_df[slots_df["Date"] == day_choice].copy()

if day_slots.empty:
    st.warning("⚠️ No time-slot data found for this day.")
    st.stop()

# Get financial info for selected day
day_fin = fin_df[fin_df["Date"] == day_choice].iloc[0]

# Sort time slots
def sort_time_slot(slot):
    try:
        part = slot.split(" - ")[0].strip()
        t = datetime.strptime(part, "%I:%M %p")
        return (t.hour, t.minute)
    except:
        return (999, 999)

day_slots["sort_key"] = day_slots["Time_slot"].apply(sort_time_slot)
day_slots = day_slots.sort_values("sort_key")

peak_thresh = day_slots["Sales"].quantile(1 - TOP_PEAK_PCT)
slow_thresh = day_slots["Sales"].quantile(BOTTOM_SLOW_PCT)

day_total_sales = day_slots["Sales"].sum()
day_total_txn = day_slots["Transactions"].sum()
day_avg_ticket = day_total_sales / max(day_total_txn, 1)

# Display day metrics with financial info
a, b, c, d, e = st.columns(5)
a.metric("Gross Sales", f"${day_fin.get('Gross Sales Before Discounts', 0):,.2f}")
b.metric("Discounts", f"${day_fin.get('Total Discounts', 0):,.2f}")
c.metric("Net Sales", f"${day_total_sales:,.2f}")
d.metric("Transactions", f"{day_total_txn:,.0f}")
e.metric("Avg Ticket", f"${day_avg_ticket:.2f}")

colA, colB = st.columns([1.3, 1])

with colA:
    fig_slots = px.bar(
        day_slots,
        x="Time_slot",
        y="Sales",
        title=f"Sales by Time Slot — {day_choice} ({day_fin['Day_Name']})",
        color="Sales",
        color_continuous_scale="Blues"
    )
    fig_slots.update_layout(
        xaxis_title="Time Slot", 
        yaxis_title="Sales ($)", 
        showlegend=False,
        height=400
    )
    fig_slots.update_traces(texttemplate='$%{y:,.0f}', textposition='outside')
    st.plotly_chart(fig_slots, use_container_width=True)

with colB:
    fig_txn = px.line(
        day_slots,
        x="Time_slot",
        y="Transactions",
        markers=True,
        title="Transactions by Time Slot"
    )
    fig_txn.update_layout(height=190)
    st.plotly_chart(fig_txn, use_container_width=True)

    fig_ticket = px.line(
        day_slots,
        x="Time_slot",
        y="Avg_Ticket",
        markers=True,
        title="Avg Ticket by Time Slot"
    )
    fig_ticket.update_layout(height=190)
    fig_ticket.update_traces(line=dict(color="orange"))
    st.plotly_chart(fig_ticket, use_container_width=True)

# Peak & slow slot tables
st.divider()
p1, p2 = st.columns(2)

with p1:
    st.subheader(f"🔥 Peak Slots (Top {int(TOP_PEAK_PCT*100)}%)")
    peaks = day_slots[day_slots["Sales"] >= peak_thresh].sort_values("Sales", ascending=False)
    st.dataframe(
        peaks[["Time_slot", "Sales", "Transactions", "Avg_Ticket"]].style.format({
            "Sales": "${:,.2f}",
            "Transactions": "{:,.0f}",
            "Avg_Ticket": "${:.2f}"
        }),
        height=300,
        use_container_width=True
    )

with p2:
    st.subheader(f"🐌 Slow Slots (Bottom {int(BOTTOM_SLOW_PCT*100)}%)")
    slows = day_slots[day_slots["Sales"] <= slow_thresh].sort_values("Sales", ascending=True)
    st.dataframe(
        slows[["Time_slot", "Sales", "Transactions", "Avg_Ticket"]].style.format({
            "Sales": "${:,.2f}",
            "Transactions": "{:,.0f}",
            "Avg_Ticket": "${:.2f}"
        }),
        height=300,
        use_container_width=True
    )

# -----------------------------
# Cross-day patterns
# -----------------------------
st.divider()
st.subheader("🔍 Cross-Day Time Slot Patterns")

if not slots_df.empty:
    avg_by_slot = (
        slots_df.groupby("Time_slot", as_index=False)
        .agg(
            Avg_Sales=("Sales", "mean"),
            Avg_Transactions=("Transactions", "mean"),
            Days=("Date", "nunique")
        )
    )
    avg_by_slot["sort_key"] = avg_by_slot["Time_slot"].apply(sort_time_slot)
    avg_by_slot = avg_by_slot.sort_values("sort_key")

    c1, c2 = st.columns([1, 1.2])
    
    with c1:
        fig_avg_slot = px.area(
            avg_by_slot,
            x="Time_slot",
            y="Avg_Sales",
            title="Average Sales by Time Slot (All Days)"
        )
        fig_avg_slot.update_traces(line=dict(color="steelblue"), fillcolor="lightblue")
        st.plotly_chart(fig_avg_slot, use_container_width=True)

    with c2:
        heat = slots_df.pivot_table(index="Date", columns="Time_slot", values="Sales", aggfunc="sum")
        heat = heat.sort_index()
        
        fig_heat = px.imshow(
            heat,
            aspect="auto",
            title="Sales Heatmap (Date × Time Slot)",
            color_continuous_scale="Blues",
            labels=dict(color="Sales ($)")
        )
        st.plotly_chart(fig_heat, use_container_width=True)

# -----------------------------
# Export
# -----------------------------
st.divider()
st.subheader("💾 Export Data")

col1, col2, col3 = st.columns(3)

with col1:
    csv_day = day_slots[["Time_slot", "Sales", "Transactions", "Avg_Ticket"]].to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Selected Day (CSV)",
        data=csv_day,
        file_name=f"{day_choice}_timeslots.csv",
        mime="text/csv"
    )

with col2:
    if 'weekly_stats' in locals() and not weekly_stats.empty:
        csv_weekly = weekly_stats.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Weekly Stats (CSV)",
            data=csv_weekly,
            file_name="weekly_stats.csv",
            mime="text/csv"
        )

with col3:
    csv_daily = display_daily.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Daily Stats (CSV)",
        data=csv_daily,
        file_name="daily_stats.csv",
        mime="text/csv"
    )