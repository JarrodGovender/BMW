import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from supabase import create_client, Client

# ==========================================
# 1. INITIALIZATION & PRODUCTION API SETUP
# ==========================================
st.set_page_config(page_title="BMW Sandton Lead Hub", layout="wide")
SAST = pytz.timezone('Africa/Johannesburg')

# Public CDN URLs for Official BMW and M Sport Logo Assets
BMW_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/4/44/BMW.svg"
M_SPORT_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/b/b3/BMW_M_logo.svg"

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
        
        /* Premium Flat Input Elements */
        .stTextInput>div>div>input, .stSelectbox>div>div>div {
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
           🚨 WATERPROOF BUTTON TEXT FIX: FORCING CRISP WHITE TEXT 🚨
           ========================================================= */
        div.stButton > button, 
        div.stButton > button:first-child,
        div.stButton > button * {
            background-color: #000000 !important; /* Absolute Black Background */
            color: #FFFFFF !important;            /* Force crisp white text on button base */
            border-radius: 0px !important;         /* Geometric corners */
            border: 1px solid #000000 !important;
            font-weight: 500 !important;
            font-size: 0.85rem !important;
            letter-spacing: 1.5px !important;     /* Luxury tracking */
            text-transform: uppercase !important;  /* Corporate naming style */
            transition: all 0.2s ease-in-out !important;
        }
        
        /* Force text to stay white during all micro-interactions */
        div.stButton > button:hover,
        div.stButton > button:hover *,
        div.stButton > button:focus,
        div.stButton > button:focus * {
            background-color: #262626 !important;
            border-color: #262626 !important;
            color: #FFFFFF !important; /* Keeps text fully visible */
        }
        
        div.stButton > button:active {
            transform: scale(0.99) !important;
        }
        
        /* Structural Framed Lead Cards */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E5E5 !important; /* Subtle corporate divider line */
            border-radius: 0px !important; /* No rounded borders */
            padding: 1.5rem !important;
            margin-bottom: 1rem !important;
            transition: border-color 0.2s ease;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: #A0A0A0 !important; /* Elegant focus indicator */
        }
        
        /* Clean Up Executive KPI Elements */
        [data-testid="stMetricValue"] {
            font-size: 2.6rem !important;
            font-weight: 300 !important; /* BMW signature light weights */
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
        
        /* Standard structural typography overrides */
        h1, h2, h3, h4, label {
            color: #262626 !important;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase_client() -> Client:
    # Authenticate cleanly using the standard secure HTTPS web layer
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
    header_col1, header_col2, header_col3 = st.columns([2.5, 4, 1.5])
    with header_col1:
        logo_sub1, logo_sub2 = st.columns(2)
        logo_sub1.image(BMW_LOGO_URL, width=60)
        logo_sub2.image(M_SPORT_LOGO_URL, width=70)
    with header_col2:
        st.subheader("BMW CORPORATE FLEET ENGINE")
        st.caption("GAUTENG DEALERSHIP PIPELINE NETWORK • PRODUCTION WORKSPACE NODE")
    with header_col3:
        if st.button("🚪 LOGOUT", key="header_logout_btn"):
            st.session_state['authenticated'] = False
            st.session_state['user'] = None
            st.session_state['name'] = None
            st.session_state['role'] = None
            st.rerun()

    st.markdown(f"LOGGED IN AS: **{st.session_state['name'].upper()}** ({st.session_state['role'].replace('_', ' ').upper()})")
    st.markdown("---")

    if st.session_state['role'] == 'dealer_principal':
        tab1, tab2, tab3 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS", "📊 COMMAND OVERVIEW"])
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
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([1, 4, 1.5])
                        col1.metric("SCORE", f"{row['score']}/100")
                        col2.markdown(f"### {row['company'].upper()} — {row['location'].upper()}")
                        col2.markdown(f"**TARGET PERSONA:** {row['target']}  |  📅 *GENERATED: {row['lead_date']}*")
                        col2.info(f"💡 {row['signal']}")
                        if col3.button("CLAIM ACCOUNT", key=f"claim_c_{row['id']}"):
                            supabase.table("leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                            st.rerun()

        elif lead_section == "🚗 Individual Leads (B2C)":
            res = supabase.table("individual_leads").select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str).order("score", desc=True).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            if df.empty:
                st.info("No unassigned individual luxury leads found for this date.")
            else:
                for idx, row in df.iterrows():
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([1, 4, 1.5])
                        col1.metric("SCORE", f"{row['score']}/100")
                        col2.markdown(f"### PROSPECT: {row['client_name'].upper()}")
                        col2.markdown(f"**POSITION:** {row['title']} at *{row['company']}* ({row['location']})  |  📅 *GENERATED: {row['lead_date']}*")
                        col2.info(f"💎 {row['signal']}")
                        if col3.button("CLAIM CLIENT", key=f"claim_i_{row['id']}"):
                            supabase.table("individual_leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                            st.rerun()

        else:
            res = supabase.table("tender_leads").select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str).order("score", desc=True).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            if df.empty:
                st.info("No unassigned government tender wins flagged for this date.")
            else:
                for idx, row in df.iterrows():
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([1, 4, 1.5])
                        col1.metric("SCORE", f"{row['score']}/100")
                        col2.markdown(f"### VENDOR: {row['company'].upper()}")
                        col2.markdown(f"**AWARDING BODY:** {row['awarding_body']}  |  💰 **VALUE:** `{row['contract_value']}`")
                        col2.info(f"🏛️ {row['tender_desc']}")
                        if col3.button("CLAIM TENDER", key=f"claim_t_{row['id']}"):
                            supabase.table("tender_leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                            st.rerun()

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
                        st.rerun()
                    if st.button("CLOSE ACCOUNT AS CONVERTED", key=f"cl_c_{row['id']}"):
                        supabase.table("leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        st.rerun()

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
                        st.rerun()
                    if st.button("MARK UNIT SECURED & DELIVERED 🔑", key=f"cl_i_{row['id']}"):
                        supabase.table("individual_leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        st.rerun()

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
                        st.rerun()
                    if st.button("MARK CONTRACT LOGISTICS SECURED 🚚", key=f"cl_t_{row['id']}"):
                        supabase.table("tender_leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                        st.rerun()

    # ---- TAB 3: DEALER PRINCIPAL OVERVIEW ----
    if st.session_state['role'] == 'dealer_principal':
        with tab3:
            st.markdown("### 👑 DEALER PRINCIPAL CONTROL GATE & METRICS")
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
    gate_col1, gate_col2, gate_col3 = st.columns([2, 3, 2])
    with gate_col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Structured corporate dual badge array
        logo_g1, logo_g2 = st.columns([1, 1.2])
        logo_g1.image(BMW_LOGO_URL, width=90)
        with logo_g2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.image(M_SPORT_LOGO_URL, width=105)
            
        st.markdown("<h2 style='text-align: center; font-weight: 300; letter-spacing: 1px; margin-top:20px;'>BMW ENTERPRISE SYSTEM</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size:0.85rem; color:#666666; letter-spacing:1px;'>GAUTENG FLEET LOGISTICS PORTAL</p>", unsafe_allow_html=True)
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
                                st.rerun()
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
            chosen_role = st.selectbox("SELECT POSITION", ["Sales Representative", "Dealer Principal"], key="reg_role")
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
                        role_db_value = 'dealer_principal' if chosen_role == "Dealer Principal" else 'sales_rep'
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
