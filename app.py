import streamlit as st
from datetime import datetime
from config import apply_theme, get_supabase_client, safe_rerun, BMW_LOGO, SAST
from views import auth_view, property_view, director_view

st.set_page_config(page_title="Phase V Enterprise Hub", layout="wide")

# Initialize Environment & Database
text_color, container_bg, metric_label, border_color, theme = apply_theme()
try: supabase = get_supabase_client()
except Exception as e: st.error(f"🔒 API Error: {str(e)}"); st.stop()

if datetime.now(SAST).hour >= 22 or datetime.now(SAST).hour < 6:
    st.error("🛑 **Access Denied: System Offline.**"); st.stop()

# Initialize Session State
for key in ['authenticated', 'user', 'name', 'role']:
    if key not in st.session_state: st.session_state[key] = False if key == 'authenticated' else None
if 'page_view' not in st.session_state: st.session_state['page_view'] = 'dashboard'

# --- THE ROUTER ---
if not st.session_state['authenticated']:
    auth_view.render(supabase)
else:
    # Build the Header
    h1, h2, h3 = st.columns([6, 1.2, 1.2])
    with h1:
        st.markdown(f"<div style='display:flex; align-items:center; gap:18px;'><img src='{BMW_LOGO}' width='50'><div><h3 style='margin:0; font-size:1.4rem; font-weight:400;'>PHASE V MOTOR INVESTMENTS</h3><p style='margin:0; font-size:0.75rem; color:{metric_label};'>ENTERPRISE PRODUCTION WORKSPACE</p></div></div>", unsafe_allow_html=True)
    with h2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚙️ SETTINGS"): st.session_state['page_view'] = 'settings'; safe_rerun()
    with h3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 LOGOUT"): st.session_state.update({'authenticated': False, 'user': None, 'name': None, 'role': None, 'page_view': 'dashboard'}); safe_rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"LOGGED IN AS: **{st.session_state['name'].upper()}** ({st.session_state['role'].replace('_', ' ').upper()})\n---")

    if st.session_state['page_view'] == 'settings':
        st.markdown("## ⚙️ ACCOUNT SETTINGS")
        if st.button("⬅️ BACK TO DASHBOARD"): st.session_state['page_view'] = 'dashboard'; safe_rerun()
        st.markdown("---")
        # Placeholder for password reset logic...
        st.info("Settings module active.")
        
    elif st.session_state['page_view'] == 'dashboard':
        role = st.session_state['role']
        if role == 'property_manager':
            property_view.render(supabase, container_bg, text_color, theme)
        elif role == 'director':
            director_view.render(supabase, container_bg, text_color, metric_label, theme)
        else:
elif st.session_state['page_view'] == 'dashboard':
        role = st.session_state['role']
        if role == 'property_manager':
            property_view.render(supabase, container_bg, text_color, theme)
        elif role == 'director':
            director_view.render(supabase, container_bg, text_color, metric_label, theme)
        else:
            from views import dealership_view
            dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)
