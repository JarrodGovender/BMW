import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
import random
import smtplib
import hashlib
from email.message import EmailMessage
from config import safe_rerun, get_ai_vehicle_specs, create_brochure_excel, SAST

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
        
    if role in ['SUPER_USER', 'DEALER_PRINCIPAL', 'FINANCE_ADMIN', 'PROPERTY_MANAGER']:
        return query_builder.eq("location_id", loc)
        
    if role in ['SALES_MANAGER', 'WORKSHOP_MANAGER', 'PARTS_MANAGER']:
        return query_builder.eq("location_id", loc).eq("department_id", dept)
        
    if brand == 'ALL_BRANDS':
        return query_builder.eq("location_id", loc).eq("department_id", dept)
    else:
        return query_builder.eq("location_id", loc).eq("department_id", dept).eq("brand_id", brand)

# ====================================================================
# SHARED COMPONENT: TOKEN & USER MANAGER
# ====================================================================
def _render_token_manager(supabase):
    st.markdown("### 🔑 SYSTEM ADMINISTRATION & PROVISIONING")
    st.info("💡 Notice: To ensure accurate system architecture testing, provisioned users will inherit the active God Mode matrix unless manually overridden below.")
    
    try: db_roles = [r['id'] for r in supabase.table("roles").select("id").execute().data]
    except: db_roles = ["SALES_REP", "SALES_MANAGER", "FINANCE_ADMIN", "DEALER_PRINCIPAL", "DIRECTOR", "SUPER_USER"]
    try: db_locs = [l['id'] for l in supabase.table("locations").select("id").execute().data]
    except: db_locs = ["BMW_SANDTON", "BMW_BEDFORDVIEW", "BMW_EASTRAND", "BMW_DALPARK", "MF_SANDTON", "MF_FOURWAYS", "GLOBAL_HQ"]
    try: db_depts = [d['id'] for d in supabase.table("departments").select("id").execute().data]
    except: db_depts = ["NEW_SALES", "USED_SALES", "SERVICE", "PARTS", "FINANCE", "ALL_DEPTS"]
    try: db_brands = [b['id'] for b in supabase.table("brands").select("id").execute().data]
    except: db_brands = ["BMW", "MINI", "MOTORRAD", "MG", "HONDA", "JAC", "ALL_BRANDS"]

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
    # ROUTE A: SERVICE / WORKSHOP DEPARTMENT
    # ----------------------------------------------------------------
    if active_dept == 'SERVICE':
        if role == 'SUPER_USER':
            t1, t2 = st.tabs(["🔧 DAILY WIP", "🔑 TOKEN MANAGER"])
        else:
            t1, = st.tabs(["🔧 DAILY WIP"])
            t2 = None
            
        with t1:
            st.markdown(f"### 🔧 {st.session_state.get('location_id', '').replace('_', ' ')} SERVICE DESK")
            WIP_STAGES = ["Scheduled", "Checked In", "In Bay / Diag", "Waiting on Parts", "QC / Wash", "Ready for Delivery", "Invoiced / Closed"]
            
            with st.expander("➕ OPEN NEW REPAIR ORDER (RO)"):
                ca, cb = st.columns(2)
                ro_num = ca.text_input("RO NUMBER (DMS Sync)")
                cname = cb.text_input("CLIENT NAME")
                veh_desc = ca.text_input("VEHICLE (Model/Reg/VIN)")
                status = cb.selectbox("INITIAL STATUS", WIP_STAGES, index=1)
                adv = ca.text_input("SERVICE ADVISOR", value=st.session_state['name'])
                tech = cb.text_input("ASSIGNED TECHNICIAN")
                val = ca.number_input("EST. RO VALUE (ZAR)", min_value=0.0, step=500.0)
                
                if st.button("CREATE RO"):
                    if ro_num and cname and veh_desc:
                        payload = {
                            "ro_number": ro_num, "client_name": cname, "vehicle_details": veh_desc,
                            "status": status, "service_advisor": adv, "technician": tech,
                            "estimated_value": val, "notes": "",
                            "location_id": st.session_state['location_id'], "department_id": st.session_state['department_id'], "brand_id": st.session_state['brand_id']
                        }
                        try:
                            supabase.table("service_wip").insert(payload).execute()
                            st.success("✅ RO Opened Successfully."); safe_rerun()
                        except Exception as e: st.error(f"Error: {e}")
                    else: st.warning("Please enter RO Number, Client, and Vehicle.")

            # Load Active WIP
            try:
                wip_query = apply_matrix_filters(supabase.table("service_wip").select("*").neq("status", "Invoiced / Closed"))
                res = wip_query.order("id", desc=True).execute().data or []
            except: res = []
            
            if not res: st.info("No active Repair Orders in the workshop right now.")
            else:
                df_wip = pd.DataFrame(res)
                
                # Top Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("ACTIVE ROs", len(df_wip))
                m2.metric("WAITING ON PARTS", len(df_wip[df_wip['status'] == 'Waiting on Parts']))
                m3.metric("TOTAL WIP VALUE", f"R {df_wip['estimated_value'].astype(float).sum():,.2f}")
                st.markdown("---")
                
                # Render Kanban-style expanders for active ROs
                for _, r in df_wip.iterrows():
                    icon = "⏳" if r['status'] == "Waiting on Parts" else ("✅" if r['status'] == "Ready for Delivery" else "🔧")
                    with st.expander(f"{icon} RO: {r['ro_number']} | {r['client_name']} ({r['vehicle_details']}) — {r['status'].upper()}"):
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.markdown(f"**Advisor:** `{r['service_advisor']}`")
                            st.markdown(f"**Value:** R {float(r.get('estimated_value', 0)):,.2f}")
                            ns = st.selectbox("UPDATE STATUS", WIP_STAGES, index=WIP_STAGES.index(r['status']) if r['status'] in WIP_STAGES else 0, key=f"ws_{r['id']}")
                            nt = st.text_input("TECHNICIAN", value=str(r.get('technician', '')), key=f"wt_{r['id']}")
                        with c2: 
                            nn = st.text_area("WORKSHOP NOTES", value=str(r.get('notes', '')), height=130, key=f"wn_{r['id']}")
                        if st.button("💾 SAVE RO", key=f"wu_{r['id']}"):
                            try:
                                supabase.table("service_wip").update({"status": ns, "technician": nt, "notes": nn}).eq("id", r['id']).execute(); safe_rerun()
                            except Exception as e: st.error(e)

        if t2:
            with t2: _render_token_manager(supabase)

    # ----------------------------------------------------------------
    # ROUTE B: SALES / ADMIN / PARTS DEPARTMENTS
    # ----------------------------------------------------------------
    else:
        if role == 'SUPER_USER':
            t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs(["🔥 FEED", "💼 CLAIMED", "🚗 STOCKROOM", "💼 PIPELINE", "📦 ARCHIVE", "📊 OVERVIEW", "💰 F&I DESK", "🔑 TOKEN MANAGER"])
        elif IS_MANAGEMENT:
            t1, t2, t3, t4, t5, t6, t7 = st.tabs(["🔥 FEED", "💼 CLAIMED", "🚗 STOCKROOM", "💼 PIPELINE", "📦 ARCHIVE", "📊 OVERVIEW", "💰 F&I DESK"])
            t8 = None
        else:
            t1, t2, t3, t4, t5 = st.tabs(["🔥 FEED", "💼 CLAIMED", "🚗 STOCKROOM", "💼 PIPELINE", "📦 ARCHIVE"])
            t6 = t7 = t8 = None

        # (THE REST OF THE TABS 1-7 REMAIN EXACTLY THE SAME AS YOUR PREVIOUS VERSION)
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
                        
                        col_b1, col_b2 = st.columns([1, 2])
                        with col_b1:
                            st.write("**AI Verified Specs:**")
                            for k, v in specs_to_render.items(): st.write(f"- **{k}:** {v}")
                        with col_b2:
                            car_details = {"desc": car_row['VEHICLE DESCRIPTION'], "vsb": car_row['VSB NUMBER'], "vin": car_row.get('CHASSIS / VIN', 'N/A'), "price": f"R {float(car_row.get('CAPITAL VAL (ZAR)', 0)):,.2f}", "raw_price": float(car_row.get('CAPITAL VAL (ZAR)', 0))}
                            try:
                                excel_bytes = create_brochure_excel(car_details, specs_to_render)
                                st.download_button(label="📥 DOWNLOAD EXCEL SPEC SHEET", data=excel_bytes, file_name=f"PhaseV_Spec_Sheet_{sel_vsb}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                            except Exception as e: st.error(f"Failed Excel generation: {e}")
                    
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
                        insert_payload = {
                            "salesperson_username": st.session_state['user'], "client_name": cname, 
                            "deal_description": ddesc, "stage": stage, "estimated_value": val, 
                            "planned_delivery_date": ddate.strftime('%Y-%m-%d'), "notes": "",
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
                            ns = st.selectbox("STATUS", PIPELINE_STAGES, index=PIPELINE_STAGES.index(r['stage']) if r['stage'] in PIPELINE_STAGES else 0, key=f"s_{r['id']}")
                            try: d = datetime.strptime(str(r.get('planned_delivery_date')).split("T")[0], '%Y-%m-%d').date()
                            except: d = datetime.now(SAST).date()
                            nd = st.date_input("DATE", value=d, key=f"d_{r['id']}")
                        with c2: nn = st.text_area("NOTES", value=str(r.get('notes', '')), height=130, key=f"n_{r['id']}")
                        if st.button("SAVE", key=f"u_{r['id']}"):
                            try: supabase.table("sales_pipeline").update({"stage": ns, "planned_delivery_date": nd.strftime('%Y-%m-%d'), "notes": nn}).eq("id", r['id']).execute(); safe_rerun()
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
                st.info("F&I desk ready.")
                
        if t8:
            with t8:
                _render_token_manager(supabase)
