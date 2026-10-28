# 📈 Stock Analyser: Autonomous AI-Powered Financial Intelligence System

**Status:** Active Development | **Architecture:** Multi-Agent Microservices

## 🎯 The Vision
Most trading algorithms rely purely on rigid quantitative metrics or basic technical indicators. **Stock Analyser** is built to bridge the gap between hard mathematics and qualitative market sentiment. It is a comprehensive, automated ecosystem designed for deep financial data ingestion, multi-layered mathematical scoring, and AI-driven decision making.

This project doesn't just output a "buy or sell" signal; it implements a robust **Decision Engine** capable of parsing complex market structures, aggregating sector-wide trends, and leveraging Natural Language Processing (NLP) to read market psychology.

---

## 🏗️ Architectural Excellence

The system is engineered with a strict modular design, decoupling data ingestion, mathematical computation, and AI inference to ensure scalable, fault-tolerant execution.

### **Core Components:**
- **AI Engine (`/ai_engine`):** Houses autonomous agents, including `agent_5_sector_aggregator` and a `decision_engine`. It utilizes dynamic NLP for `news_sentiment_generator` with built-in retry mechanisms for resilient API calls.
- **Math Engine (`/math_engine`):** The quantitative brain of the system. It processes raw data to generate precise `fundamental_segment_scores` and `pattern_scores` to evaluate the true intrinsic value of equities.
- **Data Ingestion Pipeline (`/data_ingestion`):** A multi-faceted ETL layer designed to pull `deep_financials`, `market_daily_data`, `market_historical_data`, and real-time `news_data`. 
- **Core Infrastructure (`/core`):** Features an asynchronous `queue_processor` for handling heavy workloads, a centralized `database` module, and a `MVC_Output_Generator` for clean, structured data presentation.
- **Automated Operations:** Controlled via granular bash scripts (`run_daily.sh`, `run_monthly.sh`) for seamless cron-job integration.

---

## 🧠 Engine Deep Dive: The "Hybrid Approach"
While the system handles massive amounts of historical data, its true power lies in the intersection of its Math and AI engines.

### **Technical Specifics:**
- **Sentiment & Retry Logic:** The `retry_news_sentiment.py` ensures that if an LLM/NLP API throttles during sudden market news spikes, the system queues and re-attempts the analysis without dropping critical qualitative data.
- **Sector Aggregation:** Rather than looking at stocks in a vacuum, `agent_5_sector_aggregator.py` provides macroeconomic context, mapping individual stock performance against broader sector trends.
- **Dynamic Charting:** The `graph_plotter.py` transforms complex, multi-dimensional array outputs into human-readable visual insights, essential for final validation before trade execution.

---

## 🛠️ The Tech Stack

| Layer | Technology / Module focus |
| :--- | :--- |
| **Language** | Python 3.x |
| **Database** | SQL (via `init_schema.sql`), custom `db_utils` |
| **AI/NLP** | Custom Sentiment Analyzers & Agentic Logic |
| **Task Management** | Queue Processor |
| **Data Visualization**| Python Graphing (Matplotlib/Plotly inferred) |
| **Automation** | Bash Shell Scripting (`run.sh` suite) |
| **Config Management** | JSON (`target_stocks.json`) & Python Dictionaries |

---

## 🚀 Deployment & Reproducibility

The system is designed for both local research and server-based scheduled execution. 

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/stock_analyser.git
    cd stock_analyser
    ```

2.  **Database Initialization:**
    Set up your relational database using the provided schema schema:
    ```bash
    psql -U your_user -d stock_db -f init_schema.sql
    ```

3.  **Environment Configuration:**
    Ensure your API keys for financial data providers and LLM integrations are set in your environment. Define your target universe in `app/config/target_stocks.json`.

4.  **Execution Routines:**
    *   **Ad-hoc Run:** `./run.sh`
    *   **Daily Market Update (Cron-friendly):** `./run_daily.sh`
    *   **Deep Monthly Rebalance:** `./run_monthly.sh`

---

## 📈 Engineering Highlights

- **Agentic Architecture:** The use of specific "Agents" (e.g., Agent 5) implies a forward-thinking design where different analytical personas vote or aggregate data for a final consensus.
- **Data-Driven Configuration:** Segment logic and educational terms are decoupled into `segment_dictionary.py` and `educational_dictionary.py`, preventing hard-coded magic numbers in the core logic.
- **Fail-Safe Observability:** Dedicated log tracking (`logs.txt`, `logs_monthly.txt`, `ui_logs.txt`) ensures complete transparency into the ETL and decision-making processes.

---

## 👤 About the Developer
I am a Data Scientist & Software Engineer focused on the intersection of **Algorithmic Finance**, **Quantitative Mathematics**, and **Artificial Intelligence**. I build tools that turn market noise into actionable intelligence.

**Connect with me:** [LinkedIn](https://www.linkedin.com/in/your-profile/) | [Portfolio](https://your-portfolio.com)
