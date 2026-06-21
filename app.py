import time
_render_start = time.time()

import streamlit as st
import hashlib
from datetime import datetime
from config import apply_theme, get_supabase_client, safe_rerun, BMW_LOGO, SAST
from utils.theme_engine import inject_custom_css
from utils.helpers import get_role
from utils import demo_data, telemetry
from views import auth_view, property_view, director_view, dealership_view, command_center, settings, admin_console
from views import admin_telemetry, admin_users, admin_properties
from views.route_d_crm import render_crm

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

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'Dark'

if 'presentation_mode' not in st.session_state:
    st.session_state['presentation_mode'] = True

if st.session_state.get('presentation_mode'):
    demo_data.init_presentation_session_state()

# ====================================================================
# ROUTER
# ====================================================================
if not st.session_state['authenticated']:
    auth_view.render(supabase)
else:
    # Lightweight session invalidation check — boots a user out mid-session if HR
    # deactivates them, a Super User forces a logout, or revokes the account outright.
    try:
        active_check = supabase.table("users").select("is_active, force_logout, is_revoked").eq("username", st.session_state.get('user')).execute().data
        if active_check:
            row = active_check[0]
            if row.get('is_active') is False or row.get('is_revoked') is True:
                st.session_state.update({'authenticated': False, 'role': None, 'page_view': 'dashboard'})
                safe_rerun()
            elif row.get('force_logout') is True:
                try:
                    supabase.table("users").update({"force_logout": False}).eq("username", st.session_state.get('user')).execute()
                except Exception:
                    pass
                st.session_state.update({'authenticated': False, 'role': None, 'page_view': 'dashboard'})
                safe_rerun()
    except Exception:
        pass

    telemetry.heartbeat(supabase)

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

    role = get_role()

    # VIEW LOGIC
    if st.session_state['page_view'] == 'settings':
        if st.button("⬅️ BACK"): st.session_state['page_view'] = 'dashboard'; safe_rerun()
        settings.render(supabase)

    else:
        # =========================================================
        # 🔍 TEMPORARY DEBUG: SESSION STATE X-RAY (COMMAND 32)
        # Dumps the raw session_state so we can see, on screen, exactly
        # what key names/values exist instead of guessing blind. Remove
        # this block once the God Mode visibility issue is confirmed fixed.
        # =========================================================
        st.sidebar.markdown("---")
        st.sidebar.caption("🔍 DEBUG: SESSION STATE X-RAY")
        st.sidebar.write(st.session_state)
        st.sidebar.markdown("---")

        # =========================================================
        # NAVIGATION FOR SUPER USERS (GOD MODE SIDEBAR)
        # SKELETON KEY: extremely forgiving role/user matching. Checks the
        # real session key ('role'/'user', set in views/auth_view.py) first,
        # then falls back to every other plausible key name/casing, plus a
        # direct admin-email override as a last resort.
        # =========================================================
        current_role = str(st.session_state.get('role', st.session_state.get('user_role', ''))).upper()
        current_user = str(st.session_state.get(
            'user', st.session_state.get('username', st.session_state.get('email', ''))
        )).lower()

        is_super_user = current_role in ['SUPER_USER', 'SUPER USER', 'DIRECTOR', 'PROPERTY_MANAGER']
        # Confirmed login username (views/auth_view.py lowercases the
        # Username field on login, so the session value is always 'jarrod').
        is_admin_email = current_user == 'jarrod'

        if is_super_user or is_admin_email:
            with st.sidebar:
                # Explicit override for Super Users -- always the first thing
                # rendered in the sidebar, directly above everything else.
                st.markdown("---")
                st.subheader("👑 GOD MODE | SOC")
                if st.button("🔐 Admin Users", use_container_width=True, key="god_mode_users_btn"):
                    st.session_state['_direct_admin_view'] = 'users'
                    safe_rerun()
                if st.button("🛰️ Telemetry", use_container_width=True, key="god_mode_telemetry_btn"):
                    st.session_state['_direct_admin_view'] = 'telemetry'
                    safe_rerun()
                if st.button("🏗️ Property Management", use_container_width=True, key="god_mode_properties_btn"):
                    st.session_state['_direct_admin_view'] = 'properties'
                    safe_rerun()
                st.markdown("---")

                st.markdown("### 👑 WORKSPACE")
                nav_mode = st.radio("Select View:", [
                    "📊 Executive Command Center", "🎯 CRM Pipeline",
                    "🏢 Dealership Operations", "🏗️ Property Portfolio",
                    "👑 Admin / God Mode",
                ], label_visibility="collapsed")
                
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

                st.markdown("---")
                if st.button("🚪 LOGOUT", use_container_width=True, key="god_mode_sidebar_logout_btn"):
                    st.session_state.update({'authenticated': False, 'role': None, 'page_view': 'dashboard'})
                    safe_rerun()

            # Direct one-click jumps from the GOD MODE | SOC block bypass the
            # nav_mode radio entirely and render the target admin view straight away.
            direct_admin_view = st.session_state.pop('_direct_admin_view', None)
            if direct_admin_view == 'users':
                if st.button("⬅️ BACK TO WORKSPACE", key="god_mode_back_from_users"): safe_rerun()
                admin_users.render(supabase)
            elif direct_admin_view == 'telemetry':
                if st.button("⬅️ BACK TO WORKSPACE", key="god_mode_back_from_telemetry"): safe_rerun()
                admin_telemetry.render(supabase, container_bg, text_color)
            elif direct_admin_view == 'properties':
                if st.button("⬅️ BACK TO WORKSPACE", key="god_mode_back_from_properties"): safe_rerun()
                admin_properties.render(supabase, container_bg, text_color, theme)
            # Route to the selected view
            elif nav_mode == "📊 Executive Command Center":
                command_center.render(supabase)
            elif nav_mode == "🎯 CRM Pipeline":
                render_crm(supabase)
            elif nav_mode == "🏗️ Property Portfolio":
                if role == 'PROPERTY_MANAGER':
                    property_view.render(supabase, container_bg, text_color, theme)
                else:
                    director_view.render(supabase, container_bg, text_color, metric_label, theme)
            elif nav_mode == "👑 Admin / God Mode":
                admin_console.render(supabase, container_bg, text_color, theme)
            else:
                st.markdown(f"**CURRENT ACTIVE NODE:** `{selected_div[4:].upper()}` — `{selected_dept[2:].upper()}`")
                dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)

        # =========================================================
        # NAVIGATION FOR STANDARD ROLES
        # =========================================================
        else:
            dealership_view.render(supabase, container_bg, text_color, metric_label, border_color, theme)

telemetry.record_render_time(time.time() - _render_start)
