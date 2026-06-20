import streamlit as st
import pandas as pd
from datetime import datetime
import re
from config import safe_rerun, SAST
from utils.helpers import get_role
from views.shared_utils import apply_matrix_filters, apply_location_matrix_filters, _render_token_manager

# ====================================================================
# ROUTE A: SERVICE / WORKSHOP / PARTS DEPARTMENTS
# ====================================================================
def render_service_parts(supabase, user_data):
    role = get_role()
    active_dept = str(st.session_state.get('department_id', '')).upper()
    container_bg = user_data.get('container_bg')
    text_color = user_data.get('text_color')

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
            ro_num = ca.text_input("RO NUMBER (DMS Sync)", key="ro_new_number")
            cname = cb.text_input("CLIENT NAME", key="ro_new_client_name")
            veh_desc = ca.text_input("VEHICLE (Model/Reg/VIN)", key="ro_new_vehicle_desc")
            status = cb.selectbox("INITIAL STATUS", WIP_STAGES, index=1, key="ro_new_status")
            adv = ca.text_input("SERVICE ADVISOR", value=st.session_state.get('name', 'Advisor'), key="ro_new_advisor")
            tech = cb.text_input("ASSIGNED TECHNICIAN", key="ro_new_technician")
            val = ca.number_input("EST. RO VALUE (ZAR)", min_value=0.0, step=500.0, key="ro_new_value")

            if st.button("CREATE RO", key="ro_create_btn"):
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

        raw_wip_paste = st.text_area("PASTE RAW DMS DATA HERE (From Excel or Kerridge/Drive)", height=200, key="wip_report_paste")

        if st.button("📊 INGEST & GENERATE REPORT", use_container_width=True, key="wip_report_ingest_btn"):
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
                inv_num = oc1.text_input("INVOICE NUMBER", key="otc_invoice_num")
                pclient = oc2.text_input("CLIENT NAME", key="otc_client_name")
                pdesc = st.text_area("PARTS DESCRIPTION", height=100, key="otc_parts_desc")
                ocap = oc1.number_input("CAPITAL COST (ZAR)", min_value=0.0, step=50.0, key="otc_capital_cost")
                oretail = oc2.number_input("RETAIL PRICE (ZAR)", min_value=0.0, step=50.0, key="otc_retail_price")
                onet = oretail - ocap
                st.metric("NET PROFIT", f"R {onet:,.2f}")

                if st.button("💾 SAVE INVOICE", use_container_width=True, key="otc_save_invoice_btn"):
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
