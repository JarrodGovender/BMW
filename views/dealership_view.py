import streamlit as st
from utils.helpers import get_role
from views.route_a_service import render_service_parts
from views.route_b_sales import render_sales_admin
from views.route_c_hr import render_hr

# ====================================================================
# TRAFFIC CONTROLLER — dispatches to the route module for the user's
# active department. Matrix gatekeepers live in views/shared_utils.py.
# ====================================================================
def render(supabase, container_bg, text_color, metric_label, border_color, theme):
    role = get_role()
    active_dept = str(st.session_state.get('department_id', '')).upper()
    user_data = {
        "container_bg": container_bg,
        "text_color": text_color,
        "metric_label": metric_label,
        "border_color": border_color,
        "theme": theme,
    }

    if active_dept in ['SERVICE', 'PARTS'] or role == 'WORKSHOP_MANAGER':
        render_service_parts(supabase, user_data)
    elif active_dept == 'HR':
        render_hr(supabase, user_data)
    else:
        render_sales_admin(supabase, user_data)
