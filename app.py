import streamlit as st
import hashlib
from datetime import datetime
from config import apply_theme, get_supabase_client, safe_rerun, BMW_LOGO, SAST
from utils.theme_engine import inject_custom_css
from views import auth_view, property_view, director_view, dealership_view, command_center

st.set_page_config(page_title="Phase V Enterprise Hub", layout="wide", initial_sidebar_state="expanded")
inject_custom_css()

# Initialize Environment & Database
text_color, container_bg, metric_label, border_color, theme = apply_theme()

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
    # Lightweight session invalidation check — boots a user out mid-session if HR deactivates them
    try:
        active_check = supabase.table("users").select("is_active").eq("username", st.session_state.get('user')).execute().data
        if active_check and active_check[0].get('is_active') is False:
            st.session_state.update({'authenticated': False, 'role': None, 'page_view': 'dashboard'})
            safe_rerun()
    except Exception:
        pass

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
        # =========================================================
        # NAVIGATION FOR SUPER USERS (GOD MODE SIDEBAR)
        # =========================================================
        if role == 'SUPER_USER':
            with st.sidebar:
                st.markdown("### 👑 WORKSPACE")
                nav_mode = st.radio("Select View:", ["📊 Executive Command Center", "🏢 Dealership Operations"], label_visibility="collapsed")
                
                if nav_mode == "🏢 Dealership Operations":
                    st.markdown("---")
                    st.markdown("#### DIVISIONS")
                    
                    # Dictionary mapping UI labels to backend Database IDs
                    divisions = {
                        "1️⃣ BMW Bedfordview": "BMW_BEDFORDVIEW",
                        "2️⃣ BMW Boksburg / East Rand": "BMW_EASTRAND",
                        "3️⃣ BMW Dalpark": "BMW_DALPARK",
                        "4️⃣ BMW Sandton": "BMW_SANDTON",
                        "5️⃣ MG/Honda Sandton": "MF_SANDTON",
                        "6️⃣ MG/JAC Fourways": "MF_FOURWAYS"
                    }
                    
                    current_loc = st.session_state.get('location_id')
                    loc_names = list(divisions.keys())
                    loc_ids = list(divisions.values())
                    # Default to Sandton if current_loc isn't in the list
                    loc_idx = loc_ids.index(current_loc) if current_loc in loc_ids else 3 
                    
                    selected_div = st.radio("Divisions", loc_names, index=loc_idx, label_visibility="collapsed")
                    
                    st.markdown("---")
                    st.markdown("#### DEPARTMENTS")
                    
                    departments = {
                        "🏦 Admin/Finance": "FINANCE",
                        "🚗 New Sales": "NEW_SALES",
                        "🏷️ Used Sales": "USED_SALES",
                        "⚙️ Parts": "PARTS",
                        "🔧 Service": "SERVICE",
                        "🏍️ Motorcycles": "MOTORRAD",
                        "👥 HR": "HR"
                    }
                    
                    current_dept = st.session_state.get('department_id')
                    dept_names = list(departments.keys())
                    dept_ids = list(departments.values())
                    # Default to Admin/Finance
                    dept_idx = dept_ids.index(current_dept) if current_dept in dept_ids else 0
                    
                    selected_dept = st.radio("Departments", dept_names, index=dept_idx, label_visibility="collapsed")
                    
                    # Intercept changes and dynamically overwrite the session matrix
                    new_loc_id = divisions[selected_div]
                    new_dept_id = departments[selected_dept]
                    
                    if new_loc_id != current_loc or new_dept_id != current_dept:
                        st.session_state['location_id'] = new_loc_id
                        st.session_state['department_id'] = new_dept_id
                        safe_rerun()

                st.markdown("---")
                st.caption("DATA AS AT")
                st.caption(f"**{datetime.now(SAST).strftime('%d %b %Y %H:%M')}** ↻")

            # Route to the selected view
            if nav_mode == "📊 Executive Command Center":
                command_center.render(supabase)
            else:
                st.markdown(f"**CURRENT ACTIVE NODE:** `{selected_div[4:].upper()}` — `{selected_dept[2:].upper()}`")
                dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)
        
        # =========================================================
        # NAVIGATION FOR STANDARD ROLES
        # =========================================================
        elif role == 'PROPERTY_MANAGER':
            property_view.render(supabase, container_bg, text_color, theme)
        elif role == 'DIRECTOR':
            director_view.render(supabase, container_bg, text_color, metric_label, theme)
        else:
            dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)
