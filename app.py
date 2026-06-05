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

# Premium BMW Corporate Brand Identity CSS Injection
st.markdown("""
    <style>
        /* Modernize input boxes, selectors, and tabs */
        .stTextInput>div>div>input, .stSelectbox>div>div>div {
            border: 1px solid #2D3748 !important;
            border-radius: 4px !important;
            background-color: #121824 !important;
            transition: all 0.3s ease;
        }
        .stTextInput>div>div>input:focus {
            border-color: #06469D !important;
            box-shadow: 0 0 0 1px #06469D !important;
        }
        
        /* Transform buttons into sharp, premium tactical triggers */
        div.stButton > button:first-child {
            background-color: #06469D !important;
            color: white !important;
            border-radius: 4px !important;
            border: none !important;
            padding: 0.6rem 2rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase;
            font-size: 0.85rem;
            width: 100%;
            transition: background-color 0.2s ease, transform 0.1s ease;
        }
        div.stButton > button:first-child:hover {
            background-color: #1D63B8 !important;
            cursor: pointer;
        }
        div.stButton > button:first-child:active {
            transform: scale(0.98);
        }
        
        /* Clean up executive KPI metrics block */
        [data-testid="stMetricValue"] {
            font-size: 2.4rem !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
            letter-spacing: -0.5px;
        }
        
        /* Style card containers */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #161C26 !important;
            border: 1px solid #232B3B !important;
            border-radius: 6px !important;
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

if not st.session_state['authenticated']:
    # Corporate Platform Header Array
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("BMW Corporate Fleet Engine")
    st.caption("Gauteng Dealership Pipeline Network • Production Workspace Node")
with header_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Secure Logout"):
        st.session_state['authenticated'] = False
        st.rerun()
    
    auth_tab, signup_tab = st.tabs(["🔒 Sign In", "📝 Create Sales Account"])
    
    with auth_tab:
        login_username = st.text_input("Username", key="login_user").strip().lower()
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", key="login_btn"):
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
                            st.success("Access granted...")
                            st.rerun()
                        else:
                            st.error("Invalid production credentials.")
                    else:
                        st.error("Account not found.")
                except Exception as e:
                    st.info("💡 Pro-Tip: Ensure your tables are initially primed by running your GitHub Scraper workflow first.")
                    st.error(f"API Fetch Error: {str(e)}")
                    
    with signup_tab:
        st.markdown("### Register New Dealer Profile")
        new_name = st.text_input("Full Name", key="reg_name").strip()
        new_username = st.text_input("Choose a Username", key="reg_user").strip().lower()
        new_password = st.text_input("Choose a Password", type="password", key="reg_pass")
        chosen_role = st.selectbox("Select Your Position", ["Sales Representative", "Dealer Principal"], key="reg_role")
        security_code = st.text_input("Dealership Authorization Code", type="password", key="reg_code")
        
        if st.button("Create Account", key="signup_btn"):
            if not new_name or not new_username or not new_password:
                st.warning("Please fill in all fields.")
            elif " " in new_username:
                st.error("Usernames cannot contain spaces.")
            elif security_code != "SandtonBMW2026":
                st.error("Incorrect Dealership Authorization Code.")
            else:
                try:
                    role_db_value = 'dealer_principal' if chosen_role == "Dealer Principal" else 'sales_rep'
                    existing = supabase.table("users").select("username").eq("username", new_username).execute()
                    if existing.data:
                        st.error("Username is already taken.")
                    else:
                        import hashlib
                        hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
                        supabase.table("users").insert({
                            "username": new_username, "password": hashed_pw, "name": new_name, "role": role_db_value
                        }).execute()
                        st.success("🎉 Account created! Switch to Sign In tab.")
                except Exception as e:
                    st.error(f"Registration Write Error: {str(e)}")
    st.stop()

# ==========================================
# 4. DASHBOARD INTERFACE WORKSPACE
# ==========================================
st.title("📈 Daily Sandton Client Lead Hub")
st.markdown(f"Logged in as: **{st.session_state['name']}** ({st.session_state['role'].replace('_', ' ').title()})")

if st.sidebar.button("Logout"):
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['name'] = None
    st.session_state['role'] = None
    st.rerun()

if st.session_state['role'] == 'dealer_principal':
    tab1, tab2, tab3 = st.tabs(["🔥 Available Daily Feed", "💼 My Claimed Accounts", "📊 Dealer Principal Command Overview"])
else:
    tab1, tab2 = st.tabs(["🔥 Available Daily Feed (First-Come, First-Served)", "💼 My Claimed Accounts"])

# ---- TAB 1: AVAILABLE DAILY FEED ----
with tab1:
    lead_section = st.radio("Select Target Section", ["🏢 Corporate Fleet (B2B)", "🚗 Individual Leads (B2C)", "🏛️ Gov Tenders (B2B)"], horizontal=True)
    selected_date = st.date_input("Filter by Generation Date", datetime.now(SAST))
    filter_date_str = selected_date.strftime('%Y-%m-%d')
    st.markdown("---")
    
    if lead_section == "🏢 Corporate Fleet (B2B)":
        res = supabase.table("leads").select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str).order("score", desc=True).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if df.empty:
            st.info("No unassigned corporate fleet leads found for this date.")
        else:
            for idx, row in df.iterrows():
                col1, col2, col3 = st.columns([1, 4, 1])
                col1.metric("Score", f"{row['score']}/100")
                col2.subheader(f"{row['company']} — {row['location']}")
                col2.markdown(f"**Target Persona:** {row['target']} | 📅 *Generated: {row['lead_date']}*")
                col2.info(f"💡 {row['signal']}")
                if col3.button("Claim Fleet Lead", key=f"claim_c_{row['id']}"):
                    supabase.table("leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                    st.rerun()
                st.markdown("---")
                    
    elif lead_section == "🚗 Individual Leads (B2C)":
        res = supabase.table("individual_leads").select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str).order("score", desc=True).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if df.empty:
            st.info("No unassigned individual luxury leads found for this date.")
        else:
            for idx, row in df.iterrows():
                col1, col2, col3 = st.columns([1, 4, 1])
                col1.metric("Score", f"{row['score']}/100")
                col2.subheader(f"Prospect: {row['client_name']}")
                col2.markdown(f"**Position:** {row['title']} at *{row['company']}* ({row['location']}) | 📅 *Generated: {row['lead_date']}*")
                col2.info(f"💎 {row['signal']}")
                if col3.button("Claim Client Lead", key=f"claim_i_{row['id']}"):
                    supabase.table("individual_leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                    st.rerun()
                st.markdown("---")

    else:
        res = supabase.table("tender_leads").select("*").eq("status", "Unassigned").eq("lead_date", filter_date_str).order("score", desc=True).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if df.empty:
            st.info("No unassigned government tender wins flagged for this date.")
        else:
            for idx, row in df.iterrows():
                col1, col2, col3 = st.columns([1, 4, 1])
                col1.metric("Score", f"{row['score']}/100")
                col2.subheader(f"Winning Vendor: {row['company']}")
                col2.markdown(f"**Awarding Body:** {row['awarding_body']} | 💰 **Contract Value:** `{row['contract_value']}`")
                col2.info(f"🏛️ {row['tender_desc']}")
                if col3.button("Claim Tender Lead", key=f"claim_t_{row['id']}"):
                    supabase.table("tender_leads").update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", row['id']).execute()
                    st.rerun()
                st.markdown("---")

# ---- TAB 2: CLAIMED LEADS INTERACTION PANELS ----
with tab2:
    my_corp_res = supabase.table("leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
    my_ind_res = supabase.table("individual_leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
    my_tend_res = supabase.table("tender_leads").select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute()
    
    st.subheader("🏢 My Claimed Corporate Fleet Accounts")
    if not my_corp_res.data:
        st.caption("No active corporate fleet claims.")
    else:
        for row in my_corp_res.data:
            with st.expander(f"Company: {row['company']} ({row['location']})"):
                st.write(f"**Signal Details:** {row['signal']}")
                st.markdown("### 📞 Public Contact Anchors")
                c_i1, c_i2, c_i3, c_i4 = st.columns(4)
                c_i1.markdown(f"**Email:**\n`{row['public_email']}`")
                c_i2.markdown(f"**Phone:**\n`{row['public_phone']}`")
                c_i3.markdown(f"[🌐 Website]({row['company_website']})")
                c_i4.markdown(f"[🔗 LinkedIn]({row['linkedin_url']})")
                st.markdown("---")
                note_text = st.text_area("Log Fleet Note", key=f"n_c_{row['id']}")
                if st.button("Save Fleet Note", key=f"s_c_{row['id']}") and note_text:
                    supabase.table("lead_notes").insert({
                        "lead_id": row['id'], "lead_type": "corporate", "username": st.session_state['user'],
                        "salesperson_name": st.session_state['name'], "note_text": note_text, "timestamp": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                    }).execute()
                    st.success("Note logged.")
                    st.rerun()
                if st.button("Mark Fleet Converted", key=f"cl_c_{row['id']}"):
                    supabase.table("leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                    st.rerun()

    st.markdown("---")
    st.subheader("🚗 My Claimed Individual Private Client Accounts")
    if not my_ind_res.data:
        st.caption("No active individual private client claims.")
    else:
        for row in my_ind_res.data:
            with st.expander(f"Prospect: {row['client_name']} — {row['title']}"):
                st.write(f"**Signal Details:** {row['signal']}")
                st.markdown("### 📞 Public Contacts")
                i_i1, i_i2, i_i3 = st.columns(3)
                i_i1.markdown(f"**Direct Email:**\n`{row['public_email']}`")
                i_i2.markdown(f"**Office Phone:**\n`{row['public_phone']}`")
                i_i3.markdown(f"[🔗 LinkedIn Profile]({row['linkedin_url']})")
                st.markdown("---")
                note_text_ind = st.text_area("Log Client Note", key=f"n_i_{row['id']}")
                if st.button("Save Client Note", key=f"s_i_{row['id']}") and note_text_ind:
                    supabase.table("lead_notes").insert({
                        "lead_id": row['id'], "lead_type": "individual", "username": st.session_state['user'],
                        "salesperson_name": st.session_state['name'], "note_text": note_text_ind, "timestamp": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                    }).execute()
                    st.success("Note logged.")
                    st.rerun()
                if st.button("Mark Sale Won 🔑", key=f"cl_i_{row['id']}"):
                    supabase.table("individual_leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                    st.rerun()

    st.markdown("---")
    st.subheader("🏛️ My Claimed Tender Winner Accounts")
    if not my_tend_res.data:
        st.caption("No active government tender claims in progress.")
    else:
        for row in my_tend_res.data:
            with st.expander(f"Tender Winner: {row['company']}"):
                st.write(f"**Project Details:** {row['tender_desc']}")
                st.markdown("### 📞 Public Corporate Contact Anchors")
                t_i1, t_i2, t_i3, t_i4 = st.columns(4)
                t_i1.markdown(f"**Email:**\n`{row['public_email']}`")
                t_i2.markdown(f"**Phone Line:**\n`{row['public_phone']}`")
                t_i3.markdown(f"[🌐 Corporate Site]({row['company_website']})")
                t_i4.markdown(f"[🔗 LinkedIn]({row['linkedin_url']})")
                st.markdown("---")
                note_text_tend = st.text_area("Log Tender Note", key=f"n_t_{row['id']}")
                if st.button("Save Tender Note", key=f"s_t_{row['id']}") and note_text_tend:
                    supabase.table("lead_notes").insert({
                        "lead_id": row['id'], "lead_type": "tender", "username": st.session_state['user'],
                        "salesperson_name": st.session_state['name'], "note_text": note_text_tend, "timestamp": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                    }).execute()
                    st.success("Note logged.")
                    st.rerun()
                if st.button("Mark Tender Fleet Secured 🚚", key=f"cl_t_{row['id']}"):
                    supabase.table("tender_leads").update({"status": "Closed"}).eq("id", row['id']).execute()
                    st.rerun()

# ---- TAB 3: DEALER PRINCIPAL OVERVIEW ----
if st.session_state['role'] == 'dealer_principal':
    with tab3:
        st.header("👑 Dealership Performance & Master Activity Pipeline")
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
        m1.metric("Total Tracked Scoped Opportunities", c_leads + i_leads + t_leads)
        m2.metric("Fleet & Tender Conversions (B2B)", c_closed + t_closed)
        m3.metric("Private Deliveries (B2C)", i_closed, delta=f"+{c_closed + i_closed + t_closed} Total Units")
        st.markdown("---")
        st.subheader("💬 Live Master Communications Audit Log")
        if df_master_notes.empty:
            st.info("No outreach updates logged yet today.")
        else:
            for idx, r_note in df_master_notes.iterrows():
                with st.chat_message("user"):
                    st.markdown(f"**{r_note['salesperson_name']}** (`@{r_note['username']}`) handled a **{r_note['lead_type'].upper()}** profile at *{r_note['timestamp']}*")
                    st.write(f"📝 *\"{r_note['note_text']}\"*")
