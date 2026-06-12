import streamlit as st
import hashlib
from config import get_local_img, BMW_LOGO, MINI_LOGO, MG_LOGO, safe_rerun

def render(supabase):
    gc1, gc2, gc3 = st.columns([1.5, 3, 1.5])
    with gc2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        cl1, cl2, cl3 = st.columns([1, 2, 1])
        with cl2:
            try: st.image(get_local_img("PHASEV.png", ""), use_container_width=True)
            except: st.markdown("<h2 style='text-align: center;'>PHASE V MOTOR INVESTMENTS</h2>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style='display: flex; justify-content: center; align-items: center; gap: 40px; margin-top: 10px; margin-bottom: 25px; flex-wrap: wrap;'>
                <img src='{BMW_LOGO}' width='50' style='height: auto;'>
                <img src='{MINI_LOGO}' width='70' style='height: auto;'>
                <img src='{MG_LOGO}' width='60' style='height: auto;'>
            </div>
            <p style='text-align: center; font-size:0.85rem; color:#666666; letter-spacing:1px; margin-top: 5px;'>ENTERPRISE SECURE GATEWAY</p><br>
        """, unsafe_allow_html=True)
    
        auth_tab, signup_tab = st.tabs(["🔒 SECURE SIGN IN", "📝 CREATE ACCESS ACCOUNT"])
        
        with auth_tab:
            lu = st.text_input("USERNAME", key="login_user").strip().lower()
            lp = st.text_input("PASSWORD", type="password", key="login_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("AUTHENTICATE ACCESS", key="login_btn"):
                if lu and lp:
                    try:
                        res = supabase.table("users").select("name", "role", "password").eq("username", lu).execute()
                        if res.data and res.data[0]['password'] == hashlib.sha256(lp.encode()).hexdigest():
                            st.session_state.update({'authenticated': True, 'user': lu, 'name': res.data[0]['name'], 'role': res.data[0]['role'], 'page_view': 'dashboard'}); safe_rerun()
                        else: st.error("Authentication rejected.")
                    except Exception as e: st.error(f"Error: {str(e)}")
                        
        with signup_tab:
            nn, nu, np = st.text_input("FULL NAME", key="rn").strip(), st.text_input("USERNAME", key="ru").strip().lower(), st.text_input("PASSWORD", type="password", key="rp")
            cr = st.selectbox("POSITION", ["Sales Representative", "Dealer Principal", "Finance/Admin", "Sales Manager", "Property Manager", "Group Director"], key="rr")
            sc = st.text_input("SECURITY CODE", type="password", key="rc")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("INITIALIZE PROFILE", key="sb"):
                if not nn or not nu or not np: st.warning("Fill all fields.")
                elif " " in nu: st.error("No spaces in username.")
                elif sc != "SandtonBMW2026": st.error("Incorrect Code.")
                else:
                    try:
                        rv = 'dealer_principal' if cr == "Dealer Principal" else 'finance_admin' if cr == "Finance/Admin" else 'sales_manager' if cr == "Sales Manager" else 'property_manager' if cr == "Property Manager" else 'director' if cr == "Group Director" else 'sales_rep'
                        if supabase.table("users").select("username").eq("username", nu).execute().data: st.error("Username claimed.")
                        else:
                            supabase.table("users").insert({"username": nu, "password": hashlib.sha256(np.encode()).hexdigest(), "name": nn, "role": rv}).execute()
                            st.success("🎉 Initialized! Proceed to Sign In.")
                    except Exception as e: st.error(f"Error: {str(e)}")
