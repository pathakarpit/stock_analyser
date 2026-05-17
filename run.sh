#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

# 1. Strict Path Definitions
PROJECT_DIR="/home/sunny/workspace/project_stock_analyser"
CONDA_DIR="/home/sunny/miniconda3"

echo "====================================================="
echo "🚀 Booting AI Institutional Dashboard (Streamlit)..."
echo "====================================================="

# 2. Initialize Conda and activate environment
# This is required so bash knows how to use the 'conda activate' command
source "$CONDA_DIR/etc/profile.d/conda.sh"
conda activate stock_analyser

# 3. Navigate to project and set Python path
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR"

# 4. Launch the Application in the Background (Detached)
echo "Starting web server in background mode..."
nohup streamlit run app.py --server.port=8501 > ui_logs.txt 2>&1 &
echo "✅ Dashboard is live! You can now close this terminal."