import streamlit as st


def inject_custom_css():
    """
    "Futuristic Premium" theme — Tesla OS x Bloomberg Terminal.

    Every selector below is prefixed with `html body` purely to win CSS
    specificity ties against config.py's apply_theme() (the existing
    Light/Dark session-state toggle, whose return values are still used
    throughout the app for inline styling). Without that prefix, whichever
    <style> block Streamlit happens to render last would win any selector
    they share — prefixing guarantees this theme always wins, regardless
    of call order.
    """
    st.markdown("""
    <style>
    :root {
        --pv-bg: #0b0f19;
        --pv-bg-elevated: #11172a;
        --pv-glass: rgba(255, 255, 255, 0.045);
        --pv-glass-border: rgba(255, 255, 255, 0.09);
        --pv-text: #e8ecf4;
        --pv-text-dim: #8993a8;
        --pv-accent: #00e0ff;
        --pv-accent-2: #7b5cff;
        --pv-glow: rgba(0, 224, 255, 0.35);
    }

    /* ---- Hide default Streamlit clutter ---- */
    html body #MainMenu { visibility: hidden !important; }
    html body header[data-testid="stHeader"] { visibility: hidden !important; height: 0 !important; }
    html body footer { visibility: hidden !important; }

    /* ---- Global background + base typography ---- */
    html body,
    html body [data-testid="stAppViewContainer"],
    html body [data-testid="stApp"] {
        background: radial-gradient(circle at top left, #101626 0%, var(--pv-bg) 55%) !important;
        color: var(--pv-text) !important;
    }
    html body h1, html body h2, html body h3, html body h4, html body h5, html body h6,
    html body p, html body label, html body span, html body div {
        color: var(--pv-text) !important;
    }

    /* ---- Sidebar: frosted glass, distinct shade ---- */
    html body [data-testid="stSidebar"] {
        background: rgba(8, 11, 20, 0.88) !important;
        backdrop-filter: blur(18px) saturate(140%);
        border-right: 1px solid var(--pv-glass-border) !important;
    }
    html body [data-testid="stSidebar"] * { color: var(--pv-text) !important; }

    /* ---- Metric cards: glassmorphism with neon hover glow ---- */
    html body div[data-testid="stMetric"] {
        background: var(--pv-glass) !important;
        border: 1px solid var(--pv-glass-border) !important;
        border-radius: 16px !important;
        padding: 1.1rem 1.3rem !important;
        backdrop-filter: blur(10px);
        transition: all 0.25s ease-in-out;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
    }
    html body div[data-testid="stMetric"]:hover {
        border-color: var(--pv-accent) !important;
        box-shadow: 0 0 18px var(--pv-glow), 0 0 40px rgba(0, 224, 255, 0.15) !important;
        transform: translateY(-2px);
    }
    html body div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--pv-text) !important;
        font-weight: 600 !important;
        text-shadow: 0 0 12px rgba(0, 224, 255, 0.25);
    }
    html body div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        color: var(--pv-text-dim) !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        font-size: 0.72rem !important;
    }

    /* ---- Buttons: pill-shaped premium gradient ---- */
    html body div[data-testid="stButton"] > button,
    html body .stButton > button {
        background: linear-gradient(135deg, var(--pv-accent-2) 0%, var(--pv-accent) 100%) !important;
        color: #0b0f19 !important;
        border: none !important;
        border-radius: 999px !important;
        padding: 0.55rem 1.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
        width: auto !important;
        box-shadow: 0 4px 18px rgba(0, 224, 255, 0.25) !important;
        transition: all 0.2s ease-in-out !important;
    }
    html body div[data-testid="stButton"] > button:hover,
    html body .stButton > button:hover {
        transform: translateY(-1px) scale(1.02);
        box-shadow: 0 6px 24px rgba(0, 224, 255, 0.45) !important;
    }
    html body div[data-testid="stButton"] > button:active,
    html body .stButton > button:active {
        transform: scale(0.97);
    }

    /* ---- Tabs: segmented control with glowing active state ---- */
    html body div[data-baseweb="tab-list"] {
        background: var(--pv-glass) !important;
        border-radius: 999px !important;
        border: 1px solid var(--pv-glass-border) !important;
        padding: 4px !important;
        gap: 4px !important;
    }
    html body button[data-baseweb="tab"] {
        border-radius: 999px !important;
        color: var(--pv-text-dim) !important;
        border: none !important;
        transition: all 0.2s ease-in-out !important;
    }
    html body button[data-baseweb="tab"][aria-selected="true"] {
        background: rgba(0, 224, 255, 0.14) !important;
        color: var(--pv-accent) !important;
        box-shadow: 0 0 14px var(--pv-glow) !important;
        font-weight: 600 !important;
    }
    html body [data-baseweb="tab-highlight"] { display: none !important; }
    html body [data-baseweb="tab-border"] { display: none !important; }

    /* ---- Tab text contrast (BaseWeb wraps tab labels in nested p/span/div) ---- */
    html body [data-baseweb="tab"] p,
    html body [data-baseweb="tab"] span,
    html body [data-baseweb="tab"] div {
        color: #A0AEC0 !important;
    }
    html body [data-baseweb="tab"][aria-selected="true"] p,
    html body [data-baseweb="tab"][aria-selected="true"] span,
    html body [data-baseweb="tab"][aria-selected="true"] div {
        color: #FFFFFF !important;
        text-shadow: 0 0 10px var(--pv-glow);
    }

    /* ---- DataFrames / tables: integrated dark styling ---- */
    html body [data-testid="stDataFrame"],
    html body [data-testid="stTable"] {
        border: 1px solid var(--pv-glass-border) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    html body [data-testid="stDataFrame"] div[role="columnheader"] {
        background: var(--pv-bg-elevated) !important;
        color: var(--pv-accent) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-size: 0.78rem !important;
    }
    html body [data-testid="stDataFrame"] div[role="gridcell"],
    html body [data-testid="stDataFrame"] div[role="row"] {
        background: rgba(255, 255, 255, 0.015) !important;
        color: var(--pv-text) !important;
        border-color: var(--pv-glass-border) !important;
    }

    /* ---- Inputs & dropdowns: frosted glass, never stark white ---- */
    html body input,
    html body textarea,
    html body [data-baseweb="input"],
    html body [data-baseweb="select"],
    html body [data-baseweb="base-input"],
    html body [data-baseweb="select"] > div,
    html body [data-baseweb="input"] > div,
    html body [data-baseweb="base-input"] input,
    html body [data-baseweb="select"] input {
        background: rgba(20, 25, 40, 0.7) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }
    html body [data-baseweb="select"] span,
    html body [data-baseweb="select"] div {
        color: #FFFFFF !important;
    }
    html body input:focus,
    html body textarea:focus,
    html body [data-baseweb="input"]:focus-within,
    html body [data-baseweb="select"]:focus-within {
        border-color: var(--pv-accent) !important;
        box-shadow: 0 0 0 1px var(--pv-accent) !important;
    }

    /* ---- Expanders ---- */
    html body [data-testid="stExpander"] {
        background: var(--pv-glass) !important;
        border: 1px solid var(--pv-glass-border) !important;
        border-radius: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)
