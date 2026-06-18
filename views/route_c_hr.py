import streamlit as st
import pandas as pd
import hashlib
from config import safe_rerun, get_static_reference_data
from views.shared_utils import apply_matrix_filters, _render_token_manager

# ====================================================================
# ROUTE C: HUMAN RESOURCES DEPARTMENT
# ====================================================================
def render_hr(supabase, user_data):
    t1, t2, t3, t4 = st.tabs(["👥 STAFF ROSTER", "🔄 MATRIX TRANSFERS", "🔐 SECURITY & RESETS", "🔑 TOKEN MANAGER"])

    ref_data = get_static_reference_data(supabase)
    db_roles, db_locs, db_depts, db_brands = ref_data["roles"], ref_data["locations"], ref_data["departments"], ref_data["brands"]

    try:
        staff_query = apply_matrix_filters(supabase.table("users").select("name, username, role, role_id, location_id, department_id, brand_id, is_active"))
        staff_res = staff_query.order("name").execute().data or []
    except Exception as e:
        st.error(f"Failed to load staff directory: {e}")
        staff_res = []

    df_staff = pd.DataFrame(staff_res)
    if not df_staff.empty:
        df_staff['role'] = df_staff['role_id'].fillna(df_staff['role'])
        df_staff['is_active'] = df_staff['is_active'].fillna(True)

    with t1:
        st.markdown(f"### 👥 {st.session_state.get('location_id', '').replace('_', ' ')} STAFF ROSTER")
        if df_staff.empty:
            st.info("No staff records found for your matrix scope.")
        else:
            ds = df_staff.rename(columns={
                "name": "NAME", "username": "USERNAME", "role": "ROLE",
                "location_id": "LOCATION", "department_id": "DEPARTMENT",
                "brand_id": "BRAND", "is_active": "ACTIVE STATUS"
            })[["NAME", "USERNAME", "ROLE", "LOCATION", "DEPARTMENT", "BRAND", "ACTIVE STATUS"]]
            st.dataframe(ds, hide_index=True, use_container_width=True)

    with t2:
        st.markdown("### 🔄 MATRIX TRANSFERS & PROMOTIONS")
        if df_staff.empty:
            st.info("No staff records available to transfer.")
        else:
            sel_user = st.selectbox("SELECT STAFF MEMBER", df_staff['username'].tolist(), key="hr_transfer_user")
            u_row = df_staff[df_staff['username'] == sel_user].iloc[0]

            tc1, tc2 = st.columns(2)
            n_role = tc1.selectbox("ROLE", db_roles, index=db_roles.index(u_row['role']) if u_row['role'] in db_roles else 0, key="hr_role_sel")
            n_loc = tc2.selectbox("LOCATION", db_locs, index=db_locs.index(u_row['location_id']) if u_row['location_id'] in db_locs else 0, key="hr_loc_sel")
            n_dept = tc1.selectbox("DEPARTMENT", db_depts, index=db_depts.index(u_row['department_id']) if u_row['department_id'] in db_depts else 0, key="hr_dept_sel")
            n_brand = tc2.selectbox("BRAND", db_brands, index=db_brands.index(u_row['brand_id']) if u_row['brand_id'] in db_brands else 0, key="hr_brand_sel")
            n_active = st.checkbox("ACTIVE STATUS", value=bool(u_row.get('is_active', True)), key="hr_active_chk")

            if st.button("💾 UPDATE STAFF MATRIX", use_container_width=True):
                try:
                    apply_matrix_filters(supabase.table("users").update({
                        "role": n_role, "role_id": n_role, "location_id": n_loc,
                        "department_id": n_dept, "brand_id": n_brand, "is_active": n_active
                    })).eq("username", sel_user).execute()
                    st.success(f"✅ @{sel_user}'s matrix updated."); safe_rerun()
                except Exception as e: st.error(f"Error: {e}")

    with t3:
        st.markdown("### 🔐 SECURITY & PASSWORD RESETS")
        if df_staff.empty:
            st.info("No staff records available.")
        else:
            sel_reset_user = st.selectbox("SELECT STAFF MEMBER", df_staff['username'].tolist(), key="hr_reset_user")
            new_pass = st.text_input("NEW PASSWORD", type="password", key="hr_reset_pass")
            if st.button("⚠️ FORCE PASSWORD RESET", use_container_width=True):
                if new_pass:
                    try:
                        hashed_pass = hashlib.sha256(new_pass.encode()).hexdigest()
                        supabase.table("users").update({"password": hashed_pass}).eq("username", sel_reset_user).execute()
                        st.success(f"✅ Password reset for @{sel_reset_user}.")
                    except Exception as e: st.error(f"Error: {e}")
                else:
                    st.warning("Enter a new password.")

    with t4:
        _render_token_manager(supabase)
