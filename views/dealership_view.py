import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
import random
import smtplib
import hashlib
from email.message import EmailMessage
from config import safe_rerun, get_ai_vehicle_specs, create_brochure_excel, SAST, get_static_reference_data

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
        u_username = st.text_input("Username (e.g., test_rep)").strip().lower()
        u_name = st.text_input("Display Name (e.g., John Doe)").strip()
        u_pass = st.text_input("Account Password", type="password").strip()
        
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
        c_tok = st.text_input("Custom Token Name").strip()
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
            edited_tokens = st.data_editor(df_display, disabled=["TOKEN KEY", "ASSIGNED ROLE", "LOCATION SCOPE", "DEPT SCOPE", "BRAND SILO"], hide_index=True, use_container_width=True)
            if st.button("COMMIT METADATA CHANGES", use_container_width=True):
                chg = 0
                for i in range(len(edited_tokens)):
                    if bool(df_display.iloc[i]["ACTIVE STATUS"]) != bool(edited_tokens.iloc[i]["ACTIVE STATUS"]):
                        supabase.table("auth_tokens").update({"is_active": bool(edited_tokens.iloc[i]["ACTIVE STATUS"])}).eq("token", edited_tokens.iloc[i]["TOKEN KEY"]).execute(); chg += 1
                if chg > 0: st.success("✅ Synchronized."); safe_rerun()
    except: pass

# ====================================================================
# MASTER RENDER ENGINE
# ====================================================================
def render(supabase, container_bg, text_color, metric_label, border_color, theme):
    role = str(st.session_state.get('role', '')).upper()
    active_dept = str(st.session_state.get('department_id', '')).upper()
    IS_MANAGEMENT = role in ['DEALER_PRINCIPAL', 'FINANCE_ADMIN', 'SALES_MANAGER', 'WORKSHOP_MANAGER', 'DIRECTOR', 'SUPER_USER']

    # ----------------------------------------------------------------
    # ROUTE A: SERVICE / WORKSHOP / PARTS DEPARTMENTS
    # ----------------------------------------------------------------
    if active_dept in ['SERVICE', 'PARTS'] or role == 'WORKSHOP_MANAGER':
        tab_labels = ["🔧 DAILY WIP", "📦 ARCHIVE", "📊 WIP REPORTS"]
        if active_dept == 'PARTS': tab_labels.append("📦 OTC SALES")
        if role == 'SUPER_USER': tab_labels.append("🔑 TOKEN MANAGER")

        tabs = st.tabs(tab_labels)
        t1, t2, t3 = tabs[0], tabs[1], tabs[2]
        _next = 3
        if active_dept == 'PARTS':
            t_otc = tabs[_next]; _next += 1
        else:
            t_otc = None
        t4 = tabs[_next] if role == 'SUPER_USER' else None

        with t1:
            st.markdown(f"### 🔧 {st.session_state.get('location_id', '').replace('_', ' ')} {active_dept} DESK")
            WIP_STAGES = ["Scheduled", "Checked In", "In Bay / Diag", "Waiting on Parts", "QC / Wash", "Ready for Delivery", "Invoiced / Closed"]
            
            with st.expander("➕ OPEN NEW REPAIR ORDER (RO)"):
                ca, cb = st.columns(2)
                ro_num = ca.text_input("RO NUMBER (DMS Sync)")
                cname = cb.text_input("CLIENT NAME")
                veh_desc = ca.text_input("VEHICLE (Model/Reg/VIN)")
                status = cb.selectbox("INITIAL STATUS", WIP_STAGES, index=1)
                adv = ca.text_input("SERVICE ADVISOR", value=st.session_state.get('name', 'Advisor'))
                tech = cb.text_input("ASSIGNED TECHNICIAN")
                val = ca.number_input("EST. RO VALUE (ZAR)", min_value=0.0, step=500.0)
                
                if st.button("CREATE RO"):
                    if ro_num and cname and veh_desc:
                        payload = {
                            "ro_number": ro_num, "client_name": cname, "vehicle_details": veh_desc,
                            "status": status, "service_advisor": adv, "technician": tech,
                            "estimated_value": val, "notes": "",
                            "location_id": st.session_state.get('location_id', 'BMW_SANDTON'), 
                            "department_id": "SERVICE", 
                            "brand_id": st.session_state.get('brand_id', 'BMW')
                        }
                        try:
                            supabase.table("service_wip").insert(payload).execute()
                            st.success("✅ RO Opened Successfully."); safe_rerun()
                        except Exception as e: st.error(f"Error: {e}")
                    else: st.warning("Please enter RO Number, Client, and Vehicle.")

            try:
                wip_query = apply_location_matrix_filters(supabase.table("service_wip").select("*").neq("status", "Invoiced / Closed"))
                res = wip_query.order("id", desc=True).execute().data or []
            except: res = []
            
            if not res: st.info("No active Repair Orders in the workshop right now.")
            else:
                df_wip = pd.DataFrame(res)
                m1, m2, m3 = st.columns(3)
                m1.metric("ACTIVE ROs", len(df_wip))
                m2.metric("WAITING ON PARTS", len(df_wip[df_wip['status'] == 'Waiting on Parts']))
                m3.metric("TOTAL WIP VALUE", f"R {df_wip['estimated_value'].astype(float).sum():,.2f}")
                st.markdown("---")
                
                PARTS_STAGES = ["Pending Diagnosis", "Parts Ordered", "ETA Delayed", "Parts Arrived"]
                IS_PARTS_VIEW = (active_dept == 'PARTS') or (role == 'PARTS_MANAGER')

                for _, r in df_wip.iterrows():
                    icon = "⏳" if r['status'] == "Waiting on Parts" else ("✅" if r['status'] == "Ready for Delivery" else "🔧")
                    parts_badge = ""
                    if r.get('parts_status') == 'ETA Delayed': parts_badge = " 🚨 [PARTS DELAYED]"
                    elif r.get('parts_status') == 'Parts Arrived': parts_badge = " ✅ [PARTS READY]"
                    with st.expander(f"{icon} RO: {r['ro_number']} | {r['client_name']} ({r['vehicle_details']}) — {r['status'].upper()}{parts_badge}"):
                        c1, c2 = st.columns([1, 2])

                        if IS_PARTS_VIEW:
                            # Parts staff: RO/workshop fields are read-only, parts fields are theirs to edit.
                            with c1:
                                st.markdown(f"**Advisor:** `{r['service_advisor']}`")
                                st.markdown(f"**Technician:** `{r.get('technician', '')}`")
                                st.markdown(f"**Value:** R {float(r.get('estimated_value', 0)):,.2f}")
                                st.text_input("RO STATUS (READ-ONLY)", value=r['status'], disabled=True, key=f"ws_ro_{r['id']}")
                                st.text_area("WORKSHOP NOTES (READ-ONLY)", value=str(r.get('notes', '')), height=130, key=f"wn_ro_{r['id']}", disabled=True)
                            with c2:
                                current_ps = r.get('parts_status') or PARTS_STAGES[0]
                                nps = st.selectbox("PARTS STATUS", PARTS_STAGES, index=PARTS_STAGES.index(current_ps) if current_ps in PARTS_STAGES else 0, key=f"ps_{r['id']}")
                                npn = st.text_area("PARTS NOTES", value=str(r.get('parts_notes', '')), height=130, key=f"pn_{r['id']}")
                            if st.button("💾 SAVE PARTS UPDATE", key=f"wu_{r['id']}"):
                                try:
                                    apply_location_matrix_filters(supabase.table("service_wip").update({"parts_status": nps, "parts_notes": npn})).eq("id", r['id']).execute(); safe_rerun()
                                except Exception as e: st.error(e)
                        else:
                            # Service/Workshop staff: keep control of the RO, view parts updates read-only.
                            with c1:
                                st.markdown(f"**Advisor:** `{r['service_advisor']}`")
                                st.markdown(f"**Value:** R {float(r.get('estimated_value', 0)):,.2f}")
                                ns = st.selectbox("UPDATE STATUS", WIP_STAGES, index=WIP_STAGES.index(r['status']) if r['status'] in WIP_STAGES else 0, key=f"ws_{r['id']}")
                                nt = st.text_input("TECHNICIAN", value=str(r.get('technician', '')), key=f"wt_{r['id']}")
                            with c2:
                                nn = st.text_area("WORKSHOP NOTES", value=str(r.get('notes', '')), height=130, key=f"wn_{r['id']}")
                                st.text_input("PARTS STATUS (READ-ONLY)", value=r.get('parts_status') or "—", disabled=True, key=f"ps_ro_{r['id']}")
                                st.text_area("PARTS NOTES (READ-ONLY)", value=str(r.get('parts_notes', '')), height=80, key=f"pn_ro_{r['id']}", disabled=True)
                            if st.button("💾 SAVE & UPDATE", key=f"wu_{r['id']}"):
                                try:
                                    apply_location_matrix_filters(supabase.table("service_wip").update({"status": ns, "technician": nt, "notes": nn})).eq("id", r['id']).execute(); safe_rerun()
                                except Exception as e: st.error(e)

        with t2:
            st.markdown(f"### 📦 {st.session_state.get('location_id', '').replace('_', ' ')} INVOICED / CLOSED RO ARCHIVE")
            try:
                arc_query = apply_location_matrix_filters(supabase.table("service_wip").select("*").eq("status", "Invoiced / Closed"))
                ares = arc_query.order("id", desc=True).execute().data or []
            except: ares = []
            
            if not ares: st.info(f"No closed Repair Orders in the archive for this branch.")
            else:
                df_a = pd.DataFrame(ares)
                df_a['DATE'] = pd.to_datetime(df_a.get('created_at', pd.Series(dtype=str))).dt.strftime('%d %b %Y').fillna("Unknown")
                
                ra = pd.DataFrame()
                ra["RO NUMBER"] = df_a["ro_number"]
                ra["CLIENT"] = df_a["client_name"]
                ra["ADVISOR"] = df_a["service_advisor"]
                ra["INVOICED VALUE"] = df_a.get("estimated_value", pd.Series([0]*len(df_a))).astype(float).map(lambda x: f"R {x:,.2f}")
                ra["DATE LOGGED"] = df_a["DATE"]
                
                st.dataframe(ra, hide_index=True, use_container_width=True)
                
                for _, r in df_a.iterrows():
                    with st.expander(f"📦 ARCHIVED RO: {r['ro_number']} | {r['client_name']} ({r['vehicle_details']})"):
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            ns = st.selectbox("REVISE STATUS", WIP_STAGES, index=WIP_STAGES.index(r['status']) if r['status'] in WIP_STAGES else 6, key=f"aws_{r['id']}")
                        with c2: 
                            nn = st.text_area("ARCHIVE NOTES", value=str(r.get('notes', '')), height=130, key=f"awn_{r['id']}")
                        if st.button("REOPEN RO", key=f"awu_{r['id']}"):
                            try: 
                                apply_location_matrix_filters(supabase.table("service_wip").update({"status": ns, "notes": nn})).eq("id", r['id']).execute(); safe_rerun()
                            except Exception as e: st.error(e)

        with t3:
            st.markdown(f"### 📊 {st.session_state.get('location_id', '').replace('_', ' ')} WORKSHOP REPORTING & EXTRACTION")
            st.info("💡 Paste your raw DMS Daily WIP Report here. The ingestion engine enforces strict filtering to only capture genuine RO lines.")
            
            raw_wip_paste = st.text_area("PASTE RAW DMS DATA HERE (From Excel or Kerridge/Drive)", height=200)
            
            if st.button("📊 INGEST & GENERATE REPORT", use_container_width=True):
                if raw_wip_paste.strip():
                    try:
                        lines = [line.strip() for line in raw_wip_paste.split('\n') if line.strip()]
                        
                        current_advisor = "Unassigned"
                        raw_headers = None
                        extracted_rows = []
                        
                        for line in lines:
                            if "WIP No" in line or "Customer name" in line:
                                separator = '\t' if '\t' in line else None
                                raw_headers = line.split(separator) if separator else re.split(r'\s{2,}', line)
                                continue
                            
                            if "opnum:" in line.lower():
                                parts = line.split('-', 1)
                                if len(parts) > 1:
                                    current_advisor = parts[1].strip()
                                else:
                                    current_advisor = line.replace("opnum:", "").strip()
                                continue
                                
                            separator = '\t' if '\t' in line else None
                            row_data = line.split(separator) if separator else re.split(r'\s{2,}', line)
                            
                            first_col = str(row_data[0]).strip()
                            if not first_col or not first_col[0].isdigit():
                                continue
                                
                            row_data.append(current_advisor)
                            extracted_rows.append(row_data)
                        
                        if not raw_headers:
                            raw_headers = ["WIP No", "Date in", "Customer name", "Reg no", "Make", "Labour", "Other/Sub", "Parts", "CES", "Total", "Acc No", "Track", "Notes1", "Notes2", "Notes3", "Ownop", "Bookin"]
                        
                        clean_headers = []
                        seen_headers = {}
                        for h in raw_headers:
                            h_clean = str(h).strip()
                            if not h_clean: h_clean = "Unnamed"
                            if h_clean in seen_headers:
                                seen_headers[h_clean] += 1
                                clean_headers.append(f"{h_clean}_{seen_headers[h_clean]}")
                            else:
                                seen_headers[h_clean] = 0
                                clean_headers.append(h_clean)
                        
                        clean_headers.append("Service_Advisor")
                        
                        max_cols = len(clean_headers)
                        normalized_rows = []
                        for row in extracted_rows:
                            if len(row) < max_cols:
                                advisor = row.pop()
                                row.extend([''] * (max_cols - len(row) - 1))
                                row.append(advisor)
                                normalized_rows.append(row)
                            else:
                                normalized_rows.append(row[:max_cols])
                                
                        df_report = pd.DataFrame(normalized_rows, columns=clean_headers)
                        
                        val_col = None
                        for col in df_report.columns:
                            if "total" in col.lower() and "wip" not in col.lower():
                                val_col = col
                                break
                        
                        if val_col:
                            df_report[val_col] = df_report[val_col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                            df_report[val_col] = pd.to_numeric(df_report[val_col], errors='coerce').fillna(0)
                            
                        cols = list(df_report.columns)
                        cols = [cols[-1]] + cols[:-1]
                        df_report = df_report[cols]
                        
                        st.success("✅ Cleaned: Duplicate totals ignored, headers deduped, and ROs strictly filtered.")
                        
                        if val_col:
                            st.markdown("### 📈 LIVE WORKSHOP METRICS")
                            c1, c2 = st.columns(2)
                            c1.metric("Total Extracted RO Value", f"R {df_report[val_col].sum():,.2f}")
                            c2.metric("Total Extracted Repair Orders", len(df_report))
                        
                        st.markdown("### 📋 ADVISOR WORK-IN-PROGRESS")
                        unique_advisors = sorted(df_report['Service_Advisor'].unique().tolist())
                        for advisor in unique_advisors:
                            if "Kerridge Vendor" in advisor: continue 
                            
                            adv_df = df_report[df_report['Service_Advisor'] == advisor].copy()
                            adv_total = adv_df[val_col].sum() if val_col else 0.0
                            
                            st.markdown(f"<div style='background-color:{container_bg}; padding:10px; border-left:4px solid {text_color}; margin-top:20px; font-weight:bold;'>👤 {advisor.upper()} | {len(adv_df)} ROs | R {adv_total:,.2f}</div>", unsafe_allow_html=True)
                            
                            display_df = adv_df.drop(columns=['Service_Advisor'])
                            if val_col:
                                display_df[val_col] = display_df[val_col].apply(lambda x: f"R {x:,.2f}")
                            
                            st.dataframe(display_df, hide_index=True, use_container_width=True)

                    except Exception as e:
                        st.error(f"Failed to process raw data: {e}")
                else:
                    st.warning("Please paste data into the field before generating.")

        if t_otc:
            with t_otc:
                st.markdown(f"### 📦 {st.session_state.get('location_id', '').replace('_', ' ')} OVER-THE-COUNTER PARTS SALES")

                with st.expander("➕ LOG RETAIL PARTS SALE"):
                    oc1, oc2 = st.columns(2)
                    inv_num = oc1.text_input("INVOICE NUMBER")
                    pclient = oc2.text_input("CLIENT NAME")
                    pdesc = st.text_area("PARTS DESCRIPTION", height=100)
                    ocap = oc1.number_input("CAPITAL COST (ZAR)", min_value=0.0, step=50.0)
                    oretail = oc2.number_input("RETAIL PRICE (ZAR)", min_value=0.0, step=50.0)
                    onet = oretail - ocap
                    st.metric("NET PROFIT", f"R {onet:,.2f}")

                    if st.button("💾 SAVE INVOICE", use_container_width=True):
                        if inv_num and pclient and pdesc:
                            otc_payload = {
                                "invoice_number": inv_num, "client_name": pclient, "parts_description": pdesc,
                                "capital_cost": ocap, "retail_price": oretail, "net_profit": onet,
                                "salesperson": st.session_state.get('user', ''),
                                "location_id": st.session_state.get('location_id'),
                                "department_id": st.session_state.get('department_id'),
                                "brand_id": st.session_state.get('brand_id')
                            }
                            try:
                                supabase.table("parts_otc").insert(otc_payload).execute()
                                st.success("✅ Invoice Logged."); safe_rerun()
                            except Exception as e: st.error(f"Error: {e}")
                        else:
                            st.warning("Enter invoice number, client name, and parts description.")

                try:
                    otc_query = apply_matrix_filters(supabase.table("parts_otc").select("*"))
                    otc_res = otc_query.order("id", desc=True).execute().data or []
                except: otc_res = []

                df_otc = pd.DataFrame(otc_res)
                if not df_otc.empty and 'created_at' in df_otc.columns:
                    today_str = datetime.now(SAST).strftime('%Y-%m-%d')
                    df_otc = df_otc[pd.to_datetime(df_otc['created_at'], errors='coerce').dt.strftime('%Y-%m-%d') == today_str]

                st.markdown("---")
                if df_otc.empty:
                    st.info("No OTC parts sales logged today for this branch.")
                else:
                    st.metric("TODAY'S NET PROFIT", f"R {df_otc['net_profit'].astype(float).sum():,.2f}")
                    do = df_otc.rename(columns={
                        "invoice_number": "INVOICE", "client_name": "CLIENT", "parts_description": "DESCRIPTION",
                        "capital_cost": "CAPITAL COST", "retail_price": "RETAIL PRICE", "net_profit": "NET PROFIT",
                        "salesperson": "SALESPERSON"
                    })
                    for col in ["CAPITAL COST", "RETAIL PRICE", "NET PROFIT"]:
                        do[col] = do[col].astype(float).map(lambda x: f"R {x:,.2f}")
                    st.dataframe(do[["INVOICE", "CLIENT", "DESCRIPTION", "CAPITAL COST", "RETAIL PRICE", "NET PROFIT", "SALESPERSON"]], hide_index=True, use_container_width=True)

        if t4:
            with t4: _render_token_manager(supabase)

    # ----------------------------------------------------------------
    # ROUTE C: HUMAN RESOURCES DEPARTMENT
    # ----------------------------------------------------------------
    elif active_dept == 'HR':
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

    # ----------------------------------------------------------------
    # ROUTE B: SALES / ADMIN DEPARTMENTS
    # ----------------------------------------------------------------
    else:
        IS_DOC_ADMIN = role in ['FINANCE_ADMIN', 'DEALER_PRINCIPAL', 'SUPER_USER']

        tab_labels = ["🔥 FEED", "💼 CLAIMED", "🚗 STOCKROOM", "💼 PIPELINE", "📦 ARCHIVE"]
        if IS_MANAGEMENT: tab_labels += ["📊 OVERVIEW", "💰 F&I DESK"]
        if IS_DOC_ADMIN: tab_labels.append("📉 DOC OVERHEADS")
        if role == 'SUPER_USER': tab_labels.append("🔑 TOKEN MANAGER")

        tabs = st.tabs(tab_labels)
        t1, t2, t3, t4, t5 = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4]
        _next = 5
        if IS_MANAGEMENT:
            t6, t7 = tabs[_next], tabs[_next + 1]; _next += 2
        else:
            t6 = t7 = None
        if IS_DOC_ADMIN:
            t_doc = tabs[_next]; _next += 1
        else:
            t_doc = None
        t8 = tabs[_next] if role == 'SUPER_USER' else None

        with t1:
            if role in ['SUPER_USER', 'DIRECTOR']:
                with st.expander("🤖 LEAD INJECTION ENGINE (SUPER USER ONLY)"):
                    st.caption(f"Leads injected here will be routed directly to the active node: {st.session_state.get('location_id')}")
                    if st.button("🔥 INJECT 12 NEW LEADS", key="inject_leads_btn"):
                        today_str = datetime.now(SAST).strftime('%Y-%m-%d')
                        b2b_list = [{"company": "Apex Logistics", "location": "Sandton", "target": "Fleet Manager", "score": random.randint(80, 99), "lead_date": today_str, "signal": "Expanding executive luxury fleet.", "status": "Unassigned", "location_id": st.session_state.get('location_id'), "department_id": st.session_state.get('department_id', 'NEW_SALES'), "brand_id": "BMW"}]
                        b2c_list = [{"client_name": "Sarah Jenkins", "title": "Senior Partner", "company": "Bowmans Law", "location": "Sandton", "score": random.randint(75, 99), "lead_date": today_str, "signal": "Current X5 M Competition lease expiring.", "status": "Unassigned", "location_id": st.session_state.get('location_id'), "department_id": st.session_state.get('department_id', 'NEW_SALES'), "brand_id": "BMW"}]
                        with st.spinner("Injecting fresh leads..."):
                            try:
                                supabase.table("leads").insert(b2b_list).execute()
                                supabase.table("individual_leads").insert(b2c_list).execute()
                                st.success("✅ Local Leads Injected!"); safe_rerun()
                            except Exception as e: st.error(f"Injection Failed: {e}")
            
            lead_section = st.radio("SELECT OPPORTUNITY CHANNEL", ["🏢 Corporate Fleet (B2B)", "🚗 Individual Leads (B2C)", "🏛️ Gov Tenders (B2B)"], horizontal=True)
            filter_date_str = st.date_input("FILTER BY GENERATION DATE", datetime.now(SAST)).strftime('%Y-%m-%d')
            st.markdown("---")
            
            tbl_map = {"🏢 Corporate Fleet (B2B)": "leads", "🚗 Individual Leads (B2C)": "individual_leads", "🏛️ Gov Tenders (B2B)": "tender_leads"}
            active_tbl = tbl_map[lead_section]
            
            try: 
                base_query = supabase.table(active_tbl).select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str)
                secure_query = apply_matrix_filters(base_query)
                res = secure_query.order("score", desc=True).execute().data
            except: res = []
            
            df_leads = pd.DataFrame(res) if res else pd.DataFrame()
            
            if df_leads.empty: st.info(f"No unassigned {lead_section.split(' ')[1].lower()} leads found in {st.session_state.get('location_id')} for this date.")
            else:
                for idx, row in df_leads.iterrows():
                    col_score, col_content = st.columns([1, 5])
                    col_score.metric("SCORE", f"{row['score']}/100")
                    with col_content:
                        if active_tbl == "leads":
                            st.markdown(f"### {row['company'].upper()} — {row['location'].upper()}")
                            st.markdown(f"**TARGET PERSONA:** {row['target']}  |  📅 *GENERATED: {row['lead_date']}*")
                            st.info(f"💡 {row['signal']}")
                        elif active_tbl == "individual_leads":
                            st.markdown(f"### PROSPECT: {row.get('client_name', '').upper()}")
                            st.markdown(f"**POSITION:** {row.get('title', '')} at *{row.get('company', '')}* ({row.get('location', '')})  |  📅 *GENERATED: {row['lead_date']}*")
                            st.info(f"💎 {row['signal']}")
                        else:
                            st.markdown(f"### VENDOR: {row.get('company', '').upper()}")
                            st.markdown(f"**AWARDING BODY:** {row.get('awarding_body', '')}  |  💰 **VALUE:** `{row.get('contract_value', '')}`")
                            st.info(f"🏛️ {row.get('tender_desc', '')}")
                            
                        if st.button("CLAIM LEAD", key=f"claim_{active_tbl}_{row['id']}"): 
                            supabase.table(active_tbl).update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute(); safe_rerun()

        with t2:
            try: my_corp = supabase.table("leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").order("id", desc=True).execute().data
            except: my_corp = []
            try: my_ind = supabase.table("individual_leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").order("id", desc=True).execute().data
            except: my_ind = []
            try: my_tend = supabase.table("tender_leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").order("id", desc=True).execute().data
            except: my_tend = []
            
            for title, data, tbl_name in [("🏢 CORPORATE FLEET ACCOUNTS", my_corp, "leads"), ("🚗 PRIVATE LUXURY CLIENTS", my_ind, "individual_leads"), ("🏛️ TENDER VENDORS", my_tend, "tender_leads")]:
                st.markdown(f"### {title}")
                if not data: st.caption("No active claims.")
                else:
                    for row in data:
                        name_display = row.get('company', row.get('client_name', '')).upper()
                        with st.expander(f"{name_display}"):
                            st.write(f"**SIGNAL:** {row.get('signal', row.get('tender_desc', ''))}")
                            c_i1, c_i2, c_i3 = st.columns(3)
                            c_i1.markdown(f"**Email:** `{row.get('public_email', '')}`")
                            c_i2.markdown(f"**Phone:** `{row.get('public_phone', '')}`")
                            c_i3.markdown(f"**LinkedIn:** [Link]({row.get('linkedin_url', '')})")
                            st.markdown("---")
                            note_text = st.text_area("LOG NOTE", key=f"n_{tbl_name}_{row['id']}")
                            if st.button("SAVE LOG NOTE", key=f"s_{tbl_name}_{row['id']}") and note_text:
                                supabase.table("lead_notes").insert({"lead_id": row['id'], "lead_type": tbl_name.replace("_leads", ""), "username": st.session_state['user'], "salesperson_name": st.session_state['name'], "note_text": note_text, "timestamp": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')}).execute()
                                st.success("Note committed."); safe_rerun()
                            ac1, ac2, ac3 = st.columns(3)
                            if ac1.button("✅ CLOSE", key=f"cl_{tbl_name}_{row['id']}"): supabase.table(tbl_name).update({"status": "Closed"}).eq("id", row['id']).execute(); safe_rerun()
                            if ac2.button("💀 DEAD", key=f"dead_{tbl_name}_{row['id']}"): supabase.table(tbl_name).update({"status": "Dead"}).eq("id", row['id']).execute(); safe_rerun()
                            if ac3.button("🔄 UNCLAIM", key=f"uncl_{tbl_name}_{row['id']}"): supabase.table(tbl_name).update({"status": "Unassigned", "assigned_to": None}).eq("id", row['id']).execute(); safe_rerun()
                st.markdown("---")

        with t3:
            st.markdown(f"### 🚗 {st.session_state.get('location_id', '').replace('_', ' ')} USED CAR STOCKROOM")
            try:
                base_stock = supabase.table("used_car_stock").select("*")
                secure_stock = apply_matrix_filters(base_stock)
                stock_res = secure_stock.order("days_in_stock", desc=True).execute().data
                df_live_stock = pd.DataFrame(stock_res) if stock_res else pd.DataFrame()
            except Exception as e: df_live_stock = pd.DataFrame()

            if df_live_stock.empty:
                 df_live_stock = pd.DataFrame(columns=["vsb_no", "description", "into_stock", "days_in_stock", "total_value", "location", "floorplan_status", "chassis_no", "comments", "stock_type"])

            df_live_stock['floorplan_status'] = df_live_stock.get('floorplan_status', "⚪ PENDING RECON")
            df_live_stock['chassis_no'] = df_live_stock.get('chassis_no', "N/A")
            df_live_stock['comments'] = df_live_stock.get('comments', "").fillna("")
            df_live_stock['stock_type'] = df_live_stock.get('stock_type', "Used").fillna("Used")
            
            def map_fp_status(status):
                if str(status) == "ON FLOORPLAN": return "🏦 ON FLOORPLAN"
                elif str(status) == "UNENCUMBERED": return "🟢 UNENCUMBERED"
                elif str(status) == "SOLD - PENDING DELIVERY": return "🔒 SOLD - PENDING DELIVERY"
                return "⚪ PENDING RECON"

            df_live_stock["floorplan_status"] = df_live_stock["floorplan_status"].apply(map_fp_status)
            df_live_stock["location"] = df_live_stock.get("location", "").astype(str).str.strip()
            df_live_stock["FRANCHISE DIVISION"] = df_live_stock.apply(lambda x: f"{x['location']} (DEMO)" if str(x.get('stock_type')) == 'Demo' else x['location'], axis=1)
                
            df_live_stock = df_live_stock.rename(columns={
                "vsb_no": "VSB NUMBER", "description": "VEHICLE DESCRIPTION", "into_stock": "INTO STOCK DATE",
                "days_in_stock": "DAYS ON FLOOR", "total_value": "CAPITAL VAL (ZAR)",
                "floorplan_status": "FP STATUS", "chassis_no": "CHASSIS / VIN", "comments": "ADMIN COMMENTS"
            })
            
            s_col1, s_col2, s_col3 = st.columns(3)
            s_col1.metric("TOTAL VEHICLES", f"{len(df_live_stock) if not df_live_stock.empty else 0:,} UNITS")
            s_col2.metric("TOTAL CAPITAL", f"R {df_live_stock.get('CAPITAL VAL (ZAR)', pd.Series([0])).sum():,.2f}")
            s_col3.metric("AVG FLOOR AGE", f"{int(df_live_stock.get('DAYS ON FLOOR', pd.Series([0])).mean()) if not df_live_stock.empty else 0} DAYS")
            st.markdown("---")
            
            SHOW_UNENCUMBERED = role in ['FINANCE_ADMIN', 'DEALER_PRINCIPAL', 'DIRECTOR', 'SUPER_USER']
            if SHOW_UNENCUMBERED: sm_tabs = st.tabs(["🌍 USED", "🔵 DEMO", "🟢 UNENCUMBERED"])
            else: sm_tabs = st.tabs(["🌍 USED", "🔵 DEMO"])
            
            with sm_tabs[0]:
                if role in ['FINANCE_ADMIN', 'SUPER_USER']:
                    with st.expander(f"🛠️ ADMIN CONSOLE: {st.session_state.get('location_id')} UPLOAD", expanded=False):
                        raw_paste_data = st.text_area("PASTE RAW DATA ROWS HERE", height=150, key="used_paste")
                        if st.button("PROCESS OVERWRITE", key="process_stock_paste_btn") and raw_paste_data.strip():
                            try:
                                mem_query = apply_matrix_filters(supabase.table("used_car_stock").select("vsb_no, comments"))
                                try: mem_res = mem_query.execute().data
                                except: mem_res = []
                                comment_memory = {str(r['vsb_no']).strip(): r.get('comments', '') for r in mem_res} if mem_res else {}
                                    
                                del_query = apply_matrix_filters(supabase.table("used_car_stock").delete().eq("stock_type", "Used").gt("days_in_stock", -1))
                                del_query.execute()
                                
                                records_processed = 0; current_franchise = "General Used Stock"
                                for line in raw_paste_data.split('\n'):
                                    cleaned_line = line.strip()
                                    if not cleaned_line: continue
                                    if "franchise:" in cleaned_line.lower():
                                        current_franchise = cleaned_line.split(':', 1)[1].strip()
                                        continue
                                    
                                    if '\t' in cleaned_line: parts = cleaned_line.split('\t')
                                    elif ',' in cleaned_line: parts = cleaned_line.split(',')
                                    else: parts = re.split(r'\s{2,}', cleaned_line)
                                    
                                    if len(parts) >= 2 and parts[0].strip().isdigit():
                                        vsb, desc = parts[0].strip(), parts[1].strip()
                                        into_stk = parts[2].strip() if len(parts) > 2 else ''
                                        val, days, chassis = 0.00, 0, ''
                                        
                                        if len(parts) >= 12:
                                            try: val = float(parts[10].strip().replace(' ', '').replace(',', ''))
                                            except: val = 0.00
                                            try: days = int(float(parts[11].strip().replace(' ', '')))
                                            except: days = 0
                                            chassis = parts[13].strip() if len(parts) > 13 else ''
                                                    
                                        insert_payload = {
                                            "vsb_no": vsb, "description": desc, "into_stock": into_stk, 
                                            "days_in_stock": days, "total_value": val, "location": current_franchise.strip(), 
                                            "chassis_no": chassis, "floorplan_status": "⚪ PENDING RECON", 
                                            "comments": comment_memory.get(vsb, ""), "stock_type": "Used",
                                            "location_id": st.session_state.get('location_id', 'BMW_SANDTON'),
                                            "department_id": "USED_SALES", 
                                            "brand_id": st.session_state.get('brand_id', 'ALL_BRANDS')
                                        }
                                        try: supabase.table("used_car_stock").upsert(insert_payload).execute()
                                        except: pass
                                        records_processed += 1
                                st.success(f"🎉 Stock refreshed successfully. {records_processed} units isolated to {st.session_state.get('location_id')}."); safe_rerun()
                            except Exception as parse_ex: st.error(f"Data processing failed: {str(parse_ex)}")

                if df_live_stock.empty:
                    st.info(f"No vehicles are currently recorded in {st.session_state.get('location_id')}.")
                else:
                    st.markdown("### 📄 AI DIGITAL BROCHURE STUDIO")
                    vehicle_series = df_live_stock['VSB NUMBER'].astype(str) + " - " + df_live_stock['VEHICLE DESCRIPTION']
                    selected_brochure = st.selectbox("SEARCH INVENTORY FOR BROCHURE GENERATION", ["Select a Vehicle..."] + vehicle_series.tolist())
                    
                    if selected_brochure != "Select a Vehicle...":
                        sel_vsb = selected_brochure.split(" - ")[0]
                        car_row = df_live_stock[df_live_stock['VSB NUMBER'] == sel_vsb].iloc[0]
                        st.markdown(f"**Vehicle Selected:** `{car_row['VEHICLE DESCRIPTION']}`")
                        with st.spinner("🤖 Gemini AI is decoding the VIN..."):
                            ai_specs = get_ai_vehicle_specs(description=car_row['VEHICLE DESCRIPTION'], franchise=car_row['FRANCHISE DIVISION'], vin=car_row.get('CHASSIS / VIN', 'N/A'))
                            
                        specs_to_render = {
                            "Engine Configuration": ai_specs.get("engine_configuration", "N/A"), "Transmission": ai_specs.get("transmission", "N/A"),
                            "Drivetrain": ai_specs.get("drivetrain", "N/A"), "Power Output": ai_specs.get("power_output", "N/A"), "Torque": ai_specs.get("torque", "N/A"),
                            "0-100 km/h Acceleration": ai_specs.get("acceleration_0_100", "N/A"), "Fuel Economy": ai_specs.get("fuel_economy", "N/A"),
                            "Body Classification": ai_specs.get("body_classification", "N/A"), "Current Mileage (km)": "Enter Current Mileage...",
                            "Active Motorplan / Warranty": "Yes / No (Update Here)"
                        }
                        
                        car_details = {"desc": car_row['VEHICLE DESCRIPTION'], "vsb": car_row['VSB NUMBER'], "vin": car_row.get('CHASSIS / VIN', 'N/A'), "price": f"R {float(car_row.get('CAPITAL VAL (ZAR)', 0)):,.2f}", "raw_price": float(car_row.get('CAPITAL VAL (ZAR)', 0))}

                        col_b1, col_b2 = st.columns([1, 2])
                        with col_b1:
                            st.write("**AI Verified Specs:**")
                            for k, v in specs_to_render.items(): st.write(f"- **{k}:** {v}")
                        with col_b2:
                            try:
                                excel_bytes = create_brochure_excel(car_details, specs_to_render)
                                st.download_button(label="📥 DOWNLOAD EXCEL SPEC SHEET", data=excel_bytes, file_name=f"PhaseV_Spec_Sheet_{sel_vsb}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                            except Exception as e: st.error(f"Failed Excel generation: {e}")

                        st.markdown("---")
                        st.markdown("##### ✉️ DIRECT CLIENT DISPATCH")
                        client_email = st.text_input("Client Email Address", key=f"brochure_email_{sel_vsb}")
                        personal_message = st.text_area("Personalized Message (Optional)", key=f"brochure_msg_{sel_vsb}")

                        if st.button("🚀 SEND DIGITAL BROCHURE", key=f"brochure_send_{sel_vsb}"):
                            if not client_email.strip():
                                st.warning("⚠️ Please provide a client email address before dispatching.")
                            else:
                                specs_rows = "".join(
                                    f"<tr><td style='padding:6px 12px;border:1px solid #ddd;'><strong>{k}</strong></td>"
                                    f"<td style='padding:6px 12px;border:1px solid #ddd;'>{v}</td></tr>"
                                    for k, v in specs_to_render.items()
                                )
                                html_body = f"""
                                <html>
                                  <body style="font-family: Arial, sans-serif; color: #222;">
                                    {f'<p>{personal_message}</p>' if personal_message.strip() else ''}
                                    <h2 style="color:#0066b1;">{car_details['desc']}</h2>
                                    <p><strong>Retail Price:</strong> {car_details['price']}</p>
                                    <table style="border-collapse: collapse; margin-top: 10px;">
                                      {specs_rows}
                                    </table>
                                    <p style="margin-top:20px;color:#888;font-size:12px;">Sent via Phase V Enterprise Digital Brochure Studio.</p>
                                  </body>
                                </html>
                                """
                                try:
                                    with st.spinner("Transmitting to client..."):
                                        msg = EmailMessage()
                                        msg["Subject"] = f"Vehicle Brochure: {car_details['desc']}"
                                        msg["From"] = st.secrets["smtp"]["username"]
                                        msg["To"] = client_email.strip()
                                        msg.set_content("Please view this email in an HTML-capable client to see the digital brochure.")
                                        msg.add_alternative(html_body, subtype="html")

                                        with smtplib.SMTP(st.secrets["smtp"]["server"], st.secrets["smtp"]["port"]) as server:
                                            server.starttls()
                                            server.login(st.secrets["smtp"]["username"], st.secrets["smtp"]["password"])
                                            server.send_message(msg)

                                    st.success("✅ Digital Brochure delivered successfully!")
                                except Exception as e:
                                    st.error(f"Failed to send brochure: {e}")

                    st.markdown("---")
                    unique_franchises_options = sorted([f for f in df_live_stock["FRANCHISE DIVISION"].unique() if f.strip() and f.strip() != "LHP"])
                    cf1, cf2, cf3 = st.columns([2, 2, 1])
                    sel_franchises = cf1.multiselect("FILTER BY DIVISION", options=unique_franchises_options)
                    search_query = cf2.text_input("🔍 LIVE SEARCH", "").strip().lower()
                    show_hot_only = cf3.checkbox("🔥 SHOW HOT STOCKS ONLY", value=False)
                    
                    filtered_df = df_live_stock.copy()
                    if sel_franchises: filtered_df = filtered_df[filtered_df["FRANCHISE DIVISION"].isin(sel_franchises)]
                    if search_query: filtered_df = filtered_df[filtered_df['VEHICLE DESCRIPTION'].astype(str).str.lower().str.contains(search_query) | filtered_df['VSB NUMBER'].astype(str).str.lower().str.contains(search_query)]
                    if show_hot_only: filtered_df = filtered_df[filtered_df["DAYS ON FLOOR"] <= 3]
                    
                    used_filtered = filtered_df[~filtered_df["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True, na=False)]
                    for franchise in sorted(list(used_filtered["FRANCHISE DIVISION"].unique())):
                        if franchise.strip() == "LHP" or not franchise.strip(): continue
                        f_df = used_filtered[used_filtered["FRANCHISE DIVISION"] == franchise]
                        if not f_df.empty:
                            st.markdown(f"<div class='franchise-header-banner'>🏢 {franchise.upper()} &nbsp;|&nbsp; <span style='font-weight: 300;'>({len(f_df)} Units — Subtotal: R {f_df['CAPITAL VAL (ZAR)'].sum():,.2f})</span></div>", unsafe_allow_html=True)
                            r_rows = []
                            for _, row in f_df.iterrows():
                                days = int(row.get("DAYS ON FLOOR", 0))
                                dbadge = "🔥 NEW STOCK" if days <= 3 else (f"🚨 {days} DAYS (Max Prov)" if days >= 121 else (f"⚠️ {days} DAYS" if days >= 91 else f"{days} Days"))
                                rd = {"VSB NUMBER": row.get("VSB NUMBER", ""), "VEHICLE DESCRIPTION": row.get("VEHICLE DESCRIPTION", ""), "INTO STOCK DATE": row.get("INTO STOCK DATE", ""), "DAYS ON FLOOR": dbadge}
                                if IS_MANAGEMENT: rd["FP STATUS"] = row.get("FP STATUS", "")
                                rd["CAPITAL VAL (ZAR)"] = f"R {float(row.get('CAPITAL VAL (ZAR)', 0)):,.2f}"
                                r_rows.append(rd)
                            cols = ["VSB NUMBER", "VEHICLE DESCRIPTION", "INTO STOCK DATE", "DAYS ON FLOOR"] + (["FP STATUS"] if IS_MANAGEMENT else []) + ["CAPITAL VAL (ZAR)"]
                            st.dataframe(pd.DataFrame(r_rows)[cols], hide_index=True, use_container_width=True)

            with sm_tabs[1]:
                st.markdown("#### 🔵 DEMO VEHICLES PORTAL")
                if role in ['FINANCE_ADMIN', 'SUPER_USER']:
                    with st.expander(f"🛠️ ADMIN CONSOLE: {st.session_state.get('location_id')} DEMO UPLOAD", expanded=False):
                        raw_demo = st.text_area("PASTE RAW DATA ROWS HERE (DEMO)", height=150, key="demo_paste")
                        if st.button("PROCESS OVERWRITE DEMO", key="process_demo_btn") and raw_demo.strip():
                            try:
                                mem_query = apply_matrix_filters(supabase.table("used_car_stock").select("vsb_no, comments"))
                                try: mem_res = mem_query.execute().data
                                except: mem_res = []
                                mem = {str(r['vsb_no']).strip(): r.get('comments', '') for r in mem_res} if mem_res else {}
                                
                                del_query = apply_matrix_filters(supabase.table("used_car_stock").delete().eq("stock_type", "Demo").gt("days_in_stock", -1))
                                del_query.execute()
                                
                                recs = 0; cf = "General Demo"
                                for line in raw_demo.split('\n'):
                                    cl = line.strip()
                                    if not cl: continue
                                    if "franchise:" in cl.lower(): cf = cl.split(':', 1)[1].strip(); continue
                                    
                                    if '\t' in cl: parts = cl.split('\t')
                                    elif ',' in cl: parts = cl.split(',')
                                    else: parts = re.split(r'\s{2,}', cl)
                                    
                                    if len(parts) >= 2 and parts[0].strip().isdigit():
                                        vsb, desc = parts[0].strip(), parts[1].strip()
                                        into = parts[2].strip() if len(parts) > 2 else ''
                                        val, days, chassis = 0.00, 0, ''
                                        
                                        if len(parts) >= 12:
                                            try: val = float(parts[10].strip().replace(' ', '').replace(',', ''))
                                            except: val = 0.00
                                            try: days = int(float(parts[11].strip().replace(' ', '')))
                                            except: days = 0
                                            chassis = parts[13].strip() if len(parts) > 13 else ''
                                            
                                        insert_payload = {
                                            "vsb_no": vsb, "description": desc, "into_stock": into, 
                                            "days_in_stock": days, "total_value": val, "location": cf.strip(), 
                                            "chassis_no": chassis, "floorplan_status": "⚪ PENDING RECON", 
                                            "comments": mem.get(vsb, ""), "stock_type": "Demo",
                                            "location_id": st.session_state.get('location_id', 'BMW_SANDTON'),
                                            "department_id": "NEW_SALES",
                                            "brand_id": st.session_state.get('brand_id', 'ALL_BRANDS')
                                        }
                                        supabase.table("used_car_stock").upsert(insert_payload).execute()
                                        recs += 1
                                st.success(f"🎉 Demo Stock refreshed. {recs} units isolated to {st.session_state.get('location_id')}."); safe_rerun()
                            except Exception as e: st.error(f"Error: {e}")
                            
                if df_live_stock.empty:
                    st.info(f"No Demo vehicles are currently recorded in {st.session_state.get('location_id')}.")
                else:
                    demo_filtered = filtered_df[filtered_df["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True, na=False)]
                    if demo_filtered.empty: st.info("No Demo vehicles currently recorded.")
                    else:
                        for franchise in sorted(list(demo_filtered["FRANCHISE DIVISION"].unique())):
                            fdf = demo_filtered[demo_filtered["FRANCHISE DIVISION"] == franchise]
                            if not fdf.empty:
                                st.markdown(f"<div class='franchise-header-banner'>🔵 {franchise.upper()} &nbsp;|&nbsp; <span style='font-weight: 300;'>({len(fdf)} Units — Subtotal: R {fdf['CAPITAL VAL (ZAR)'].sum():,.2f})</span></div>", unsafe_allow_html=True)
                                render_rows = []
                                for _, r in fdf.iterrows():
                                    rd = {"VSB NUMBER": r.get("VSB NUMBER", ""), "VEHICLE DESCRIPTION": r.get("VEHICLE DESCRIPTION", ""), "INTO STOCK DATE": r.get("INTO STOCK DATE", ""), "DAYS ON FLOOR": f"{int(r.get('DAYS ON FLOOR', 0))} Days"}
                                    if IS_MANAGEMENT: rd["FP STATUS"] = r.get("FP STATUS", "")
                                    rd["CAPITAL VAL (ZAR)"] = f"R {float(r.get('CAPITAL VAL (ZAR)', 0)):,.2f}"
                                    render_rows.append(rd)
                                cols = ["VSB NUMBER", "VEHICLE DESCRIPTION", "INTO STOCK DATE", "DAYS ON FLOOR"] + (["FP STATUS"] if IS_MANAGEMENT else []) + ["CAPITAL VAL (ZAR)"]
                                st.dataframe(pd.DataFrame(render_rows)[cols], hide_index=True, use_container_width=True)

            if SHOW_UNENCUMBERED:
                with sm_tabs[2]:
                    st.markdown("#### 🟢 UNENCUMBERED VEHICLES REGISTER")
                    if df_live_stock.empty:
                        st.info("No vehicles available.")
                    else:
                        unenc_df = df_live_stock[df_live_stock["FP STATUS"] == "🟢 UNENCUMBERED"].copy().reset_index(drop=True)
                        if unenc_df.empty: st.info("No unencumbered vehicles found on the current floorplan recon.")
                        else:
                            edit_cols = ["VSB NUMBER", "VEHICLE DESCRIPTION", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)", "ADMIN COMMENTS"]
                            e_unenc = st.data_editor(unenc_df[edit_cols], disabled=["VSB NUMBER", "VEHICLE DESCRIPTION", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)"], hide_index=True, use_container_width=True, key="u_edit")
                            if st.button("💾 SAVE COMMENTS", key="save_u_comments"):
                                uc = 0
                                for i in range(len(e_unenc)):
                                    if str(unenc_df.iloc[i]["ADMIN COMMENTS"]).strip() != str(e_unenc.iloc[i]["ADMIN COMMENTS"]).strip():
                                        try: supabase.table("used_car_stock").update({"comments": str(e_unenc.iloc[i]["ADMIN COMMENTS"]).strip()}).eq("vsb_no", e_unenc.iloc[i]["VSB NUMBER"]).execute(); uc += 1
                                        except: pass
                                if uc > 0: st.success(f"✅ {uc} saved."); safe_rerun()

        with t4:
            st.markdown(f"### 💼 {st.session_state.get('location_id', '').replace('_', ' ')} SALES PIPELINE")
            PIPELINE_STAGES = ["Prospecting", "Test Drive", "Finance App", "Awaiting Delivery", "Delivered", "Cancelled"]
            with st.expander("➕ ADD NEW DEAL"):
                ca, cb = st.columns(2)
                cname = ca.text_input("CLIENT NAME")
                try: 
                    p_query = apply_matrix_filters(supabase.table("used_car_stock").select("vsb_no, description"))
                    p_stock = p_query.execute().data or []
                except: p_stock = []
                
                opts = ["✏️ CUSTOM ENTRY (Not in Stock)"] + [f"{s['vsb_no']} - {s['description']}" for s in p_stock]
                sel_s = cb.selectbox("LINK TO INVENTORY", opts)
                ddesc = cb.text_input("ENTER CUSTOM DEAL DESC") if sel_s == "✏️ CUSTOM ENTRY (Not in Stock)" else sel_s
                stage = ca.selectbox("STAGE", PIPELINE_STAGES)
                ddate = ca.date_input("PLANNED DELIVERY", datetime.now(SAST))
                val = cb.number_input("EST. VALUE (ZAR)", min_value=0.0)
                if st.button("COMMIT DEAL"):
                    if cname and ddesc:
                        linked_vsb = sel_s.split(" - ")[0] if sel_s != "✏️ CUSTOM ENTRY (Not in Stock)" else None
                        insert_payload = {
                            "salesperson_username": st.session_state['user'], "client_name": cname,
                            "deal_description": ddesc, "stage": stage, "estimated_value": val,
                            "planned_delivery_date": ddate.strftime('%Y-%m-%d'), "notes": "",
                            "linked_vsb": linked_vsb,
                            "location_id": st.session_state['location_id'],
                            "department_id": st.session_state['department_id'],
                            "brand_id": st.session_state['brand_id']
                        }
                        try: supabase.table("sales_pipeline").insert(insert_payload).execute(); st.success("Logged."); safe_rerun()
                        except Exception as e: st.error(f"Error: {e}")
                    else: st.warning("Enter client name and description.")

            try: 
                pipe_query = apply_matrix_filters(supabase.table("sales_pipeline").select("*").neq("stage", "Delivered"))
                res = pipe_query.order("id", desc=True).execute().data or []
            except: res = []
            
            if not IS_MANAGEMENT: res = [r for r in res if r['salesperson_username'] == st.session_state['user']]
            
            if not res: st.info(f"No active pipeline deals in {st.session_state.get('location_id')}.")
            else:
                df_p = pd.DataFrame(res)
                rp = pd.DataFrame()
                if IS_MANAGEMENT: rp["REP"] = df_p["salesperson_username"].apply(lambda x: f"@{x}")
                rp["CLIENT"] = df_p["client_name"]
                rp["DEAL"] = df_p["deal_description"]
                rp["VSB"] = df_p.get("linked_vsb", pd.Series([None]*len(df_p))).apply(lambda x: x if pd.notna(x) and str(x).strip() else "Custom")
                rp["STAGE"] = df_p["stage"]
                rp["EST VALUE"] = df_p.get("estimated_value", pd.Series([0]*len(df_p))).map(lambda x: f"R {float(x):,.2f}")
                rp["DELIVERY"] = pd.to_datetime(df_p.get("planned_delivery_date", pd.Series()), errors='coerce').dt.strftime('%d %b %Y').fillna("Unscheduled")
                st.dataframe(rp, hide_index=True, use_container_width=True)
                
                for _, r in df_p.iterrows():
                    icon = "🛑" if r['stage'] == "Cancelled" else "⏳"
                    with st.expander(f"{icon} {r['client_name'].upper()} | {r['deal_description']} — {r['stage'].upper()}"):
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.markdown(f"**REP:** `@{r['salesperson_username']}`")
                            st.markdown(f"**EST. VALUE:** R {float(r.get('estimated_value', 0)):,.2f}")
                            st.markdown(f"**LINKED VSB:** `{r.get('linked_vsb') or 'Custom Deal'}`")
                            ns = st.selectbox("STATUS", PIPELINE_STAGES, index=PIPELINE_STAGES.index(r['stage']) if r['stage'] in PIPELINE_STAGES else 0, key=f"s_{r['id']}")
                            try: d = datetime.strptime(str(r.get('planned_delivery_date')).split("T")[0], '%Y-%m-%d').date()
                            except: d = datetime.now(SAST).date()
                            nd = st.date_input("DATE", value=d, key=f"d_{r['id']}")
                        with c2: nn = st.text_area("NOTES", value=str(r.get('notes', '')), height=130, key=f"n_{r['id']}")
                        if st.button("SAVE", key=f"u_{r['id']}"):
                            try:
                                linked_vsb = r.get('linked_vsb')

                                if ns == "Delivered" and linked_vsb:
                                    # Vehicle has left the floorplan — purge it so it stops accruing ghost aging provisions.
                                    apply_matrix_filters(supabase.table("used_car_stock").delete().eq("vsb_no", linked_vsb)).execute()
                                elif ns == "Cancelled" and linked_vsb:
                                    # Reverse the F&I Desk's SOLD lock since the deal fell through.
                                    apply_matrix_filters(supabase.table("used_car_stock").update({"floorplan_status": "⚪ PENDING RECON"}).eq("vsb_no", linked_vsb)).execute()

                                apply_matrix_filters(supabase.table("sales_pipeline").update({"stage": ns, "planned_delivery_date": nd.strftime('%Y-%m-%d'), "notes": nn})).eq("id", r['id']).execute()
                                safe_rerun()
                            except Exception as e: st.error(e)

        with t5:
            st.markdown(f"### 📦 {st.session_state.get('location_id', '').replace('_', ' ')} ARCHIVED DELIVERIES")
            try: 
                arc_query = apply_matrix_filters(supabase.table("sales_pipeline").select("*").eq("stage", "Delivered"))
                ares = arc_query.execute().data or []
            except: ares = []
            
            if not ares: st.info(f"No archives found in {st.session_state.get('location_id')}.")
            else:
                df_a = pd.DataFrame(ares)
                ra = pd.DataFrame()
                ra["CLIENT"] = df_a["client_name"]
                ra["DEAL"] = df_a["deal_description"]
                st.dataframe(ra, hide_index=True, use_container_width=True)

        if t6:
            with t6:
                st.markdown(f"### 👑 LOCAL COMMAND OVERVIEW ({st.session_state.get('location_id')})")
                st.info("Local audit functions enabled.")

        if t7:
            with t7:
                st.markdown(f"### 💰 {st.session_state.get('location_id', '').replace('_', ' ')} F&I PROFITABILITY DESK")

                DEAL_SOURCES = ["📥 Pipeline", "🚗 Master Stockroom", "✏️ Custom Buy-In"]
                origin = st.radio("DEAL ORIGINATION", DEAL_SOURCES, horizontal=True)

                client_name, vehicle_vsb, vehicle_desc, default_capital = "", "", "", 0.0
                lock_vsb_field = False

                if origin == "📥 Pipeline":
                    try:
                        pipe_query = apply_matrix_filters(supabase.table("sales_pipeline").select("*").neq("stage", "Delivered"))
                        pipe_deals = pipe_query.order("id", desc=True).execute().data or []
                    except: pipe_deals = []

                    if not pipe_deals:
                        st.info("No active pipeline deals to pull from.")
                    else:
                        deal_opts = {f"{d['client_name']} — {d['deal_description']}": d for d in pipe_deals}
                        sel_deal = deal_opts[st.selectbox("SELECT PIPELINE DEAL", list(deal_opts.keys()))]
                        client_name = sel_deal['client_name']
                        vehicle_desc = sel_deal['deal_description']
                        vehicle_vsb = sel_deal.get('linked_vsb') or ""
                        default_capital = float(sel_deal.get('estimated_value', 0) or 0)

                elif origin == "🚗 Master Stockroom":
                    try:
                        stock_query = apply_matrix_filters(supabase.table("used_car_stock").select("vsb_no, description, total_value"))
                        stock_list = stock_query.execute().data or []
                    except: stock_list = []

                    if not stock_list:
                        st.info("No vehicles available in the stockroom.")
                    else:
                        stock_opts = {f"{s['vsb_no']} - {s['description']}": s for s in stock_list}
                        sel_stock = stock_opts[st.selectbox("SELECT VEHICLE FROM STOCK", list(stock_opts.keys()))]
                        vehicle_vsb = str(sel_stock['vsb_no'])
                        vehicle_desc = sel_stock['description']
                        default_capital = float(sel_stock.get('total_value', 0) or 0)
                        lock_vsb_field = True

                st.markdown("---")
                fc1, fc2 = st.columns(2)
                with fc1:
                    client_name = st.text_input("CLIENT NAME", value=client_name)
                    vehicle_vsb = st.text_input("VSB NUMBER", value=vehicle_vsb, disabled=lock_vsb_field)
                    vehicle_desc = st.text_input("VEHICLE DESCRIPTION", value=vehicle_desc, disabled=lock_vsb_field)
                with fc2:
                    capital_cost = st.number_input("CAPITAL COST (ZAR)", min_value=0.0, step=500.0, value=default_capital)
                    retail_price = st.number_input("RETAIL SELLING PRICE (ZAR)", min_value=0.0, step=500.0)
                    fi_vaps_revenue = st.number_input("F&I VAPS & DIC REVENUE (ZAR)", min_value=0.0, step=100.0)

                net_retained_profit = (retail_price - capital_cost) + fi_vaps_revenue
                st.markdown("---")
                st.metric("NET RETAINED PROFIT", f"R {net_retained_profit:,.2f}")

                if st.button("💾 LOCK DEAL", use_container_width=True):
                    if client_name and vehicle_desc:
                        deal_payload = {
                            "deal_source": origin, "client_name": client_name, "vehicle_vsb": vehicle_vsb,
                            "vehicle_desc": vehicle_desc, "capital_cost": capital_cost, "retail_price": retail_price,
                            "fi_vaps_revenue": fi_vaps_revenue, "net_retained_profit": net_retained_profit,
                            "created_by": st.session_state.get('user', ''),
                            "location_id": st.session_state.get('location_id'),
                            "department_id": st.session_state.get('department_id'),
                            "brand_id": st.session_state.get('brand_id')
                        }
                        try:
                            supabase.table("deal_desk").insert(deal_payload).execute()
                            if vehicle_vsb:
                                apply_matrix_filters(supabase.table("used_car_stock").update({"floorplan_status": "SOLD - PENDING DELIVERY"}).eq("vsb_no", vehicle_vsb)).execute()
                            st.success("✅ Deal Locked & Stockroom Updated.")
                            safe_rerun()
                        except Exception as e: st.error(f"Error: {e}")
                    else:
                        st.warning("Enter client name and vehicle description.")
                
        if t_doc:
            with t_doc:
                st.markdown(f"### 📉 {st.session_state.get('location_id', '').replace('_', ' ')} DEALER OPERATING COSTS (DOC)")

                now = datetime.now(SAST)
                month_opts = []
                y, m = now.year, now.month
                for _ in range(6):
                    month_opts.append(datetime(y, m, 1).strftime('%B %Y'))
                    m -= 1
                    if m == 0: m, y = 12, y - 1

                DOC_CATEGORIES = ["Salaries", "Rent & Facilities", "Marketing", "Utilities", "Miscellaneous"]

                with st.expander("➕ LOG MONTHLY EXPENSE"):
                    dc1, dc2 = st.columns(2)
                    exp_month = dc1.selectbox("EXPENSE MONTH", month_opts, key="doc_month_sel")
                    exp_cat = dc2.selectbox("EXPENSE CATEGORY", DOC_CATEGORIES, key="doc_cat_sel")
                    exp_amt = st.number_input("AMOUNT (ZAR)", min_value=0.0, step=500.0, key="doc_amt_input")

                    if st.button("💾 COMMIT EXPENSE", use_container_width=True):
                        if exp_amt > 0:
                            doc_payload = {
                                "expense_month": exp_month, "expense_category": exp_cat, "amount": exp_amt,
                                "logged_by": st.session_state.get('user', ''),
                                "location_id": st.session_state.get('location_id'),
                                "department_id": st.session_state.get('department_id'),
                                "brand_id": st.session_state.get('brand_id')
                            }
                            try:
                                supabase.table("doc_expenses").insert(doc_payload).execute()
                                st.success("✅ Expense Logged."); safe_rerun()
                            except Exception as e: st.error(f"Error: {e}")
                        else:
                            st.warning("Enter an amount greater than zero.")

                st.markdown("---")
                try:
                    doc_query = apply_matrix_filters(supabase.table("doc_expenses").select("*").eq("expense_month", exp_month))
                    doc_res = doc_query.order("id", desc=True).execute().data or []
                except: doc_res = []

                df_doc = pd.DataFrame(doc_res)
                if df_doc.empty:
                    st.info(f"No overheads logged for {exp_month} yet.")
                else:
                    df_doc['amount'] = pd.to_numeric(df_doc['amount'], errors='coerce').fillna(0.0)
                    st.metric(f"TOTAL MONTHLY DOC ({exp_month})", f"R {df_doc['amount'].sum():,.2f}")
                    dd = df_doc.rename(columns={
                        "expense_month": "MONTH", "expense_category": "CATEGORY",
                        "amount": "AMOUNT", "logged_by": "LOGGED BY"
                    })
                    dd["AMOUNT"] = dd["AMOUNT"].apply(lambda x: f"R {x:,.2f}")
                    st.dataframe(dd[["MONTH", "CATEGORY", "AMOUNT", "LOGGED BY"]], hide_index=True, use_container_width=True)

        if t8:
            with t8:
                _render_token_manager(supabase)
