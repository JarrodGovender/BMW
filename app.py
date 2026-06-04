import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
import pytz
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# ==========================================
# 1. INITIALIZATION & PRODUCTION DB CONNECTION
# ==========================================
st.set_page_config(page_title="BMW Sandton Lead Hub", layout="wide")
SAST = pytz.timezone('Africa/Johannesburg')

# Establishes a permanent connection utilizing encrypted Streamlit Secrets credentials
@st.cache_resource
def get_db_engine():
    # Explicitly import both components to resolve the naming error completely
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL
    
    db_secrets = st.secrets["connections"]["postgresql"]
    
    # Build a structured connection object to guarantee tenant resolution
    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=db_secrets['username'],
        password=db_secrets['password'],
        host=db_secrets['host'],
        port=int(db_secrets['port']),
        database=db_secrets['database'],
        query={"sslmode": "require"}
    )
    return create_engine(connection_url, pool_pre_ping=True)

def init_production_db():
    engine = get_db_engine()
    with engine.begin() as conn:
        # Create enterprise relational architecture schemas safely if missing on Supabase instance
        conn.execute(text('''CREATE TABLE IF NOT EXISTS users 
                             (username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT)'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS lead_notes 
                             (id SERIAL PRIMARY KEY, lead_id INTEGER, lead_type TEXT, username TEXT, 
                              salesperson_name TEXT, note_text TEXT, timestamp TEXT)'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS leads 
                             (id SERIAL PRIMARY KEY, company TEXT, location TEXT, signal TEXT, 
                              target TEXT, score INTEGER, status TEXT, assigned_to TEXT, lead_date TEXT,
                              public_email TEXT, public_phone TEXT, linkedin_url TEXT, company_website TEXT)'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS individual_leads 
                             (id SERIAL PRIMARY KEY, client_name TEXT, title TEXT, company TEXT, location TEXT, 
                               signal TEXT, score INTEGER, status TEXT, assigned_to TEXT, lead_date TEXT,
                               public_email TEXT, public_phone TEXT, linkedin_url TEXT)'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS tender_leads 
                             (id SERIAL PRIMARY KEY, company TEXT, location TEXT, awarding_body TEXT,
                              tender_desc TEXT, contract_value TEXT, score INTEGER, status TEXT, assigned_to TEXT, lead_date TEXT,
                              public_email TEXT, public_phone TEXT, linkedin_url TEXT, company_website TEXT)'''))

try:
    init_production_db()
except Exception as e:
    st.error(f"🔒 Database Connection Error: {str(e)}")
    st.info("Ensure your alphanumeric database password and your explicit username format (postgres.your_reference_id) are saved cleanly inside your App Secrets panel.")
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
    st.title("🏢 BMW Sandton Fleet Platform Gateway")
    st.caption("Production Enterprise Access Gate")
    
    auth_tab, signup_tab = st.tabs(["🔒 Sign In", "📝 Create Sales Account"])
    
    with auth_tab:
        login_username = st.text_input("Username", key="login_user").strip().lower()
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", key="login_btn"):
            if login_username and login_password:
                engine = get_db_engine()
                hashed_input = hashlib.sha256(login_password.encode()).hexdigest()
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT name, role FROM users WHERE username=:u AND password=:p"), 
                                          {"u": login_username, "p": hashed_input}).fetchone()
                if result:
                    st.session_state['authenticated'] = True
                    st.session_state['user'] = login_username
                    st.session_state['name'] = result[0]
                    st.session_state['role'] = result[1]
                    st.success("Access granted...")
                    st.rerun()
                else:
                    st.error("Invalid production credentials.")
                    
    with signup_tab:
        st.markdown("### Register New Dealer Profile")
        new_name = st.text_input("Full Name", key="reg_name").strip()
        new_username = st.text_input("Choose a Username", key="reg_user").strip().lower()
        new_password = st.text_input("Choose a Password", type="password", key="reg_pass")
        chosen_role = st.selectbox("Select Your Position", ["Sales Representative", "Dealer Principal"], key="reg_role")
        security_code = st.text_input("Dealership Authorization Code", type="password", key="reg_code")
        
        if st.button("Create Account", key="signup_btn"):
            if not new_name or not new_username or not new_password:
                st.warning("Please fill in all profile fields.")
            elif " " in new_username:
                st.error("Usernames cannot contain spaces.")
            elif security_code != "SandtonBMW2026":
                st.error("Incorrect Dealership Authorization Code.")
            else:
                role_db_value = 'dealer_principal' if chosen_role == "Dealer Principal" else 'sales_rep'
                engine = get_db_engine()
                with engine.begin() as conn:
                    existing = conn.execute(text("SELECT username FROM users WHERE username=:u"), {"u": new_username}).fetchone()
                    if existing:
                        st.error("Username is already taken.")
                    else:
                        hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
                        conn.execute(text("INSERT INTO users VALUES (:u, :p, :n, :r)"),
                                     {"u": new_username, "p": hashed_pw, "n": new_name, "r": role_db_value})
                        st.success("🎉 Enterprise account created! Switch to Sign In tab.")
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

engine = get_db_engine()

# ---- TAB 1: AVAILABLE DAILY FEED ----
with tab1:
    lead_section = st.radio("Select Target Section", ["🏢 Corporate Fleet (B2B)", "🚗 Individual Leads (B2C)", "🏛️ Gov Tenders (B2B)"], horizontal=True)
    selected_date = st.date_input("Filter by Generation Date", datetime.now(SAST))
    filter_date_str = selected_date.strftime('%Y-%m-%d')
    st.markdown("---")
    
    with engine.connect() as conn:
        if lead_section == "🏢 Corporate Fleet (B2B)":
            df = pd.read_sql(text("SELECT * FROM leads WHERE status='Unassigned' AND lead_date=:d ORDER BY score DESC"), conn, params={"d": filter_date_str})
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
                        with engine.begin() as click_conn:
                            click_conn.execute(text("UPDATE leads SET status='Claimed', assigned_to=:u WHERE id=:i"), {"u": st.session_state['user'], "i": row['id']})
                        st.rerun()
                    st.markdown("---")
                        
        elif lead_section == "🚗 Individual Leads (B2C)":
            df = pd.read_sql(text("SELECT * FROM individual_leads WHERE status='Unassigned' AND lead_date=:d ORDER BY score DESC"), conn, params={"d": filter_date_str})
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
                        with engine.begin() as click_conn:
                            click_conn.execute(text("UPDATE individual_leads SET status='Claimed', assigned_to=:u WHERE id=:i"), {"u": st.session_state['user'], "i": row['id']})
                        st.rerun()
                    st.markdown("---")

        else:
            df = pd.read_sql(text("SELECT * FROM tender_leads WHERE status='Unassigned' AND lead_date=:d ORDER BY score DESC"), conn, params={"d": filter_date_str})
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
                        with engine.begin() as click_conn:
                            click_conn.execute(text("UPDATE tender_leads SET status='Claimed', assigned_to=:u WHERE id=:i"), {"u": st.session_state['user'], "i": row['id']})
                        st.rerun()
                    st.markdown("---")

# ---- TAB 2: CLAIMED LEADS INTERACTION PANELS ----
with tab2:
    with engine.connect() as conn:
        my_corp = pd.read_sql(text("SELECT * FROM leads WHERE assigned_to=:u AND status='Claimed'"), conn, params={"u": st.session_state['user']})
        my_ind = pd.read_sql(text("SELECT * FROM individual_leads WHERE assigned_to=:u AND status='Claimed'"), conn, params={"u": st.session_state['user']})
        my_tend = pd.read_sql(text("SELECT * FROM tender_leads WHERE assigned_to=:u AND status='Claimed'"), conn, params={"u": st.session_state['user']})
    
    st.subheader("🏢 My Claimed Corporate Fleet Accounts")
    if my_corp.empty:
        st.caption("No active corporate fleet claims.")
    else:
        for idx, row in my_corp.iterrows():
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
                    with engine.begin() as note_conn:
                        note_conn.execute(text("INSERT INTO lead_notes (lead_id, lead_type, username, salesperson_name, note_text, timestamp) VALUES (:i, 'corporate', :u, :n, :t, :ts)"),
                                          {"i": row['id'], "u": st.session_state['user'], "n": st.session_state['name'], "t": note_text, "ts": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')})
                    st.success("Note logged.")
                    st.rerun()
                if st.button("Mark Fleet Converted", key=f"cl_c_{row['id']}"):
                    with engine.begin() as close_conn:
                        close_conn.execute(text("UPDATE leads SET status='Closed' WHERE id=:i"), {"i": row['id']})
                    st.rerun()

    st.markdown("---")
    st.subheader("🚗 My Claimed Individual Private Client Accounts")
    if my_ind.empty:
        st.caption("No active individual private client claims.")
    else:
        for idx, row in my_ind.iterrows():
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
                    with engine.begin() as note_conn:
                        note_conn.execute(text("INSERT INTO lead_notes (lead_id, lead_type, username, salesperson_name, note_text, timestamp) VALUES (:i, 'individual', :u, :n, :t, :ts)"),
                                          {"i": row['id'], "u": st.session_state['user'], "n": st.session_state['name'], "t": note_text_ind, "ts": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')})
                    st.success("Note logged.")
                    st.rerun()
                if st.button("Mark Sale Won 🔑", key=f"cl_i_{row['id']}"):
                    with engine.begin() as close_conn:
                        close_conn.execute(text("UPDATE individual_leads SET status='Closed' WHERE id=:i"), {"i": row['id']})
                    st.rerun()

    st.markdown("---")
    st.subheader("🏛️ My Claimed Tender Winner Accounts")
    if my_tend.empty:
        st.caption("No active government tender claims in progress.")
    else:
        for idx, row in my_tend.iterrows():
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
                    with engine.begin() as note_conn:
                        note_conn.execute(text("INSERT INTO lead_notes (lead_id, lead_type, username, salesperson_name, note_text, timestamp) VALUES (:i, 'tender', :u, :n, :t, :ts)"),
                                          {"i": row['id'], "u": st.session_state['user'], "n": st.session_state['name'], "t": note_text_tend, "ts": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')})
                    st.success("Note logged.")
                    st.rerun()
                if st.button("Mark Tender Fleet Secured 🚚", key=f"cl_t_{row['id']}"):
                    with engine.begin() as close_conn:
                        close_conn.execute(text("UPDATE tender_leads SET status='Closed' WHERE id=:i"), {"i": row['id']})
                    st.rerun()

# ---- TAB 3: DEALER PRINCIPAL OVERVIEW ----
if st.session_state['role'] == 'dealer_principal':
    with tab3:
        st.header("👑 Dealership Performance & Master Activity Pipeline")
        with engine.connect() as conn:
            c_leads = conn.execute(text("SELECT COUNT(*) FROM leads")).scalar()
            i_leads = conn.execute(text("SELECT COUNT(*) FROM individual_leads")).scalar()
            t_leads = conn.execute(text("SELECT COUNT(*) FROM tender_leads")).scalar()
            c_closed = conn.execute(text("SELECT COUNT(*) FROM leads WHERE status='Closed'")).scalar()
            i_closed = conn.execute(text("SELECT COUNT(*) FROM individual_leads WHERE status='Closed'")).scalar()
            t_closed = conn.execute(text("SELECT COUNT(*) FROM tender_leads WHERE status='Closed'")).scalar()
            df_master_notes = pd.read_sql(text("SELECT * FROM lead_notes ORDER BY timestamp DESC"), conn)
            
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
