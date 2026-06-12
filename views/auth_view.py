import streamlit as st
import hashlib

def render(supabase):
    st.markdown("<h2 style='text-align: center;'>PHASE V ENTERPRISE SYSTEM</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey;'>MULTI-TENANT CONTROL GATEWAY</p>", unsafe_allow_html=True)
    
    # Toggle between Login and Secure Registration
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
                # Hash input password to match database security standards
                hashed_input = hashlib.sha256(login_pass.encode()).hexdigest()
                
                # Query user profile along with all linked matrix parameters
                res = supabase.table("users").select("*").eq("username", login_user).execute()
                
                if res.data and res.data[0]['password'] == hashed_input:
                    user_data = res.data[0]
                    
                    # Store entire 4-Dimensional matrix profile in session state
                    st.session_state['authenticated'] = True
                    st.session_state['user'] = user_data['username']
                    st.session_state['name'] = user_data['name']
                    # Fallback to legacy 'role' if 'role_id' is missing for any reason
                    st.session_state['role'] = user_data.get('role_id', user_data.get('role'))
                    st.session_state['location_id'] = user_data.get('location_id')
                    st.session_state['department_id'] = user_data.get('department_id')
                    st.session_state['brand_id'] = user_data.get('brand_id')
                    
                    st.success(f"✅ Access Granted. Welcome back, {user_data['name']}.")
                    st.rerun()
                else:
                    st.error("❌ Authentication Failed: Invalid username or password.")

    # ====================================================================
    # 2. REGISTRATION INTERFACE (TOKEN-DRIVEN)
    # ====================================================================
    with auth_mode[1]:
        st.markdown("### REGISTER NEW ORGANIZATION ACCOUNT")
        st.info("ℹ️ Registration requires a unique corporate authorization token provided by a System Super User.")
        
        reg_name = st.text_input("Full Name (e.g., John Doe)", key="reg_fullname")
        reg_user = st.text_input("Choose Username", key="reg_uid").strip().lower()
        reg_pass = st.text_input("Secure Password", type="password", key="reg_pwd")
        reg_conf = st.text_input("Confirm Password", type="password", key="reg_cpwd")
        
        # The single security gateway field replacing manual dropdown selectors
        reg_token = st.text_input("Enterprise Authorization Token", key="reg_auth_token").strip()
        
        if st.button("VALIDATE & REGISTER ACCOUNT", use_container_width=True):
            if not reg_name or not reg_user or not reg_pass or not reg_token:
                st.warning("⚠️ All registration fields, including the Authorization Token, are mandatory.")
            elif reg_pass != reg_conf:
                st.error("⚠️ Password fields do not match.")
            elif len(reg_pass) < 6:
                st.error("⚠️ For system protection, passwords must be at least 6 characters long.")
            else:
                # Step A: Validate the Authorization Token against the matrix registry
                token_res = supabase.table("auth_tokens").select("*").eq("token", reg_token).eq("is_active", True).execute()
                
                if not token_res.data:
                    st.error("❌ Invalid or deactivated Authorization Token. Cross-contamination blocked.")
                else:
                    token_data = token_res.data[0]
                    
                    # Step B: Double check username availability
                    check_user = supabase.table("users").select("username").eq("username", reg_user).execute()
                    if check_user.data:
                        st.error("⚠️ This username is already registered within Phase V.")
                    else:
                        # Step C: Construct and inject the user account mapped directly to the token details
                        hashed_password = hashlib.sha256(reg_pass.encode()).hexdigest()
                        
                        new_user = {
                            "username": reg_user,
                            "name": reg_name,
                            "password": hashed_password,
                            "role": token_data['role_id'],     # <-- FIXED: Satisfies legacy database constraint
                            "role_id": token_data['role_id'],  # <-- Satisfies new Matrix architecture
                            "location_id": token_data['location_id'],
                            "department_id": token_data['department_id'],
                            "brand_id": token_data['brand_id']
                        }
                        
                        # Save the new verified profile
                        try:
                            supabase.table("users").insert(new_user).execute()
                            st.success("🎉 Registration successful! Proceed to the Login tab to authenticate.")
                        except Exception as e:
                            st.error(f"Database Error: {e}")
