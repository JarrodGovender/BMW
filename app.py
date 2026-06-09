import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
from supabase import create_client, Client

# ==========================================
# 1. INITIALIZATION & PRODUCTION API SETUP
# ==========================================
st.set_page_config(page_title="BMW Sandton Lead Hub", layout="wide")
SAST = pytz.timezone('Africa/Johannesburg')

# Public CDN URLs for Official BMW and M Sport Logo Assets
BMW_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/4/44/BMW.svg"
M_SPORT_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/b/b3/BMW_M_logo.svg"

def safe_rerun():
    """Waterproof context manager to handle page refreshes across all Streamlit versions."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ====================================================================
# OFFICIAL BMW DIGITAL DESIGN IDENTITY CSS INJECTION
# ====================================================================
st.markdown("""
    <style>
        /* Global Typography & Background Restructuring */
        html, body, [data-testid="stAppViewContainer"] {
            font-family: "BMWTypeNext", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
            background-color: #FFFFFF !important;
        }
        
        /* Premium Flat Input Elements & Dropzones */
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea, .stMultiSelect>div {
            border: 1px solid #E5E5E5 !important;
            border-radius: 0px !important; 
            background-color: #F6F6F6 !important;
            color: #262626 !important;
            font-size: 0.95rem !important;
            padding: 0.2rem 0.5rem !important;
            transition: all 0.2s ease-in-out;
        }
        .stTextInput>div>div>input:focus {
            border-color: #000000 !important;
            background-color: #FFFFFF !important;
            box-shadow: none !important;
        }
        
        /* Premium Flat Buttons */
        div.stButton {
            width: auto !important;
            max-width: 240px !important; 
            display: inline-block !important;
            margin-top: 0.5rem !important;
        }
        
        div.stButton > button, 
        div.stButton > button:first-child {
            background-color: #000000 !important; 
            border-radius: 0px !important;         
            border: 1px solid #000000 !important;
            padding: 0.6rem 0rem !important;       
            font-weight: 500 !important;
            font-size: 0.8rem !important;
            letter-spacing: 1.5px !important;     
            text-transform: uppercase !important;  
            width: 240px !important;               
            max-width: 240px !important;
            height: 42px !important;
            display: block !important;
            transition: all 0.2s ease-in-out !important;
        }
        
        div.stButton > button * {
            color: #FFFFFF !important;
            width: auto !important;
            max-width: none !important;
            display: inline-block !important;
        }
        
        div.stButton > button:hover,
        div.stButton > button:focus {
            background-color: #262626 !important;
            border-color: #262626 !important;
        }
        
        /* Executive KPI Layout Tweak */
        [data-testid="stMetricValue"] {
            font-size: 2.3rem !important;
            font-weight: 300 !important; 
            color: #000000 !important;
            letter-spacing: -1px !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            color: #666666 !important;
        }
        
        /* Main Navigation Tab Customization */
        button[data-baseweb="tab"] {
            font-size: 0.9rem !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            color: #666666 !important;
            border-bottom-width: 2px !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #000000 !important;
            border-bottom-color: #000000 !important;
            font-weight: 600 !important;
        }
        
        .bmw-logo-left-header {
            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
            gap: 18px !important; 
            width: 100% !important;
        }
        
        .franchise-header-banner {
            background-color: #F6F6F6 !important;
            padding: 10px 15px !important;
            border-left: 4px solid #000000 !important;
            margin-top: 25px !important;
            margin-bottom: 10px !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        /* Center alignment natively targeting data columns */
        .stTable thead tr th:nth-of-type(4),
        .stTable thead tr th:nth-of-type(5),
        .stTable thead tr th:nth-of-type(6) {
            text-align: center !important;
        }
        .stTable tbody tr td:nth-of-type(3),
        .stTable tbody tr td:nth-of-type(4),
        .stTable tbody tr td:nth-of-type(5) {
            text-align: center !important;
        }

        /* Hides the default Pandas row numbers to prevent misalignment without overriding data */
        .stTable thead tr th:first-child,
        .stTable tbody tr th {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase_client() -> Client:
    sb_url = st.secrets["supabase"]["url"]
    sb_key = st.secrets["supabase"]["key"]
    return create_client(sb_url, sb_key)

try:
    supabase = get_supabase_client()
except Exception as e:
    st.error(f"🔒 Secure API Hook Connection Error: {str(e)}")
    st.stop()

# Operational Hour Compliance Guard
now_sast = datetime.now(SAST)
if now_sast.hour >= 22 or now_sast.hour < 6:
    st.error("🛑 **Access Denied: System Offline.**")
    st.stop()

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['name'] = None
    st.session_state['role'] = None

if st.session_state['authenticated']:
    # Authenticated Workspace Layout Header
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.markdown(f"""
            <div class='bmw-logo-left-header'>
                <img src='{BMW_LOGO_URL}' width='50' style='height: auto;'>
                <img src='{M_SPORT_LOGO_URL}' width='65' style='height: auto; margin-top: 4px;'>
                <div style='margin-left: 10px;'>
                    <h3 style='margin: 0; padding: 0; font-size: 1.4rem; font-weight: 400; letter-spacing: 0.5px;'>BMW SANDTON</h3>
                    <p style='margin: 0; padding: 0; font-size: 0.75rem; color: #666666; letter-spacing: 1px;'>SALES LEADS PORTAL • PRODUCTION WORKSPACE NODE</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with header_col2:
        st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
        if st.button("🚪 LOGOUT", key="header_logout_btn"):
            st.session_state['authenticated'] = False
            st.session_state['user'] = None
            st.session_state['name'] = None
            st.session_state['role'] = None
            safe_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"LOGGED IN AS: **{st.session_state['name'].upper()}** ({st.session_state['role'].replace('_', ' ').upper()})")
    st.markdown("---")

    MANAGEMENT_ROLES = ['dealer_principal', 'finance_admin', 'sales_manager']
    IS_MANAGEMENT = st.session_state['role'] in MANAGEMENT_ROLES
    
    if IS_MANAGEMENT:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS", "🚗 USED CAR STOCK STOCKROOM", "💼 PIPELINE TRACKER", "📦 ARCHIVED DELIVERIES", "📊 COMMAND OVERVIEW"])
    else:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS", "🚗 USED CAR STOCK STOCKROOM", "💼 PIPELINE TRACKER", "📦 ARCHIVED DELIVERIES"])

    # ---- TAB 1: AVAILABLE DAILY FEED ----
    with tab1:
        lead_section = st.radio("SELECT OPPORTUNITY CHANNEL", ["🏢 Corporate Fleet (B2B)", "🚗 Individual Leads (B2C)", "🏛️ Gov Tenders (B2B)"], horizontal=True)
        selected_date = st.date_input("FILTER BY GENERATION DATE", datetime.now(SAST))
        filter_date_str = selected_date.strftime('%Y-%m-%d')
        st.markdown("---")
        
        if lead_section == "🏢 Corporate Fleet (B2B)":
            res = supabase.table("leads").select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str).order("score", desc=True).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            if df.empty:
                st.info("No unassigned corporate fleet leads found for this date.")
            else:
                for idx, row in df.iterrows():
                    with st.container():
                        col_score, col_content = st.columns([1, 5])
                        with col_score:
                            st.metric("SCORE", f"{row['score']}/100")
                        with col_content:
                            st.markdown(f"### {row['company'].upper()} — {row['location'].upper()}")
                            st.markdown(f"**TARGET PERSONA:** {row['target']}  |  📅 *GENERATED: {row['lead_date']}*")
                            st.info(f"💡 {row['signal']}")
                            if st.button("CLAIM ACCOUNT", key=f"claim_c_{row['id']}"):
                                supabase.table("leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                                safe_rerun()

        elif lead_section == "🚗 Individual Leads (B2C)":
            res = supabase.table("individual_leads").select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str).order("score", desc=True).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            if df.empty:
                st.info("No unassigned individual luxury leads found for this date.")
            else:
                for idx, row in df.iterrows():
                    with st.container():
                        col_score, col_content = st.columns([1, 5])
                        with col_score:
                            st.metric("SCORE", f"{row['score']}/100")
                        with col_content:
                            st.markdown(f"### PROSPECT: {row['client_name'].upper()}")
                            st.markdown(f"**POSITION:** {row['title']} at *{row['company']}* ({row['location']})  |  📅 *GENERATED: {row['lead_date']}*")
                            st.info(f"💎 {row['signal']}")
                            if st.button("CLAIM CLIENT", key=f"claim_i_{row['id']}"):
                                supabase.table("individual_leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                                safe_rerun()

        else:
            res = supabase.table("tender_leads").select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str).order("score", desc=True).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            if df.empty:
                st.info("No unassigned government tender wins flagged for this date.")
            else:
                for idx, row in df.iterrows():
                    with st.container():
                        col_score, col_content = st.columns([1, 5])
                        with col_score:
                            st.metric("SCORE", f"{row['score']}/100")
                        with col_content:
                            st.markdown(f"### VENDOR: {row['company'].upper()}")
                            st.markdown(f"**AWARDING BODY:** {row['awarding_body']}  |  💰 **VALUE:** `{row['contract_value']}`")
                            st.info(f"🏛️ {row['tender_desc']}")
                            if st.button("CLAIM TENDER", key=f"claim_t_{row['id']}"):
                                supabase.table("tender_leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                                safe_rerun()

    # ---- TAB 2: CLAIMED LEADS INTERACTION PANELS ----
    with tab2:
        my_corp_res = supabase.table("leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
        my_ind_res = supabase.table("individual_leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
        my_tend_res = supabase.table("tender_leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
        
        st.markdown("### 🏢 CLAIMED CORPORATE FLEET ACCOUNTS")
        if not my_corp_res.data:
            st.caption("No active corporate fleet claims linked to your profile.")
        else:
            for row in my_corp_res.data:
                with st.expander(f"COMPANY: {row['company'].upper()} ({row['location'].upper()})"):
                    st.write(f"**SIGNAL ANALYSIS:** {row['signal']}")
                    st.markdown("#### 📞 CONTACT SECURE ANCHORS")
                    c_i1, c_i2, c_i3, c_i4 = st.columns(4)
                    c_i1.markdown(f"**Email:**\n`{row['public_email']}`")
                    c_i2.markdown(f"**Phone Line:**\n`{row['public_phone']}`")
                    c_i3.markdown(f"[🌐 Web Domain]({row['company_website']})")
                    c_i4.markdown(f"[🔗 LinkedIn Connect]({row['linkedin_url']})")
                    st.markdown("---")
                    note_text = st.text_area("LOG COMMUNICATIONS NOTE", key=f"n_c_{row['id']}")
                    if st.button("SAVE LOG NOTE", key=f"s_c_{row['id']}") and note_text:
                        supabase.table("lead_notes").insert({
                            "lead_id": row['id'], "lead_type": "corporate", "username": st.session_state['user'],
                            "salesperson_name": st.session_state['name'], "note_text": note_text, "timestamp": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                        }).execute()
                        st.success("Note committed to cloud registry.")
                        safe_rerun()
                    if st.button("CLOSE ACCOUNT AS CONVERTED", key=f"cl_c_{row['id']}"):
                        supabase.table("leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        safe_rerun()

        st.markdown("---")
        st.markdown("### 🚗 MY CLAIMED PRIVATE LUXURY CLIENTS")
        if not my_ind_res.data:
            st.caption("No active individual accounts claimed.")
        else:
            for row in my_ind_res.data:
                with st.expander(f"PROSPECT: {row['client_name'].upper()} — {row['title'].upper()}"):
                    st.write(f"**OUTREACH SIGNAL:** {row['signal']}")
                    st.markdown("#### 📞 DIRECT CONTACT DETAILS")
                    i_i1, i_i2, i_i3 = st.columns(3)
                    i_i1.markdown(f"**Direct Email:**\n`{row['public_email']}`")
                    i_i2.markdown(f"**Office Line:**\n`{row['public_phone']}`")
                    i_i3.markdown(f"[🔗 LinkedIn Profile]({row['linkedin_url']})")
                    st.markdown("---")
                    note_text_ind = st.text_area("LOG CLIENT VERBAL UPDATE", key=f"n_i_{row['id']}")
                    if st.button("SAVE CLIENT UPDATE", key=f"s_i_{row['id']}") and note_text_ind:
                        supabase.table("lead_notes").insert({
                            "lead_id": row['id'], "lead_type": "individual", "username": st.session_state['user'],
                            "salesperson_name": st.session_state['name'], "note_text": note_text_ind, "timestamp": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                        }).execute()
                        st.success("Client updates cataloged.")
                        safe_rerun()
                    if st.button("MARK UNIT SECURED & DELIVERED 🔑", key=f"cl_i_{row['id']}"):
                        supabase.table("individual_leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        safe_rerun()

        st.markdown("---")
        st.markdown("### 🏛️ CLAIMED TENDER VENDORS")
        if not my_tend_res.data:
            st.caption("No active government tender claims currently flagged.")
        else:
            for row in my_tend_res.data:
                with st.expander(f"TENDER WINNER: {row['company'].upper()}"):
                    st.write(f"**PROJECT ANCHOR DESC:** {row['tender_desc']}")
                    st.markdown("#### 📞 CORPORATE MANAGEMENT ANCHORS")
                    t_i1, t_i2, t_i3, t_i4 = st.columns(4)
                    t_i1.markdown(f"**Primary Email:**\n`{row['public_email']}`")
                    t_i2.markdown(f"**Switchboard Phone:**\n`{row['public_phone']}`")
                    t_i3.markdown(f"[🌐 Corporate Site]({row['company_website']})")
                    t_i4.markdown(f"[🔗 LinkedIn Anchor]({row['linkedin_url']})")
                    st.markdown("---")
                    note_text_tend = st.text_area("LOG FLEET ENGAGEMENT SUMMARY", key=f"n_t_{row['id']}")
                    if st.button("SAVE TENDER DATA NOTE", key=f"s_t_{row['id']}") and note_text_tend:
                        supabase.table("lead_notes").insert({
                            "lead_id": row['id'], "lead_type": "tender", "username": st.session_state['user'],
                            "salesperson_name": st.session_state['name'], "note_text": note_text_tend, "timestamp": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                        }).execute()
                        st.success("Engagement data safely written.")
                        safe_rerun()
                    if st.button("MARK CONTRACT LOGISTICS SECURED 🚚", key=f"cl_t_{row['id']}"):
                        supabase.table("tender_leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        safe_rerun()

    # ---- 🚗 TAB 3: USED CAR STOCKROOM NODE WITH NEW FLOORPLAN ENGINE ----
    with tab3:
        st.markdown("### 🚗 LIVE USED CAR STOCKROOM")
        st.caption("Single source of truth inventory registry organized and separated by official franchise division lines.")
        
        if st.session_state['role'] == 'finance_admin':
            with st.expander("🛠️ ADMIN CONSOLE: INVENTORY & FLOORPLAN MANAGEMENT", expanded=False):
                # Section 1: Standard Paste Data
                st.markdown("#### 1. Paste Daily Spreadsheet Data")
                raw_paste_data = st.text_area("PASTE RAW DATA ROWS HERE", height=150, placeholder="Franchise: B - BMW\n109237\tX4 xDrive20d Sport A...")
                
                if st.button("PROCESS AND OVERWRITE INVENTORY", key="process_stock_paste_btn"):
                    if raw_paste_data.strip():
                        try:
                            lines = raw_paste_data.split('\n')
                            records_processed = 0
                            current_franchise = "General Used Stock"
                            
                            supabase.table("used_car_stock").delete().gt("days_in_stock", -1).execute()
                            supabase.table("used_car_stock").delete().eq("days_in_stock", 0).execute()
                            
                            for line in lines:
                                cleaned_line = line.strip()
                                if not cleaned_line:
                                    continue
                                    
                                if "franchise:" in cleaned_line.lower():
                                    current_franchise = cleaned_line.split(':', 1)[1].strip()
                                    continue
                                    
                                parts = cleaned_line.split('\t') if '\t' in cleaned_line else cleaned_line.split(',')
                                
                                if len(parts) >= 2 and parts[0].strip().isdigit():
                                    vsb = parts[0].strip()
                                    desc = parts[1].strip()
                                    into_stk = parts[2].strip() if len(parts) > 2 else ''
                                    
                                    try: val = float(parts[10].strip().replace(' ', '').replace(' ', '').replace(',', '')) if len(parts) > 10 else 0.00
                                    except: val = 0.00
                                        
                                    try: days = int(float(parts[11].strip().replace(' ', '').strip())) if len(parts) > 11 and parts[11].strip() else 0
                                    except: days = 0
                                        
                                    chassis = parts[13].strip() if len(parts) > 13 else ''
                                    
                                    try:
                                        supabase.table("used_car_stock").upsert({
                                            "vsb_no": vsb, "description": desc, "into_stock": into_stk,
                                            "days_in_stock": days, "total_value": val, "location": current_franchise.strip(), "chassis_no": chassis,
                                            "floorplan_status": "⚪ PENDING RECON"
                                        }).execute()
                                    except Exception as e:
                                        supabase.table("used_car_stock").upsert({
                                            "vsb_no": vsb, "description": desc, "into_stock": into_stk,
                                            "days_in_stock": days, "total_value": val, "location": current_franchise.strip(), "chassis_no": chassis
                                        }).execute()
                                    
                                    records_processed += 1
                                    
                            st.success(f"🎉 Stock refreshed successfully. {records_processed} units inserted.")
                            safe_rerun()
                        except Exception as parse_ex:
                            st.error(f"Data processing failed: {str(parse_ex)}")
                    else:
                        st.warning("Please populate the data terminal before submitting.")
                
                st.markdown("---")
                
                # Section 2: Automated Recon Engine prioritizing VIN
                st.markdown("#### 2. Run Daily Floorplan Recon")
                st.caption("Upload your daily CSV export reports (Current Units Summary) to automatically cross-reference VINs and identify unencumbered vs financed stock.")
                fp_files = st.file_uploader("Upload Floorplan & Bridge CSV Files", type=['csv'], accept_multiple_files=True)
                
                if st.button("RUN FLOORPLAN RECONCILIATION", key="run_recon_btn"):
                    if fp_files:
                        with st.spinner("Analyzing CSV reports and cross-referencing VINs against database..."):
                            fp_vsbs = set()
                            fp_chassis = set()
                            
                            for f in fp_files:
                                try:
                                    content = f.read().decode("utf-8", errors="ignore").splitlines()
                                    header_idx = 0
                                    for i, line in enumerate(content):
                                        if "Stock No" in line or "Chassis" in line:
                                            header_idx = i
                                            break
                                    
                                    f.seek(0)
                                    df_fp = pd.read_csv(f, skiprows=header_idx)
                                    
                                    stock_col = next((c for c in df_fp.columns if 'stock no' in c.lower()), None)
                                    if stock_col:
                                        digits_only = df_fp[stock_col].astype(str).str.replace(r'\D', '', regex=True)
                                        fp_vsbs.update(digits_only.tolist())
                                        
                                    chassis_col = next((c for c in df_fp.columns if 'chassis' in c.lower() or 'vin' in c.lower()), None)
                                    if chassis_col:
                                        clean_chassis = df_fp[chassis_col].astype(str).str.strip().str.upper()
                                        fp_chassis.update(clean_chassis.tolist())
                                except Exception as e:
                                    st.error(f"Error parsing {f.name}: {e}")
                                    
                            try:
                                db_stock = supabase.table("used_car_stock").select("vsb_no, chassis_no").execute()
                            except:
                                db_stock = supabase.table("used_car_stock").select("vsb_no").execute()
                                
                            if db_stock.data:
                                update_count = 0
                                for row in db_stock.data:
                                    db_chassis = str(row.get('chassis_no', '')).strip().upper()
                                    db_vsb = str(row.get('vsb_no', '')).strip()
                                    db_vsb_clean = ''.join(filter(str.isdigit, db_vsb))
                                    
                                    is_on_fp = False
                                    if db_chassis and db_chassis in fp_chassis:
                                        is_on_fp = True
                                    elif db_vsb_clean and db_vsb_clean in fp_vsbs:
                                        is_on_fp = True
                                        
                                    status = "ON FLOORPLAN" if is_on_fp else "UNENCUMBERED"
                                    try:
                                        supabase.table("used_car_stock").update({"floorplan_status": status}).eq("vsb_no", row['vsb_no']).execute()
                                        update_count += 1
                                    except:
                                        pass
                                    
                                st.success(f"✅ Recon complete! {update_count} units successfully cross-referenced using globally unique VIN strings.")
                                safe_rerun()
                    else:
                        st.warning("Please upload at least one CSV file to run the reconciliation engine.")

        # ---- LIVE STOCK DATA FETCHING & DISPLAY ----
        try:
            try:
                stock_res = supabase.table("used_car_stock").select("vsb_no, description, into_stock, days_in_stock, total_value, location, floorplan_status").order("days_in_stock", desc=True).execute()
            except:
                stock_res = supabase.table("used_car_stock").select("vsb_no, description, into_stock, days_in_stock, total_value, location").order("days_in_stock", desc=True).execute()
                
            df_live_stock = pd.DataFrame(stock_res.data) if stock_res.data else pd.DataFrame()
        except:
            df_live_stock = pd.DataFrame()

        if not df_live_stock.empty:
            
            # Map and format display fields cleanly
            if 'floorplan_status' not in df_live_stock.columns:
                df_live_stock['floorplan_status'] = "⚪ PENDING RECON"
            
            def map_fp_status(status):
                s = str(status)
                if s == "ON FLOORPLAN": return "🏦 ON FLOORPLAN"
                elif s == "UNENCUMBERED": return "🟢 UNENCUMBERED"
                return "⚪ PENDING RECON"

            df_live_stock["floorplan_status"] = df_live_stock["floorplan_status"].apply(map_fp_status)
                
            df_live_stock = df_live_stock.rename(columns={
                "vsb_no": "VSB NUMBER",
                "description": "VEHICLE DESCRIPTION",
                "into_stock": "INTO STOCK DATE",
                "days_in_stock": "DAYS ON FLOOR",
                "total_value": "CAPITAL VAL (ZAR)",
                "location": "FRANCHISE DIVISION",
                "floorplan_status": "FP STATUS"
            })
            
            if "FP STATUS" not in df_live_stock.columns:
                df_live_stock["FP STATUS"] = "⚪ PENDING RECON"
                
            df_live_stock["FRANCHISE DIVISION"] = df_live_stock["FRANCHISE DIVISION"].astype(str).str.strip()
            
            total_units_global = len(df_live_stock)
            total_value_global = df_live_stock['CAPITAL VAL (ZAR)'].sum()
            total_age_global = df_live_stock['DAYS ON FLOOR'].mean()
            
            s_col1, s_col2, s_col3 = st.columns(3)
            s_col1.metric("TOTAL VEHICLES AVAILABLE", f"{total_units_global:,} UNITS")
            s_col2.metric("TOTAL STOCKHOLDING CAPITAL", f"R {total_value_global:,.2f}")
            s_col3.metric("TOTAL AVERAGE FLOOR AGE", f"{int(total_age_global)} DAYS")
            
            st.markdown("---")
            unique_franchises_options = sorted(list(df_live_stock["FRANCHISE DIVISION"].unique()))
            unique_franchises_options = [f for f in unique_franchises_options if f.strip() != "LHP" and f.strip()]
            
            # 🚨 FILTER UPGRADE: Responsive column split for management filters
            if IS_MANAGEMENT:
                col_filter1, col_filter2, col_filter3, col_filter4 = st.columns([2, 2, 2, 1])
                with col_filter1:
                    selected_franchises = st.multiselect("FILTER BY FRANCHISE DIVISION(S)", options=unique_franchises_options, key="franchise_multi_selector")
                with col_filter2:
                    search_query = st.text_input("🔍 LIVE GLOBAL VEHICLE SEARCH", "").strip().lower()
                with col_filter3:
                    fp_opts = ["ALL", "🏦 ON FLOORPLAN", "🟢 UNENCUMBERED", "⚪ PENDING RECON"]
                    selected_fp = st.selectbox("FILTER BY FLOORPLAN STATUS", fp_opts)
                with col_filter4:
                    st.markdown("<br>", unsafe_allow_html=True)
                    show_hot_only = st.checkbox("🔥 HOT STOCKS", value=False, key="hot_stocks_toggle")
            else:
                col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])
                with col_filter1:
                    selected_franchises = st.multiselect("FILTER BY FRANCHISE DIVISION(S)", options=unique_franchises_options, key="franchise_multi_selector")
                with col_filter2:
                    search_query = st.text_input("🔍 LIVE GLOBAL VEHICLE SEARCH", "").strip().lower()
                with col_filter3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    show_hot_only = st.checkbox("🔥 SHOW HOT STOCKS ONLY", value=False, key="hot_stocks_toggle")
                selected_fp = "ALL"
            
            filtered_df = df_live_stock.copy()
            if selected_franchises:
                filtered_df = filtered_df[filtered_df["FRANCHISE DIVISION"].isin(selected_franchises)]
                
            if selected_fp != "ALL":
                filtered_df = filtered_df[filtered_df["FP STATUS"] == selected_fp]
                
            if search_query:
                filtered_df = filtered_df[
                    filtered_df['VEHICLE DESCRIPTION'].astype(str).str.lower().str.contains(search_query) |
                    filtered_df['VSB NUMBER'].astype(str).str.lower().str.contains(search_query)
                ]
                
            if show_hot_only:
                filtered_df = filtered_df[filtered_df["DAYS ON FLOOR"] <= 3]
            
            loop_franchises = sorted(list(filtered_df["FRANCHISE DIVISION"].unique())) if not selected_franchises else selected_franchises
            
            for franchise in loop_franchises:
                if franchise.strip() == "LHP" or not franchise.strip():
                    continue
                    
                franchise_df = filtered_df[filtered_df["FRANCHISE DIVISION"] == franchise].copy()
                
                if not franchise_df.empty:
                    f_units = len(franchise_df)
                    f_value = franchise_df['CAPITAL VAL (ZAR)'].sum()
                    
                    st.markdown(f"""
                        <div class='franchise-header-banner'>
                            🏢 FRANCHISE DIVISION: {franchise.upper()} &nbsp;|&nbsp; 
                            <span style='font-weight: 300; text-transform: none;'>({f_units} Units — Subtotal: R {f_value:,.2f})</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    render_rows = []
                    for _, row in franchise_df.iterrows():
                        days = int(row.get("DAYS ON FLOOR", 0))
                        
                        if days <= 3: days_badge = "🔥 NEW STOCK"
                        elif days >= 121: days_badge = f"🚨 {days} DAYS (Critical Ageing: Max Prov)"
                        elif days >= 91: days_badge = f"⚠️ {days} DAYS (Approaching max prov)"
                        else: days_badge = f"{days} Days"
                        
                        row_dict = {
                            "VSB NUMBER": row.get("VSB NUMBER", ""),
                            "VEHICLE DESCRIPTION": row.get("VEHICLE DESCRIPTION", ""),
                            "INTO STOCK DATE": row.get("INTO STOCK DATE", ""),
                            "DAYS ON FLOOR": days_badge
                        }
                        
                        if IS_MANAGEMENT:
                            row_dict["FP STATUS"] = row.get("FP STATUS", "")
                            
                        row_dict["CAPITAL VAL (ZAR)"] = f"R {float(row.get('CAPITAL VAL (ZAR)', 0)):,.2f}"
                        
                        render_rows.append(row_dict)
                        
                    render_df = pd.DataFrame(render_rows)
                    
                    # 🚨 FIX: Do not set index so VSB number stays visible as Column 1
                    # Custom CSS removes the blank index numbering natively!
                    
                    # Determine columns to explicitly show based on role
                    cols_to_render = ["VSB NUMBER", "VEHICLE DESCRIPTION", "INTO STOCK DATE", "DAYS ON FLOOR"]
                    if IS_MANAGEMENT:
                        cols_to_render.append("FP STATUS")
                    cols_to_render.append("CAPITAL VAL (ZAR)")
                    
                    st.table(render_df[cols_to_render])
        else:
            st.info("💡 The used vehicle stock register is currently empty. Waiting for Finance/Admin profile sync.")

    # ---- TAB 4: INTERACTIVE PIPELINE TRACKER ----
    with tab4:
        st.markdown("### 💼 SALES PIPELINE: ACTIVE DEALS")
        
        PIPELINE_STAGES = ["Prospecting", "Test Drive", "Finance App", "Awaiting Delivery", "Delivered", "Cancelled"]
        
        with st.expander("➕ ADD NEW DEAL TO PIPELINE"):
            col_a, col_b = st.columns(2)
            client = col_a.text_input("CLIENT NAME")
            
            try:
                pipe_stock_res = supabase.table("used_car_stock").select("vsb_no, description").execute()
                pipe_stock_list = pipe_stock_res.data if pipe_stock_res.data else []
            except:
                pipe_stock_list = []
                
            stock_options = ["✏️ CUSTOM ENTRY (Not in Stock / Buy-in)"] + [f"{s['vsb_no']} - {s['description']}" for s in pipe_stock_list]
            stock_selection = col_b.selectbox("LINK TO INVENTORY (Type to search stock)", stock_options)
            
            if stock_selection == "✏️ CUSTOM ENTRY (Not in Stock / Buy-in)":
                deal_desc = col_b.text_input("ENTER CUSTOM VEHICLE / DEAL DESCRIPTION")
            else:
                deal_desc = stock_selection
            
            stage = col_a.selectbox("CURRENT STAGE", PIPELINE_STAGES)
            delivery_date = col_a.date_input("PLANNED DELIVERY DATE (Estimated)", datetime.now(SAST))
            value = col_b.number_input("ESTIMATED VALUE (ZAR)", min_value=0.0)
            
            if st.button("COMMIT DEAL TO PIPELINE"):
                if client and deal_desc:
                    try:
                        supabase.table("sales_pipeline").insert({
                            "salesperson_username": st.session_state['user'],
                            "client_name": client,
                            "deal_description": deal_desc,
                            "stage": stage,
                            "estimated_value": value,
                            "planned_delivery_date": delivery_date.strftime('%Y-%m-%d'),
                            "notes": ""
                        }).execute()
                        st.success("Deal successfully logged to pipeline.")
                        safe_rerun()
                    except Exception as e:
                        st.error(f"Save failed. Did you run the SQL commands to update the database? Error: {e}")
                else:
                    st.warning("Please enter both the client name and deal description.")

        if st.session_state['role'] in MANAGEMENT_ROLES:
            st.markdown("#### 🕵️ MANAGER VIEW: ALL ACTIVE DEALS")
            res = supabase.table("sales_pipeline").select("*").neq("stage", "Delivered").order("id", desc=True).execute()
        else:
            st.markdown("#### 👤 MY ACTIVE DEALS")
            res = supabase.table("sales_pipeline").select("*").eq("salesperson_username", st.session_state['user']).neq("stage", "Delivered").order("id", desc=True).execute()
        
        df_pipeline = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        
        if not df_pipeline.empty:
            if 'planned_delivery_date' not in df_pipeline.columns: df_pipeline['planned_delivery_date'] = None
            if 'notes' not in df_pipeline.columns: df_pipeline['notes'] = ""
            if 'estimated_value' not in df_pipeline.columns: df_pipeline['estimated_value'] = 0.0
            
            render_pipe = pd.DataFrame()
            if st.session_state['role'] in MANAGEMENT_ROLES:
                render_pipe["REP USERNAME"] = df_pipeline["salesperson_username"].apply(lambda x: f"@{x}")
                
            render_pipe["CLIENT NAME"] = df_pipeline["client_name"]
            render_pipe["DEAL DESCRIPTION"] = df_pipeline["deal_description"]
            render_pipe["STAGE"] = df_pipeline["stage"]
            render_pipe["ESTIMATED VALUE (ZAR)"] = df_pipeline["estimated_value"].map(lambda x: f"R {float(x):,.2f}")
            render_pipe["DELIVERY DATE"] = pd.to_datetime(df_pipeline["planned_delivery_date"], errors='coerce').dt.strftime('%d %b %Y').fillna("Unscheduled")
            
            st.table(render_pipe)
            
            st.markdown("#### 🛠️ UPDATE ACTIVE PIPELINE DEALS")
            for idx, row in df_pipeline.iterrows():
                if row['stage'] == "Cancelled":
                    stage_icon = "🛑"
                else:
                    stage_icon = "⏳"
                
                with st.expander(f"{stage_icon} {row['client_name'].upper()} | {row['deal_description']} — {row['stage'].upper()}"):
                    c1, c2 = st.columns([1, 2])
                    
                    with c1:
                        st.markdown(f"**REP:** `@{row['salesperson_username']}`")
                        st.markdown(f"**EST. VALUE:** R {float(row.get('estimated_value', 0)):,.2f}")
                        
                        db_date = row.get('planned_delivery_date')
                        if pd.isna(db_date) or not db_date:
                            curr_date = datetime.now(SAST).date()
                        else:
                            try: curr_date = datetime.strptime(str(db_date).split("T")[0], '%Y-%m-%d').date()
                            except: curr_date = datetime.now(SAST).date()
                                
                        current_index = PIPELINE_STAGES.index(row['stage']) if row['stage'] in PIPELINE_STAGES else 0
                        new_stage = st.selectbox("UPDATE STATUS", PIPELINE_STAGES, index=current_index, key=f"stage_{row['id']}")
                        new_date = st.date_input("UPDATE DELIVERY DATE", value=curr_date, key=f"date_{row['id']}")
                        
                    with c2:
                        current_notes = row.get('notes', '')
                        if pd.isna(current_notes) or current_notes is None: current_notes = ""
                        new_notes = st.text_area("DEAL NOTES (Shared between Rep & Manager)", value=str(current_notes), height=180, key=f"notes_{row['id']}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("SAVE PIPELINE UPDATES", key=f"update_{row['id']}"):
                        try:
                            supabase.table("sales_pipeline").update({
                                "stage": new_stage,
                                "planned_delivery_date": new_date.strftime('%Y-%m-%d'),
                                "notes": new_notes
                            }).eq("id", row['id']).execute()
                            st.success("Deal updated successfully.")
                            safe_rerun()
                        except Exception as e:
                            st.error(f"Failed to update. Error: {e}")
        else:
            st.info("No active pipeline deals currently tracked.")

    # ---- TAB 5: ARCHIVED DELIVERIES ----
    with tab5:
        st.markdown("### 📦 ARCHIVED DELIVERIES")
        st.caption("Historical log of successfully delivered vehicles, ordered by the latest delivery date.")
        
        if st.session_state['role'] in MANAGEMENT_ROLES:
            arc_res = supabase.table("sales_pipeline").select("*").eq("stage", "Delivered").execute()
        else:
            arc_res = supabase.table("sales_pipeline").select("*").eq("salesperson_username", st.session_state['user']).eq("stage", "Delivered").execute()
            
        df_archive = pd.DataFrame(arc_res.data) if arc_res.data else pd.DataFrame()
        
        if not df_archive.empty:
            if 'planned_delivery_date' not in df_archive.columns: df_archive['planned_delivery_date'] = None
            if 'notes' not in df_archive.columns: df_archive['notes'] = ""
            if 'estimated_value' not in df_archive.columns: df_archive['estimated_value'] = 0.0
            
            df_archive['sort_date'] = pd.to_datetime(df_archive['planned_delivery_date'], errors='coerce')
            df_archive = df_archive.sort_values(by='sort_date', ascending=False).drop(columns=['sort_date'])
            
            render_arch = pd.DataFrame()
            if st.session_state['role'] in MANAGEMENT_ROLES:
                render_arch["REP USERNAME"] = df_archive["salesperson_username"].apply(lambda x: f"@{x}")
                
            render_arch["CLIENT NAME"] = df_archive["client_name"]
            render_arch["DEAL DESCRIPTION"] = df_archive["deal_description"]
            render_arch["DELIVERY DATE"] = pd.to_datetime(df_archive["planned_delivery_date"], errors='coerce').dt.strftime('%d %b %Y').fillna("Unknown")
            render_arch["FINAL VALUE (ZAR)"] = df_archive["estimated_value"].map(lambda x: f"R {float(x):,.2f}")
            
            st.table(render_arch)
            
            st.markdown("#### 📂 ARCHIVE DETAILS & REVISIONS")
            for idx, row in df_archive.iterrows():
                with st.expander(f"✅ {row['client_name'].upper()} | {row['deal_description']} — DELIVERED ON: {pd.to_datetime(row['planned_delivery_date'], errors='coerce').strftime('%d %b %Y')}"):
                    c1, c2 = st.columns([1, 2])
                    
                    with c1:
                        st.markdown(f"**REP:** `@{row['salesperson_username']}`")
                        st.markdown(f"**EST. VALUE:** R {float(row.get('estimated_value', 0)):,.2f}")
                        
                        db_date = row.get('planned_delivery_date')
                        if pd.isna(db_date) or not db_date:
                            curr_date = datetime.now(SAST).date()
                        else:
                            try: curr_date = datetime.strptime(str(db_date).split("T")[0], '%Y-%m-%d').date()
                            except: curr_date = datetime.now(SAST).date()
                                
                        PIPELINE_STAGES = ["Prospecting", "Test Drive", "Finance App", "Awaiting Delivery", "Delivered", "Cancelled"]
                        current_index = PIPELINE_STAGES.index(row['stage']) if row['stage'] in PIPELINE_STAGES else 4
                        
                        new_stage = st.selectbox("REVISE STATUS", PIPELINE_STAGES, index=current_index, key=f"arc_stage_{row['id']}")
                        new_date = st.date_input("REVISE DELIVERY DATE", value=curr_date, key=f"arc_date_{row['id']}")
                        
                    with c2:
                        current_notes = row.get('notes', '')
                        if pd.isna(current_notes) or current_notes is None: current_notes = ""
                        new_notes = st.text_area("DEAL NOTES", value=str(current_notes), height=180, key=f"arc_notes_{row['id']}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("SAVE REVISIONS", key=f"arc_update_{row['id']}"):
                        try:
                            supabase.table("sales_pipeline").update({
                                "stage": new_stage,
                                "planned_delivery_date": new_date.strftime('%Y-%m-%d'),
                                "notes": new_notes
                            }).eq("id", row['id']).execute()
                            st.success("Archive record updated successfully.")
                            safe_rerun()
                        except Exception as e:
                            st.error(f"Failed to update. Error: {e}")
        else:
            st.info("No delivered deals have been archived yet.")

    # ---- TAB 6: COMMAND OVERVIEW & EXECUTIVE SUMMARIES ----
    if st.session_state['role'] in MANAGEMENT_ROLES:
        with tab6:
            st.markdown("### 👑 MANAGEMENT COMMAND OVERVIEW & AUDITS")
            
            # --- OVERVIEW A: STOCK SUMMARY MATRIX ---
            st.markdown("#### 📊 DEALERSHIP USED CAR STOCK SUMMARY OVERVIEW")
            try:
                raw_res = supabase.table("used_car_stock").select("total_value, days_in_stock, location").execute()
                df_summary = pd.DataFrame(raw_res.data) if raw_res.data else pd.DataFrame()
            except:
                df_summary = pd.DataFrame()
                
            categories_def = [
                ("Used BMW", lambda df: df["location"].str.lower().str.contains("b -") | df["location"].str.lower().str.contains("i -")),
                ("Used MINI", lambda df: df["location"].str.lower().str.contains("m -")),
                ("Used MC", lambda df: df["location"].str.lower().str.contains("a -") | df["location"].str.lower().str.contains("c -")),
                ("Tier Sandton", lambda df: df["location"].str.lower().str.contains("z -"))
            ]
            
            summary_matrix_data = []
            provision_rows = []
            
            for cat_name, mask_func in categories_def:
                if not df_summary.empty:
                    df_summary["location"] = df_summary["location"].astype(str).str.strip()
                    mask = mask_func(df_summary)
                    cat_df = df_summary[mask]
                    
                    units = len(cat_df)
                    val_sum = cat_df["total_value"].sum()
                    
                    v_30_60 = cat_df[(cat_df["days_in_stock"] >= 30) & (cat_df["days_in_stock"] <= 60)]["total_value"].sum()
                    v_61_90 = cat_df[(cat_df["days_in_stock"] >= 61) & (cat_df["days_in_stock"] <= 90)]["total_value"].sum()
                    v_91_120 = cat_df[(cat_df["days_in_stock"] >= 91) & (cat_df["days_in_stock"] <= 120)]["total_value"].sum()
                    v_121_plus = cat_df[cat_df["days_in_stock"] >= 121]["total_value"].sum()
                else:
                    units = 0
                    val_sum = 0.00
                    v_30_60 = v_61_90 = v_91_120 = v_121_plus = 0.00
                
                p_2_5 = v_30_60 * 0.025
                p_5_0 = v_61_90 * 0.050
                p_7_5 = v_91_120 * 0.075
                p_10_0 = v_121_plus * 0.100
                p_total = p_2_5 + p_5_0 + p_7_5 + p_10_0
                
                summary_matrix_data.append({
                    "STOCK DIVISION": cat_name, 
                    "UNITS ON HAND": f"{units:,}", 
                    "PORTFOLIO INVESTMENT VALUE": f"R {val_sum:,.2f}"
                })
                
                provision_rows.append({
                    "STOCK DIVISION": cat_name,
                    "2.5% (30-60 Days)": f"R {p_2_5:,.2f}",
                    "5.0% (61-90 Days)": f"R {p_5_0:,.2f}",
                    "7.5% (91-120 Days)": f"R {p_7_5:,.2f}",
                    "10.0% (121+ Days)": f"R {p_10_0:,.2f}",
                    "TOTAL PROVISION": f"R {p_total:,.2f}"
                })
            
            df_sum_mat = pd.DataFrame(summary_matrix_data)
            df_sum_mat.set_index("STOCK DIVISION", inplace=True)
            st.table(df_sum_mat)
            
            # --- OVERVIEW B: AGING PROVISION SUMMARY MATRIX ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 🪙 DEALERSHIP VEHICLE AGING PROVISION MATRIX")
            df_prov_mat = pd.DataFrame(provision_rows)
            df_prov_mat.set_index("STOCK DIVISION", inplace=True)
            st.table(df_prov_mat)
                
            st.markdown("---")
            try:
                c_leads = len(supabase.table("leads").select("id").execute().data)
                i_leads = len(supabase.table("individual_leads").select("id").execute().data)
                t_leads = len(supabase.table("tender_leads").select("id").execute().data)
                c_closed = len(supabase.table("leads").select("id").eq("status", "Closed").execute().data)
                i_closed = len(supabase.table("individual_leads").select("id").eq("status", "Closed").execute().data)
                t_closed = len(supabase.table("tender_leads").select("id").eq("status", "Closed").execute().data)
                df_master_notes = pd.DataFrame(supabase.table("lead_notes").select("*").order("timestamp", desc=True).execute().data)
            except:
                c_leads, i_leads, t_leads, c_closed, i_closed, t_closed = 0, 0, 0, 0, 0, 0
                df_master_notes = pd.DataFrame()
                
            m1, m2, m3 = st.columns(3)
            m1.metric("TOTAL OPPORTUNITIES", c_leads + i_leads + t_leads)
            m2.metric("CONVERSIONS (B2B)", c_closed + t_closed)
            m3.metric("DELIVERIES (B2C)", i_closed)
            
            st.markdown("---")
            st.markdown("### 💬 MASTER OUTREACH AUDIT REGISTRY")
            if df_master_notes.empty:
                st.info("No transaction log adjustments submitted today.")
            else:
                for idx, r_note in df_master_notes.iterrows():
                    with st.chat_message("user"):
                        st.markdown(f"**{r_note['salesperson_name'].upper()}** (`@{r_note['username']}`) handled a **{r_note['lead_type'].upper()}** channel asset at *{r_note['timestamp']}*")
                        st.write(f"📝 *\"{r_note['note_text']}\"*")
else:
    # Gateway Authorization Interface Layer
    gate_col1, gate_col2, gate_col3 = st.columns([1.5, 3, 1.5])
    with gate_col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
            <div class='bmw-logo-centered-header'>
                <img src='{BMW_LOGO_URL}' width='82' style='height: auto; display: block;'>
                <img src='{M_SPORT_LOGO_URL}' width='98' style='height: auto; display: block; margin-top: 6px;'>
            </div>
        """, unsafe_allow_html=True)
            
        st.markdown("<h2 style='text-align: center; font-weight: 300; letter-spacing: 1px; margin-top:25px; margin-bottom: 0;'>BMW SANDTON</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size:0.85rem; color:#666666; letter-spacing:1px; margin-top: 5px;'>SALES LEADS PORTAL</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    
        auth_tab, signup_tab = st.tabs(["🔒 SECURE SIGN IN", "📝 CREATE ACCESS ACCOUNT"])
        
        with auth_tab:
            login_username = st.text_input("USERNAME", key="login_user").strip().lower()
            login_password = st.text_input("PASSWORD", type="password", key="login_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("AUTHENTICATE ACCESS", key="login_btn"):
                if login_username and login_password:
                    try:
                        res = supabase.table("users").select("name", "role", "password").eq("username", login_username).execute()
                        if res.data:
                            import hashlib
                            hashed_input = hashlib.sha256(login_password.encode()).hexdigest()
                            if res.data[0]['password'] == hashed_input:
                                st.session_state['authenticated'] = True
                                st.session_state['user'] = login_username
                                st.session_state['name'] = res.data[0]['name']
                                st.session_state['role'] = res.data[0]['role']
                                safe_rerun()
                            else:
                                st.error("Authentication rejected: invalid credentials.")
                        else:
                            st.error("Identity matching trace failed: profile not found.")
                    except Exception as e:
                        st.error(f"Gateway Handshake Error: {str(e)}")
                        
        with signup_tab:
            st.markdown("### REGISTER NEW DEALERSHIP PROFILE")
            new_name = st.text_input("FULL NAME", key="reg_name").strip()
            new_username = st.text_input("CHOOSE SYSTEM USERNAME", key="reg_user").strip().lower()
            new_password = st.text_input("CHOOSE ACCESS PASSWORD", type="password", key="reg_pass")
            chosen_role = st.selectbox("SELECT POSITION", ["Sales Representative", "Dealer Principal", "Finance/Admin", "Sales Manager"], key="reg_role")
            security_code = st.text_input("DEALERSHIP SECURITY AUTHORIZATION CODE", type="password", key="reg_code")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("INITIALIZE ACCOUNT PROFILE", key="signup_btn"):
                if not new_name or not new_username or not new_password:
                    st.warning("All verification input parameters must be compiled.")
                elif " " in new_username:
                    st.error("Usernames cannot incorporate empty spacing gaps.")
                elif security_code != "SandtonBMW2026":
                    st.error("Incorrect Dealership Security Authorization Code.")
                else:
                    try:
                        if chosen_role == "Dealer Principal":
                            role_db_value = 'dealer_principal'
                        elif chosen_role == "Finance/Admin":
                            role_db_value = 'finance_admin'
                        elif chosen_role == "Sales Manager":
                            role_db_value = 'sales_manager'
                        else:
                            role_db_value = 'sales_rep'
                            
                        existing = supabase.table("users").select("username").eq("username", new_username).execute()
                        if existing.data:
                            st.error("System username is already claimed.")
                        else:
                            import hashlib
                            hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
                            supabase.table("users").insert({
                                "username": new_username, "password": hashed_pw, "name": new_name, "role": role_db_value
                            }).execute()
                            st.success("🎉 Account profile initialized. Proceed to Sign In tab.")
                    except Exception as e:
                        st.error(f"Profile Initialization Error: {str(e)}")
    st.stop()
