# Sodexo Nikos Sales Dashboard 📊

Real-time sales analytics dashboard for Nikos restaurant, combining data from Oracle Micros Symphony and GetApp.

## 🔗 Live Dashboard

**View Live Dashboard:** [Your Streamlit App URL will appear here after deployment]

## 📋 Features

- **Overall Performance Metrics** - Total sales, transactions, average ticket, discount analysis
- **Weekly Trends** - Thursday to Wednesday sales weeks with week-over-week growth
- **Day of Week Analysis** - Compare performance across different days
- **Daily Details** - Complete breakdown with financial metrics
- **Time Slot Analysis** - Hourly performance with peak/slow period identification
- **Cross-Day Patterns** - Heatmaps and trends across all days

## 🚀 Quick Start

### Option 1: View Online (Recommended for Boss)
Simply visit the live dashboard link above - no installation needed!

### Option 2: Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/patilmayur526/Sodexo-nikos-dashboard.git
   cd Sodexo-nikos-dashboard
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the dashboard:**
   ```bash
   streamlit run sales_dashboard.py
   ```

## 📁 Repository Structure

```
Sodexo-nikos-dashboard/
├── sales_dashboard.py           # Main dashboard application
├── combine_sources.py           # Data processing script
├── combined_sales_data.xlsx     # Combined sales data (updated weekly)
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── .gitignore                   # Git ignore rules
```

## 🔄 Updating Data (For Mayur)

### Weekly Update Process:

1. **Update source files** on your local machine:
   - `combined_daily_operations.xlsx` (Oracle data)
   - `combined_get_app_sales.xlsx` (GetApp data)

2. **Run the combination script:**
   ```bash
   python3 combine_sources.py
   ```
   This creates/updates `combined_sales_data.xlsx`

3. **Commit and push changes:**
   ```bash
   git add combined_sales_data.xlsx
   git commit -m "Update sales data - Week XX YYYY"
   git push origin main
   ```

4. **Streamlit Cloud auto-deploys** - Dashboard updates automatically within 1-2 minutes!

## 📊 Dashboard Sections

### 1. Overall Performance
- Days tracked
- Total sales (USD)
- Total transactions
- Average ticket
- Discount analysis

### 2. Weekly Analysis
- Sales trends by week (Thu-Wed)
- Week-over-week growth
- Discount rates
- Average daily performance

### 3. Day of Week Performance
- Best/worst performing days
- Average sales by day
- Discount patterns

### 4. Daily Details
- Complete daily breakdown
- Gross vs Net sales
- Transaction counts
- Discount percentages

### 5. Time Slot Analysis
- Hourly sales breakdown
- Peak hours identification
- Slow periods
- Transaction patterns

## 🎯 For Management

**Dashboard URL:** [Insert Streamlit Cloud URL after deployment]

**Update Frequency:** 
- Data updated weekly (every Thursday after business week ends)
- Dashboard auto-refreshes when new data is pushed

**Date Range:** 
- Currently showing: January 19, 2026 - February 8, 2026
- Updates automatically as new data is added

## 🛠️ Technical Details

**Built with:**
- Python 3.10+
- Streamlit (dashboard framework)
- Pandas (data processing)
- Plotly (interactive charts)
- OpenPyXL (Excel file handling)

**Data Sources:**
- Oracle Micros Symphony POS system
- GetApp ordering platform

**Sales Week Definition:**
- Week runs Thursday to Wednesday
- Aligns with business operations cycle

## 📝 Notes

- All amounts in USD ($)
- Time slots in 15-minute intervals
- Discount rates calculated as % of gross sales
- Week-over-week growth shows % change from previous week

## 🔐 Data Privacy

- Source data files (Oracle, GetApp) are NOT committed to repository
- Only processed, anonymized aggregate data is stored
- No customer personal information included

## 👤 Maintainer

**Mayur Patil**  
Data Analyst -  N.C Schultz LLC

For questions or issues, contact: patilmayur073@gmail.com

---

**Last Updated:** February 10,2026  
**Version:** 1.0
