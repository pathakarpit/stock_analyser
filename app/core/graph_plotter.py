# app/core/graph_plotter.py
import plotly.graph_objects as go

def generate_radar_chart(scores, chart_color):
    """
    Generates a clean, visually distinct interactive radar chart.
    Raw text values are removed to prevent visual clutter.
    """
    categories = ['Valuation', 'Profitability', 'Solvency', 'Momentum', 'Cap Efficiency']
    
    fig = go.Figure(data=go.Scatterpolar(
        r=scores + [scores[0]], 
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor=chart_color,
        opacity=0.6, 
        line=dict(color=chart_color, width=3),
        mode='lines+markers', # Text removed to keep the web clean
        marker=dict(size=8, color=chart_color),
        hoverinfo="theta+r" # Interactive tooltips remain
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, 
                range=[0, 10],
                showticklabels=False, 
                gridcolor="rgba(128, 128, 128, 0.2)", 
                linecolor="rgba(128, 128, 128, 0.2)"
            ),
            angularaxis=dict(
                tickfont=dict(size=14, weight="bold"), 
                gridcolor="rgba(128, 128, 128, 0.2)",
                linecolor="rgba(128, 128, 128, 0.2)"
            )
        ),
        showlegend=False,
        height=350, 
        margin=dict(l=60, r=60, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig