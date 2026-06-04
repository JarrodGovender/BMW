import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. INITIALIZATION & DATABASE SETUP
# ==========================================
st.set_page_config(page_title="BMW Sandton Lead Hub", layout="wide")
SAST = pytz.timezone('Africa/Johannesburg')

def init_db():
    conn = sqlite3.connect('fleet_leads.db')
    c = conn.cursor()
    
    # Drop older tables to ensure the new tender layout compiles cleanly
    c.execute("DROP TABLE IF EXISTS leads")
    c.execute("DROP TABLE IF EXISTS individual_leads")
    c.execute("DROP TABLE IF EXISTS tender_leads")
    
    # 1. System structural tables
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lead_notes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, lead_type TEXT, username TEXT, 
                  salesperson_name TEXT, note_text TEXT, timestamp TEXT)''')
    
    # 2. Pipeline Table A: Corporate Fleet Leads (B2B)
    c.execute('''CREATE TABLE IF NOT EXISTS leads 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, location TEXT, 
                  signal TEXT, target TEXT, score INTEGER, status TEXT, assigned_to TEXT, lead_date TEXT,
                  public_email TEXT, public_phone TEXT, linkedin_url TEXT, company_website TEXT)''')
                  
    # 3. Pipeline Table B: Individual Luxury Leads (B2C)
    c.execute('''CREATE TABLE IF NOT EXISTS individual_leads 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT, title TEXT, company TEXT, location TEXT, 
                  signal TEXT, score INTEGER, status TEXT, assigned_to TEXT, lead_date TEXT,
                  public_email TEXT, public_phone TEXT, linkedin_url TEXT)''')

    # 4. Pipeline Table C: Government Tender Awards (B2B Tender Focus) - 14 Columns
    c.execute('''CREATE TABLE IF NOT EXISTS tender_leads 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, location TEXT, awarding_body TEXT,
                  tender_desc TEXT, contract_value TEXT, score INTEGER, status TEXT, assigned_to TEXT, lead_date TEXT,
                  public_email TEXT, public_phone TEXT, linkedin_url TEXT, company_website TEXT)''')
    conn.commit()
    conn.close()

# THE AUTO-INGEST ENGINE: Refreshes daily simulated public Gauteng signals
def sync_live_feeds():
    conn = sqlite3.connect('fleet_leads.db')
    c = conn.cursor()
    
    today_str = datetime.now(SAST).strftime('%Y-%m-%d')
    yesterday_str = (datetime.now(SAST) - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Feed Vector A: Live JSE Corporate Fleet Signals
    mock_corporate = [
        ("Vanguard Financial Group", "Sandton Central, Johannesburg", "Office Hub Consolidation: Moving 220 executives to a single facility. ESG mandate requires high-end PHEV/EV corporate fleet updates.", "Procurement Director", 96, "Unassigned", None, today_str, "procurement@vanguardfg.co.za", "+27 11 555 0192", "https://linkedin.com/company/vanguard-financial", "https://vanguardfg.co.za"),
        ("Apex Logistics Solutions", "Linbro Park, Sandton", "Hiring Velocity: Scaled up 4 regional client managers requiring premium corporate travel vehicles.", "Fleet Supervisor", 91, "Unassigned", None, today_str, "fleet@apexlogistics.co.za", "+27 11 555 0783", "https://linkedin.com/company/apex-logistics", "https://apexlogistics.co.za"),
        ("Discovery Limited", "Sandton, Johannesburg", "JSE SENS Announcement: Operational structural adjustments. Consolidating field consulting units into a unified Gauteng regional hub, generating travel fleet demand.", "Fleet Procurement Manager", 93, "Unassigned", None, today_str, "procurement@discovery.co.za", "+27 11 529 2888", "https://linkedin.com/company/discovery-limited", "https://discovery.co.za"),
        ("Sasol Limited", "Rosebank, Johannesburg", "JSE SENS Announcement: Capital allocation approval for clean-energy logistics expansion along the Witwatersrand corridor.", "Supply Chain Director", 90, "Unassigned", None, today_str, "fleet.services@sasol.com", "+27 11 441 3111", "https://linkedin.com/company/sasol", "https://sasol.com"),
        ("Gauteng Tech Holdings", "Bryanston, Johannesburg", "Company recently secured a massive capital expansion funding round. Fleet upgrade strategy pending.", "Operations Manager", 89, "Unassigned", None, yesterday_str, "ops@gautengtech.co.za", "+27 11 555 0321", "https://linkedin.com/company/gautengtech", "https://gautengtech.co.za")
    ]
    
    # Feed Vector B: Live JSE Executive Appointments & HNW Middle Management
    mock_individual = [
        ("Sipho Modise", "Newly Appointed Managing Partner", "Sandton Legal Consultants", "Sandton, Gauteng", "Promoted from Senior Associate to Senior Managing Partner. Relocating to head office.", 94, "Unassigned", None, today_str, "s.modise@sandtonlegal.co.za", "+27 11 555 0431", "https://linkedin.com/in/sipho-modise"),
        ("Naledi Dlamini", "Newly Appointed Executive Director", "Standard Bank Group", "Rosebank, Gauteng", "JSE SENS Board Update: Appointed to head regional retail asset expansion operations across South Africa.", 95, "Unassigned", None, today_str, "n.dlamini@standardbank.co.za", "+27 11 636 9111", "https://linkedin.com/in/naledi-dlamini-sb"),
        ("Mark van der Merwe", "Senior IT Operations Manager (Middle Management)", "Fintech Solutions SA", "Pretoria East", "Promoted to Regional Infrastructure Lead. Upgrading personal commute allowance.", 82, "Unassigned", None, today_str, "m.vandermerwe@fintechsa.co.za", "+27 12 555 0912", "https://linkedin.com/in/mark-vdm"),
        ("Johan Pretorius", "Regional Operations Manager (Middle Management)", "Implats Platinum", "Johannesburg South", "Corporate Notice: Promoted from Head of Safety to Regional Mining Infrastructure lead across Gauteng operations.", 83, "Unassigned", None, today_str, "j.pretorius@implats.co.za", "+27 11 731 9000", "https://linkedin.com/in/johan-pretorius-mining"),
        ("Naidoo Pillay", "Department Head of Logistics (Middle Management)", "E-Commerce Express", "Kempton Park", "Received annual performance incentive benchmark. Actively researching premium sports sedans.", 80, "Unassigned", None, yesterday_str, "n.pillay@ecexpress.co.za", "+27 11 555 0244", "https://linkedin.com/in/naidoo-pillay")
    ]

    # Feed Vector C: NEW Government Tender Awards (Gauteng Region B2B) - 13 items mapped
    mock_tenders = [
        ("Siza Infrastructure Ltd", "Midrand Hub, Johannesburg", "Gauteng Dept of Roads & Transport", "Awarded contract for Phase 2 provincial highway arterial maintenance. Immediate vehicle onboarding footprint required.", "R 42,500,000", 95, "Unassigned", None, today_str, "logistics@sizainfra.co.za", "+27 11 555 0943", "https://linkedin.com/company/siza-infrastructure", "https://sizainfra.co.za"),
        ("Mokoena Security Force", "Pretoria Central", "City of Tshwane Municipality", "Awarded regional critical infrastructure guarding contract. Operational footprint scaling up across 14 municipal sites.", "R 18,900,000", 91, "Unassigned", None, today_str, "tenders@mokoenasec.co.za", "+27 12 555 0115", "https://linkedin.com/company/mokoena-security", "https://mokoenasec.co.za"),
        ("Ekurhuleni Medical Logistics", "Kempton Park", "Gauteng Department of Health", "Awarded medical supply chain distribution tender for East Rand clinic clusters. Fleet updates mandatory.", "R 29,400,000", 88, "Unassigned", None, yesterday_str, "ops@ekurhulenimed.co.za", "+27 11 555 0872", "https://linkedin.com/company/ekurhuleni-med", "https://ekurhulenimed.co.za")
    ]
    
    # Safe verification insertion blocks
    for item in mock_corporate:
        c.execute("SELECT COUNT(*) FROM leads WHERE company=? AND signal=?", (item[0], item[2]))
        if c.fetchone()[0] == 0:
            c.execute('''INSERT INTO leads (company, location, signal, target, score, status, assigned_to, lead_date, public_email, public_phone, linkedin_url, company_website) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', item)

    for exec_item in mock_individual:
        c.execute("SELECT COUNT(*) FROM individual_leads WHERE client_name=? AND signal=?", (exec_item[0], exec_item[4]))
        if c.fetchone()[0] == 0:
            c.execute('''INSERT INTO individual_leads (client_name, title, company, location, signal, score, status, assigned_to, lead_date, public_email, public_phone, linkedin_url) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', exec_item)

    for tender_item in mock_tenders:
        c.execute("SELECT COUNT(*) FROM tender_leads WHERE company=? AND tender_desc=?", (tender_item[0], tender_item[3]))
        if c.fetchone()[0] == 0:
            c.execute('''INSERT INTO tender_leads (company, location, awarding_body, tender_desc, contract_value, score, status, assigned_to, lead_date, public_email, public_phone, linkedin_url, company_website) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', tender_item)
            
    conn.commit()
    conn.close()

init_db()
sync_live_feeds()

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
    st.caption("Standalone Account Access & Registration")
    
    auth_tab, signup_tab = st.tabs(["🔒 Sign In", "📝 Create Sales Account"])
    
    with auth_tab:
        login_username = st.text_input("Username", key="login_user").strip().lower()
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", key="login_btn"):
            if not login_username or not login_password:
                st.warning("Please enter both your username and password.")
            else:
                conn = sqlite3.connect('fleet_leads.db')
                c = conn.cursor()
                hashed_input = hashlib.sha256(login_password.encode()).hexdigest()
                c.execute("SELECT name, role FROM users WHERE username=? AND password=?", (login_username, hashed_input))
                user_match = c.fetchone()
                conn.close()
                
                if user_match:
                    st.session_state['authenticated'] = True
                    st.session_state['user'] = login_username
                    st.session_state['name'] = user_match[0]
                    st.session_state['role'] = user_match[1]
                    st.success("Access granted. Loading feed...")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
                
    with signup_tab:
        st.markdown("### Register New Dealer Profile")
        new_name = st.text_input("Full Name (e.g., John Doe)", key="reg_name").strip()
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
                conn = sqlite3.connect('fleet_leads.db')
                c = conn.cursor()
                c.execute("SELECT username FROM users WHERE username=?", (new_username,))
                if c.fetchone():
                    st.error(f"🛑 The username '@{new_username}' is already taken.")
                    conn.close()
                else:
                    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
                    c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (new_username, hashed_pw, new_name, role_db_value))
                    conn.commit()
                    conn.close()
                    st.success("🎉 Account successfully created! Switch to the 'Sign In' tab to log in.")
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

# ---- TAB 1: AVAILABLE DAILY FEED (WITH NEW TENDER RADIO TOGGLE) ----
with tab1:
    lead_section = st.radio("Select Target Section", ["🏢 Corporate Fleet (B2B)", "🚗 Individual Leads (B2C)", "🏛️ Gov Tenders (B2B)"], horizontal=True)
    
    st.markdown("🔍 **Filter Feed Pipeline**")
    f_col1, f_col2 = st.columns([1, 3])
    with f_col1:
        selected_date = st.date_input("Filter by Generation Date", datetime.now(SAST))
    filter_date_str = selected_date.strftime('%Y-%m-%d')
    
    st.markdown("---")
    conn = sqlite3.connect('fleet_leads.db')
    
    if lead_section == "🏢 Corporate Fleet (B2B)":
        df_unassigned = pd.read_sql_query("SELECT * FROM leads WHERE status='Unassigned' AND lead_date=? ORDER BY score DESC", conn, params=(filter_date_str,))
        conn.close()
        
        if df_unassigned.empty:
            st.info(f"No unassigned corporate fleet leads found for {filter_date_str}.")
        else:
            for idx, row in df_unassigned.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([1, 4, 1])
                    with col1:
                        st.metric(label="Score", value=f"{row['score']}/100")
                    with col2:
                        st.subheader(f"{row['company']} — {row['location']}")
                        st.markdown(f"**Target Title:** {row['target']} | 📅 *Generated: {row['lead_date']}*")
                        st.info(f"💡 {row['signal']}")
                    with col3:
                        st.write(" ")
                        st.write(" ")
                        if st.button("Claim Fleet Lead", key=f"claim_corp_{row['id']}"):
                            conn = sqlite3.connect('fleet_leads.db')
                            with conn:
                                conn.execute("UPDATE leads SET status='Claimed', assigned_to=? WHERE id=?", (st.session_state['user'], row['id']))
                            st.success("Lead claimed!")
                            st.rerun()
                st.markdown("---")
                    
    elif lead_section == "🚗 Individual Leads (B2C)":
        df_unassigned_ind = pd.read_sql_query("SELECT * FROM individual_leads WHERE status='Unassigned' AND lead_date=? ORDER BY score DESC", conn, params=(filter_date_str,))
        conn.close()
        
        if df_unassigned_ind.empty:
            st.info(f"No unassigned individual leads found for {filter_date_str}.")
        else:
            for idx, row in df_unassigned_ind.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([1, 4, 1])
                    with col1:
                        st.metric(label="Score", value=f"{row['score']}/100")
                    with col2:
                        st.subheader(f"Prospect: {row['client_name']}")
                        st.markdown(f"**Position:** {row['title']} at *{row['company']}* ({row['location']}) | 📅 *Generated: {row['lead_date']}*")
                        st.info(f"💎 {row['signal']}")
                    with col3:
                        st.write(" ")
                        st.write(" ")
                        if st.button("Claim Client Lead", key=f"claim_ind_{row['id']}"):
                            conn = sqlite3.connect('fleet_leads.db')
                            with conn:
                                conn.execute("UPDATE individual_leads SET status='Claimed', assigned_to=? WHERE id=?", (st.session_state['user'], row['id']))
                            st.success("Individual lead claimed!")
                            st.rerun()
                st.markdown("---")

    else: # 🏛️ Gov Tenders Section (RENDER THE NEW VIEW)
        df_unassigned_tender = pd.read_sql_query("SELECT * FROM tender_leads WHERE status='Unassigned' AND lead_date=? ORDER BY score DESC", conn, params=(filter_date_str,))
        conn.close()
        
        if df_unassigned_tender.empty:
            st.info(f"No unassigned government tender wins flagged on {filter_date_str}.")
        else:
            for idx, row in df_unassigned_tender.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([1, 4, 1])
                    with col1:
                        st.metric(label="Score", value=f"{row['score']}/100")
                    with col2:
                        st.subheader(f"Winning Vendor: {row['company']}")
                        st.markdown(f"**Awarding Body:** {row['awarding_body']} | 💰 **Contract Value:** `{row['contract_value']}`")
                        st.caption(f"📅 *Generated: {row['lead_date']}* | 📍 *Region: {row['location']}*")
                        st.info(f"🏛️ **Tender Project Details:** {row['tender_desc']}")
                    with col3:
                        st.write(" ")
                        st.write(" ")
                        if st.button("Claim Tender Lead", key=f"claim_tend_{row['id']}"):
                            conn = sqlite3.connect('fleet_leads.db')
                            with conn:
                                conn.execute("UPDATE tender_leads SET status='Claimed', assigned_to=? WHERE id=?", (st.session_state['user'], row['id']))
                            st.success("Tender opportunity locked!")
                            st.rerun()
                st.markdown("---")

# ---- TAB 2: CLAIMED LEADS INTERACTION PANELS ----
with tab2:
    conn = sqlite3.connect('fleet_leads.db')
    my_corp = pd.read_sql_query("SELECT * FROM leads WHERE assigned_to=? AND status='Claimed'", conn, params=(st.session_state['user'],))
    my_ind = pd.read_sql_query("SELECT * FROM individual_leads WHERE assigned_to=? AND status='Claimed'", conn, params=(st.session_state['user'],))
    my_tend = pd.read_sql_query("SELECT * FROM tender_leads WHERE assigned_to=? AND status='Claimed'", conn, params=(st.session_state['user'],))
    conn.close()
    
    st.subheader("🏢 My Claimed Corporate Fleet Accounts")
    if my_corp.empty:
        st.caption("No active corporate fleet claims.")
    else:
        for idx, row in my_corp.iterrows():
            with st.expander(f"Company: {row['company']} ({row['location']})"):
                st.write(f"**Signal Details:** {row['signal']}")
                st.markdown("### 📞 Public Contact Anchors")
                c_info_1, c_info_2, c_info_3, c_info_4 = st.columns(4)
                c_info_1.markdown(f"**Email:**\n`{row['public_email']}`")
                c_info_2.markdown(f"**Phone Line:**\n`{row['public_phone']}`")
                c_info_3.markdown(f"[🌐 Visit Company Website]({row['company_website']})")
                c_info_4.markdown(f"[🔗 View Corporate LinkedIn]({row['linkedin_url']})")
                
                st.markdown("---")
                note_text = st.text_area("Log Corporate Outreach Note", key=f"note_corp_{row['id']}")
                if st.button("Save Fleet Note", key=f"save_c_{row['id']}"):
                    if note_text:
                        conn = sqlite3.connect('fleet_leads.db')
                        timestamp_str = datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                        conn.execute("INSERT INTO lead_notes (lead_id, lead_type, username, salesperson_name, note_text, timestamp) VALUES (?, 'corporate', ?, ?, ?, ?)",
                                     (row['id'], st.session_state['user'], st.session_state['name'], note_text, timestamp_str))
                        conn.commit()
                        conn.close()
                        st.success("Note saved.")
                        st.rerun()
                if st.button("Mark Fleet Converted", key=f"close_c_{row['id']}"):
                    conn = sqlite3.connect('fleet_leads.db')
                    conn.execute("UPDATE leads SET status='Closed' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()

    st.markdown("---")
    st.subheader("🚗 My Claimed Individual Private Client Accounts")
    if my_ind.empty:
        st.caption("No active individual private client claims.")
    else:
        for idx, row in my_ind.iterrows():
            with st.expander(f"Prospect: {row['client_name']} — {row['title']} at {row['company']}"):
                st.write(f"**Signal Details:** {row['signal']}")
                st.markdown("### 📞 Public Professional Contacts")
                i_info_1, i_info_2, i_info_3 = st.columns(3)
                i_info_1.markdown(f"**Direct Email:**\n`{row['public_email']}`")
                i_info_2.markdown(f"**Office Phone:**\n`{row['public_phone']}`")
                i_info_3.markdown(f"[🔗 View Professional LinkedIn Profile]({row['linkedin_url']})")
                
                st.markdown("---")
                note_text_ind = st.text_area("Log Private Client Outreach Note", key=f"note_ind_{row['id']}")
                if st.button("Save Client Note", key=f"save_i_{row['id']}"):
                    if note_text_ind:
                        conn = sqlite3.connect('fleet_leads.db')
                        timestamp_str = datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                        conn.execute("INSERT INTO lead_notes (lead_id, lead_type, username, salesperson_name, note_text, timestamp) VALUES (?, 'individual', ?, ?, ?, ?)",
                                     (row['id'], st.session_state['user'], st.session_state['name'], note_text_ind, timestamp_str))
                        conn.commit()
                        conn.close()
                        st.success("Note saved.")
                        st.rerun()
                if st.button("Mark Sale Won 🔑", key=f"close_i_{row['id']}"):
                    conn = sqlite3.connect('fleet_leads.db')
                    c = conn.cursor()
                    c.execute("UPDATE individual_leads SET status='Closed' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()

    st.markdown("---")
    st.subheader("🏛️ My Claimed Tender Winner Accounts")
    if my_tend.empty:
        st.caption("No active government tender claims in progress.")
    else:
        for idx, row in my_tend.iterrows():
            with st.expander(f"Tender Winner: {row['company']} ({row['contract_value']})"):
                st.write(f"**Awarding Entity:** {row['awarding_body']}")
                st.write(f"**Project Details:** {row['tender_desc']}")
                
                st.markdown("### 📞 Public Corporate Contact Anchors")
                t_info_1, t_info_2, t_info_3, t_info_4 = st.columns(4)
                t_info_1.markdown(f"**Email:**\n`{row['public_email']}`")
                t_info_2.markdown(f"**Phone Line:**\n`{row['public_phone']}`")
                t_info_3.markdown(f"[🌐 Visit Corporate Site]({row['company_website']})")
                t_info_4.markdown(f"[🔗 View LinkedIn]({row['linkedin_url']})")
                
                st.markdown("---")
                note_text_tend = st.text_area("Log Tender Outreach Note", key=f"note_tend_{row['id']}")
                if st.button("Save Tender Note", key=f"save_t_{row['id']}"):
                    if note_text_tend:
                        conn = sqlite3.connect('fleet_leads.db')
                        timestamp_str = datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')
                        conn.execute("INSERT INTO lead_notes (lead_id, lead_type, username, salesperson_name, note_text, timestamp) VALUES (?, 'tender', ?, ?, ?, ?)",
                                     (row['id'], st.session_state['user'], st.session_state['name'], note_text_tend, timestamp_str))
                        conn.commit()
                        conn.close()
                        st.success("Note saved.")
                        st.rerun()
                if st.button("Mark Tender Fleet Secured 🚚", key=f"close_t_{row['id']}"):
                    conn = sqlite3.connect('fleet_leads.db')
                    with conn:
                        conn.execute("UPDATE tender_leads SET status='Closed' WHERE id=?", (row['id'],))
                    st.rerun()

# ---- TAB 3: DEALER PRINCIPAL MANAGEMENT OVERVIEW ----
if st.session_state['role'] == 'dealer_principal':
    with tab3:
        st.header("👑 Dealership Performance & Master Activity Pipeline")
        
        conn = sqlite3.connect('fleet_leads.db')
        
        col_m1, col_m2, col_m3 = st.columns(3)
        c_leads = pd.read_sql_query("SELECT COUNT(*) as cnt FROM leads", conn)['cnt'][0]
        i_leads = pd.read_sql_query("SELECT COUNT(*) as cnt FROM individual_leads", conn)['cnt'][0]
        t_leads = pd.read_sql_query("SELECT COUNT(*) as cnt FROM tender_leads", conn)['cnt'][0]
        
        c_closed = pd.read_sql_query("SELECT COUNT(*) as cnt FROM leads WHERE status='Closed'", conn)['cnt'][0]
        i_closed = pd.read_sql_query("SELECT COUNT(*) as cnt FROM individual_leads WHERE status='Closed'", conn)['cnt'][0]
        t_closed = pd.read_sql_query("SELECT COUNT(*) as cnt FROM tender_leads WHERE status='Closed'", conn)['cnt'][0]
        
        col_m1.metric("Total Scoped Opportunities", c_leads + i_leads + t_leads)
        col_m2.metric("Corporate & Tender Fleet Units", c_closed + t_closed)
        col_m3.metric("Private Deliveries (B2C)", i_closed, delta=f"+{c_closed + i_closed + t_closed} Total Units")
        
        st.markdown("---")
        st.subheader("💬 Live Master Communications Audit Log")
        df_master_notes = pd.read_sql_query("SELECT * FROM lead_notes ORDER BY timestamp DESC", conn)
        conn.close()
        
        if df_master_notes.empty:
            st.info("No sales rep communication activity has been logged today yet.")
        else:
            for idx, note_row in df_master_notes.iterrows():
                with st.chat_message("user"):
                    st.markdown(f"**{note_row['salesperson_name']}** (`@{note_row['username']}`) handled a **{note_row['lead_type'].upper()}** profile at *{note_row['timestamp']}*")
                    st.write(f"📝 *\"{note_row['note_text']}\"*")
