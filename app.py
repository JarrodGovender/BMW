import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import pytz

# ==========================================
# 1. INITIALIZATION & DATABASE SETUP
# ==========================================
st.set_page_config(page_title="BMW Sandton Corporate Fleet Feed", layout="wide")
SAST = pytz.timezone('Africa/Johannesburg')

def init_db():
    conn = sqlite3.connect('fleet_leads.db')
    c = conn.cursor()
    # Create tables if they do not exist
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leads 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, location TEXT, 
                  signal TEXT, target TEXT, score INTEGER, status TEXT, assigned_to TEXT)''')
    
    # Insert a default salesperson if table is empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        hashed_pw = hashlib.sha256("Sandton2026".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES ('sales1', ?, 'Jarrod Govender')", (hashed_pw,))
        
    # Insert mock daily corporate signals if table is empty
    c.execute("SELECT COUNT(*) FROM leads")
    if c.fetchone()[0] == 0:
        mock_leads = [
            ("Vanguard Financial Group", "Sandton Central", "Office Hub Consolidation: Moving 220 executives to a single facility. ESG mandate requires high-end PHEV/EV corporate fleet updates.", "Procurement Director", 96, "Unassigned", None),
            ("Apex Logistics Solutions", "Linbro Park", "Hiring Velocity: Scaled up 4 regional client managers requiring premium corporate travel vehicles.", "Fleet Supervisor", 91, "Unassigned", None),
            ("Siza Infrastructure", "Midrand Hub", "Capital Expansion: Awarded massive logistics contract. Expanding executive oversight vehicle pool.", "Head of Supply Chain", 88, "Unassigned", None)
        ]
        c.executemany("INSERT INTO leads (company, location, signal, target, score, status, assigned_to) VALUES (?,?,?,?,?,?,?)", mock_leads)
    conn.commit()
    conn.close()

init_db()

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

if not st.session_state['authenticated']:
    st.title("🏢 BMW Sandton Fleet Platform Login")
    st.caption("Standalone MVP Authentication Gateway")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        conn = sqlite3.connect('fleet_leads.db')
        c = conn.cursor()
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        c.execute("SELECT name FROM users WHERE username=? AND password=?", (username, hashed_input))
        user_match = c.fetchone()
        conn.close()
        
        if user_match:
            st.session_state['authenticated'] = True
            st.session_state['user'] = username
            st.session_state['name'] = user_match[0]
            st.rerun()
        else:
            st.error("Invalid Username or Password. Please check your credentials.")
    st.stop()

# ==========================================
# 4. DASHBOARD INTERFACE WORKSPACE
# ==========================================
st.title("📈 Daily Corporate Fleet Lead Feed")
st.markdown(f"Logged in as: **{st.session_state['name']}** | System Session Clears at **06:00 AM SAST**")

# Sidebar Actions
if st.sidebar.button("Logout"):
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['name'] = None
    st.rerun()

# Tabs Split
tab1, tab2 = st.tabs(["🔥 Available Daily Feed (First-Come, First-Served)", "💼 My Claimed Accounts"])

# ---- TAB 1: UNASSIGNED LEADS ----
with tab1:
    conn = sqlite3.connect('fleet_leads.db')
    df_unassigned = pd.read_sql_query("SELECT * FROM leads WHERE status='Unassigned' ORDER BY score DESC", conn)
    conn.close()
    
    if df_unassigned.empty:
        st.success("All daily corporate leads have been claimed! Check back tomorrow at 06:00 AM.")
    else:
        for idx, row in df_unassigned.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    st.metric(label="Lead Score", value=f"{row['score']}/100")
                with col2:
                    st.subheader(f"{row['company']} — {row['location']}")
                    st.markdown(f"**Target Persona:** {row['target']}")
                    st.info(f"💡 **Buying Signal:** {row['signal']}")
                with col3:
                    st.write(" ")
                    st.write(" ")
                    # Claim Button using pessimistic-style validation
                    if st.button("Claim Account", key=f"claim_{row['id']}"):
                        conn = sqlite3.connect('fleet_leads.db')
                        c = conn.cursor()
                        # Verify the row status inside an isolated check
                        c.execute("SELECT status FROM leads WHERE id=?", (row['id'],))
                        current_status = c.fetchone()[0]
                        
                        if current_status == 'Unassigned':
                            c.execute("UPDATE leads SET status='Claimed', assigned_to=? WHERE id=?", 
                                      (st.session_state['user'], row['id']))
                            conn.commit()
                            st.success(f"Successfully locked {row['company']} to your profile!")
                            conn.close()
                            st.rerun()
                        else:
                            st.error("Too late! Another salesperson claimed this lead just split-seconds ago.")
                            conn.close()
                st.markdown("---")

# ---- TAB 2: CLAIMED LEADS ----
with tab2:
    conn = sqlite3.connect('fleet_leads.db')
    df_claimed = pd.read_sql_query("SELECT * FROM leads WHERE assigned_to=? AND status='Claimed'", conn, params=(st.session_state['user'],))
    conn.close()
    
    if df_claimed.empty:
        st.info("You haven't claimed any corporate leads yet today. Head over to the live feed to capture opportunities.")
    else:
        for idx, row in df_claimed.iterrows():
            with st.expander(f"🏢 {row['company']} ({row['location']}) - Target: {row['target']}"):
                st.markdown(f"**Corporate Target Intelligence:** {row['signal']}")
                st.markdown("### Operational Actions")
                
                # Activity Tracking Input Box
                note = st.text_area("Log Call or Meeting Summary", key=f"note_{row['id']}")
                if st.button("Save Log Entry", key=f"save_{row['id']}"):
                    st.success(f"Activity note successfully saved for {row['company']}.")
                
                if st.button("Mark Account as Successfully Converted", key=f"close_{row['id']}"):
                    conn = sqlite3.connect('fleet_leads.db')
                    c = conn.cursor()
                    c.execute("UPDATE leads SET status='Closed' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()
