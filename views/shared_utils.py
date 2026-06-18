import streamlit as st
import pandas as pd
import hashlib
from config import safe_rerun, get_static_reference_data

# ====================================================================
# MASTER SECURITY GATEKEEPER
# ====================================================================
def apply_matrix_filters(query_builder):
    role = str(st.session_state.get('role', '')).upper()
    loc = st.session_state.get('location_id')
    dept = st.session_state.get('department_id')
    brand = st.session_state.get('brand_id')

    if role == 'DIRECTOR':
        return query_builder

    if role in ['SUPER_USER', 'DEALER_PRINCIPAL', 'FINANCE_ADMIN', 'PROPERTY_MANAGER', 'HR_ADMIN']:
        return query_builder.eq("location_id", loc)

    if role in ['SALES_MANAGER', 'WORKSHOP_MANAGER', 'PARTS_MANAGER']:
        return query_builder.eq("location_id", loc).eq("department_id", dept)

    if brand == 'ALL_BRANDS':
        return query_builder.eq("location_id", loc).eq("department_id", dept)
    else:
        return query_builder.eq("location_id", loc).eq("department_id", dept).eq("brand_id", brand)

# ====================================================================
# LOCATION-ONLY GATEKEEPER (service_wip is shared across Service/Parts
# staff at one branch — department_id on the row is always "SERVICE"
# regardless of who's viewing it, so department/brand scoping doesn't
# apply here. Use this instead of apply_matrix_filters() for service_wip.
# ====================================================================
def apply_location_matrix_filters(query_builder):
    role = str(st.session_state.get('role', '')).upper()
    loc = st.session_state.get('location_id')

    if role == 'DIRECTOR':
        return query_builder

    return query_builder.eq("location_id", loc)

# ====================================================================
# SHARED COMPONENT: TOKEN & USER MANAGER
# ====================================================================
def _render_token_manager(supabase):
    st.markdown("### 🔑 SYSTEM ADMINISTRATION & PROVISIONING")
    st.info("💡 Notice: To ensure accurate system architecture testing, provisioned users will inherit the active God Mode matrix unless manually overridden below.")

    ref_data = get_static_reference_data(supabase)
    db_roles, db_locs, db_depts, db_brands = ref_data["roles"], ref_data["locations"], ref_data["departments"], ref_data["brands"]

    loc_idx = db_locs.index(st.session_state.get('location_id')) if st.session_state.get('location_id') in db_locs else 0
    dept_idx = db_depts.index(st.session_state.get('department_id')) if st.session_state.get('department_id') in db_depts else 0

    with st.form("direct_user_creation_form", clear_on_submit=True):
        st.markdown("#### 👤 INSTANTLY PROVISION TEST USER ACCOUNT")
        u_username = st.text_input("Username (e.g., test_rep)", key="tok_new_username").strip().lower()
        u_name = st.text_input("Display Name (e.g., John Doe)", key="tok_new_name").strip()
        u_pass = st.text_input("Account Password", type="password", key="tok_new_password").strip()

        uc1, uc2 = st.columns(2)
        u_role = uc1.selectbox("Assigned Role Matrix", db_roles, key="u_role_sel")
        u_loc = uc2.selectbox("Assigned Location", db_locs, index=loc_idx, key="u_loc_sel")
        u_dept = uc1.selectbox("Assigned Department Silo", db_depts, index=dept_idx, key="u_dept_sel")
        u_brand = uc2.selectbox("Assigned Brand Scope", db_brands, key="u_brand_sel")

        if st.form_submit_button("🚀 CREATE USER ACCOUNT IMMEDIATELY", use_container_width=True):
            if not u_username or not u_name or not u_pass:
                st.error("❌ All fields required.")
            else:
                hashed_pass = hashlib.sha256(u_pass.encode()).hexdigest()
                payload = {
                    "username": u_username, "name": u_name, "password": hashed_pass,
                    "role": u_role, "role_id": u_role, "location_id": u_loc,
                    "department_id": u_dept, "brand_id": u_brand
                }
                try:
                    supabase.table("users").insert(payload).execute()
                    st.success(f"🎉 Account `@{u_username}` successfully created!")
                except Exception as e: st.error(f"❌ Database rejection: {e}")

    st.markdown("---")
    st.markdown("### 🔑 ENTERPRISE AUTH TOKEN DECK")
    with st.form("generate_token_form", clear_on_submit=True):
        c_tok = st.text_input("Custom Token Name", key="tok_custom_name").strip()
        cc1, cc2 = st.columns(2)
        c_role = cc1.selectbox("Matrix Role Override", db_roles, key="t_role_sel")
        c_loc = cc2.selectbox("Location Identifier", db_locs, index=loc_idx, key="t_loc_sel")
        c_dept = cc1.selectbox("Department Access Silo", db_depts, index=dept_idx, key="t_dept_sel")
        c_brand = cc2.selectbox("Brand Scope Guard", db_brands, key="t_brand_sel")

        if st.form_submit_button("GENERATE TOKEN", use_container_width=True):
            if not c_tok:
                import secrets; c_tok = f"TK-{secrets.token_hex(4).upper()}"
            payload = {"token": c_tok, "role_id": c_role, "location_id": c_loc, "department_id": c_dept, "brand_id": c_brand, "is_active": True}
            try:
                supabase.table("auth_tokens").insert(payload).execute()
                st.success(f"🎉 Token established: `{c_tok}`"); safe_rerun()
            except Exception as e: st.error(f"Database rejection: {e}")

    try:
        tokens_res = supabase.table("auth_tokens").select("*").order("is_active", desc=True).execute().data
        if tokens_res:
            df_tokens = pd.DataFrame(tokens_res).drop(columns=['created_at'], errors='ignore')
            df_display = df_tokens.rename(columns={"token": "TOKEN KEY", "role_id": "ASSIGNED ROLE", "location_id": "LOCATION SCOPE", "department_id": "DEPT SCOPE", "brand_id": "BRAND SILO", "is_active": "ACTIVE STATUS"})
            edited_tokens = st.data_editor(df_display, disabled=["TOKEN KEY", "ASSIGNED ROLE", "LOCATION SCOPE", "DEPT SCOPE", "BRAND SILO"], hide_index=True, use_container_width=True, key="tok_data_editor")
            if st.button("COMMIT METADATA CHANGES", use_container_width=True, key="tok_commit_changes_btn"):
                chg = 0
                for i in range(len(edited_tokens)):
                    if bool(df_display.iloc[i]["ACTIVE STATUS"]) != bool(edited_tokens.iloc[i]["ACTIVE STATUS"]):
                        supabase.table("auth_tokens").update({"is_active": bool(edited_tokens.iloc[i]["ACTIVE STATUS"])}).eq("token", edited_tokens.iloc[i]["TOKEN KEY"]).execute(); chg += 1
                if chg > 0: st.success("✅ Synchronized."); safe_rerun()
    except: pass
