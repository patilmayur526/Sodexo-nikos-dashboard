# GitHub & Streamlit Cloud Deployment Guide 🚀

## 📋 Prerequisites

1. GitHub account: https://github.com/patilmayur526
2. Streamlit Cloud account: https://streamlit.io/cloud (sign in with GitHub)
3. Git installed on your Mac

---

## 🗑️ Step 1: Clean Your GitHub Repository

### Remove old files from your repository:

```bash
# Navigate to your repository
cd /path/to/Sodexo-nikos-dashboard

# Remove old files
git rm *.py  # Remove old Python scripts
git rm *.xlsx  # Remove old Excel files (if any)
git rm *.csv  # Remove old CSV files (if any)

# Commit the removal
git commit -m "Clean repository - remove old files"
git push origin main
```

---

## 📤 Step 2: Add New Dashboard Files

### 1. Copy files to your repository folder:

```bash
# Navigate to your repository
cd /path/to/local/Sodexo-nikos-dashboard

# Copy the new files
cp /Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/Combined_reports/code/sales_dashboard.py .
cp /Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/Combined_reports/code/combine_sources.py .
cp /Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/Combined_reports/combined_sales_data.xlsx .

# Copy configuration files (download these from the files I provided)
cp /path/to/downloads/requirements.txt .
cp /path/to/downloads/README.md .
cp /path/to/downloads/.gitignore .
```

### 2. Update the file paths in `combine_sources.py`:

Edit lines 12-14 to point to YOUR local source files:
```python
DAILY_REPORTS_PATH = Path("/Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/Oracle_daily_operations/input_excels/combined_daily_operations.xlsx")
GET_APP_PATH = Path("/Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/GET_APP_SALES/get_app_input_excels/combined_get_app_sales.xlsx")
OUTPUT_PATH = Path("/Users/mayurpatil/path/to/Sodexo-nikos-dashboard/combined_sales_data.xlsx")
```

### 3. Update the file path in `sales_dashboard.py`:

The dashboard should work as-is, but verify line 22:
```python
ROOT = Path(__file__).resolve().parent
DEFAULT_FILE = ROOT / "combined_sales_data.xlsx"
```

This will work in both local and Streamlit Cloud environments.

---

## 📝 Step 3: Commit and Push to GitHub

```bash
# Check what's being added
git status

# Add all new files
git add .

# Commit
git commit -m "Add sales dashboard with weekly analysis and USD currency"

# Push to GitHub
git push origin main
```

---

## ☁️ Step 4: Deploy to Streamlit Cloud

### 1. Go to Streamlit Cloud:
- Visit: https://share.streamlit.io/
- Click "Sign in" (use your GitHub account)

### 2. Create New App:
- Click "New app" button
- Repository: `patilmayur526/Sodexo-nikos-dashboard`
- Branch: `main`
- Main file path: `sales_dashboard.py`
- Click "Deploy!"

### 3. Wait for deployment (2-3 minutes)
- Streamlit will install dependencies
- Build the app
- Provide a public URL

### 4. Get your URL:
- Format: `https://[your-app-name].streamlit.app`
- Example: `https://sodexo-nikos-dashboard.streamlit.app`

---

## 🔄 Step 5: Weekly Update Workflow

### Every week (or when you want to update data):

```bash
# 1. Run the data combination script
cd /Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/Combined_reports/code
python3 combine_sources.py

# 2. Copy updated file to your repository
cp /Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/Combined_reports/combined_sales_data.xlsx \
   /path/to/Sodexo-nikos-dashboard/

# 3. Navigate to repository
cd /path/to/Sodexo-nikos-dashboard

# 4. Commit and push
git add combined_sales_data.xlsx
git commit -m "Update sales data - $(date +%Y-%m-%d)"
git push origin main
```

**That's it!** Streamlit Cloud will automatically detect the change and redeploy (takes 1-2 minutes).

---

## 🎯 Step 6: Share with Your Boss

### Send this email:

```
Subject: Sales Dashboard - Real-time Access

Hi [Boss Name],

I've created a real-time sales dashboard for our weekly performance analysis.

🔗 Dashboard Link: https://[your-app-name].streamlit.app

Features:
✅ Weekly sales trends (Thursday-Wednesday)
✅ Day-of-week performance analysis
✅ Gross sales, discounts, and net sales tracking
✅ Time slot analysis (hourly breakdown)
✅ Week-over-week growth metrics

The dashboard updates automatically every week with the latest data. 
No login required - just click the link!

Let me know if you have any questions or need additional metrics.

Best regards,
Mayur
```

---

## 🛠️ Troubleshooting

### Issue: "App not deploying"
**Solution:** Check the logs in Streamlit Cloud dashboard. Common issues:
- Wrong file path in `sales_dashboard.py`
- Missing dependencies in `requirements.txt`
- Python version mismatch

### Issue: "File not found" error
**Solution:** Make sure `combined_sales_data.xlsx` is committed to GitHub:
```bash
git add combined_sales_data.xlsx
git commit -m "Add data file"
git push origin main
```

### Issue: "Module not found"
**Solution:** Add missing package to `requirements.txt`:
```bash
echo "package_name==version" >> requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push origin main
```

### Issue: Dashboard shows old data
**Solution:** 
1. Verify file was pushed: Check GitHub repository
2. Force redeploy: Go to Streamlit Cloud → Settings → Reboot app
3. Clear cache: In the app, click "⋮" menu → "Clear cache" → "Rerun"

---

## 🔐 Optional: Make Repository Private

If you want to keep the code private but dashboard public:

1. Go to GitHub repository settings
2. Scroll to "Danger Zone"
3. Click "Change visibility"
4. Select "Private"
5. Streamlit Cloud will still have access

**Note:** The dashboard URL remains public even with a private repo.

---

## 📊 Advanced: Custom Domain (Optional)

If you want a custom URL like `sales.nikos.com`:

1. Buy domain (GoDaddy, Namecheap, etc.)
2. In Streamlit Cloud settings, add custom domain
3. Update DNS records as instructed
4. Wait for DNS propagation (24-48 hours)

---

## ✅ Checklist

- [ ] Clean old files from GitHub repository
- [ ] Add new dashboard files
- [ ] Update file paths in scripts
- [ ] Test locally: `streamlit run sales_dashboard.py`
- [ ] Push to GitHub
- [ ] Deploy to Streamlit Cloud
- [ ] Test live dashboard URL
- [ ] Share URL with boss
- [ ] Set up weekly update routine

---

## 📞 Support

**Streamlit Documentation:** https://docs.streamlit.io/  
**GitHub Help:** https://docs.github.com/

**For questions, check:**
- Streamlit Community Forum: https://discuss.streamlit.io/
- GitHub Issues in your repository

---

**Ready to go live!** 🚀

Follow the steps above and your boss will have real-time access to the dashboard within 30 minutes!
