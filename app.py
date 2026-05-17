import streamlit as st
import pandas as pd
import sys
import os

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

# --- UI: LANDING PAGE ---
def render_landing_page():
    st.title("🌐 Macro Market Overview")
    
    market_score = fetch_market_sentiment_model()
    if market_score:
        mood = "Bullish 📈" if market_score >= 60 else "Bearish 📉" if market_score <= 40 else "Neutral ⚖️"
        label, color = get_score_context(market_score, 100)
        st.markdown(f"### Overall Market Sentiment: <span style='color:{color}'>{market_score}/100 ({mood})</span>", unsafe_allow_html=True)

    st.divider()
    st.subheader("Equities Database")
    
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
    
    # --- TAB 1: ABOUT ---
    with tab1:
        st.subheader("Company Overview")
        st.write(profile.get('description', 'No detailed description available in the database.'))

    # --- TAB 2: FUNDAMENTALS ---
    with tab2:
        st.subheader("Interactive Fundamental Weighting")
        segments = fetch_fundamental_segments_model(stock)
        
        if segments:
            val_score = float(segments.get('valuation_score', 0))
            prof_score = float(segments.get('profitability_score', 0))
            solv_score = float(segments.get('solvency_score', 0))
            mom_score = float(segments.get('momentum_score', 0))
            cap_score = float(segments.get('capital_efficiency_score', 0))
            
            st.markdown("**Adjust Segment Relative Importance (0-10):**")
            wc1, wc2, wc3, wc4, wc5 = st.columns(5)
            
            with wc1: w_val = st.slider("Valuation", 0, 10, 5, key="w_val", label_visibility="collapsed")
            with wc2: w_prof = st.slider("Profitability", 0, 10, 5, key="w_prof", label_visibility="collapsed")
            with wc3: w_solv = st.slider("Solvency", 0, 10, 5, key="w_solv", label_visibility="collapsed")
            with wc4: w_mom = st.slider("Momentum", 0, 10, 5, key="w_mom", label_visibility="collapsed")
            with wc5: w_cap = st.slider("Cap Efficiency", 0, 10, 5, key="w_cap", label_visibility="collapsed")
                
            total_weight = w_val + w_prof + w_solv + w_mom + w_cap
            if total_weight == 0: total_weight = 1
                
            pct_val, pct_prof, pct_solv, pct_mom, pct_cap = [(w / total_weight) * 100 for w in [w_val, w_prof, w_solv, w_mom, w_cap]]

            with wc1: 
                if st.button("📖 Valuation", key="btn_val", use_container_width=True): show_math_modal("valuation")
                st.caption(f"**Weight: {pct_val:.1f}%**")
            with wc2: 
                if st.button("📖 Profitability", key="btn_prof", use_container_width=True): show_math_modal("profitability")
                st.caption(f"**Weight: {pct_prof:.1f}%**")
            with wc3: 
                if st.button("📖 Solvency", key="btn_solv", use_container_width=True): show_math_modal("solvency")
                st.caption(f"**Weight: {pct_solv:.1f}%**")
            with wc4: 
                if st.button("📖 Momentum", key="btn_mom", use_container_width=True): show_math_modal("momentum")
                st.caption(f"**Weight: {pct_mom:.1f}%**")
            with wc5: 
                if st.button("📖 Cap Efficiency", key="btn_cap", use_container_width=True): show_math_modal("capital_efficiency")
                st.caption(f"**Weight: {pct_cap:.1f}%**")
            
            custom_score = ((val_score * w_val) + (prof_score * w_prof) + (solv_score * w_solv) + (mom_score * w_mom) + (cap_score * w_cap)) / total_weight 
            label, color = get_score_context(custom_score, 10)
            st.markdown(f"#### Your Custom Weighted Score: <span style='color:{color}'>{custom_score:.1f}/10 ({label})</span>", unsafe_allow_html=True)
            st.divider()

            scores = [val_score, prof_score, solv_score, mom_score, cap_score]
            _, chart_color = get_score_context(sum(scores)/len(scores), 10)
            graph_col, values_col = st.columns([2, 1])
            
            with graph_col:
                fig = generate_radar_chart(scores, chart_color)
                st.plotly_chart(fig, use_container_width=True)
            with values_col:
                st.markdown("#### Segment Output")
                for cat, s in zip(['Valuation', 'Profitability', 'Solvency', 'Momentum', 'Cap Efficiency'], scores):
                    _, sc = get_score_context(s, 10)
                    st.markdown(f"<div class='segment-value-box'><span>{cat}</span><span style='color:{sc};'>{s:.1f} / 10</span></div>", unsafe_allow_html=True)
        else:
            st.warning("Fundamental segment data missing.")

        st.divider()
        st.subheader("Raw Calculated Metrics")
        calc_data = fetch_calculated_fundamentals_model(stock)
        if calc_data:
            clean_calc = {k: v for k, v in calc_data.items() if k not in ['stock_id', 'date', 'id']}
            cols = st.columns(3) 
            for i, (key, val) in enumerate(clean_calc.items()):
                display_val = round(val, 2) if isinstance(val, (int, float)) else val
                edu_data = get_educational_context(key)
                with cols[i % 3]:
                    if edu_data:
                        with st.expander(f"**{edu_data['title']}** : {display_val}"):
                            st.markdown(f"**Definition:** {edu_data['def']}")
                            st.markdown(f"**Interpretation:** {edu_data['interp']}")
                    else:
                        st.metric(label=key.replace('_', ' ').title(), value=display_val)

    # --- TAB 3: NEWS (REFACTORED FOR CSV) ---
    with tab3:
        st.subheader(f"📰 Recent News & AI Sentiment for {stock}")
        news_file = os.path.join("data", stock, "news", "news_score.csv")
        
        if os.path.exists(news_file):
            try:
                df_news = pd.read_csv(news_file)
                if not df_news.empty:
                    latest_score = df_news.iloc[-1]['score']
                    label, color = get_score_context(latest_score, 100)
                    st.metric(label="Latest Aggregated Sentiment", value=f"{latest_score}/100", delta=label)
                    
                    st.divider()
                    st.markdown("### Historical News events")
                    df_display = df_news.sort_values(by='capture_date', ascending=False)
                    for _, row in df_display.iterrows():
                        with st.container(border=True):
                            sc = row['score']
                            _, sc_color = get_score_context(sc, 100)
                            st.markdown(f"**📅 {row['news_date']}** | Sector: `{row['sector']}` | Score: <span style='color:{sc_color}; font-weight:bold'>{sc}</span>", unsafe_allow_html=True)
                            st.write(row['overview'])
                else:
                    st.info("News file is empty.")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning(f"No localized news data found at {news_file}.")

    # --- TAB 4: AI VERDICT ---
    with tab4:
        st.subheader("🧠 AI Quantitative Verdict")
        with st.form("decision_engine_form"):
            risk = st.selectbox("Risk Tolerance", ["Conservative", "Moderate", "Aggressive"])
            horizon = st.selectbox("Investment Horizon", ["Day Trader", "Swing Trader", "Long-term"])
            submitted = st.form_submit_button("Generate Institutional Thesis", type="primary")
            
            if submitted:
                with st.spinner("AI is synthesizing data..."):
                    result = generate_investment_thesis(stock, risk, horizon)
                    st.divider()
                    rec = result.get('recommendation', 'ERROR')
                    rec_color = "#00CC96" if rec == "BUY" else "#EF553B" if rec == "SELL" else "#FFA15A"
                    st.markdown(f"### Recommendation: <span style='color:{rec_color}'>{rec}</span>", unsafe_allow_html=True)
                    st.progress(result.get('final_actionable_score', 0) / 100, text=f"Confidence Score: {result.get('final_actionable_score', 0)}/100")
                    st.info(f"**Thesis:** {result.get('thesis', 'No thesis generated.')}")

# --- MAIN EXECUTION ---
if st.session_state.selected_stock is None:
    render_landing_page()
else:
    render_detail_page()