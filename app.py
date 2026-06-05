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
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
            border: 1px solid #E5E5E5 !important;
            border-radius: 0px !important; /* Flat geometric corners */
            background-color: #F6F6F6 !important;
            color: #262626 !important;
            font-size: 0.95rem !important;
            padding: 0.5rem !important;
            transition: all 0.2s ease-in-out;
        }
        .stTextInput>div>div>input:focus {
            border-color: #000000 !important;
            background-color: #FFFFFF !important;
            box-shadow: none !important;
        }
        
        /* =========================================================
           🚨 WATERPROOF BUTTON TEXT & FIXED NORMAL SIZE CONTAINER FIX 🚨
           ========================================================= */
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
        
        div.stButton > button:hover *,
        div.stButton > button:focus * {
            color: #FFFFFF !important;
        }
        
        /* Clean Up Executive KPI Elements */
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
        
        h1, h2, h3, h4, label {
            color: #262626 !important;
        }
        
        .bmw-logo-left-header {
            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
            gap: 18px !important; 
            width: 100% !important;
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

# ==========================================
# 2. OPERATIONAL TIME GUARD (10PM - 6AM LOCKOUT)
# ==========================================
now_sast = datetime.now(SAST)
current_hour = now_sast.hour

if current_hour >= 22 or current_hour < 6:
    st.error("🛑 **Access Denied: System Offline.**")
    st.info("To maintain security and compliance boundaries, the BMW Sandton Corporate Fleet Engine locks out all access between **22:00 PM and 06:00 AM SAST**.")
    st.stop()

# ==========================================
# 3. AUTHENTICATION SESSION STATE
# ==========================================
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['name'] = None
    st.session_state['role'] = None

# ==========================================
# 4. CORE PLATFORM ROUTING ROUTER
# ==========================================
if st.session_state['authenticated']:
    # ------------------------------------------
    # VIEW A: AUTHENTICATED PARTNER WORKSPACE
    # ------------------------------------------
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
    
    # Injection Layout Rules: Stock dashboard tab is available across all authentication levels
    if st.session_state['role'] in MANAGEMENT_ROLES:
        tab1, tab2, tab3, tab4 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS", "🚗 USED CAR STOCK STOCKROOM", "📊 COMMAND OVERVIEW"])
    else:
        tab1, tab2, tab3 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS", "🚗 USED CAR STOCK STOCKROOM"])

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

    # ---- 🚗 TAB 3: USED CAR STOCKROOM NODE ----
    with tab3:
        st.markdown("### 🚗 LIVE USED CAR STOCKROOM")
        st.caption("Single source of truth inventory registry organized by official franchise grouping boundaries.")
        
        # Admin Terminal Zone: Locked strictly to Finance/Admin roles
        if st.session_state['role'] == 'finance_admin':
            with st.expander("🛠️ ADMIN CONSOLE: BULK CAR STOCK TERMINAL", expanded=False):
                st.markdown("#### Paste Spreadsheet Data Rows Below")
                raw_paste_data = st.text_area("PASTE RAW DATA ROWS HERE", height=250, placeholder="Franchise: B - BMW\n109237\tX4 xDrive20d Sport A...")
                
                if st.button("PROCESS AND OVERWRITE INVENTORY", key="process_stock_paste_btn"):
                    if raw_paste_data.strip():
                        try:
                            lines = raw_paste_data.split('\n')
                            records_processed = 0
                            current_franchise = "General Used Stock"
                            
                            # Clean old rows cleanly first before mapping new registers
                            supabase.table("used_car_stock").delete().neq("vsb_no", "placeholder_wipe").execute()
                            
                            for line in lines:
                                cleaned_line = line.strip()
                                if not cleaned_line:
                                    continue
                                    
                                # Catch franchise name updates directly
                                if "franchise:" in cleaned_line.lower():
                                    current_franchise = cleaned_line.split(':', 1)[1].strip()
                                    continue
                                    
                                parts = cleaned_line.split('\t') if '\t' in cleaned_line else cleaned_line.split(',')
                                
                                # Isolate rows matching numeric primary VSB key metrics
                                if len(parts) >= 2 and parts[0].strip().isdigit():
                                    vsb = parts[0].strip()
                                    desc = parts[1].strip()
                                    into_stk = parts[2].strip() if len(parts) > 2 else ''
                                    
                                    try:
                                        val = float(parts[10].strip().replace(' ', '').replace(' ', '').replace(',', '')) if len(parts) > 10 else 0.00
                                    except:
                                        val = 0.00
                                        
                                    try:
                                        days = int(float(parts[11].strip().replace(' ', '').strip())) if len(parts) > 11 and parts[11].strip() else 0
                                    except:
                                        days = 0
                                        
                                    chassis = parts[13].strip() if len(parts) > 13 else ''
                                    
                                    supabase.table("used_car_stock").upsert({
                                        "vsb_no": vsb, "description": desc, "into_stock": into_stk,
                                        "days_in_stock": days, "total_value": val, "location": current_franchise, "chassis_no": chassis
                                    }).execute()
                                    records_processed += 1
                                    
                            st.success(f"🎉 Stock refreshed successfully. {records_processed} units assigned to their respective franchises inside cloud engine.")
                            safe_rerun()
                        except Exception as parse_ex:
                            st.error(f"Data processing failed: {str(parse_ex)}")
                    else:
                        st.warning("Please populate the data terminal before submitting.")

        # ---- LIVE COHORT DATA DISPLAY PANELS ----
        try:
            stock_res = supabase.table("used_car_stock").select("vsb_no, description, into_stock, days_in_stock, total_value, location").order("days_in_stock", desc=True).execute()
            df_live_stock = pd.DataFrame(stock_res.data) if stock_res.data else pd.DataFrame()
        except:
            df_live_stock = pd.DataFrame()

        if not df_live_stock.empty:
            df_live_stock.columns = ["VSB NUMBER", "VEHICLE DESCRIPTION", "INTO STOCK DATE", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)", "FRANCHISE DIVISION"]
            franchise_list = ["ALL FRANCHISES"] + sorted(list(df_live_stock["FRANCHISE DIVISION"].unique()))
            
            col_filter1, col_filter2 = st.columns([1, 2])
            with col_filter1:
                selected_franchise = st.selectbox("FILTER BY FRANCHISE DIVISION", franchise_list, key="franchise_selector_dropdown")
            with col_filter2:
                search_query = st.text_input("🔍 SEARCH CATALOG (Type Model name or VSB Number)", "").strip().lower()
            
            filtered_df = df_live_stock.copy()
            if selected_franchise != "ALL FRANCHISES":
                filtered_df = filtered_df[filtered_df["FRANCHISE DIVISION"] == selected_franchise]
                
            if search_query:
                filtered_df = filtered_df[
                    filtered_df['VEHICLE DESCRIPTION'].astype(str).str.lower().str.contains(search_query) |
                    filtered_df['VSB NUMBER'].astype(str).str.lower().str.contains(search_query)
                ]
                
            cnt_units = len(filtered_df)
            sum_capital = filtered_df['CAPITAL VAL (ZAR)'].sum()
            avg_age = filtered_df['DAYS ON FLOOR'].mean() if cnt_units > 0 else 0
            
            st.markdown("<br>", unsafe_allow_html=True)
            s_col1, s_col2, s_col3 = st.columns(3)
            s_col1.metric("UNITS IN SELECTION", f"{cnt_units:,} VEHICLES")
            s_col2.metric("SELECTION BOOK VALUE", f"R {sum_capital:,.2f}")
            s_col3.metric("AVERAGE SELECTION FLOOR AGE", f"{int(avg_age)} DAYS")
            
            st.markdown("---")
            display_df = filtered_df.copy()
            display_df["CAPITAL VAL (ZAR)"] = display_df["CAPITAL VAL (ZAR)"].map(lambda x: f"R {float(x):,.2f}")
            st.table(display_df[["VSB NUMBER", "VEHICLE DESCRIPTION", "INTO STOCK DATE", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)", "FRANCHISE DIVISION"]])
        else:
            st.info("💡 The used vehicle stock register is currently empty. Waiting for Finance/Admin profile sync.")

    # ---- TAB 4: COMMAND OVERVIEW ----
    if st.session_state['role'] in MANAGEMENT_ROLES:
        with tab4:
            st.markdown("### 👑 MANAGEMENT COMMAND OVERVIEW & AUDITS")
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
    # ------------------------------------------
    # VIEW B: GATEWAY INTERFACE (SIGN IN / UP)
    # ------------------------------------------
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
