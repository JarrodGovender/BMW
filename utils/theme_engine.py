import streamlit as st

# Two value-sets for the same selector tree below -- only the :root tokens
# differ per theme, so Dark/Light stay DRY instead of forking the whole sheet.
_DARK_VARS = {
    "pv-bg": "#0b0f19",
    "pv-bg-elevated": "#11172a",
    "pv-bg-gradient": "radial-gradient(circle at top left, #101626 0%, #0b0f19 55%)",
    "pv-glass": "rgba(255, 255, 255, 0.045)",
    "pv-glass-border": "rgba(255, 255, 255, 0.09)",
    "pv-text": "#e8ecf4",
    "pv-text-dim": "#8993a8",
    "pv-accent": "#00e0ff",
    "pv-accent-2": "#7b5cff",
    "pv-glow": "rgba(0, 224, 255, 0.35)",
    "pv-text-glow": "rgba(0, 224, 255, 0.25)",
    "pv-card-bg": "rgba(17, 25, 40, 0.75)",
    "pv-card-border": "rgba(255, 255, 255, 0.125)",
    "pv-input-text": "#FFFFFF",
    "pv-table-accent": "#00E5FF",
    "pv-sidebar-bg": "rgba(8, 11, 20, 0.88)",
    "pv-tab-dim": "#A0AEC0",
    "pv-tab-active": "#FFFFFF",
    "pv-row-hover": "rgba(0, 229, 255, 0.1)",
}

_LIGHT_VARS = {
    "pv-bg": "#f2f4f9",
    "pv-bg-elevated": "#ffffff",
    "pv-bg-gradient": "radial-gradient(circle at top left, #ffffff 0%, #f2f4f9 55%)",
    "pv-glass": "rgba(10, 20, 40, 0.035)",
    "pv-glass-border": "rgba(10, 20, 40, 0.10)",
    "pv-text": "#1a2233",
    "pv-text-dim": "#5b6478",
    "pv-accent": "#0066cc",
    "pv-accent-2": "#3355dd",
    "pv-glow": "rgba(0, 102, 204, 0.25)",
    "pv-text-glow": "rgba(0, 102, 204, 0.18)",
    "pv-card-bg": "rgba(255, 255, 255, 0.85)",
    "pv-card-border": "rgba(10, 20, 40, 0.10)",
    "pv-input-text": "#1a2233",
    "pv-table-accent": "#0066CC",
    "pv-sidebar-bg": "rgba(255, 255, 255, 0.92)",
    "pv-tab-dim": "#5b6478",
    "pv-tab-active": "#0a0f1a",
    "pv-row-hover": "rgba(0, 102, 204, 0.08)",
}


def inject_custom_css():
    """
    "Futuristic Premium" theme -- Tesla OS x Bloomberg Terminal (Dark), with a
    full parallel "Enterprise Light" variant. Both share the exact same
    selector tree; only the :root token values below switch on
    st.session_state['theme'] ('Dark' default, or 'Light').

    Every selector is prefixed with `html body` purely to win CSS specificity
    ties against config.py's apply_theme() (the legacy Light/Dark toggle whose
    return values are still consumed inline elsewhere). Without that prefix,
    whichever <style> block renders last would win shared selectors --
    prefixing guarantees this theme always wins, regardless of call order.
    """
    theme = st.session_state.get('theme', 'Dark')
    v = _LIGHT_VARS if theme == 'Light' else _DARK_VARS
    root_vars = "\n".join(f"        --{k}: {val};" for k, val in v.items())

    st.markdown(f"""
    <style>
    :root {{
{root_vars}
    }}

    /* ---- Hide default Streamlit clutter ---- */
    html body #MainMenu {{ visibility: hidden !important; }}
    html body header[data-testid="stHeader"] {{ visibility: hidden !important; height: 0 !important; }}
    html body footer {{ visibility: hidden !important; }}

    /* ---- Global background + base typography ---- */
    html body,
    html body [data-testid="stAppViewContainer"],
    html body [data-testid="stApp"] {{
        background: var(--pv-bg-gradient) !important;
        color: var(--pv-text) !important;
        font-family: "Inter", "Segoe UI", Helvetica, Arial, sans-serif !important;
    }}
    html body h1, html body h2, html body h3, html body h4, html body h5, html body h6,
    html body p, html body label, html body span, html body div {{
        color: var(--pv-text) !important;
    }}

    /* ---- Sidebar: frosted glass, distinct shade ---- */
    html body [data-testid="stSidebar"] {{
        background: var(--pv-sidebar-bg) !important;
        backdrop-filter: blur(18px) saturate(140%);
        border-right: 1px solid var(--pv-glass-border) !important;
    }}
    html body [data-testid="stSidebar"] * {{ color: var(--pv-text) !important; }}

    /* ---- Metric cards: ultra-glassmorphism with neon hover glow ---- */
    html body div[data-testid="stMetric"] {{
        background: var(--pv-card-bg) !important;
        border: 1px solid var(--pv-card-border) !important;
        border-radius: 16px !important;
        padding: 1.1rem 1.3rem !important;
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        transition: all 0.25s ease-in-out;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
    }}
    html body div[data-testid="stMetric"]:hover {{
        border-color: var(--pv-accent) !important;
        box-shadow: 0 0 18px var(--pv-glow) !important;
        transform: translateY(-2px);
    }}
    html body div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: var(--pv-text) !important;
        font-weight: 600 !important;
        font-family: 'Roboto Mono', 'Space Mono', monospace !important;
        text-shadow: 0 0 12px var(--pv-text-glow);
    }}
    html body div[data-testid="stMetric"] [data-testid="stMetricLabel"] {{
        color: var(--pv-text-dim) !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        font-size: 0.72rem !important;
    }}

    /* ---- Buttons: pill-shaped premium gradient ---- */
    html body div[data-testid="stButton"] > button,
    html body .stButton > button {{
        background: linear-gradient(135deg, var(--pv-accent-2) 0%, var(--pv-accent) 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 999px !important;
        padding: 0.55rem 1.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
        width: auto !important;
        box-shadow: 0 4px 18px var(--pv-glow) !important;
        transition: all 0.2s ease-in-out !important;
    }}
    html body div[data-testid="stButton"] > button:hover,
    html body .stButton > button:hover {{
        transform: translateY(-1px) scale(1.02);
        box-shadow: 0 6px 24px var(--pv-glow) !important;
    }}
    html body div[data-testid="stButton"] > button:active,
    html body .stButton > button:active {{
        transform: scale(0.97);
    }}

    /* ---- Tabs: segmented control with glowing active state ---- */
    html body div[data-baseweb="tab-list"] {{
        background: var(--pv-glass) !important;
        border-radius: 999px !important;
        border: 1px solid var(--pv-glass-border) !important;
        padding: 4px !important;
        gap: 4px !important;
    }}
    html body button[data-baseweb="tab"] {{
        border-radius: 999px !important;
        color: var(--pv-text-dim) !important;
        border: none !important;
        transition: all 0.2s ease-in-out !important;
    }}
    html body button[data-baseweb="tab"][aria-selected="true"] {{
        background: var(--pv-glow) !important;
        color: var(--pv-accent) !important;
        box-shadow: 0 0 14px var(--pv-glow) !important;
        font-weight: 600 !important;
    }}
    html body [data-baseweb="tab-highlight"] {{ display: none !important; }}
    html body [data-baseweb="tab-border"] {{ display: none !important; }}

    /* ---- Tab text contrast (BaseWeb wraps tab labels in nested p/span/div) ---- */
    html body [data-baseweb="tab"] p,
    html body [data-baseweb="tab"] span,
    html body [data-baseweb="tab"] div {{
        color: var(--pv-tab-dim) !important;
    }}
    html body [data-baseweb="tab"][aria-selected="true"] p,
    html body [data-baseweb="tab"][aria-selected="true"] span,
    html body [data-baseweb="tab"][aria-selected="true"] div {{
        color: var(--pv-tab-active) !important;
        text-shadow: 0 0 10px var(--pv-glow);
    }}

    /* ---- DataFrames / tables: integrated styling ---- */
    html body [data-testid="stDataFrame"],
    html body [data-testid="stTable"] {{
        border: 1px solid var(--pv-glass-border) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }}
    html body [data-testid="stDataFrame"] div[role="columnheader"] {{
        background: var(--pv-bg-elevated) !important;
        color: var(--pv-table-accent) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-size: 0.78rem !important;
    }}
    html body [data-testid="stDataFrame"] div[role="gridcell"],
    html body [data-testid="stDataFrame"] div[role="row"] {{
        background: var(--pv-glass) !important;
        color: var(--pv-text) !important;
        border-color: var(--pv-glass-border) !important;
        font-family: 'Roboto Mono', 'Space Mono', monospace !important;
    }}
    html body [data-testid="stDataFrame"] div[role="row"]:hover div[role="gridcell"] {{
        background: var(--pv-row-hover) !important;
    }}

    /* ---- HTML tables (st.table / markdown tables): premium grid ---- */
    html body table {{
        background: transparent !important;
        border-collapse: collapse !important;
        border: none !important;
    }}
    html body th {{
        background: var(--pv-bg-elevated) !important;
        color: var(--pv-table-accent) !important;
        border: none !important;
        border-bottom: 2px solid var(--pv-table-accent) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }}
    html body td {{
        background: transparent !important;
        border: none !important;
        border-bottom: 1px solid var(--pv-glass-border) !important;
        color: var(--pv-text) !important;
        font-family: 'Roboto Mono', 'Space Mono', monospace !important;
    }}
    html body tr {{
        background: transparent !important;
        border: none !important;
        transition: background-color 0.2s ease-in-out;
    }}
    html body tr:hover {{
        background-color: var(--pv-row-hover) !important;
    }}

    /* ---- Inputs & dropdowns: ultra-glassmorphism, never stark white ---- */
    html body input,
    html body textarea,
    html body [data-baseweb="input"],
    html body [data-baseweb="select"],
    html body [data-baseweb="base-input"],
    html body [data-baseweb="select"] > div,
    html body [data-baseweb="input"] > div,
    html body [data-baseweb="base-input"] input,
    html body [data-baseweb="select"] input {{
        background: var(--pv-card-bg) !important;
        color: var(--pv-input-text) !important;
        border: 1px solid var(--pv-card-border) !important;
        border-radius: 10px !important;
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
    }}
    html body [data-baseweb="select"] span,
    html body [data-baseweb="select"] div {{
        color: var(--pv-input-text) !important;
    }}
    html body input:focus,
    html body textarea:focus,
    html body [data-baseweb="input"]:focus-within,
    html body [data-baseweb="select"]:focus-within {{
        border-color: var(--pv-accent) !important;
        box-shadow: 0 0 0 1px var(--pv-accent) !important;
    }}

    /* ---- Expanders: ultra-glassmorphism, glowing title ---- */
    html body [data-testid="stExpander"] {{
        background: var(--pv-card-bg) !important;
        border: 1px solid var(--pv-card-border) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
    }}
    html body [data-testid="stExpander"] summary {{
        background: transparent !important;
    }}
    html body [data-testid="stExpander"] summary p,
    html body [data-testid="stExpander"] summary span,
    html body [data-testid="stExpander"] summary div {{
        color: var(--pv-table-accent) !important;
        font-weight: 600 !important;
    }}

    /* ---- Dividers: fading neon gradient instead of a flat grey line ---- */
    html body hr {{
        background: linear-gradient(to right, transparent, var(--pv-table-accent), transparent) !important;
        height: 1px !important;
        border: none !important;
    }}

    /* ---- Security/trust alerts: semantic colors, constant across themes ---- */
    html body [data-testid="stAlert"] {{
        background: var(--pv-card-bg) !important;
        border: 1px solid var(--pv-card-border) !important;
        border-radius: 8px !important;
        backdrop-filter: blur(12px);
    }}
    html body [data-testid="stAlertContentSuccess"] {{
        border-left: 3px solid #00C853 !important;
        box-shadow: -4px 0 16px rgba(0, 200, 83, 0.25) !important;
    }}
    html body [data-testid="stAlertContentError"] {{
        border-left: 3px solid #FF3366 !important;
        box-shadow: -4px 0 16px rgba(255, 51, 102, 0.25) !important;
    }}
    html body [data-testid="stAlertContentWarning"] {{
        border-left: 3px solid #FFB300 !important;
        box-shadow: -4px 0 16px rgba(255, 179, 0, 0.25) !important;
    }}
    html body [data-testid="stAlertContentInfo"] {{
        border-left: 3px solid var(--pv-table-accent) !important;
        box-shadow: -4px 0 16px var(--pv-glow) !important;
    }}

    /* ---- Dynamic Logo Logic: Phase V logo gets a black bounding box in
       Light Mode only (it's a light/transparent mark, invisible otherwise) ---- */
    html body .pv-logo-box {{
        display: inline-block;
        {"background: #0a0f1a; padding: 6px 14px; border-radius: 8px;" if theme == "Light" else "background: transparent; padding: 0;"}
    }}
    </style>
    """, unsafe_allow_html=True)


def render_logo(logo_data_uri, height=32):
    """Phase V logo with the Dynamic Logo Logic black bounding box in Light Mode."""
    st.markdown(
        f'<div class="pv-logo-box"><img src="{logo_data_uri}" height="{height}"></div>',
        unsafe_allow_html=True,
    )
