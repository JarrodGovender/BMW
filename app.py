import streamlit as st
import hashlib
from datetime import datetime
from config import apply_theme, get_supabase_client, safe_rerun, BMW_LOGO, SAST
from views import auth_view, property_view, director_view, dealership_view

st.set_page_config(page_title="Phase V Enterprise Hub", layout="wide")

# Initialize Environment & Database
text_color, container_bg, metric_label, border_color, theme = apply_theme()

# ==========================================
# AGGRESSIVE GLOBAL BUTTON CSS FIX
# Forces dark buttons with white text globally
# ==========================================
st.markdown(f"""
    <style>
        /* Force background and border for the outer button container */
        .stButton > button, div.stButton > button:first-child {{
            background-color: #111111 !important;
            border: 1px solid #444444 !important;
            border-radius: 4px !important;
            transition: all 0.2s ease-in-out !important;
        }}
        
        /* Force ALL text inside the button to be white */
        .stButton > button * {{
            color: #FFFFFF !important;
            font-weight: 500 !important;
            letter-spacing: 1px !important;
        }}
        
        /* Hover state for better UX */
        .stButton > button:hover {{
            background-color: #222222 !important;
            border-color: #FFFFFF !important;
        }}
    </style>
""", unsafe_allow_html=True)
# ==========================================

try:
    supabase = get_supabase_client()
except Exception as e:
    st.error(f"🔒 API Error: {str(e)}")
    st.stop()

if datetime.now(SAST).hour >= 22 or datetime.now(SAST).hour < 6:
    st.error("🛑 **Access Denied: System Offline.**")
    st.stop()

# Initialize Session State with Matrix Tenancy Variables
for key in ['authenticated', 'user', 'name', 'role', 'location_id', 'department_id', 'brand_id']:
    if key not in st.session_state:
        st.session_state[key] = False if key == 'authenticated' else None

if 'page_view' not in st.session_state:
    st.session_state['page_view'] = 'dashboard'

# ====================================================================
# MAIN APPLICATION ROUTER
# ====================================================================
if not st.session_state['authenticated']:
    auth_view.render(supabase)
else:
    # Build the Universal Enterprise Header
    h1, h2, h3 = st.columns([6, 1.2, 1.2])
    with h1:
        st.markdown(f"<div style='display:flex; align-items:center; gap:18px;'><img src='{BMW_LOGO}' width='50'><div><h3 style='margin:0; font-size:1.4rem; font-weight:400;'>PHASE V MOTOR INVESTMENTS</h3><p style='margin:0; font-size:0.75rem; color:{metric_label};'>ENTERPRISE PRODUCTION WORKSPACE</p></div></div>", unsafe_allow_html=True)
    with h2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚙️ SETTINGS"):
            st.session_state['page_view'] = 'settings'
            safe_rerun()
    with h3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 LOGOUT"):
            st.session_state.update({
                'authenticated': False, 'user': None, 'name': None, 'role': None, 
                'location_id': None, 'department_id': None, 'brand_id': None, 'page_view': 'dashboard'
            })
            safe_rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"LOGGED IN AS: **{st.session_state['name'].upper()}** ({str(st.session_state['role']).replace('_', ' ').upper()})\n---")

    # ---------------------------------------------------------
    # SETTINGS VIEW
    # ---------------------------------------------------------
    if st.session_state['page_view'] == 'settings':
        st.markdown("## ⚙️ ACCOUNT SETTINGS")
        col_back, _ = st.columns([1, 4])
        with col_back:
            if st.button("⬅️ BACK TO DASHBOARD"):
                st.session_state['page_view'] = 'dashboard'
                safe_rerun()
                
        st.markdown("---")
        st.markdown("#### 🌗 THEME PREFERENCE")
        new_theme = st.radio("Select Interface Display Mode:", ["Light", "Dark"], index=0 if st.session_state['theme'] == 'Light' else 1, horizontal=True)
        if new_theme != st.session_state['theme']:
            st.session_state['theme'] = new_theme
            safe_rerun()
            
        st.markdown("---")
        st.markdown("#### 🔑 CHANGE SECURE PASSWORD")
        pw_c1, pw_c2 = st.columns(2)
        with pw_c1:
            curr_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            conf_pw = st.text_input("Confirm New Password", type="password")
            if st.button("UPDATE PASSWORD", key="update_pw_btn"):
                if not curr_pw or not new_pw or not conf_pw:
                    st.warning("⚠️ Please fill all password fields.")
                elif new_pw != conf_pw:
                    st.error("⚠️ New passwords do not match.")
                elif len(new_pw) < 6:
                    st.error("⚠️ New password must be at least 6 characters.")
                else:
                    res = supabase.table("users").select("password").eq("username", st.session_state['user']).execute()
                    if res.data and res.data[0]['password'] == hashlib.sha256(curr_pw.encode()).hexdigest():
                        supabase.table("users").update({"password": hashlib.sha256(new_pw.encode()).hexdigest()}).eq("username", st.session_state['user']).execute()
                        st.success("✅ Password successfully updated!")
                    else:
                        st.error("⚠️ The current password you entered is incorrect.")

    # ---------------------------------------------------------
    # MODULAR DASHBOARD ROUTING
    # ---------------------------------------------------------
    elif st.session_state['page_view'] == 'dashboard':
        # Normalize role text to handle case-insensitive database records
        role = str(st.session_state['role']).upper()
        
        # Route to Property Manager Kanban Board
        if role == 'PROPERTY_MANAGER':
            property_view.render(supabase, container_bg, text_color, theme)
            
        # Route to Executive Level Portfolio Dashboard
        elif role in ['DIRECTOR', 'SUPER_USER']:
            director_view.render(supabase, container_bg, text_color, metric_label, theme)
            
        # Route all operational roles (Sales, Parts, Workshop, Finance) to the Dealership Operations Workspace
        else:
            dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)
