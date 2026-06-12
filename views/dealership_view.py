import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
import random
import smtplib
from email.message import EmailMessage
from config import safe_rerun, get_ai_vehicle_specs, create_brochure_excel, SAST

# ====================================================================
# MASTER SECURITY GATEKEEPER
# Automatically appends 4-Dimensional Matrix filters to Supabase queries
# ====================================================================
def apply_matrix_filters(query_builder):
    role = str(st.session_state.get('role', '')).upper()
    loc = st.session_state.get('location_id')
    dept = st.session_state.get('department_id')
    brand = st.session_state.get('brand_id')
    
    # 1. Executive Bypass: See the entire holding company
    if role in ['DIRECTOR', 'SUPER_USER']:
        return query_builder
        
    # 2. Management Level: Locked to Building & Department, sees all local brands
    if role in ['DEALER_PRINCIPAL', 'SALES_MANAGER', 'WORKSHOP_MANAGER', 'PARTS_MANAGER', 'FINANCE_ADMIN']:
        return query_builder.eq("location_id", loc).eq("department_id", dept)
        
    # 3. Staff Level: Locked to Building, Department, and specific Brand silo
    return query_builder.eq("location_id", loc).eq("department_id", dept).eq("brand_id", brand)


def render(supabase, container_bg, text_color, metric_label, border_color, theme):
    # Standardize Role Check
    role = str(st.session_state.get('role', '')).upper()
    IS_MANAGEMENT = role in ['DEALER_PRINCIPAL', 'FINANCE_ADMIN', 'SALES_MANAGER', 'DIRECTOR', 'SUPER_USER']

    if IS_MANAGEMENT:
        t1, t2, t3, t4, t5, t6, t7 = st.tabs(["🔥 FEED", "💼 CLAIMED", "🚗 STOCKROOM", "💼 PIPELINE", "📦 ARCHIVE", "📊 OVERVIEW", "💰 F&I DESK"])
    else:
        t1, t2, t3, t4, t5 = st.tabs(["🔥 FEED", "💼 CLAIMED", "🚗 STOCKROOM", "💼 PIPELINE", "📦 ARCHIVE"])

    # ---- TAB 1: DAILY FEED ----
    with t1:
        if role in ['SUPER_USER', 'DIRECTOR']:
            with st.expander("🤖 LEAD INJECTION ENGINE (SUPER USER ONLY)"):
                st.caption("WARNING: Injecting leads here will bypass matrix locks and push to global unassigned.")
                if st.button("🔥 INJECT 12 NEW LEADS", key="inject_leads_btn"):
                    today_str = datetime.now(SAST).strftime('%Y-%m-%d')
                    b2b_list = [{"company": "Apex Logistics", "location": "Sandton", "target": "Fleet Manager", "score": random.randint(80, 99), "lead_date": today_str, "signal": "Expanding executive luxury fleet.", "status": "Unassigned", "location_id": "BMW_SANDTON", "department_id": "NEW_SALES", "brand_id": "BMW"}]
                    b2c_list = [{"client_name": "Sarah Jenkins", "title": "Senior Partner", "company": "Bowmans Law", "location": "Sandton", "score": random.randint(75, 99), "lead_date": today_str, "signal": "Current X5 M Competition lease expiring.", "status": "Unassigned", "location_id": "BMW_SANDTON", "department_id": "NEW_SALES", "brand_id": "BMW"}]
                    with st.spinner("Injecting fresh leads..."):
                        try:
                            supabase.table("leads").insert(b2b_list).execute()
                            supabase.table("individual_leads").insert(b2c_list).execute()
                            st.success("✅ Global Leads Injected!"); safe_rerun()
                        except Exception as e: st.error(f"Injection Failed: {e}")
        
        lead_section = st.radio("SELECT OPPORTUNITY CHANNEL", ["🏢 Corporate Fleet (B2B)", "🚗 Individual Leads (B2C)", "🏛️ Gov Tenders (B2B)"], horizontal=True)
        filter_date_str = st.date_input("FILTER BY GENERATION DATE", datetime.now(SAST)).strftime('%Y-%m-%d')
        st.markdown("---")
        
        tbl_map = {"🏢 Corporate Fleet (B2B)": "leads", "🚗 Individual Leads (B2C)": "individual_leads", "🏛️ Gov Tenders (B2B)": "tender_leads"}
        active_tbl = tbl_map[lead_section]
        
        try: 
            # APPLIED SECURITY MATRIX
            base_query = supabase.table(active_tbl).select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str)
            secure_query = apply_matrix_filters(base_query)
            res = secure_query.order("score", desc=True).execute().data
        except: res = []
        
        df_leads = pd.DataFrame(res) if res else pd.DataFrame()
        
        if df_leads.empty: st.info(f"No unassigned {lead_section.split(' ')[1].lower()} leads found in your jurisdiction for this date.")
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

    # ---- TAB 2: CLAIMED PANELS ----
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

    # ---- 🚗 TAB 3: STOCKROOM NODE ----
    with t3:
        st.markdown("### 🚗 LIVE USED CAR STOCKROOM")
        
        try:
            # APPLIED SECURITY MATRIX
            base_stock = supabase.table("used_car_stock").select("*")
            secure_stock = apply_matrix_filters(base_stock)
            stock_res = secure_stock.order("days_in_stock", desc=True).execute().data
            df_live_stock = pd.DataFrame(stock_res) if stock_res else pd.DataFrame()
        except Exception as e:
            df_live_stock = pd.DataFrame()

        # Hardcode columns if empty so visual metrics & tables never crash
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
            # Admins upload data specific to their matrix location
            if role in ['FINANCE_ADMIN', 'SUPER_USER']:
                with st.expander("🛠️ ADMIN CONSOLE: INVENTORY UPLOAD", expanded=False):
                    st.markdown("#### Paste Daily Spreadsheet Data (USED STOCK)")
                    raw_paste_data = st.text_area("PASTE RAW DATA ROWS HERE", height=150, key="used_paste")
                    
                    if st.button("PROCESS OVERWRITE", key="process_stock_paste_btn") and raw_paste_data.strip():
                        try:
                            # APPLIED SECURITY MATRIX - Only delete/update the user's specific location
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
                                                
                                    mem_comment = comment_memory.get(vsb, "")
                                    
                                    # Inject the Matrix Identifiers when saving
                                    insert_payload = {
                                        "vsb_no": vsb, "description": desc, "into_stock": into_stk, 
                                        "days_in_stock": days, "total_value": val, "location": current_franchise.strip(), 
                                        "chassis_no": chassis, "floorplan_status": "⚪ PENDING RECON", 
                                        "comments": mem_comment, "stock_type": "Used",
                                        "location_id": st.session_state['location_id'],
                                        "department_id": st.session_state['department_id'],
                                        "brand_id": st.session_state['brand_id']
                                    }
                                    try: supabase.table("used_car_stock").upsert(insert_payload).execute()
                                    except: pass
                                    records_processed += 1
                            st.success(f"🎉 Stock refreshed successfully. {records_processed} units inserted."); safe_rerun()
                        except Exception as parse_ex: st.error(f"Data processing failed: {str(parse_ex)}")

            if df_live_stock.empty:
                st.info("No vehicles are currently recorded in your jurisdiction.")
            else:
                st.markdown("### 📄 AI DIGITAL BROCHURE STUDIO")
                vehicle_series = df_live_stock['VSB NUMBER'].astype(str) + " - " + df_live_stock['VEHICLE DESCRIPTION']
                selected_brochure = st.selectbox("SEARCH INVENTORY FOR BROCHURE GENERATION", ["Select a Vehicle..."] + vehicle_series.tolist())
                
                if selected_brochure != "Select a Vehicle...":
                    sel_vsb = selected_brochure.split(" - ")[0]
                    car_row = df_live_stock[df_live_stock['VSB NUMBER'] == sel_vsb].iloc[0]
                    
                    st.markdown(f"**Vehicle Selected:** `{car_row['VEHICLE DESCRIPTION']}`")
                    with st.spinner("🤖 Gemini AI is decoding the VIN and actively searching the web..."):
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
            if IS_MANAGEMENT and role == 'FINANCE_ADMIN':
                with st.expander("🛠️ ADMIN CONSOLE: DEMO INVENTORY UPLOAD", expanded=False):
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
                                        "location_id": st.session_state['location_id'],
                                        "department_id": st.session_state['department_id'],
                                        "brand_id": st.session_state['brand_id']
                                    }
                                    supabase.table("used_car_stock").upsert(insert_payload).execute()
                                    recs += 1
                            st.success(f"🎉 Demo Stock refreshed. {recs} units."); safe_rerun()
                        except Exception as e: st.error(f"Error: {e}")
                        
            if df_live_stock.empty:
                st.info("No Demo vehicles are currently recorded in your jurisdiction.")
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
                
                if IS_MANAGEMENT:
                    with st.expander("📤 DISTRIBUTE UNENCUMBERED LIST VIA EMAIL"):
                        u_email = st.text_input("RECIPIENT EMAIL ADDRESS", key="u_email_in")
                        if st.button("🚀 DISPATCH UNENCUMBERED", key="u_disp"):
                            if u_email and not df_live_stock.empty:
                                with st.spinner("Formatting Executive Unencumbered Matrix..."):
                                    try:
                                        ebuf = io.BytesIO()
                                        with pd.ExcelWriter(ebuf, engine='xlsxwriter') as wr:
                                            wb = wr.book; ws_e = wb.add_worksheet('EXECUTIVE OVERVIEW')
                                            ws_e.set_landscape() 
                                            ws_e.hide_gridlines(2); ws_e.set_column('A:A', 40); ws_e.set_column('B:D', 25)
                                            
                                            tf = wb.add_format({'bold': True, 'font_size': 14, 'bg_color': '#003366', 'font_color': '#FFFFFF', 'align': 'center', 'valign': 'vcenter', 'border': 1})
                                            hf = wb.add_format({'bold': True, 'bg_color': '#E0E0E0', 'align': 'center', 'valign': 'vcenter', 'border': 1})
                                            nf = wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0'})
                                            cf = wb.add_format({'border': 1, 'valign': 'vcenter', 'num_format': 'R #,##0.00'})
                                            xf = wb.add_format({'border': 1, 'valign': 'vcenter'})
                                            gold_fmt = wb.add_format({'bg_color': '#FFC000', 'border': 1, 'valign': 'vcenter'})
                                            gold_cur = wb.add_format({'bg_color': '#FFC000', 'border': 1, 'valign': 'vcenter', 'num_format': 'R #,##0.00'})
                                            pct_fmt = wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.0%'})
                                            
                                            ce = [
                                                ("MINI Used", df_live_stock[(df_live_stock["FRANCHISE DIVISION"].str.lower().str.contains("m -", regex=True)) & (~df_live_stock["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True))]),
                                                ("Demo stock", df_live_stock[df_live_stock["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True)]),
                                                ("BMW Used", df_live_stock[(df_live_stock["FRANCHISE DIVISION"].str.lower().str.contains("b -|i -", regex=True)) & (~df_live_stock["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True))]),
                                                ("Tier", df_live_stock[(df_live_stock["FRANCHISE DIVISION"].str.lower().str.contains("z -", regex=True)) & (~df_live_stock["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True))]),
                                                ("MC Used", df_live_stock[(df_live_stock["FRANCHISE DIVISION"].str.lower().str.contains("a -|c -", regex=True)) & (~df_live_stock["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True))])
                                            ]
                                            
                                            exp_data, gs, gu = [], 0.0, 0.0
                                            for cn, cdf in ce:
                                                totv = float(cdf["CAPITAL VAL (ZAR)"].sum())
                                                unencv = float(cdf[cdf["FP STATUS"] == "🟢 UNENCUMBERED"]["CAPITAL VAL (ZAR)"].sum())
                                                if totv > 0:
                                                    exp_data.extend([[f"Total {cn}", totv], [f"Total {cn} unencumbered", unencv]])
                                                    gs += totv; gu += unencv
                                                    
                                            exp_data.extend([["", ""], ["Total Stock + Demo", gs], ["Total unencumbered", gu]])
                                            
                                            ri = 1
                                            ws_e.merge_range(ri, 0, ri, 1, "DEALERSHIP CAPITAL EXPOSURE", tf)
                                            ws_e.set_row(ri, 30); ri += 2
                                            for item in exp_data:
                                                lbl, val = item[0], item[1]
                                                if lbl == "": ri += 1; continue
                                                is_u = "unencumbered" in lbl.lower()
                                                lbf, vaf = (gold_fmt, gold_cur) if is_u else (xf, cf)
                                                if lbl == "Total unencumbered":
                                                    lbf = wb.add_format({'bold': True, 'bg_color': '#FFC000', 'border': 1})
                                                    vaf = wb.add_format({'bold': True, 'bg_color': '#FFC000', 'border': 1, 'num_format': 'R #,##0.00'})
                                                    ws_e.write(ri, 2, gu/gs if gs else 0, wb.add_format({'bold': True, 'font_size': 14, 'font_color': 'red', 'bg_color': '#FFFF00', 'align': 'center', 'valign': 'vcenter', 'num_format': '0%'}))
                                                ws_e.write(ri, 0, lbl, lbf)
                                                if val != "": ws_e.write_number(ri, 1, val, vaf)
                                                ri += 1
                                                
                                            rs = ri + 2
                                            ws_e.merge_range(rs, 0, rs, 2, "FLOORPLAN RATIO", tf)
                                            ws_e.set_row(rs, 30); ws_e.set_row(rs+1, 35)
                                            ws_e.write(rs+1, 0, "FINANCE STATUS", hf); ws_e.write(rs+1, 1, "TOTAL UNITS", hf); ws_e.write(rs+1, 2, "% OF TOTAL", hf)
                                            
                                            unenc_df = df_live_stock[df_live_stock["FP STATUS"] == "🟢 UNENCUMBERED"].copy()
                                            totu, uu = len(df_live_stock), len(unenc_df)
                                            fpu = len(df_live_stock[df_live_stock["FP STATUS"] == "🏦 ON FLOORPLAN"])
                                            pu = len(df_live_stock[df_live_stock["FP STATUS"] == "⚪ PENDING RECON"])
                                            
                                            dm = [("🟢 UNENCUMBERED", uu, uu/totu if totu else 0), ("🏦 ON FLOORPLAN", fpu, fpu/totu if totu else 0), ("⚪ PENDING RECON", pu, pu/totu if totu else 0)]
                                            for i, (sts, c, p) in enumerate(dm, rs+2):
                                                ws_e.write(i, 0, sts, xf); ws_e.write(i, 1, c, nf); ws_e.write(i, 2, p, pct_fmt)
                                            ws_e.write(rs+5, 0, "TOTAL DEALERSHIP STOCK", hf); ws_e.write(rs+5, 1, totu, hf); ws_e.write(rs+5, 2, 1.0, wb.add_format({'bold': True, 'bg_color': '#E0E0E0', 'border': 1, 'num_format': '0.0%'}))
                                            
                                            for f in sorted(list(unenc_df["FRANCHISE DIVISION"].unique())):
                                                fdf = unenc_df[unenc_df["FRANCHISE DIVISION"] == f]
                                                if fdf.empty or f.strip() == "LHP": continue
                                                ws = wb.add_worksheet(str(f).replace('/', '-')[:31])
                                                ws.set_landscape() 
                                                ws.hide_gridlines(2); ws.set_column('A:A', 15); ws.set_column('B:B', 40); ws.set_column('C:E', 15); ws.set_column('F:F', 45)
                                                ws.merge_range(0, 0, 0, 5, f"UNENCUMBERED ASSETS: {f.upper()}", tf); ws.set_row(0, 30); ws.set_row(1, 35)
                                                cols = ["VSB NUMBER", "VEHICLE DESCRIPTION", "INTO STOCK DATE", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)", "ADMIN COMMENTS"]
                                                for ci, cn in enumerate(cols): ws.write(1, ci, cn, hf)
                                                for rxi, rv in enumerate(fdf[cols].values, 2):
                                                    ws.write(rxi, 0, rv[0], xf); ws.write(rxi, 1, rv[1], xf); ws.write(rxi, 2, rv[2], xf); ws.write(rxi, 3, rv[3], nf); ws.write_number(rxi, 4, float(rv[4]), cf); ws.write(rxi, 5, str(rv[5]), xf)

                                        msg = EmailMessage(); msg['Subject'] = f"🟢 UNENCUMBERED MATRICES - {datetime.now(SAST).strftime('%d %b %Y')}"; msg['From'] = st.secrets["smtp"]["sender_email"]; msg['To'] = u_email
                                        msg.set_content("Attached is the Live Unencumbered Stockbook and Matrix."); msg.add_attachment(ebuf.getvalue(), maintype='application', subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"PhaseV_Unencumbered_{datetime.now(SAST).strftime('%Y%m%d')}.xlsx")
                                        with smtplib.SMTP(st.secrets["smtp"]["server"], int(st.secrets["smtp"]["port"])) as srv: srv.starttls(); srv.login(st.secrets["smtp"]["sender_email"], st.secrets["smtp"]["password"]); srv.send_message(msg)
                                        st.success("✅ Dispatched!")
                                    except Exception as e: st.error(f"❌ Failed: {e}")
                            elif df_live_stock.empty:
                                st.warning("Database empty. Please upload inventory first.")
                            else:
                                st.warning("Please enter an email address.")

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

    # ---- TAB 4: PIPELINE ----
    with t4:
        st.markdown("### 💼 SALES PIPELINE: ACTIVE DEALS")
        PIPELINE_STAGES = ["Prospecting", "Test Drive", "Finance App", "Awaiting Delivery", "Delivered", "Cancelled"]
        with st.expander("➕ ADD NEW DEAL"):
            ca, cb = st.columns(2)
            cname = ca.text_input("CLIENT NAME")
            try: 
                # APPLIED SECURITY MATRIX
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
            # APPLIED SECURITY MATRIX
            pipe_query = apply_matrix_filters(supabase.table("sales_pipeline").select("*").neq("stage", "Delivered"))
            res = pipe_query.order("id", desc=True).execute().data or []
        except: res = []
        
        if not IS_MANAGEMENT: res = [r for r in res if r['salesperson_username'] == st.session_state['user']]
        
        if not res: st.info("No active pipeline deals in your jurisdiction.")
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
                        try: d = datetime.strptime(str(r.get('planned_delivery_date')).split("T")[0], '%Y-%m-%d').date()
                        except: d = datetime.now(SAST).date()
                        ns = st.selectbox("STATUS", PIPELINE_STAGES, index=PIPELINE_STAGES.index(r['stage']) if r['stage'] in PIPELINE_STAGES else 0, key=f"s_{r['id']}")
                        nd = st.date_input("DATE", value=d, key=f"d_{r['id']}")
                    with c2: nn = st.text_area("NOTES", value=str(r.get('notes', '')), height=130, key=f"n_{r['id']}")
                    if st.button("SAVE", key=f"u_{r['id']}"):
                        try: supabase.table("sales_pipeline").update({"stage": ns, "planned_delivery_date": nd.strftime('%Y-%m-%d'), "notes": nn}).eq("id", r['id']).execute(); safe_rerun()
                        except Exception as e: st.error(e)

    # ---- TAB 5: ARCHIVE ----
    with t5:
        st.markdown("### 📦 ARCHIVED DELIVERIES")
        try: 
            # APPLIED SECURITY MATRIX
            arc_query = apply_matrix_filters(supabase.table("sales_pipeline").select("*").eq("stage", "Delivered"))
            ares = arc_query.execute().data or []
        except: ares = []
        
        if not IS_MANAGEMENT: ares = [r for r in ares if r['salesperson_username'] == st.session_state['user']]
        
        if not ares: st.info("No archives found in your jurisdiction.")
        else:
            df_a = pd.DataFrame(ares)
            df_a['sort_date'] = pd.to_datetime(df_a.get('planned_delivery_date'), errors='coerce')
            df_a = df_a.sort_values(by='sort_date', ascending=False)
            ra = pd.DataFrame()
            if IS_MANAGEMENT: ra["REP"] = df_a["salesperson_username"].apply(lambda x: f"@{x}")
            ra["CLIENT"] = df_a["client_name"]
            ra["DEAL"] = df_a["deal_description"]
            ra["DATE"] = pd.to_datetime(df_a["planned_delivery_date"], errors='coerce').dt.strftime('%d %b %Y').fillna("Unknown")
            ra["VALUE"] = df_a.get("estimated_value", pd.Series([0]*len(df_a))).map(lambda x: f"R {float(x):,.2f}")
            st.dataframe(ra, hide_index=True, use_container_width=True)
            for _, r in df_a.iterrows():
                with st.expander(f"✅ {r['client_name'].upper()} | {r['deal_description']}"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        try: d = datetime.strptime(str(r.get('planned_delivery_date')).split("T")[0], '%Y-%m-%d').date()
                        except: d = datetime.now(SAST).date()
                        ns = st.selectbox("REVISE STATUS", ["Prospecting", "Test Drive", "Finance App", "Awaiting Delivery", "Delivered", "Cancelled"], index=4, key=f"as_{r['id']}")
                        nd = st.date_input("REVISE DATE", value=d, key=f"ad_{r['id']}")
                    with c2: nn = st.text_area("NOTES", value=str(r.get('notes', '')), height=130, key=f"an_{r['id']}")
                    if st.button("SAVE REVISION", key=f"au_{r['id']}"):
                        try: supabase.table("sales_pipeline").update({"stage": ns, "planned_delivery_date": nd.strftime('%Y-%m-%d'), "notes": nn}).eq("id", r['id']).execute(); safe_rerun()
                        except Exception as e: st.error(e)

    # ---- TAB 6: COMMAND ----
    if IS_MANAGEMENT:
        with t6:
            st.markdown("### 👑 COMMAND OVERVIEW & AUDITS")
            try: 
                # APPLIED SECURITY MATRIX
                cmd_query = apply_matrix_filters(supabase.table("used_car_stock").select("total_value, days_in_stock, location, floorplan_status, stock_type"))
                dfs = pd.DataFrame(cmd_query.execute().data or [])
            except: dfs = pd.DataFrame()
            
            if not dfs.empty:
                dfs['floorplan_status'] = dfs.get('floorplan_status', "⚪ PENDING RECON")
                dfs['stock_type'] = dfs.get('stock_type', "Used")
                dfs["location"] = dfs.get("location", "").astype(str).str.strip()
                dfs["FRANCHISE DIVISION"] = dfs.apply(lambda x: f"{x['location']} (DEMO)" if str(x['stock_type']) == 'Demo' else x['location'], axis=1)
                
            cats = [("BMW Used", "b -|i -", False), ("BMW Demo", "b -|i -", True), ("MINI Used", "m -", False), ("MINI Demo", "m -", True), ("MC Used", "a -|c -", False), ("MC Demo", "a -|c -", True), ("Tier Sandton", "z -", False), ("Tier Demo", "z -", True)]
            s_d, p_d, u_d = [], [], []
            ts = tv = tp25 = tp50 = tp75 = tp100 = tpt = tuu = tuv = 0.0
            
            for cn, msk, is_d in cats:
                if not dfs.empty:
                    cdf = dfs[dfs["FRANCHISE DIVISION"].str.lower().str.contains(msk, regex=True)]
                    cdf = cdf[cdf["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True)] if is_d else cdf[~cdf["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True)]
                    u, v = len(cdf), cdf["total_value"].sum()
                    v30, v61 = cdf[(cdf["days_in_stock"]>=30)&(cdf["days_in_stock"]<=60)]["total_value"].sum(), cdf[(cdf["days_in_stock"]>=61)&(cdf["days_in_stock"]<=90)]["total_value"].sum()
                    v91, v121 = cdf[(cdf["days_in_stock"]>=91)&(cdf["days_in_stock"]<=120)]["total_value"].sum(), cdf[cdf["days_in_stock"]>=121]["total_value"].sum()
                    udf = cdf[cdf['floorplan_status'] == 'UNENCUMBERED']
                    uu, uv = len(udf), udf["total_value"].sum()
                else: u=v=v30=v61=v91=v121=uu=uv=0
                p25, p50, p75, p100 = v30*0.025, v61*0.050, v91*0.075, v121*0.100
                ptot = p25+p50+p75+p100
                ts+=u; tv+=v; tp25+=p25; tp50+=p50; tp75+=p75; tp100+=p100; tpt+=ptot; tuu+=uu; tuv+=uv
                s_d.append({"STOCK DIVISION": cn, "UNITS": f"{u:,}", "INVESTMENT (ZAR)": f"R {v:,.2f}"})
                p_d.append({"STOCK DIVISION": cn, "2.5% (30-60)": f"R {p25:,.2f}", "5.0% (61-90)": f"R {p50:,.2f}", "7.5% (91-120)": f"R {p75:,.2f}", "10.0% (121+)": f"R {p100:,.2f}", "TOTAL PROV": f"R {ptot:,.2f}"})
                u_d.append({"STOCK DIVISION": cn, "UNITS": f"{uu:,}", "UNENCUMBERED VAL": f"R {uv:,.2f}"})
            
            s_d.append({"STOCK DIVISION": "GRAND TOTAL", "UNITS": f"{ts:,.0f}", "INVESTMENT (ZAR)": f"R {tv:,.2f}"})
            p_d.append({"STOCK DIVISION": "GRAND TOTAL", "2.5% (30-60)": f"R {tp25:,.2f}", "5.0% (61-90)": f"R {tp50:,.2f}", "7.5% (91-120)": f"R {tp75:,.2f}", "10.0% (121+)": f"R {tp100:,.2f}", "TOTAL PROV": f"R {tpt:,.2f}"})
            u_d.append({"STOCK DIVISION": "GRAND TOTAL", "UNITS": f"{tuu:,.0f}", "UNENCUMBERED VAL": f"R {tuv:,.2f}"})
            
            st.dataframe(pd.DataFrame(s_d), hide_index=True, use_container_width=True)
            st.markdown("#### 🪙 AGING PROVISION MATRIX"); st.dataframe(pd.DataFrame(p_d), hide_index=True, use_container_width=True)
            st.markdown("#### 🟢 UNENCUMBERED MATRIX"); st.dataframe(pd.DataFrame(u_d), hide_index=True, use_container_width=True)
                
            st.markdown("---")
            try:
                cl = len(apply_matrix_filters(supabase.table("leads").select("id")).execute().data or [])
                il = len(apply_matrix_filters(supabase.table("individual_leads").select("id")).execute().data or [])
                tl = len(apply_matrix_filters(supabase.table("tender_leads").select("id")).execute().data or [])
                c_cl = len(apply_matrix_filters(supabase.table("leads").select("id").eq("status", "Closed")).execute().data or [])
                i_cl = len(apply_matrix_filters(supabase.table("individual_leads").select("id").eq("status", "Closed")).execute().data or [])
                t_cl = len(apply_matrix_filters(supabase.table("tender_leads").select("id").eq("status", "Closed")).execute().data or [])
                
                # Fetch notes related to this specific location
                note_query = supabase.table("lead_notes").select("*").order("timestamp", desc=True)
                # Since lead_notes doesn't have division tracking natively, we filter in memory for extreme security
                raw_notes = note_query.execute().data or []
                
                if role in ['DIRECTOR', 'SUPER_USER']:
                    df_notes = pd.DataFrame(raw_notes)
                else:
                    valid_users = [u['username'] for u in supabase.table("users").select("username").eq("location_id", st.session_state['location_id']).execute().data or []]
                    filtered_notes = [n for n in raw_notes if n['username'] in valid_users]
                    df_notes = pd.DataFrame(filtered_notes)
                    
            except: cl=il=tl=c_cl=i_cl=t_cl=0; df_notes = pd.DataFrame()
                
            m1, m2, m3 = st.columns(3)
            m1.metric("TOTAL OPPORTUNITIES", cl + il + tl); m2.metric("CONVERSIONS (B2B)", c_cl + t_cl); m3.metric("DELIVERIES (B2C)", i_cl)
            st.markdown("---")
            st.markdown("### 💬 MASTER OUTREACH REGISTRY")
            if df_notes.empty: st.info("No transaction log adjustments submitted today in your jurisdiction.")
            else:
                for _, rn in df_notes.iterrows():
                    with st.chat_message("user"):
                        st.markdown(f"**{rn.get('salesperson_name','').upper()}** (`@{rn.get('username','')}`) handled a **{rn.get('lead_type','').upper()}** channel asset at *{rn.get('timestamp','')}*")
                        st.write(f"📝 *\"{rn.get('note_text','')}\"*")

    # ---- TAB 7: F&I DESK ----
    if IS_MANAGEMENT and role == 'FINANCE_ADMIN':
        with t7:
            st.markdown("### 💰 F&I PROFITABILITY DESK")
            ds = st.radio("ORIGINATION", ["📥 Pipeline: Pending Finance Apps", "🚗 Master Stockroom", "✏️ Custom Buy-In"], horizontal=True)
            st.markdown("---")
            
            ddesc, dcli, dcap, dsell, lid, dbt = "", "", 0.0, 0.0, None, ""
            c1, c2 = st.columns(2)
            
            if ds == "📥 Pipeline: Pending Finance Apps":
                dbt = "Pipeline"
                try: 
                    p_query = apply_matrix_filters(supabase.table("sales_pipeline").select("*").eq("stage", "Finance App"))
                    pdata = p_query.execute().data or []
                except: pdata = []
                
                if not pdata: st.info("No pending apps.")
                else:
                    opts = {f"#{d['id']} - {d['client_name']} ({d['deal_description']})": d for d in pdata}
                    sp = c1.selectbox("SELECT DEAL", ["Select Deal..."] + list(opts.keys()))
                    if sp != "Select Deal...":
                        d = opts[sp]
                        lid, dcli, ddesc, dsell = d['id'], d['client_name'], d['deal_description'], float(d.get('estimated_value',0))
                        try:
                            sm = apply_matrix_filters(supabase.table("used_car_stock").select("total_value").eq("vsb_no", str(d['deal_description']).split(" - ")[0])).execute().data
                            if sm: dcap = float(sm[0]['total_value'])
                        except: pass
            elif ds == "🚗 Master Stockroom":
                dbt = "Stock"
                try: 
                    s_query = apply_matrix_filters(supabase.table("used_car_stock").select("vsb_no, description, total_value"))
                    sdata = s_query.execute().data or []
                except: sdata = []
                opts = {f"{s['vsb_no']} - {s['description']}": s for s in sdata}
                ss = c1.selectbox("SELECT VEHICLE", ["Select Vehicle..."] + list(opts.keys()))
                if ss != "Select Vehicle...":
                    veh = opts[ss]
                    ddesc, dcap = ss, float(veh.get('total_value',0))
                    dsell = dcap * 1.12
            else:
                dbt = "Custom"
                ddesc = c1.text_input("CUSTOM DESCRIPTION")
                dcli = c1.text_input("CLIENT")
                dcap = c1.number_input("EST COST (ZAR)", value=0.0, step=10000.0)
            
            if ddesc or ds == "✏️ Custom Buy-In":
                with c1:
                    fc = st.text_input("Confirmed Client", value=dcli)
                    fd = st.text_input("Confirmed Vehicle", value=ddesc, disabled=(ds != "✏️ Custom Buy-In"))
                    cc, sc = st.columns(2)
                    capc = cc.number_input("Cost (ZAR)", value=dcap, step=5000.0)
                    sellp = sc.number_input("Retail Price (ZAR)", value=dsell, step=5000.0)
                with c2:
                    ht = st.checkbox("INCLUDES TRADE-IN")
                    tdesc, tacv, toff, tset = "", 0.0, 0.0, 0.0
                    if ht:
                        tdesc = st.text_input("Trade Desc")
                        tc1, tc2 = st.columns(2)
                        tacv = tc1.number_input("Actual Cash Value", value=0.0, step=5000.0)
                        toff = tc2.number_input("Offer", value=0.0, step=5000.0)
                        tset = st.number_input("Settlement", value=0.0, step=5000.0)
                        
                st.markdown("---")
                fc_col, sumc = st.columns(2)
                with fc_col:
                    fdic = st.number_input("DIC (Finance Kickback)", value=0.0, step=1000.0)
                    fvaps = st.number_input("VAPS Revenue", value=0.0, step=1000.0)
                
                rfe = sellp - capc
                oua = tacv - toff
                tbe = fdic + fvaps
                nrp = rfe + oua + tbe
                
                with sumc:
                    st.markdown("#### SUMMARY")
                    st.markdown(f"**Front-End:** R {rfe:,.2f}")
                    if ht: st.markdown(f"**Trade Impact:** <span style='color:{'green' if oua>=0 else 'red'};'>{'Under' if oua>=0 else 'Over'}-Allowance: R {oua:,.2f}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Back-End:** R {tbe:,.2f}")
                    st.markdown(f"<h3 style='background:{container_bg}; border:1px solid {border_color}; text-align:center;'>NET RETAINED: R {nrp:,.2f}</h3>", unsafe_allow_html=True)
                    
                st.markdown("<br>", unsafe_allow_html=True)
                ac1, ac2 = st.columns([1, 3])
                if ac1.button("💾 LOCK DEAL", key="s_cost"):
                    insert_payload = {
                        "pipeline_id": lid, "deal_source": dbt, "client_name": fc, "vehicle_desc": fd, 
                        "capital_cost": capc, "selling_price": sellp, "has_trade": ht, "trade_desc": tdesc, 
                        "trade_acv": tacv, "trade_offer": toff, "trade_settlement": tset, "fi_dic": fdic, 
                        "fi_vaps": fvaps, "net_profit": nrp, "created_by": st.session_state['user'],
                        "location_id": st.session_state['location_id'],
                        "department_id": st.session_state['department_id'],
                        "brand_id": st.session_state['brand_id']
                    }
                    try: supabase.table("deal_desk").insert(insert_payload).execute(); st.success("✅ Locked.")
                    except Exception as e: st.error(f"Error: {e}")
                if ac2.button("📧 REQUEST DP APPROVAL", key="em_dp"):
                    tem = st.text_input("DP EMAIL", key="dp_em")
                    if tem:
                        try:
                            msg = EmailMessage(); msg['Subject'] = f"APPROVAL REQUIRED: {fc}"; msg['From'] = st.secrets["smtp"]["sender_email"]; msg['To'] = tem
                            ebody = f"VEHICLE: {fd}\nCost: R {capc:,.2f}\nPrice: R {sellp:,.2f}\n\nTRADE: {tdesc if ht else 'No'}\nACV: R {tacv:,.2f}\nOffer: R {toff:,.2f}\nImpact: R {oua:,.2f}\n\nF&I: R {tbe:,.2f}\n\nNET RETAINED: R {nrp:,.2f}\n\nSubmitted by: {st.session_state['name']}"
                            msg.set_content(ebody)
                            with smtplib.SMTP(st.secrets["smtp"]["server"], int(st.secrets["smtp"]["port"])) as srv: srv.starttls(); srv.login(st.secrets["smtp"]["sender_email"], st.secrets["smtp"]["password"]); srv.send_message(msg)
                            st.success("✅ Routed.")
                        except Exception as e: st.error(f"Error: {e}")
