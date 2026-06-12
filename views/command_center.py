import streamlit as st
import pandas as pd

def render(supabase):
    st.markdown("## 👑 PHASE V EXECUTIVE COMMAND CENTER")
    
    # 1. Define the exact layout rows from your Excel sheet
    target_dealers = [
        "BMW Bedfordview",
        "BMW Sandton",
        "BMW East Rand",
        "BMW Dalpark",
        "MF Sandton",
        "MF Fourways"
    ]

    # Map database IDs to your preferred display names
    dealer_map = {
        'BMW_BEDFORDVIEW': 'BMW Bedfordview',
        'BMW_SANDTON': 'BMW Sandton',
        'BMW_EASTRAND': 'BMW East Rand',
        'BMW_DALPARK': 'BMW Dalpark',
        'MF_SANDTON': 'MF Sandton',
        'MF_FOURWAYS': 'MF Fourways'
    }

    # 2. Fetch ALL stock data globally
    try:
        data = supabase.table("used_car_stock").select("location_id, total_value, days_in_stock, floorplan_status").execute().data
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to load portfolio data: {e}")
        return

    summary_data = []

    if not df.empty:
        # Clean data types
        df['total_value'] = pd.to_numeric(df['total_value'], errors='coerce').fillna(0.0)
        df['days_in_stock'] = pd.to_numeric(df['days_in_stock'], errors='coerce').fillna(0)
        df['floorplan_status'] = df['floorplan_status'].astype(str).str.upper()

        # Apply Aging Provision Logic
        def calc_prov(row):
            d = row['days_in_stock']
            v = row['total_value']
            if 30 <= d <= 60: return v * 0.025
            elif 61 <= d <= 90: return v * 0.050
            elif 91 <= d <= 120: return v * 0.075
            elif d >= 121: return v * 0.100
            return 0.0

        df['provision_value'] = df.apply(calc_prov, axis=1)
        
        # Determine Unencumbered Status
        df['is_unencumbered'] = df['floorplan_status'].str.contains('UNENCUMBERED', na=False)
        df['unencumbered_value'] = df.apply(lambda x: x['total_value'] if x['is_unencumbered'] else 0.0, axis=1)

        # Map the raw DB location_id to the exact Excel names
        df['Dealership'] = df['location_id'].map(dealer_map)

    # 3. Build the Grid (Ensuring every dealer shows up, even if stock is 0)
    for dealer in target_dealers:
        if not df.empty and 'Dealership' in df.columns:
            d_df = df[df['Dealership'] == dealer]
            t_stock = d_df['total_value'].sum()
            t_unenc = d_df['unencumbered_value'].sum()
            t_prov = d_df['provision_value'].sum()
        else:
            t_stock = t_unenc = t_prov = 0.0

        summary_data.append({
            '': dealer,  # Blank column header to match Excel exactly
            'Total Stock Values': t_stock,
            'Total Unencumbered': t_unenc,
            'Total Aging Provision': t_prov
        })

    summary_df = pd.DataFrame(summary_data)

    # 4. Add the Grand Total Row
    grand_total = {
        '': 'GRAND TOTAL',
        'Total Stock Values': summary_df['Total Stock Values'].sum(),
        'Total Unencumbered': summary_df['Total Unencumbered'].sum(),
        'Total Aging Provision': summary_df['Total Aging Provision'].sum()
    }
    summary_df = pd.concat([summary_df, pd.DataFrame([grand_total])], ignore_index=True)

    # 5. Format as proper ZAR Currency
    for col in ['Total Stock Values', 'Total Unencumbered', 'Total Aging Provision']:
        summary_df[col] = summary_df[col].apply(lambda x: f"R {x:,.2f}")

    # 6. Render the exact Excel structure
    st.markdown("### 🏢 EXECUTIVE DEALERSHIP ROLLUP")
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

    st.markdown("---")

    # 7. Drill-Down Tool
    st.markdown("### 🔍 DEALERSHIP DEEP-DIVE")
    selected = st.selectbox("Drill down into specific dealership:", ["None"] + target_dealers)
    
    if selected != "None":
        if df.empty:
            st.info(f"No active inventory logged for {selected} yet.")
        else:
            s_df = df[df['Dealership'] == selected].copy()
            
            # Show top-level stats for the selected branch
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Units", len(s_df))
            c2.metric("Unencumbered Units", len(s_df[s_df['is_unencumbered']]))
            c3.metric("Avg Days on Floor", f"{int(s_df['days_in_stock'].mean()) if not s_df.empty else 0} Days")
            
            # Show high exposure risk
            st.markdown("#### ⚠️ High Exposure Vehicles (90+ Days)")
            exposure_df = s_df[s_df['days_in_stock'] >= 90].sort_values('days_in_stock', ascending=False)
            
            if exposure_df.empty:
                st.success("No critical aging stock (90+ days).")
            else:
                exp_display = exposure_df[['days_in_stock', 'total_value', 'provision_value']].copy()
                exp_display['total_value'] = exp_display['total_value'].apply(lambda x: f"R {x:,.2f}")
                exp_display['provision_value'] = exp_display['provision_value'].apply(lambda x: f"R {x:,.2f}")
                exp_display.rename(columns={
                    'days_in_stock': 'Days on Floor', 
                    'total_value': 'Capital Value', 
                    'provision_value': 'Required Provision'
                }, inplace=True)
                
                st.dataframe(exp_display, hide_index=True, use_container_width=True)
