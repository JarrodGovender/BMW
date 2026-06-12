import streamlit as st
import hashlib

def get_hash(password):
    """Consistent hashing utility for the entire application."""
    return hashlib.sha256(password.encode()).hexdigest()

def render(supabase):
    st.markdown("<h2 style='text-align: center;'>PHASE V ENTERPRISE SYSTEM</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey;'>MULTI-TENANT CONTROL GATEWAY</p>", unsafe_allow_html=True)
    
    auth_mode = st.tabs(["🔒 SECURE LOGIN", "📝 AUTHORIZED REGISTRATION"])
    
    # ====================================================================
    # 1. LOGIN INTERFACE
    # ====================================================================
    with auth_mode[0]:
        st.markdown("### ENTER YOUR CREDENTIALS")
        login_user = st.text_input("Username", key="login_uid", autocomplete="username").strip().lower()
        login_pass = st.text_input("Password", type="password", key="login_pwd", autocomplete="current-password")
        
        if st.button("AUTHENTICATE SYSTEM ACCESS", use_container_width=True):
            if not login_user or not login_pass:
                st.warning("⚠️ Please provide both your username and password.")
            else:
                hashed_input = get_hash(login_pass)
                
                res = supabase.table("users").select("*").eq("username", login_user).execute()
                
                if res.data:
                    stored_pass = res.data[0]['password']
                    
                    if stored_pass == hashed_input:
                        user_data = res.data[0]
                        
                        st.session_state['authenticated'] = True
                        st.session_state['user'] = user_data['username']
                        st.session_state['name'] = user_data['name']
                        st.session_state['role'] = user_data.get('role_id', user_data.get('role'))
                        st.session_state['location_id'] = user_data.get('location_id')
                        st.session_state['department_id'] = user_data.get('department_id')
                        st.session_state['brand_id'] = user_data.get('brand_id')
                        
                        st.success(f"✅ Access Granted.")
                        st.rerun()
                    else:
                        st.error("❌ Authentication Failed: Invalid password.")
                        # Helpful debugging
                        with st.expander("Diagnostic Info"):
                            st.write(f"Stored Hash (First 8): {stored_pass[:8]}")
                            st.write(f"Input Hash (First 8): {hashed_input[:8]}")
                else:
                    st.error("❌ Authentication Failed: User not found.")

    # ====================================================================
    # 2. REGISTRATION INTERFACE (TOKEN-DRIVEN)
    # ====================================================================
    with auth_mode[1]:
        st.markdown("### REGISTER NEW ORGANIZATION ACCOUNT")
        
        reg_name = st.text_input("Full Name", key="reg_fullname")
        reg_user = st.text_input("Choose Username", key="reg_uid").strip().lower()
        reg_pass = st.text_input("Secure Password", type="password", key="reg_pwd")
        reg_conf = st.text_input("Confirm Password", type="password", key="reg_cpwd")
        reg_token = st.text_input("Enterprise Authorization Token", key="reg_auth_token").strip()
        
        if st.button("VALIDATE & REGISTER ACCOUNT", use_container_width=True):
            if not reg_name or not reg_user or not reg_pass or not reg_token:
                st.warning("⚠️ All fields are mandatory.")
            elif reg_pass != reg_conf:
                st.error("⚠️ Password fields do not match.")
            else:
                token_res = supabase.table("auth_tokens").select("*").eq("token", reg_token).eq("is_active", True).execute()
                
                if not token_res.data:
                    st.error("❌ Invalid Authorization Token.")
                else:
                    token_data = token_res.data[0]
                    
                    check_user = supabase.table("users").select("username").eq("username", reg_user).execute()
                    if check_user.data:
                        st.error("⚠️ This username is already registered.")
                    else:
                        # Construct payload with legacy support ('role') and new architecture ('role_id')
                        new_user = {
                            "username": reg_user,
                            "name": reg_name,
                            "password": get_hash(reg_pass),
                            "role": token_data['role_id'], 
                            "role_id": token_data['role_id'],
                            "location_id": token_data['location_id'],
                            "department_id": token_data['department_id'],
                            "brand_id": token_data['brand_id']
                        }
                        
                        try:
                            supabase.table("users").insert(new_user).execute()
                            st.success("🎉 Registration successful! Switch to the Login tab.")
                        except Exception as e:
                            st.error(f"Database Error: {e}")
