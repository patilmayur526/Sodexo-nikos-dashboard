#!/bin/bash

# Weekly Sales Dashboard Update Script
# Run this script every week to update the dashboard with latest data

echo "🔄 Starting weekly sales dashboard update..."
echo ""

# Configuration - UPDATE THESE PATHS
COMBINE_SCRIPT="/Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/Combined_reports/code/combine_sources.py"
OUTPUT_FILE="/Users/mayurpatil/Downloads/NIKOS_2026/Sales_data/Combined_reports/combined_sales_data.xlsx"
REPO_DIR="/path/to/your/Sodexo-nikos-dashboard"  # UPDATE THIS!

# Step 1: Run data combination
echo "📊 Step 1: Combining data from Oracle and GetApp..."
python3 "$COMBINE_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Error: Data combination failed!"
    exit 1
fi

echo "✅ Data combined successfully!"
echo ""

# Step 2: Copy to repository
echo "📁 Step 2: Copying updated file to repository..."
cp "$OUTPUT_FILE" "$REPO_DIR/"

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to copy file to repository!"
    exit 1
fi

echo "✅ File copied successfully!"
echo ""

# Step 3: Git operations
echo "📤 Step 3: Committing and pushing to GitHub..."
cd "$REPO_DIR"

git add combined_sales_data.xlsx

# Create commit message with current date
COMMIT_MSG="Update sales data - $(date '+%Y-%m-%d')"
git commit -m "$COMMIT_MSG"

if [ $? -ne 0 ]; then
    echo "⚠️  Warning: No changes to commit (data might be the same)"
else
    echo "✅ Changes committed!"
fi

git push origin main

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push to GitHub!"
    exit 1
fi

echo "✅ Pushed to GitHub successfully!"
echo ""
echo "🎉 Dashboard update complete!"
echo ""
echo "Streamlit Cloud will auto-deploy in 1-2 minutes."
echo "Dashboard URL: https://[your-app-name].streamlit.app"
echo ""
