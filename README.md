# 📊 Sodexo Nikos Sales Dashboard

**Real-time sales analytics and commission tracking dashboard for Niko's food service operations at Sodexo.**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://sodexo-nikos-dashboard-scsujncz7s524kxima4r9m.streamlit.app)

---

## 🎯 Overview

This dashboard provides comprehensive weekly and daily sales analysis for Niko's operations, combining data from Oracle Micros Symphony POS and GetApp online ordering systems. It automatically calculates commission splits between Aramark and Niko, generates invoices, and provides detailed performance metrics.

### Key Features

- **📈 Weekly Commission Tracking** - Automated commission calculations with configurable rates
- **💳 Payment Breakdown** - Credit card, cash, and sales tax tracking by week
- **📅 Sales Week Analysis** - Thursday-Wednesday reporting cycles with week-over-week growth
- **🕐 Time Slot Analytics** - 15-minute interval performance tracking (9:00 AM - 8:30 PM)
- **📊 Visual Insights** - Interactive charts for trends, patterns, and comparisons
- **💰 Invoice Generation** - Automatic invoice numbering and detailed breakdowns
- **📥 Data Export** - CSV exports for daily, weekly, and commission data

---

## 🏗️ Architecture

### Data Flow

```
Oracle POS (Daily Files)     GetApp System (Daily Files)
         ↓                              ↓
  combine_daily_operations.py    combine_get_app.py
         ↓                              ↓
    combined_daily_           combined_get_app_
     operations.xlsx              sales.xlsx
         ↓                              ↓
         └──────────┬───────────────────┘
                    ↓
          add_two_sources.py
                    ↓
         combined_sales_data.xlsx
                    ↓
              GitHub Repository
                    ↓
           Streamlit Cloud (Auto-deploy)
                    ↓
         📊 Live Dashboard
```

### Repository Structure

```
Sodexo-nikos-dashboard/
├── sales_dashboard.py           # Main Streamlit application
├── combined_sales_data.xlsx     # Merged sales data (updated weekly)
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── .gitignore                   # Git ignore rules
└── .streamlit/
    └── config.toml              # Dashboard theme configuration
```

---

## 📊 Dashboard Sections

### 1. Overall Performance
- Total sales across all periods
- Days tracked, total transactions
- Gross sales before/after discounts
- Average daily sales and ticket size
- Overall discount rate

### 2. Weekly Commission & Payment Summary
**Configurable Settings:**
- Aramark Commission Rate (default: 20%)
- Credit Card Fee (default: 3%)
- Sales Tax Rate (default: 8%)

**Manual Entry Fields:**
- GetApp Credit Card sales by week
- Sales Tax Collected by week

**Commission Breakdown:**
- **Sales Breakdown:** Credit card, cash, sales tax
- **Aramark Commission:** Total commissionable, commission amount, discount deduction, net commission
- **Niko Payment:** Niko commission, cash deduction, tax addition, total check amount
- **Summary:** Total sales, Aramark gets, Niko gets, CC fees (all with percentages)

**Invoice Details:**
- Automatic invoice number generation (MMDDYY format)
- Week date ranges (Thursday-Wednesday)

### 3. Weekly Trends Comparison
- Commission split visualization (Aramark vs Niko)
- Week-over-week sales growth
- Weekly statistics table
- Discount rate trends

### 4. Day of Week Performance
- Average sales by day of week
- Transaction patterns
- Discount rates by day
- Average ticket size analysis

### 5. Daily Performance Details
- Complete day-by-day breakdown
- Gross vs net sales comparison
- Color-coded discount percentages
- Daily trend charts

### 6. Time Slot Analysis
- 15-minute interval breakdown (9:00 AM - 8:30 PM)
- Peak vs slow period identification
- Transaction heatmaps
- Hourly performance patterns

### 7. Export Options
- Daily sales data (CSV)
- Weekly statistics (CSV)
- Commission details for selected week (CSV)

---

## 💼 Commission Calculation Logic

### Formula Breakdown

```python
# Step 1: Calculate Gross Before Discounts (Accountant's Method)
Gross_Before_Discounts = Gross_After_Discounts + Total_Discounts

# Step 2: Calculate Credit Card Fee
CC_Fee = Credit_Card_Sales × 3%

# Step 3: Calculate Total Commissionable Base
Total_Commissionable = Gross_Before_Discounts - CC_Fee

# Step 4: Calculate Aramark Commission (20%)
Aramark_Commission = Total_Commissionable × 20%
TOTAL_ARA_Commission = Aramark_Commission - Total_Discounts

# Step 5: Calculate Niko Commission (80%)
Niko_Commission = Total_Commissionable × 80%
Total_Check_to_Niko = Niko_Commission - Cash + Sales_Tax

# Note: Cash is always $0 (all credit card transactions)
```

### Why Manual Entry?

**GetApp Credit Card:**
- GetApp export files don't include payment method breakdown
- Manual weekly entry ensures accurate credit card totals

**Sales Tax:**
- Source systems show $0 for tax collected
- Actual tax rate varies by transaction (7.92% - 8.32%)
- Manual entry from POS reports ensures 100% accuracy

---

## 🚀 Deployment

### Prerequisites

- Python 3.11+
- Streamlit Cloud account
- GitHub account

### Local Development

```bash
# Clone repository
git clone https://github.com/patilmayur526/Sodexo-nikos-dashboard.git
cd Sodexo-nikos-dashboard

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run sales_dashboard.py
```

### Production Deployment

Dashboard is automatically deployed to Streamlit Cloud:
- **URL:** https://sodexo-nikos-dashboard-scsujncz7s524kxima4r9m.streamlit.app
- **Auto-deploy:** Enabled (deploys on every push to `main` branch)
- **Python Version:** 3.11

---

## 🔄 Weekly Update Workflow

### Step 1: Generate Combined Data

```bash
# Navigate to Oracle folder
cd ~/Downloads/NIKOS_2026/Sales_data/Oracle_daily_operations/input_excels
python3 combine_daily_operations.py

# Navigate to GetApp folder
cd ~/Downloads/NIKOS_2026/Sales_data/GET_APP_SALES/get_app_input_excels
python3 combine_get_app.py

# Navigate to Combined folder
cd ~/Downloads/NIKOS_2026/Sales_data/Combined_reports
python3 add_two_sources.py
```

### Step 2: Update GitHub

```bash
# Navigate to repository
cd /path/to/Sodexo-nikos-dashboard

# Copy latest combined data
cp ~/Downloads/NIKOS_2026/Sales_data/Combined_reports/combined_sales_data.xlsx .

# Commit and push
git add combined_sales_data.xlsx
git commit -m "Update sales data - Week ending $(date +%m/%d/%Y)"
git push origin main
```

### Step 3: Update Dashboard

1. Wait 1-2 minutes for Streamlit auto-deployment
2. Open dashboard
3. Enter manual values in sidebar:
   - **GetApp CC** for the week
   - **Sales Tax** for the week
4. Verify commission calculations match accountant's spreadsheet
5. Share updated URL with stakeholders

---

## 📋 Requirements

```txt
streamlit==1.31.0
pandas==2.1.4
numpy==1.26.3
plotly==5.18.0
openpyxl==3.1.2
matplotlib==3.8.2
```

---

## 📁 Data Sources

### Oracle Micros Symphony
- **Type:** Daily POS reports
- **Format:** Excel (.xlsx)
- **Location:** `Oracle_daily_operations/input_excels/`
- **Contains:** 
  - Sales transactions
  - Discounts
  - Payment methods (Credit Card, Cash)
  - Time slot data (15-min intervals)

### GetApp Online Ordering
- **Type:** Daily order reports
- **Format:** Excel (.xlsx)
- **Location:** `GET_APP_SALES/get_app_input_excels/`
- **Contains:**
  - Online orders
  - Order totals
  - Pickup/Delivery breakdown
  - Discounts

### Combined Output
- **File:** `combined_sales_data.xlsx`
- **Structure:** One sheet per day (YYYY-MM-DD format)
- **Sections per sheet:**
  1. Date & Day information
  2. Run Financial Control Report (7 metrics)
  3. Payment Summary (Credit Card, Cash, Sales Tax)
  4. Day Part Summary (15-min time slots)

---

## ⚙️ Configuration

### Sales Week Definition
- **Start:** Thursday
- **End:** Wednesday
- Ensures alignment with accounting periods

### Time Slots
- **Interval:** 15 minutes
- **Range:** 9:00 AM - 8:30 PM
- **Total Slots:** 46 per day
- Automatically fills missing slots with zeros

### Commission Rates (Configurable in Sidebar)
- **Aramark Commission:** 20% (adjustable 0-100%)
- **Credit Card Fee:** 3% (adjustable 0-10%)
- **Sales Tax Rate:** 8% (adjustable 0-15%, used for auto-calculation)

---

## 🎨 Features

### Interactive Visualizations
- **Plotly charts** for dynamic exploration
- **Color-coded tables** for quick insights
- **Responsive design** for desktop and mobile

### Real-time Calculations
- Commission splits update instantly
- Week-over-week growth auto-calculated
- Invoice numbers generated on-the-fly

### Data Validation
- Automatic discount rate calculations
- Zero-filling for missing time slots
- Date parsing with multiple format support

---

## 🐛 Troubleshooting

### Common Issues

**Issue:** Dashboard shows "File Not Found"
- **Solution:** Verify `combined_sales_data.xlsx` is in repository root
- Check line 17 in `sales_dashboard.py`: `ROOT = Path(__file__).resolve().parent`

**Issue:** Commission numbers don't match
- **Solution:** Verify manual entries for GetApp CC and Sales Tax are correct
- Check commission rate settings in sidebar

**Issue:** Time slots showing all zeros
- **Solution:** Verify Day Part Summary section exists in source sheets
- Check time format in source files (should be "HH:MM AM/PM")

**Issue:** Old data showing after update
- **Solution:** Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Force app reboot in Streamlit Cloud dashboard

---

## 📈 Performance Metrics

### Dashboard Load Time
- **Initial Load:** ~3-5 seconds
- **Data Refresh:** ~1-2 seconds
- **Chart Rendering:** Real-time

### Data Capacity
- **Supported Weeks:** Unlimited
- **Days per Week:** 7 (Thursday-Wednesday)
- **Time Slots per Day:** 46 (15-min intervals)

---

## 🔐 Security & Privacy

- **Public Dashboard:** No authentication required (suitable for internal sharing)
- **No PII:** Dashboard contains only aggregated sales data
- **Read-Only:** Users cannot modify data through dashboard
- **Version Control:** All changes tracked in GitHub

---

## 🤝 Contributing

This is a private dashboard for Sodexo Nikos operations. For updates or issues:

1. Contact the dashboard administrator
2. Report issues via GitHub Issues
3. Suggest features via GitHub Discussions

---

## 📞 Support

For questions, issues, or feature requests:
- **Repository:** https://github.com/patilmayur526/Sodexo-nikos-dashboard
- **Dashboard URL:** https://sodexo-nikos-dashboard-irc6z7ufvpwflfueknify7.streamlit.app

---

## 📄 License

© 2026 Sodexo Nikos Operations. Internal use only.

---

## 🙏 Acknowledgments

- **Streamlit** - Dashboard framework
- **Plotly** - Interactive visualizations
- **Pandas** - Data processing
- **Anthropic Claude** - Development assistance

---

## 📝 Version History

### v2.0.0 (Current)
- ✅ Manual GetApp CC entry by week
- ✅ Manual Sales Tax entry by week
- ✅ Corrected commission formulas (matches accountant)
- ✅ Cash forced to $0
- ✅ Invoice number generation
- ✅ Improved weekly analysis
- ✅ Enhanced payment breakdown

### v1.0.0
- Initial release
- Basic sales tracking
- Time slot analysis
- Weekly trends

---

**Built with ❤️ for Niko's Sodexo Operations**
