import streamlit as st
import hashlib
from datetime import datetime
from config import apply_theme, get_supabase_client, safe_rerun, BMW_LOGO, SAST
from views import auth_view, property_view, director_view, dealership_view, command_center

st.set_page_config(page_title="Phase V Enterprise Hub", layout="wide")

# Initialize Environment & Database
text_color, container_bg, metric_label, border_color, theme = apply_theme()

# ==========================================
# AGGRESSIVE GLOBAL BUTTON CSS FIX
# ==========================================
st.markdown(f"""
    <style>
        .stButton > button, div.stButton > button:first-child {{
            background-color: #111111 !important;
            border: 1px solid #444444 !important;
            border-radius: 4px !important;
            transition: all 0.2s ease-in-out !important;
        }}
        .stButton > button * {{
            color: #FFFFFF !important;
            font-weight: 500 !important;
            letter-spacing: 1px !important;
        }}
        .stButton > button:hover {{
            background-color: #222222 !important;
            border-color: #FFFFFF !important;
        }}
    </style>
""", unsafe_allow_html=True)

try:
    supabase = get_supabase_client()
except Exception as e:
    st.error(f"🔒 API Error: {str(e)}")
    st.stop()

# Initialize Session State
for key in ['authenticated', 'user', 'name', 'role', 'location_id', 'department_id', 'brand_id']:
    if key not in st.session_state:
        st.session_state[key] = False if key == 'authenticated' else None

if 'page_view' not in st.session_state:
    st.session_state['page_view'] = 'dashboard'

# ====================================================================
# ROUTER
# ====================================================================
if not st.session_state['authenticated']:
    auth_view.render(supabase)
else:
    # Header
    h1, h2, h3 = st.columns([6, 1.2, 1.2])
    with h1:
        st.markdown(f"<div style='display:flex; align-items:center; gap:18px;'><img src='{BMW_LOGO}' width='50'><div><h3 style='margin:0; font-size:1.4rem; font-weight:400;'>PHASE V MOTOR INVESTMENTS</h3><p style='margin:0; font-size:0.75rem; color:{metric_label};'>ENTERPRISE PRODUCTION WORKSPACE</p></div></div>", unsafe_allow_html=True)
    with h2:
        if st.button("⚙️ SETTINGS"):
            st.session_state['page_view'] = 'settings'
            safe_rerun()
    with h3:
        if st.button("🚪 LOGOUT"):
            st.session_state.update({'authenticated': False, 'role': None, 'page_view': 'dashboard'})
            safe_rerun()

    st.markdown("---")

    # ---------------------------------------------------------
    # ROUTING LOGIC
    # ---------------------------------------------------------
    role = str(st.session_state.get('role', '')).upper()

    if st.session_state['page_view'] == 'settings':
        # (Settings logic remains identical to your previous version)
        st.markdown("## ⚙️ ACCOUNT SETTINGS")
        if st.button("⬅️ BACK TO DASHBOARD"):
            st.session_state['page_view'] = 'dashboard'; safe_rerun()
    
    elif st.session_state['page_view'] == 'dashboard':
        # Matrix Routing
        if role == 'SUPER_USER':
            # SUPER USER sees the Command Center
            command_center.render(supabase)
        elif role == 'PROPERTY_MANAGER':
            property_view.render(supabase, container_bg, text_color, theme)
        elif role == 'DIRECTOR':
            director_view.render(supabase, container_bg, text_color, metric_label, theme)
        else:
            # All operational roles (Sales/Parts/Workshop)
            dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)
