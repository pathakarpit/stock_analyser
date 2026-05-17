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

echo "[1/4] INGESTION PHASE (Sequential)..."
python -m app.data_ingestion.market_daily_data
python -m app.data_ingestion.news_data
python -m app.data_ingestion.fundamental_data
echo "✅ Ingestion Complete: $(date)"

echo "[2/4] FUNDAMENTALS PHASE (Sequential)..."
python -m app.math_engine.calc_fundamentals
python -m app.math_engine.fundamental_segment_score_generator
python -m app.math_engine.pattern_score_generator
python -m app.math_engine.overall_fundamental_score_generator
echo "✅ Fundamentals Complete: $(date)"

echo "[3/4] SENTIMENT PHASE..."
python -m app.ai_engine.news_sentiment_generator
python -m app.math_engine.agent4_aggregator
python -m app.ai_engine.agent_5_sector_aggregator
echo "✅ Sentiment Complete: $(date)"

echo "[4/4] DECISION ENGINE (Master Analyst)..."
python -m app.ai_engine.decision_engine
echo "✅ Decision Engine Complete: $(date)"

echo "====================================================="
echo "🏁 DAILY PIPELINE COMPLETE: $(date)"
echo "====================================================="