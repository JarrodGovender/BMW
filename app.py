import streamlit as st
import hashlib
from datetime import datetime
from config import apply_theme, get_supabase_client, safe_rerun, BMW_LOGO, SAST
from views import auth_view, property_view, director_view, dealership_view, command_center

st.set_page_config(page_title="Phase V Enterprise Hub", layout="wide")

# Initialize Environment & Database
text_color, container_bg, metric_label, border_color, theme = apply_theme()

# Global Button CSS
st.markdown("""<style>
    .stButton > button { background-color: #111111 !important; color: #FFFFFF !important; }
    .stButton > button:hover { background-color: #222222 !important; border-color: #FFFFFF !important; }
</style>""", unsafe_allow_html=True)

supabase = get_supabase_client()

# Session State Initialization
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
        st.markdown(f"### PHASE V MOTOR INVESTMENTS")
    with h2:
        if st.button("⚙️ SETTINGS"): st.session_state['page_view'] = 'settings'; safe_rerun()
    with h3:
        if st.button("🚪 LOGOUT"):
            st.session_state.update({'authenticated': False, 'role': None, 'page_view': 'dashboard'})
            safe_rerun()

    st.markdown("---")

    role = str(st.session_state.get('role', '')).upper()

    # VIEW LOGIC
    if st.session_state['page_view'] == 'settings':
        st.markdown("## ⚙️ SETTINGS")
        if st.button("⬅️ BACK"): st.session_state['page_view'] = 'dashboard'; safe_rerun()
    
    else:
        # NAVIGATION FOR SUPER USERS
        if role == 'SUPER_USER':
            nav = st.sidebar.radio("NAVIGATION", ["COMMAND CENTER", "DEALERSHIP OPERATIONS"])
            if nav == "COMMAND CENTER":
                command_center.render(supabase)
            else:
                dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)
        
        # NAVIGATION FOR OTHER ROLES
        elif role == 'PROPERTY_MANAGER':
            property_view.render(supabase, container_bg, text_color, theme)
        elif role == 'DIRECTOR':
            director_view.render(supabase, container_bg, text_color, metric_label, theme)
        else:
            dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)
