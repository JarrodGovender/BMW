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
    
    # Tables are created safely only if they do not exist
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leads 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, location TEXT, 
                  signal TEXT, target TEXT, score INTEGER, status TEXT, assigned_to TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lead_notes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, username TEXT, 
                  salesperson_name TEXT, note_text TEXT, timestamp TEXT)''')
        
    # Re-populate mock daily corporate signals if table is empty
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
                    st.error("Invalid credentials. Please verify your spelling or re-register your profile.")
                
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
                st.error("Usernames cannot contain spaces. Use letters or numbers only.")
            elif security_code != "SandtonBMW2026":
                st.error("Incorrect Dealership Authorization Code.")
            else:
                role_db_value = 'dealer_principal' if chosen_role == "Dealer Principal" else 'sales_rep'
                
                conn = sqlite3.connect('fleet_leads.db')
                c = conn.cursor()
                
                c.execute("SELECT username FROM users WHERE username=?", (new_username,))
                existing_user = c.fetchone()
                
                if existing_user:
                    st.error(f"🛑 The username '@{new_username}' is already taken. Please pick a different unique username.")
                    conn.close()
                else:
                    c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                              (new_username, hashlib.sha256(new_password.encode()).hexdigest(), new_name, role_db_value))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 Account successfully created for {new_name} as a {chosen_role}! Switch to the 'Sign In' tab to log in.")
    st.stop()

# ==========================================
# 4. DASHBOARD INTERFACE WORKSPACE
# ==========================================
st.title("📈 Daily Corporate Fleet Lead Feed")
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
    tab1, tab2 = st.tabs(
