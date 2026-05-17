import streamlit as st
import pandas as pd
import sys
import os
import time

# Import modularized backend engine, configs, and plotters
try:
    from app.config.educational_dictionary import get_educational_context
    from app.config.segment_dictionary import get_segment_context
    from app.core.graph_plotter import generate_radar_chart
    from app.core.MVC_Output_Generator import (
        fetch_market_sentiment_model, 
        fetch_landing_page_model, 
        fetch_static_profile_model, 
        fetch_fundamental_segments_model,
        fetch_calculated_fundamentals_model
    )
    from app.ai_engine.decision_engine import generate_investment_thesis
except ImportError as e:
    st.error(f"Failed to load modules: {e}. Ensure PYTHONPATH is set correctly.")
    sys.exit(1)

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="AI Institutional Dashboard", layout="wide", page_icon="🏦")

# --- CUSTOM CSS ---
custom_css = """
<style>
.stAppDeployButton {display:none;}
div[data-testid="stExpander"] {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: transparent;
    transition: all 0.3s ease-in-out;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
}
div[data-testid="stExpander"]:hover {
    border-color: #00CC96; 
    box-shadow: 2px 2px 15px rgba(0,204,150,0.2);
    transform: translateY(-2px);
}
.segment-value-box {
    padding: 10px;
    margin-bottom: 10px;
    border-radius: 5px;
    background-color: rgba(128, 128, 128, 0.1);
    font-weight: bold;
    display: flex;
    justify-content: space-between;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- SESSION STATE ROUTER ---
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = None

# --- HELPER FORMATTING FUNCTION ---
def get_score_context(score, scale=10):
    if score is None: return "N/A", "gray"
    try:
        val = float(score)
        if scale == 10:
            if val >= 7.5: return "Strong", "#00CC96" 
            elif val >= 4.0: return "Fair", "#FFA15A" 
            else: return "Weak", "#EF553B" 
        else:
            if val >= 70: return "Bullish", "#00CC96"
            elif val >= 40: return "Neutral", "#FFA15A"
            else: return "Bearish", "#EF553B"
    except:
        return "Unknown", "gray"

# --- HELPER: MODAL POPUP FOR MATH ---
@st.dialog("📖 Deep Dive: Math & Theory", width="large")
def show_math_modal(segment_key):
    ctx = get_segment_context(segment_key)
    st.write(f"**Quantitative Theory:** {ctx['theory']}")
    st.divider()
    st.latex(ctx['formula'])
    st.divider()
    st.caption(f"**Engine Mechanics:** {ctx['math_details']}")

# --- UI: REQUEST DIALOG ---
@st.dialog("➕ Request New Stocks")
def request_stock_dialog():
    st.markdown("### Asset Expansion Request")
    st.write("Enter Stock Names or IDs (e.g., RELIANCE, Tata Motors, AAPL)")
    raw_input = st.text_area(
        "Separate multiple entries with commas", 
        placeholder="e.g., NESTLEIND, ASIANPAINT, Google",
        help="System will resolve tickers and backfill data within 4 hours."
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Submit", type="primary"):
            if raw_input.strip():
                try:
                    os.makedirs("data", exist_ok=True)
                    queue_path = os.path.join("data", "request_queue.txt")
                    with open(queue_path, "a", encoding="utf-8") as f:
                        f.write(f"{raw_input.strip()}\n")
                    
                    st.toast("Request Logged Successfully!", icon="✅")
                    # Refined Compact Success Message
                    st.markdown(
                        """
                        <div style="padding:10px; border-radius:5px; background-color:rgba(0,204,150,0.1); 
                        border:1px solid #00CC96; color:#00CC96; font-size:14px; text-align:center; margin:10px 0;">
                        ✅ <b>Request Submitted:</b> Added to the 4-hour background queue.
                        </div>
                        """, unsafe_allow_html=True
                    )
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Write Error: {e}")
            else:
                st.warning("Please enter a name.")
    with col2:
        if st.button("Cancel"):
            st.rerun()

# --- UI: LANDING PAGE ---
def render_landing_page():
    st.title("🌐 Macro Market Overview")
    
    market_score = fetch_market_sentiment_model()
    if market_score:
        mood = "Bullish 📈" if market_score >= 60 else "Bearish 📉" if market_score <= 40 else "Neutral ⚖️"
        label, color = get_score_context(market_score, 100)
        st.markdown(f"### Overall Market Sentiment: <span style='color:{color}'>{market_score}/100 ({mood})</span>", unsafe_allow_html=True)

    st.divider()
    
    col_db, col_req = st.columns([3, 1])
    with col_db:
        st.subheader("Equities Database")
    with col_req:
        st.write("") 
        if st.button("➕ Request More Stocks", use_container_width=True):
            request_stock_dialog()
    
    df = fetch_landing_page_model()
    if df is None or df.empty:
        st.info("No stocks found in the database. Please run the ingestion pipeline.")
        return

    def color_performance(val):
        color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
        return f'color: {color}; font-weight: bold;'
    
    styled_df = df.style.format({
        "Fundamental Score": "{:.1f}",
        "Pattern Score": "{:.1f}",
        "Last Price (₹)": "{:.2f}",
        "Daily Change (Pct)": "{:.2f}"
    }).map(color_performance, subset=['Daily Change (Pct)'])
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.markdown("### 🔍 Analyze a Specific Stock")
    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.selectbox("Select a stock to open its Deep Dive Profile:", options=df['Stock'].tolist())
    with col2:
        st.write("") 
        st.write("") 
        if st.button("Open Deep Dive", use_container_width=True, type="primary"):
            st.session_state.selected_stock = selected
            st.rerun()

# --- UI: DETAIL PAGE ---
def render_detail_page():
    stock = st.session_state.selected_stock
    
    if st.button("← Back to Market Overview"):
        st.session_state.selected_stock = None
        st.rerun()

    profile = fetch_static_profile_model(stock)
    if not profile:
        st.error(f"Profile data not found for {stock}.")
        return

    st.title(f"{profile.get('company_name', stock)} ({stock})")
    st.caption(f"{profile.get('sector', 'Unknown Sector')} | {profile.get('industry', 'Unknown Industry')} | [Website]({profile.get('website', '#')})")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 About", "📊 Fundamentals", "📰 News & Sentiment", "🧠 AI Verdict"])
    
    with tab1:
        st.subheader("Company Overview")
        st.write(profile.get('description', 'No detailed description available.'))

    with tab2:
        st.subheader("Interactive Fundamental Weighting")
        segments = fetch_fundamental_segments_model(stock)
        if segments:
            val_score, prof_score, solv_score, mom_score, cap_score = [
                float(segments.get(k, 0)) for k in [
                    'valuation_score', 'profitability_score', 'solvency_score', 
                    'momentum_score', 'capital_efficiency_score'
                ]
            ]
            
            st.markdown("**Adjust Segment Relative Importance (0-10):**")
            wc = st.columns(5)
            weights = []
            for i, label in enumerate(['Valuation', 'Profitability', 'Solvency', 'Momentum', 'Cap Efficiency']):
                weights.append(wc[i].slider(label, 0, 10, 5, key=f"w_{i}", label_visibility="collapsed"))
                
            total_weight = sum(weights) if sum(weights) > 0 else 1
            custom_score = sum([s * w for s, w in zip([val_score, prof_score, solv_score, mom_score, cap_score], weights)]) / total_weight
            
            label, color = get_score_context(custom_score, 10)
            st.markdown(f"#### Your Custom Weighted Score: <span style='color:{color}'>{custom_score:.1f}/10 ({label})</span>", unsafe_allow_html=True)
            
            st.divider()
            scores = [val_score, prof_score, solv_score, mom_score, cap_score]
            graph_col, values_col = st.columns([2, 1])
            with graph_col:
                st.plotly_chart(generate_radar_chart(scores, color), use_container_width=True)
            with values_col:
                st.markdown("#### Segment Output")
                for cat, s in zip(['Valuation', 'Profitability', 'Solvency', 'Momentum', 'Cap Efficiency'], scores):
                    _, sc_color = get_score_context(s, 10)
                    st.markdown(f"<div class='segment-value-box'><span>{cat}</span><span style='color:{sc_color};'>{s:.1f} / 10</span></div>", unsafe_allow_html=True)

    with tab3:
        st.subheader(f"📰 Recent News & AI Sentiment for {stock}")
        news_file = os.path.join("data", stock, "news", "news_score.csv")
        if os.path.exists(news_file):
            try:
                df_news = pd.read_csv(news_file)
                if not df_news.empty:
                    latest = df_news.iloc[-1]['score']
                    _, sc_color = get_score_context(latest, 100)
                    st.metric("Latest Aggregated Sentiment", f"{latest}/100")
                    st.divider()
                    for _, row in df_news.sort_values(by='capture_date', ascending=False).iterrows():
                        with st.container(border=True):
                            st.markdown(f"**📅 {row['news_date']}** | Sector: `{row['sector']}`")
                            st.write(row['overview'])
                else: st.info("News file is empty.")
            except Exception as e: st.error(f"CSV Read Error: {e}")
        else: st.warning("No news data found.")

    with tab4:
        st.subheader("🧠 AI Quantitative Verdict")
        with st.form("decision_engine_form"):
            risk = st.selectbox("Risk Tolerance", ["Conservative", "Moderate", "Aggressive"])
            horizon = st.selectbox("Investment Horizon", ["Day Trader", "Swing Trader", "Long-term"])
            if st.form_submit_button("Generate Institutional Thesis", type="primary"):
                with st.spinner("AI is synthesizing data..."):
                    result = generate_investment_thesis(stock, risk, horizon)
                    rec = result.get('recommendation', 'HOLD')
                    rec_color = "#00CC96" if rec == "BUY" else "#EF553B" if rec == "SELL" else "#FFA15A"
                    st.markdown(f"### Recommendation: <span style='color:{rec_color}'>{rec}</span>", unsafe_allow_html=True)
                    st.progress(result.get('final_actionable_score', 0)/100, text=f"Confidence: {result.get('final_actionable_score', 0)}/100")
                    st.info(f"**Thesis:** {result.get('thesis', 'N/A')}")

# --- MAIN EXECUTION ---
if st.session_state.selected_stock is None:
    render_landing_page()
else:
    render_detail_page()