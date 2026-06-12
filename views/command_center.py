import streamlit as st
import pandas as pd

def render(supabase):
    st.markdown("## 👑 PHASE V COMMAND CENTER")
    
    # 1. Fetch data for all dealerships (No matrix filters applied)
    # Using .select("*") without .eq() pulls the global portfolio
    stock_data = supabase.table("used_car_stock").select("*").execute().data
    df = pd.DataFrame(stock_data)

    # 2. Filter Bar (The Vision)
    col1, col2, col3 = st.columns(3)
    with col1:
        dealer_filter = st.selectbox("Select Dealership", ["All"] + df['location'].unique().tolist())
    with col2:
        brand_filter = st.selectbox("Select Brand", ["All"] + df['brand_id'].unique().tolist())
    
    # 3. Apply Filters
    filtered_df = df.copy()
    if dealer_filter != "All":
        filtered_df = filtered_df[filtered_df['location'] == dealer_filter]
    if brand_filter != "All":
        filtered_df = filtered_df[filtered_df['brand_id'] == brand_filter]

    # 4. KPI Grid (Matching your vision)
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Stock Units", len(filtered_df))
    k2.metric("Total Asset Value", f"R {filtered_df['total_value'].sum():,.2f}")
    k3.metric("Avg Days on Floor", f"{int(filtered_df['days_in_stock'].mean())} Days")

    # 5. Visual Data Grid
    st.dataframe(filtered_df, use_container_width=True)
