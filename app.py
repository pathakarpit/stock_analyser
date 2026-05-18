import streamlit as st
import pandas as pd
import sys
import os
import time

# --- MODULE IMPORT BRIDGE ---
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
    st.error(f"Mapping Error: {e}. Ensure the app is run from the project root.")
    sys.exit(1)

# --- PAGE SETTINGS ---
st.set_page_config(page_title="AI Institutional Dashboard", layout="wide", page_icon="🏦")

# --- GLOBAL STYLING ---
st.markdown("""
<style>
    .stAppDeployButton {display:none;}
    div[data-testid="stExpander"] {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
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
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = None

# --- HELPER FUNCTIONS ---
def get_score_context(score, scale=10):
    if score is None or pd.isna(score): return "N/A", "gray"
    val = float(score)
    if scale == 10:
        if val >= 7.5: return "Strong", "#00CC96" 
        elif val >= 4.0: return "Fair", "#FFA15A" 
        else: return "Weak", "#EF553B" 
    else:
        if val >= 70: return "Bullish", "#00CC96"
        elif val >= 40: return "Neutral", "#FFA15A"
        else: return "Bearish", "#EF553B"

@st.dialog("📖 Deep Dive: Math & Theory", width="large")
def show_math_modal(segment_key):
    ctx = get_segment_context(segment_key)
    st.write(f"**Quantitative Theory:** {ctx['theory']}")
    st.divider()
    st.latex(ctx['formula'])
    st.divider()
    st.caption(f"**Engine Mechanics:** {ctx['math_details']}")

@st.dialog("➕ Request New Stocks")
def request_stock_dialog():
    st.markdown("### Asset Expansion Request")
    raw_input = st.text_area("Enter Stock Names/IDs (separated by commas)", placeholder="RELIANCE, AAPL, HDFC...")
    if st.button("Submit Request", type="primary"):
        if raw_input.strip():
            try:
                os.makedirs("data", exist_ok=True)
                queue_path = os.path.join("data", "request_queue.txt")
                with open(queue_path, "a", encoding="utf-8") as f:
                    f.write(f"{raw_input.strip()}\n")
                st.toast("Request Logged", icon="✅")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# --- PAGE 1: LANDING ---
def render_landing_page():
    st.title("🌐 Macro Market Overview")
    
    m_score = fetch_market_sentiment_model()
    if m_score:
        mood = "Bullish 📈" if m_score >= 60 else "Bearish 📉" if m_score <= 40 else "Neutral ⚖️"
        _, color = get_score_context(m_score, 100)
        st.markdown(f"### Overall Market Sentiment: <span style='color:{color}'>{m_score}/100 ({mood})</span>", unsafe_allow_html=True)

    st.divider()
    
    col_db, col_req = st.columns([3, 1])
    with col_db: st.subheader("Equities Database")
    with col_req:
        if st.button("➕ Request More Stocks", use_container_width=True):
            request_stock_dialog()
    
    df = fetch_landing_page_model()
    if df is None or df.empty:
        st.info("No data available. Run the ingestion pipeline.")
        return

    # --- DYNAMIC COLUMN MAPPING ---
    # Find the ticker column (likely 'Stock' or 'stock_id')
    ticker_col = 'Stock' if 'Stock' in df.columns else 'stock_id' if 'stock_id' in df.columns else None
    
    if ticker_col:
        # Rename internal column to Ticker for display consistency
        df = df.rename(columns={ticker_col: 'Ticker'})
    else:
        st.error("Data integrity error: Ticker column not found in database results.")
        return

    # Rename Company Name if exists
    if 'company_name' in df.columns:
        df = df.rename(columns={'company_name': 'Company Name'})
        # Reorder: Name, then Ticker, then others
        cols = ['Company Name', 'Ticker'] + [c for c in df.columns if c not in ['Company Name', 'Ticker']]
        df = df[cols]

    # Sanitize Numeric Columns
    num_cols = ["Fundamental Score", "Pattern Score", "Last Price (₹)", "Daily Change (Pct)"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    def color_performance(val):
        color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
        return f'color: {color}; font-weight: bold;'
    
    styled_df = df.style.format({
        "Fundamental Score": "{:.2f}",
        "Pattern Score": "{:.2f}",
        "Last Price (₹)": "{:.2f}",
        "Daily Change (Pct)": "{:.2f}"
    }).map(color_performance, subset=['Daily Change (Pct)'])
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.markdown("### 🔍 Analyze a Specific Stock")
    sel_col, btn_col = st.columns([3, 1])
    with sel_col:
        selected = st.selectbox("Search for ticker:", options=df['Ticker'].tolist())
    with btn_col:
        st.write("") ; st.write("")
        if st.button("Open Deep Dive", use_container_width=True, type="primary"):
            st.session_state.selected_stock = selected
            st.rerun()

# --- PAGE 2: DETAIL ---
def render_detail_page():
    stock = st.session_state.selected_stock
    if st.button("← Back to Overview"):
        st.session_state.selected_stock = None
        st.rerun()

    profile = fetch_static_profile_model(stock)
    if not profile:
        st.error(f"Data not found for {stock}.")
        return

    st.title(f"{profile.get('company_name', stock)} ({stock})")
    st.caption(f"{profile.get('sector', 'N/A')} | {profile.get('industry', 'N/A')} | [Website]({profile.get('website', '#')})")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 About", "📊 Fundamentals", "📰 News", "🧠 AI Verdict"])
    
    with tab1:
        st.subheader("Company Overview")
        st.write(profile.get('description', 'No description available.'))

    with tab2:
        st.subheader("Fundamental Weighting")
        segments = fetch_fundamental_segments_model(stock)
        if segments:
            scores = [float(segments.get(k, 0)) for k in ['valuation_score', 'profitability_score', 'solvency_score', 'momentum_score', 'capital_efficiency_score']]
            wc = st.columns(5)
            w_keys = ["valuation", "profitability", "solvency", "momentum", "capital_efficiency"]
            weights = []
            for i, label in enumerate(['Valuation', 'Profitability', 'Solvency', 'Momentum', 'Efficiency']):
                with wc[i]:
                    w = st.slider(label, 0, 10, 5, key=f"w_{i}", label_visibility="collapsed")
                    weights.append(w)
                    if st.button(f"📖 {label}", key=f"btn_{i}", use_container_width=True):
                        show_math_modal(w_keys[i])
            
            total_w = sum(weights) if sum(weights) > 0 else 1
            custom_score = sum([s * w for s, w in zip(scores, weights)]) / total_w
            label, color = get_score_context(custom_score, 10)
            st.markdown(f"#### Weighted Score: <span style='color:{color}'>{custom_score:.1f}/10 ({label})</span>", unsafe_allow_html=True)
            
            st.divider()
            g_col, v_col = st.columns([2, 1])
            with g_col: st.plotly_chart(generate_radar_chart(scores, color), use_container_width=True)
            with v_col:
                for cat, s in zip(['Valuation', 'Profitability', 'Solvency', 'Momentum', 'Efficiency'], scores):
                    _, sc_color = get_score_context(s, 10)
                    st.markdown(f"<div class='segment-value-box'><span>{cat}</span><span style='color:{sc_color};'>{s:.1f} / 10</span></div>", unsafe_allow_html=True)

        # Raw Metrics Cards
        st.divider()
        st.subheader("Raw Quantitative Metrics")
        calc_data = fetch_calculated_fundamentals_model(stock)
        if calc_data:
            clean_calc = {k: v for k, v in calc_data.items() if k not in ['stock_id', 'date', 'id']}
            cols = st.columns(3) 
            for i, (key, val) in enumerate(clean_calc.items()):
                display_val = round(val, 2) if isinstance(val, (int, float)) else val
                edu = get_educational_context(key)
                with cols[i % 3]:
                    if edu:
                        with st.expander(f"**{edu['title']}** : {display_val}"):
                            st.write(f"**Def:** {edu['def']}")
                            st.write(f"**Interp:** {edu['interp']}")
                    else: st.metric(label=key.replace('_', ' ').title(), value=display_val)

    with tab3:
        st.subheader("Recent News Sentiment")
        n_file = os.path.join("data", stock, "news", "news_score.csv")
        if os.path.exists(n_file):
            df_n = pd.read_csv(n_file)
            if not df_n.empty:
                latest = df_n.iloc[-1]['score']
                _, sc_c = get_score_context(latest, 100)
                st.metric("Latest Sentiment", f"{latest}/100")
                st.divider()
                for _, row in df_n.sort_values(by='capture_date', ascending=False).iterrows():
                    with st.container(border=True):
                        st.markdown(f"**📅 {row['news_date']}** | Sector: `{row['sector']}`")
                        st.write(row['overview'])

    with tab4:
        st.subheader("🧠 AI Quantitative Verdict")
        with st.form("verdict_form"):
            risk = st.selectbox("Risk Tolerance", ["Conservative", "Moderate", "Aggressive"])
            horiz = st.selectbox("Investment Horizon", ["Day Trader", "Swing Trader", "Long-term"])
            if st.form_submit_button("Generate Thesis", type="primary"):
                with st.spinner("Synthesizing..."):
                    res = generate_investment_thesis(stock, risk, horiz)
                    rec = res.get('recommendation', 'HOLD')
                    rec_c = "#00CC96" if rec == "BUY" else "#EF553B" if rec == "SELL" else "#FFA15A"
                    st.markdown(f"### Recommendation: <span style='color:{rec_c}'>{rec}</span>", unsafe_allow_html=True)
                    st.progress(res.get('final_actionable_score', 0)/100, text=f"Confidence: {res.get('final_actionable_score', 0)}/100")
                    st.info(f"**Thesis:** {res.get('thesis', 'N/A')}")

# --- EXECUTION ---
if st.session_state.selected_stock is None:
    render_landing_page()
else:
    render_detail_page()