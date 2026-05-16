#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

# 1. Strict Path Definitions
PROJECT_DIR="/home/sunny/workspace/project_stock_analyser"
CONDA_DIR="/home/sunny/miniconda3"

# 2. Configure Dual Logging (Terminal + File Overwrite)
LOG_FILE="$PROJECT_DIR/logs.txt"
exec > >(tee "$LOG_FILE") 2>&1

# 3. CRITICAL: Force Python to print immediately without buffering
export PYTHONUNBUFFERED=1

echo "====================================================="
echo "FILE: $(basename "$0")"
echo "RUN INITIATED: $(date)"
echo "====================================================="

# 4. Initialize Conda and activate environment
source "$CONDA_DIR/etc/profile.d/conda.sh"
conda activate stock_analyser

# 5. Navigate to project and set Python path
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR"

echo "[1/2] Fetching Raw Accounting CSVs (Sequential)..."
# Pulls the deep fundamental data like Balance Sheets, Income Statements, etc.
python -m app.data_ingestion.deep_financials
echo "✅ Deep Financials Complete: $(date)"

echo "[2/2] Syncing Static Company Profiles (Sequential)..."
# Updates static company info, sector tags, and descriptions
python -m app.data_ingestion.static_company_profiles
echo "✅ Company Profiles Complete: $(date)"

echo "====================================================="
echo "🏁 MONTHLY PIPELINE COMPLETE: $(date)"
echo "====================================================="