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
# Reference: https://www.bmw.co.za/en/index.html flat luxury architecture
# ====================================================================
st.markdown("""
    <style>
        /* Global Typography & Background Restructuring */
        html, body, [data-testid="stAppViewContainer"] {
            font-family: "BMWTypeNext", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
            background-color: #FFFFFF !important;
        }
        
        /* Premium Flat Input Elements & Dropzones */
        .stTextInput>div>div>input, .stSelectbox>div>div>div, [data-testid="stFileUploader"] {
            border: 1px solid #E5E5E5 !important;
            border-radius: 0px !important; /* Flat geometric corners */
            background-color: #F6F6F6 !important;
            color: #262626 !important;
            font-size: 0.95rem !important;
        }
        .stTextInput>div>div>input:focus {
            border-color: #000000 !important;
            background-color: #FFFFFF !important;
            box-shadow: none !important;
        }
        
        /* =========================================================
           🚨 WATERPROOF BUTTON TEXT & FIXED NORMAL SIZE CONTAINER FIX 🚨
           ========================================================= */
        /* Completely contains the Streamlit block wrapper from expanding */
        div.stButton {
            width: auto !important;
            max-width: 240px !important; 
            display: inline-block !important;
            margin-top: 0.5rem !important;
        }
        
        /* TARGETS THE BUTTON CANVAS ONLY */
        div.stButton > button, 
        div.stButton > button:first-child {
            background-color: #000000 !important; /* Absolute Black Background */
            border-radius: 0px !important;         /* Sharp geometric edges */
            border: 1px solid #000000 !important;
            padding: 0.6rem 0rem !important;       
            font-weight: 500 !important;
            font-size: 0.8rem !important;
            letter-spacing: 1.5px !important;     /* Premium text tracking */
            text-transform: uppercase !important;  /* Corporate styling */
            width: 240px !important;               /* FIXED CLEAN DIMENSIONS */
            max-width: 240px !important;
            height: 42px !important;
            display: block !important;
            transition: all 0.2s ease-in-out !important;
        }
        
        /* TARGETS INNER TEXT LAYERS SEPARATELY */
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
        
        div.stButton > button:active {
            transform: scale(0.98) !important;
        }
        
        /* Clean Up Executive KPI Elements */
        [data-testid="stMetricValue"] {
            font-size: 2.3rem !important;
            font-weight: 300 !important; /* BMW premium signature light weight */
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
        
        .bmw-logo-centered-header {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            gap: 24px !important; 
            width: 100% !important;
            margin: 0 auto !important;
            padding-bottom: 10px !important;
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
    
    if st.session_state['role'] in MANAGEMENT_ROLES:
        tab1, tab2, tab3, tab4 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS", "📦 LIVE STOCK DASHBOARD", "📊 COMMAND OVERVIEW"])
    else:
        tab1, tab2 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS"])

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

    # ---- TAB 2: CLAIMED ACCOUNTS CHANNEL MONITORING ----
    with tab2:
        my_corp_res = supabase.table("leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
        my_ind_res = supabase.table("individual_leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
        my_tend_res = supabase.table("tender_leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
        
        st.markdown("### 🏢 CLAIMED CORPORATE FLEET ACCOUNTS")
        if not my_corp_res.data:
            st.caption("No active claims linked to your profile.")
        else:
            for row in my_corp_res.data:
                with st.expander(f"COMPANY: {row['company'].upper()} ({row['location'].upper()})"):
                    st.write(f"**SIGNAL:** {row['signal']}")
                    if st.button("CLOSE ACCOUNT AS CONVERTED", key=f"cl_c_{row['id']}"):
                        supabase.table("leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        safe_rerun()
                        
        st.markdown("### 🚗 CLAIMED PRIVATE LUXURY CLIENTS")
        if not my_ind_res.data:
            st.caption("No active private client claims linked to your profile.")
        else:
            for row in my_ind_res.data:
                with st.expander(f"CLIENT: {row['client_name'].upper()}"):
                    st.write(f"**SIGNAL:** {row['signal']}")
                    if st.button("CLOSE CLIENT AS DELIVERED", key=f"cl_i_{row['id']}"):
                        supabase.table("individual_leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        safe_rerun()
                        
        st.markdown("### 🏛️ CLAIMED GOVERNMENT TENDER ACCOUNTS")
        if not my_tend_res.data:
            st.caption("No active tender wins linked to your profile.")
        else:
            for row in my_tend_res.data:
                with st.expander(f"VENDOR: {row['company'].upper()}"):
                    st.write(f"**SIGNAL:** {row['tender_desc']}")
                    if st.button("CLOSE TENDER AS LOGISTICS SECURED", key=f"cl_t_{row['id']}"):
                        supabase.table("tender_leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        safe_rerun()

    # ---- 📦 TAB 3: LIVE STOCK DASHBOARD PORTAL ----
    if st.session_state['role'] in MANAGEMENT_ROLES:
        with tab3:
            st.markdown("### 📦 DEALERSHIP STOCK CONTROL ENGINE")
            st.caption("Morning stock registry upload zone. Upload your daily 'BMW Sandton Stock - 05.06.2026.xlsx' spreadsheet below to refresh inventory metrics.")
            
            stock_file = st.file_uploader("UPLOAD CURRENT MORNING STOCK EXCEL TEMPLATE", type=["xlsx", "csv"], key="stock_sheet_uploader")
            default_overview_path = "BMW Sandton Stock - 05.06.2026.xlsx - Overview.csv"
            
            if stock_file is not None:
                try:
                    if stock_file.name.endswith('.csv'):
                        df_stock = pd.read_csv(stock_file)
                    else:
                        df_stock = pd.read_excel(stock_file, sheet_name='Overview')
                    st.success("⚡ Morning inventory sheet successfully parsed and committed to session memory.")
                except Exception as ex:
                    st.error(f"Error parsing uploaded file format: {str(ex)}")
                    df_stock = pd.read_csv(default_overview_path) if os.path.exists(default_overview_path) else pd.DataFrame()
            else:
                df_stock = pd.read_csv(default_overview_path) if os.path.exists(default_overview_path) else pd.DataFrame()
                if not df_stock.empty:
                    st.caption("📊 Displaying current live repository stock footprint data:")
            
            if not df_stock.empty:
                total_units = int(df_stock.iloc[9]['Units']) if len(df_stock) > 9 else df_stock['Units'].sum()
                total_value = float(df_stock.iloc[9]['Value']) if len(df_stock) > 9 and not pd.isna(df_stock.iloc[9]['Value']) else df_stock['Value'].sum()
                
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("TOTAL VEHICLES IN STOCK", f"{total_units} UNITS")
                m_col2.metric("PORTFOLIO CAPITAL VALUE", f"R {total_value:,.2f}")
                m_col3.metric("SANDTON NODE COMPLEX", "HQ SHOWROOM")
                
                st.markdown("---")
                st.markdown("#### 📑 FRANCHISE SEGMENTATION ANALYSIS")
                
                cleaned_stock = df_stock.dropna(subset=[df_stock.columns[0]]).copy()
                cleaned_stock.columns = ["STOCK SEGMENT CHANNEL", "UNITS ON HAND", "INVESTMENT VALUE (ZAR)"]
                
                cleaned_stock["UNITS ON HAND"] = cleaned_stock["UNITS ON HAND"].map(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
                cleaned_stock["INVESTMENT VALUE (ZAR)"] = cleaned_stock["INVESTMENT VALUE (ZAR)"].map(lambda x: f"R {float(x):,.2f}" if pd.notna(x) else "R 0.00")
                
                st.table(cleaned_stock)
            else:
                st.warning("No template inventory lines could be verified in memory. Please complete an operational upload cycle.")

    # ---- TAB 4: MANAGEMENT COMMAND OVERVIEW ----
    if st.session_state['role'] in MANAGEMENT_ROLES:
        with tab4:
            st.markdown("### 📊 AUDIT REGISTRY AND INTERACTION SYSTEM")
            try:
                c_leads = len(supabase.table("leads").select("id").execute().data)
                i_leads = len(supabase.table("individual_leads").select("id").execute().data)
                t_leads = len(supabase.table("tender_leads").select("id").execute().data)
                df_master_notes = pd.DataFrame(supabase.table("lead_notes").select("*").order("timestamp", desc=True).execute().data)
            except:
                c_leads, i_leads, t_leads = 0, 0, 0
                df_master_notes = pd.DataFrame()
                
            m1, m2 = st.columns(2)
            m1.metric("TOTAL OPPORTUNITIES IN ENGINE", c_leads + i_leads + t_leads)
            m2.metric("ACTIVE LOGGED AGENTS", "ONLINE")
            
            if not df_master_notes.empty:
                st.markdown("---")
                st.markdown("### 💬 LATEST LOGGED COMMUNICATIONS")
                st.dataframe(df_master_notes[["salesperson_name", "lead_type", "note_text", "timestamp"]], use_container_width=True)
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
            chosen_role = st.selectbox(
                "SELECT POSITION", 
                ["Sales Representative", "Dealer Principal", "Finance/Admin", "Sales Manager"], 
                key="reg_role"
            )
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
