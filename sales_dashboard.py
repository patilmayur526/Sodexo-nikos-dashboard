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
st.title("📊 Sales Dashboard — Weekly & Daily Analysis")

# -----------------------------
# File path
# -----------------------------
ROOT = Path(__file__).resolve().parent
DEFAULT_FILE = ROOT / "combined_sales_data.xlsx"

st.sidebar.header("⚙️ Configuration")
file_path_str = st.sidebar.text_input("Excel file path", str(DEFAULT_FILE))

st.sidebar.subheader("Commission Settings")
ARAMARK_COMMISSION_RATE = st.sidebar.number_input(
    "Aramark Commission %", 
    min_value=0.0, 
    max_value=100.0, 
    value=20.0, 
    step=0.5
) / 100.0

CREDIT_CARD_FEE_RATE = st.sidebar.number_input(
    "Credit Card Fee %",
    min_value=0.0,
    max_value=10.0,
    value=3.0,
    step=0.1
) / 100.0

SALES_TAX_RATE = st.sidebar.number_input(
    "Sales Tax %",
    min_value=0.0,
    max_value=15.0,
    value=8.0,
    step=0.5,
    help="Sales tax calculated on credit card sales"
) / 100.0

st.sidebar.subheader("GetApp Credit Card (Manual Entry)")
st.sidebar.caption("💡 Enter GetApp CC sales by sales week (Thu-Wed)")
st.sidebar.caption("⚠️ GetApp source files don't show payment breakdown")
GETAPP_CC_MANUAL = st.sidebar.expander("📝 Add GetApp CC by Week")

st.sidebar.subheader("Sales Tax (Manual Entry)")
st.sidebar.caption("💡 Enter actual sales tax collected by week")
st.sidebar.caption("⚠️ Source files show $0 for tax, enter actual amounts")
SALES_TAX_MANUAL = st.sidebar.expander("📝 Add Sales Tax by Week")

# Store manual entries by week
getapp_cc_by_week = {}
sales_tax_by_week = {}

st.sidebar.subheader("Time Slot Settings")
TOP_PEAK_PCT = st.sidebar.slider("Peak slots (Top %)", 1, 30, 10) / 100.0
BOTTOM_SLOW_PCT = st.sidebar.slider("Slow slots (Bottom %)", 1, 50, 20) / 100.0

# -----------------------------
# Helper functions
# -----------------------------
def to_num(x):
    return pd.to_numeric(x, errors="coerce")


def get_sales_week(date_obj):
    """Calculate sales week number (Thursday-Wednesday)"""
    days_since_thursday = (date_obj.weekday() - 3) % 7
    week_start = date_obj - timedelta(days=days_since_thursday)
    
    year = week_start.year
    jan_1 = datetime(year, 1, 1)
    days_since_jan_thursday = (jan_1.weekday() - 3) % 7
    first_thursday = jan_1 - timedelta(days=days_since_jan_thursday)
    
    if week_start < first_thursday:
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
        
        if "run financial" in k_lower or "payment summary" in k_lower:
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
        
        if "tender summary" in k_lower or "payment summary" in k_lower or "day part summary" in k_lower:
            break
        
        if in_control_section and k_lower not in ("name", ""):
            v = row[col1]
            v_num = to_num(v)
            if pd.notna(v_num):
                metrics[k] = float(v_num)
                # Also capture Tax Collected for payment calculations
                if "tax collected" in k_lower:
                    metrics["Sales Tax Collected"] = float(v_num)

    return metrics


def extract_payment_data(raw_df: pd.DataFrame) -> dict:
    """Extract payment breakdown (Credit Card, Cash, Sales Tax)"""
    payments = {
        "Credit Card": 0.0,
        "Cash": 0.0,
        "Sales Tax Collected": 0.0
    }
    
    if raw_df.shape[1] < 2:
        return payments
    
    col0 = raw_df.columns[0]
    col1 = raw_df.columns[1]
    
    in_tender_section = False
    for _, row in raw_df.iterrows():
        k = str(row[col0]).strip() if pd.notna(row[col0]) else ""
        if not k:
            continue
        
        k_lower = k.lower()
        
        # Start of tender/payment section
        if "tender summary" in k_lower or "payment summary" in k_lower:
            in_tender_section = True
            continue
        
        # End of tender section
        if in_tender_section and ("day part" in k_lower):
            break
        
        # Extract payment amounts
        if in_tender_section and k_lower not in ("type", "amount", ""):
            v = row[col1]
            v_num = to_num(v)
            if pd.notna(v_num):
                if "credit card" in k_lower or "credit" in k_lower:
                    payments["Credit Card"] += float(v_num)
                elif "cash" in k_lower:
                    payments["Cash"] += float(v_num)
    
    return payments


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
        
        # Extract payment data
        payment = extract_payment_data(raw)
        
        # Combine
        fin_row = {
            "Sheet": sheet,
            "Date": date_info.get("date", sheet),
            "Day_Name": date_info.get("day_name", ""),
            **fin,
            **payment
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
    week_info = fin_df["Date_Parsed"].apply(get_sales_week)
    fin_df["Week_Year"] = week_info.apply(lambda x: x[0])
    fin_df["Week_Number"] = week_info.apply(lambda x: x[1])
    fin_df["Week_Start"] = week_info.apply(lambda x: x[2])
    fin_df["Week_End"] = fin_df["Week_Start"] + timedelta(days=6)
    fin_df["Week_Label"] = fin_df.apply(
        lambda row: f"W{row['Week_Number']:02d} ({row['Week_Start'].strftime('%b %d')}-{row['Week_End'].strftime('%b %d')})", 
        axis=1
    )
    
    slots_df = pd.concat(days_slots, ignore_index=True) if days_slots else pd.DataFrame(
        columns=["Sheet", "Date", "Day_Name", "Time_slot", "Sales", "Transactions", "Avg_Ticket"]
    )
    
    if not slots_df.empty:
        slots_df["Date_Parsed"] = pd.to_datetime(slots_df["Date"], errors="coerce")
        slots_df = slots_df.dropna(subset=["Date_Parsed"])
        
        # Add week info to slots
        week_info_slots = slots_df["Date_Parsed"].apply(get_sales_week)
        slots_df["Week_Year"] = week_info_slots.apply(lambda x: x[0])
        slots_df["Week_Number"] = week_info_slots.apply(lambda x: x[1])
        slots_df["Week_Start"] = week_info_slots.apply(lambda x: x[2])
        
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
    st.error(f"❌ File not found at: {file_path}")
    st.info("💡 Please check the file path in the sidebar.")
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
    return df[col].sum() if col in df.columns else 0.0

# Financial metrics
gross_before = metric_value(fin_df, "Gross Sales Before Discounts")
total_discounts = metric_value(fin_df, "Total Discounts")
gross_after = metric_value(fin_df, "Gross Sales After Discounts")
net_vat = metric_value(fin_df, "Sales Net VAT")

# Payment metrics - remove from overall, will show in weekly section only
# total_credit_card = metric_value(fin_df, "Credit Card")
# total_cash = metric_value(fin_df, "Cash")
# total_sales_tax = metric_value(fin_df, "Sales Tax Collected")

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

# Financial Control Metrics
st.caption("**Financial Control Totals**")
fc1, fc2, fc3, fc4 = st.columns(4)
fc1.metric("Gross Sales (Before Disc.)", f"${gross_before:,.2f}")
fc2.metric("Total Discounts", f"${total_discounts:,.2f}", 
          delta=f"-{(total_discounts/gross_before*100):.1f}%" if gross_before > 0 else None,
          delta_color="inverse")
fc3.metric("Gross Sales (After Disc.)", f"${gross_after:,.2f}")
fc4.metric("Sales Net VAT", f"${net_vat:,.2f}")

# Remove payment breakdown from overall section - will show in weekly commission
# st.caption("**Payment Breakdown**")
# pm1, pm2, pm3 = st.columns(3)
# pm1.metric("💳 Credit Card", f"${total_credit_card:,.2f}")
# pm2.metric("💵 Cash", f"${total_cash:,.2f}")
# pm3.metric("📄 Sales Tax", f"${total_sales_tax:,.2f}")

if gross_before > 0:
    discount_rate = (total_discounts / gross_before) * 100
    st.info(f"💡 Overall discount rate: **{discount_rate:.2f}%** of gross sales")

# -----------------------------
# Weekly Commission Summary
# -----------------------------
st.divider()
st.subheader("💼 Weekly Commission & Payment Summary")

# Calculate weekly aggregates
weekly_data = fin_df.groupby("Week_Label", as_index=False).agg({
    "Gross Sales Before Discounts": "sum",
    "Total Discounts": "sum",
    "Gross Sales After Discounts": "sum",
    "Sales Net VAT": "sum",
    "Credit Card": "sum",
    "Cash": "sum",
    "Sales Tax Collected": "sum",
    "Tax Collected": "sum",  # Also capture this field name
    "Week_Start": "first",
    "Week_End": "first",
    "Week_Number": "first"
})

weekly_data = weekly_data.sort_values("Week_Start")

# FORCE Cash to 0.0 (as per accountant's requirement - no cash transactions)
weekly_data["Cash"] = 0.0

# Combine tax fields (might be named differently in different sheets)
weekly_data["Sales Tax Collected"] = (
    weekly_data["Sales Tax Collected"].fillna(0) + 
    weekly_data["Tax Collected"].fillna(0)
)
weekly_data = weekly_data.drop(columns=["Tax Collected"], errors='ignore')

# Add manual GetApp CC entry interface in sidebar
with GETAPP_CC_MANUAL:
    st.caption("**Sales Week: Thursday to Wednesday**")
    st.caption("Enter GetApp credit card amount if you know weekly totals")
    st.markdown("---")
    
    for idx, row in weekly_data.iterrows():
        week_label = row["Week_Label"]
        week_start = row["Week_Start"].strftime("%b %d")
        week_end = row["Week_End"].strftime("%b %d, %Y")
        
        # Show full week range for clarity
        st.caption(f"**{week_label}**")
        st.caption(f"📅 {week_start} (Thu) - {week_end} (Wed)")
        
        manual_cc = st.number_input(
            "GetApp Credit Card ($)",
            min_value=0.0,
            value=0.0,
            step=50.0,
            format="%.2f",
            key=f"getapp_cc_{week_label}",
            help=f"Enter GetApp CC sales for week {week_start} - {week_end}"
        )
        
        if manual_cc > 0:
            getapp_cc_by_week[week_label] = manual_cc
            st.success(f"✓ ${manual_cc:,.2f} will be added to Oracle CC")
        
        st.markdown("---")

# Add manual Sales Tax entry interface in sidebar
with SALES_TAX_MANUAL:
    st.caption("**Sales Week: Thursday to Wednesday**")
    st.caption("Enter actual sales tax collected for each week")
    st.markdown("---")
    
    for idx, row in weekly_data.iterrows():
        week_label = row["Week_Label"]
        week_start = row["Week_Start"].strftime("%b %d")
        week_end = row["Week_End"].strftime("%b %d, %Y")
        
        # Show full week range for clarity
        st.caption(f"**{week_label}**")
        st.caption(f"📅 {week_start} (Thu) - {week_end} (Wed)")
        
        manual_tax = st.number_input(
            "Sales Tax Collected ($)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            format="%.2f",
            key=f"sales_tax_{week_label}",
            help=f"Enter sales tax collected for week {week_start} - {week_end}"
        )
        
        if manual_tax > 0:
            sales_tax_by_week[week_label] = manual_tax
            st.success(f"✓ ${manual_tax:,.2f} will be used for this week")
        
        st.markdown("---")

# Apply manual GetApp CC entries to weekly data
if getapp_cc_by_week:
    for week_label, cc_amount in getapp_cc_by_week.items():
        mask = weekly_data["Week_Label"] == week_label
        weekly_data.loc[mask, "Credit Card"] += cc_amount

# Apply manual Sales Tax entries to weekly data
if sales_tax_by_week:
    for week_label, tax_amount in sales_tax_by_week.items():
        mask = weekly_data["Week_Label"] == week_label
        weekly_data.loc[mask, "Sales Tax Collected"] = tax_amount
else:
    # If no manual entry, calculate as fallback
    # Default: 8% of Credit Card sales (configurable)
    weekly_data["Sales Tax Collected"] = weekly_data["Credit Card"] * SALES_TAX_RATE

# Add commission calculations (matching accountant's exact method)
# Calculate Gross Before Discounts the same way accountant does:
# Gross Before = Gross After + Discounts (instead of using the field directly)
weekly_data["Calculated_Gross_Before"] = (
    weekly_data["Gross Sales After Discounts"] + 
    weekly_data["Total Discounts"]
)

weekly_data["CC_Fee"] = weekly_data["Credit Card"] * CREDIT_CARD_FEE_RATE
# Use calculated gross to match accountant's numbers exactly
weekly_data["Total_Commissionable"] = weekly_data["Calculated_Gross_Before"] - weekly_data["CC_Fee"]
weekly_data["Aramark_Commission"] = weekly_data["Total_Commissionable"] * ARAMARK_COMMISSION_RATE
weekly_data["Total_ARA_Commission"] = weekly_data["Aramark_Commission"] - weekly_data["Total Discounts"]
weekly_data["Niko_Commission"] = weekly_data["Total_Commissionable"] - weekly_data["Aramark_Commission"]
weekly_data["Total_Check_Niko"] = weekly_data["Niko_Commission"] - weekly_data["Cash"] + weekly_data["Sales Tax Collected"]

# Generate invoice numbers (format: MMDDYY)
weekly_data["Invoice_Number"] = weekly_data["Week_Start"].apply(
    lambda x: f"{x.month:02d}{x.day:02d}{str(x.year)[2:]}"
)

# Select week to display
selected_week = st.selectbox("Select Sales Week", weekly_data["Week_Label"].tolist(), index=len(weekly_data)-1)
week_row = weekly_data[weekly_data["Week_Label"] == selected_week].iloc[0]

# Display header
st.markdown(f"### Week: {week_row['Week_Start'].strftime('%b %d')} - {week_row['Week_End'].strftime('%b %d, %Y')}")
st.markdown(f"**Invoice Number:** {week_row['Invoice_Number']}")

# Display selected week's commission summary
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.markdown(f"#### 📊 Sales Breakdown")
    
    # Show Oracle vs GetApp CC breakdown
    oracle_cc = week_row["Credit Card"] - getapp_cc_by_week.get(selected_week, 0.0)
    getapp_cc = getapp_cc_by_week.get(selected_week, 0.0)
    
    st.metric("Credit Card", f"${week_row['Credit Card']:,.2f}")
    if getapp_cc > 0:
        st.caption(f"  ├─ Oracle: ${oracle_cc:,.2f}")
        st.caption(f"  └─ GetApp: ${getapp_cc:,.2f} (manual)")
    
    st.metric("Cash", f"${week_row['Cash']:,.2f}")
    st.metric("Sales Tax Collected", f"${week_row['Sales Tax Collected']:,.2f}")
    st.caption(f"**Aramark Commission Rate:** {ARAMARK_COMMISSION_RATE*100:.1f}%")
    st.caption(f"**Credit Card Fee:** {CREDIT_CARD_FEE_RATE*100:.1f}%")

with col2:
    st.markdown(f"#### 🏢 Aramark Commission")
    st.metric("Total Commissionable Sales", f"${week_row['Total_Commissionable']:,.2f}")
    st.metric("Aramark Commission", f"${week_row['Aramark_Commission']:,.2f}")
    st.metric("Less: Discount", f"${week_row['Total Discounts']:,.2f}", delta_color="inverse")
    
    # Color code based on positive/negative
    ara_color = "normal" if week_row['Total_ARA_Commission'] >= 0 else "inverse"
    st.metric("**TOTAL ARA Commission**", 
             f"${week_row['Total_ARA_Commission']:,.2f}",
             delta=f"{(week_row['Total_ARA_Commission']/week_row['Total_Commissionable']*100):.1f}% of commissionable",
             delta_color=ara_color)

with col3:
    st.markdown(f"#### 🍽️ Niko Payment")
    st.metric("Niko Commission", f"${week_row['Niko_Commission']:,.2f}")
    st.metric("Less: Cash Collected", f"${week_row['Cash']:,.2f}")
    st.metric("Add: Sales Tax Collected", f"${week_row['Sales Tax Collected']:,.2f}")
    st.metric("**Total Check to Niko**", f"${week_row['Total_Check_Niko']:,.2f}",
             delta=f"{(week_row['Total_Check_Niko']/week_row['Sales Net VAT']*100):.1f}% of sales")

# Summary row (matching accountant format)
st.markdown("---")
st.markdown("#### Summary")
sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
sum_col1.metric("💰 Total Sales", f"${week_row['Sales Net VAT']:,.2f}")
sum_col2.metric("🏢 Aramark Gets", f"${week_row['Total_ARA_Commission']:,.2f}",
               delta=f"{(week_row['Total_ARA_Commission']/week_row['Sales Net VAT']*100):.1f}%")
sum_col3.metric("🍽️ Niko Gets", f"${week_row['Total_Check_Niko']:,.2f}",
               delta=f"{(week_row['Total_Check_Niko']/week_row['Sales Net VAT']*100):.1f}%")
sum_col4.metric("💳 CC Fees", f"${week_row['CC_Fee']:,.2f}",
               delta=f"-{(week_row['CC_Fee']/week_row['Sales Net VAT']*100):.2f}%", delta_color="inverse")

# -----------------------------
# Weekly Trends (All Weeks)
# -----------------------------
st.divider()
st.subheader("📅 Weekly Trends Comparison")

# Week-over-week growth
weekly_data["WoW_Sales_Growth"] = weekly_data["Sales Net VAT"].pct_change() * 100
weekly_data["WoW_Txn_Growth"] = weekly_data["Gross Sales After Discounts"].pct_change() * 100
weekly_data["Discount_Rate"] = (weekly_data["Total Discounts"] / weekly_data["Gross Sales Before Discounts"]) * 100

col1, col2 = st.columns([1.3, 1.2])

with col1:
    # Weekly commission split chart
    fig_weekly = go.Figure()
    
    fig_weekly.add_trace(go.Bar(
        x=weekly_data["Week_Label"],
        y=weekly_data["Total_ARA_Commission"],
        name="Aramark Commission",
        marker_color="salmon",
        text=weekly_data["Total_ARA_Commission"],
        texttemplate='$%{text:,.0f}',
        textposition='outside'
    ))
    
    fig_weekly.add_trace(go.Bar(
        x=weekly_data["Week_Label"],
        y=weekly_data["Total_Check_Niko"],
        name="Niko Payment",
        marker_color="lightblue",
        text=weekly_data["Total_Check_Niko"],
        texttemplate='$%{text:,.0f}',
        textposition='outside'
    ))
    
    fig_weekly.update_layout(
        title="Weekly Commission Split",
        yaxis_title="Amount ($)",
        barmode='group',
        hovermode="x unified",
        height=400
    )
    st.plotly_chart(fig_weekly, use_container_width=True)

with col2:
    # Weekly table
    display_weekly = weekly_data[[
        "Week_Label", "Sales Net VAT", "Gross Sales After Discounts", "Discount_Rate",
        "Total_ARA_Commission", "Total_Check_Niko", "WoW_Sales_Growth"
    ]].copy()
    display_weekly.columns = ["Week", "Net Sales", "Gross After Disc", "Disc %", "Aramark", "Niko", "WoW Growth"]
    
    st.dataframe(
        display_weekly.style.format({
            "Net Sales": "${:,.2f}",
            "Gross After Disc": "${:,.2f}",
            "Disc %": "{:.1f}%",
            "Aramark": "${:,.2f}",
            "Niko": "${:,.2f}",
            "WoW Growth": "{:+.1f}%"
        }).background_gradient(subset=["WoW Growth"], cmap="RdYlGn", vmin=-20, vmax=20),
        height=400,
        use_container_width=True
    )

# Week-over-week growth chart
fig_wow = go.Figure()

colors = ['green' if x > 0 else 'red' for x in weekly_data["WoW_Sales_Growth"]]
fig_wow.add_trace(go.Bar(
    x=weekly_data["Week_Label"],
    y=weekly_data["WoW_Sales_Growth"],
    name="Sales Growth %",
    marker_color=colors,
    text=weekly_data["WoW_Sales_Growth"],
    texttemplate='%{text:+.1f}%',
    textposition='outside'
))

fig_wow.add_trace(go.Scatter(
    x=weekly_data["Week_Label"],
    y=weekly_data["Discount_Rate"],
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
            marker_color="lightblue"
        ))
        
        fig_dow.add_trace(go.Bar(
            x=dow_stats["Day_Name"],
            y=dow_stats["Avg_Discounts_Per_Day"],
            name="Avg Discounts",
            marker_color="salmon"
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
            marker_color="steelblue"
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

# Prepare daily data
display_daily = fin_df[[
    "Date", "Day_Name", "Week_Label", 
    "Gross Sales Before Discounts", "Total Discounts", 
    "Gross Sales After Discounts", "Sales Net VAT",
    "Credit Card", "Cash"
]].copy()

display_daily["Discount_Rate"] = (display_daily["Total Discounts"] / display_daily["Gross Sales Before Discounts"].replace(0, np.nan)) * 100
display_daily.columns = ["Date", "Day", "Week", "Gross Before", "Discounts", "Gross After", "Net Sales", "Credit Card", "Cash", "Disc %"]

col1, col2 = st.columns([1.2, 1])

with col1:
    st.dataframe(
        display_daily.style.format({
            "Gross Before": "${:,.2f}",
            "Discounts": "${:,.2f}",
            "Gross After": "${:,.2f}",
            "Net Sales": "${:,.2f}",
            "Credit Card": "${:,.2f}",
            "Cash": "${:,.2f}",
            "Disc %": "{:.1f}%"
        }).background_gradient(subset=["Disc %"], cmap="YlOrRd", vmin=0, vmax=50),
        height=450,
        use_container_width=True
    )

with col2:
    # Daily trend
    fig_daily = go.Figure()
    
    fig_daily.add_trace(go.Scatter(
        x=fin_df["Date_Parsed"],
        y=fin_df["Gross Sales Before Discounts"],
        name="Gross Before Disc",
        mode="lines",
        line=dict(color="lightblue", width=1),
        fill='tonexty'
    ))
    
    fig_daily.add_trace(go.Scatter(
        x=fin_df["Date_Parsed"],
        y=fin_df["Sales Net VAT"],
        name="Net Sales",
        mode="lines+markers",
        line=dict(color="steelblue", width=2),
        marker=dict(size=6)
    ))
    
    fig_daily.update_layout(
        title="Daily Sales Trend",
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
else:
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

    # Display day metrics
    a, b, c, d, e = st.columns(5)
    a.metric("Gross Before", f"${day_fin.get('Gross Sales Before Discounts', 0):,.2f}")
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
# Export
# -----------------------------
st.divider()
st.subheader("💾 Export Data")

col1, col2, col3 = st.columns(3)

with col1:
    if 'day_slots' in locals() and not day_slots.empty:
        csv_day = day_slots[["Time_slot", "Sales", "Transactions", "Avg_Ticket"]].to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Selected Day (CSV)",
            data=csv_day,
            file_name=f"{day_choice}_timeslots.csv",
            mime="text/csv"
        )

with col2:
    if 'weekly_data' in locals() and not weekly_data.empty:
        csv_weekly = weekly_data.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Weekly Stats (CSV)",
            data=csv_weekly,
            file_name="weekly_commission_stats.csv",
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
