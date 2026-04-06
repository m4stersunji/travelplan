"""Flight Price Tracker — Web UI

Run locally: streamlit run app.py
Deploy: Push to GitHub → connect at share.streamlit.io
"""
import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Flight Tracker", page_icon="✈️", layout="wide",
                   initial_sidebar_state="collapsed")

# Mobile-friendly CSS
st.markdown("""
<style>
    /* Compact on mobile */
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem; }
        h1 { font-size: 1.5rem !important; }
        h2, h3 { font-size: 1.1rem !important; }
        .stTabs [data-baseweb="tab"] { font-size: 0.85rem; padding: 8px 12px; }
    }
    /* Hide sidebar hamburger on mobile */
    [data-testid="collapsedControl"] { display: none; }
    /* Card styling */
    .metric-card {
        background: #f8f9fa; padding: 16px; border-radius: 10px;
        border-left: 4px solid #1DB446; margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- Sheets connection ---
@st.cache_resource
def get_spreadsheet():
    try:
        gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        # Try top-level first, then inside gcp_service_account
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID") or st.secrets["gcp_service_account"].get("GOOGLE_SHEET_ID")
        if not sheet_id:
            st.error("GOOGLE_SHEET_ID not found in secrets")
            return None
        return gc.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Cannot connect to Google Sheets: {e}")
        return None


@st.cache_data(ttl=300)  # Cache 5 min
def load_sheet(name):
    sh = get_spreadsheet()
    if not sh:
        return pd.DataFrame()
    try:
        return pd.DataFrame(sh.worksheet(name).get_all_records())
    except Exception:
        return pd.DataFrame()


def save_trip(trip_name, origin, dest, go_date, back_date, pref_dep, pref_arr, added_by):
    sh = get_spreadsheet()
    if not sh:
        return False
    try:
        ws = sh.worksheet('Config')
        row = [trip_name, origin, dest, go_date.strftime('%Y-%m-%d'),
               back_date.strftime('%Y-%m-%d'), pref_dep, pref_arr, 'Yes', added_by]
        ws.update(f'A{len(ws.get_all_values()) + 1}', [row])
        return True
    except Exception as e:
        st.error(f"Failed: {e}")
        return False


def delete_trip(row_idx):
    sh = get_spreadsheet()
    if not sh:
        return
    try:
        ws = sh.worksheet('Config')
        ws.update_acell(f'H{row_idx + 2}', 'No')
    except Exception:
        pass


# --- Main ---
st.title("✈️ Flight Price Tracker")

tab_dash, tab_flights, tab_trends, tab_config = st.tabs([
    "Dashboard", "All Flights", "Price Trends", "Manage Trips"
])


# ═══════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════
with tab_dash:
    overview = load_sheet('Overview')
    dashboard = load_sheet('Dashboard')

    if not overview.empty:
        combo_row = overview[overview['Route'] == 'BEST ROUNDTRIP']
        routes_row = overview[overview['Route'] != 'BEST ROUNDTRIP']

        # Big best roundtrip price
        if not combo_row.empty:
            r = combo_row.iloc[0]
            best_price = r.get('Best Price', 'N/A')
            combo_info = r.get('Best Source', '')
            col_big, col_info = st.columns([1, 2])
            with col_big:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1DB446, #0a8f2f); padding: 20px; border-radius: 12px; text-align: center; color: white;">
                    <div style="font-size: 14px; opacity: 0.8;">Best Roundtrip</div>
                    <div style="font-size: 36px; font-weight: bold;">฿{best_price:,}</div>
                    <div style="font-size: 12px; opacity: 0.8;">{combo_info}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_info:
                last_check = routes_row.iloc[0].get('Last Check', '') if not routes_row.empty else ''
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 20px; border-radius: 12px;">
                    <div style="font-size: 14px; color: #666;">Last checked</div>
                    <div style="font-size: 18px; font-weight: bold;">{last_check}</div>
                    <div style="font-size: 12px; color: #999; margin-top: 8px;">Auto-checks every 4 hours</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # Per-route cards
        if not routes_row.empty:
            st.subheader("Price per Route")
            cols = st.columns(len(routes_row))
            for i, (_, row) in enumerate(routes_row.iterrows()):
                with cols[i]:
                    route = row.get('Route', '')
                    date_l = row.get('Date', '')
                    best_p = row.get('Best Price', '')
                    src = row.get('Best Source', '')
                    airline = row.get('Cheapest Airline', '')
                    airline_p = row.get('Airline Price', '')

                    direction = "🛫" if "BKK" == route[:3] else "🛬"
                    st.markdown(f"**{direction} {route}** — {date_l}")
                    if isinstance(best_p, (int, float)) and best_p > 0:
                        st.metric("Best Price", f"฿{best_p:,}", f"via {src}" if src else None)
                        if isinstance(airline_p, (int, float)) and airline_p != best_p:
                            st.caption(f"Airline direct: ฿{airline_p:,} ({airline})")
                    else:
                        st.metric("Best Price", str(best_p))

    # Heatmap
    heatmap = load_sheet('Heatmap')
    if not heatmap.empty:
        st.markdown("---")
        st.subheader("Date Comparison")
        st.dataframe(heatmap, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════
# ALL FLIGHTS
# ═══════════════════════════════════════
with tab_flights:
    flights_df = load_sheet('All Flights')

    if not flights_df.empty:
        # Filters
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            routes = ['All'] + sorted(flights_df['Route'].unique().tolist())
            sel_route = st.selectbox("Route", routes, key="fl_route")
        with c2:
            dates = ['All'] + sorted(flights_df['Date'].unique().tolist())
            sel_date = st.selectbox("Date", dates, key="fl_date")
        with c3:
            sel_direct = st.selectbox("Stops", ['All', 'Direct only', 'With stops'], key="fl_stops")
        with c4:
            sel_sort = st.selectbox("Sort by", ['Score (best first)', 'Price (cheapest)', 'Departure time'], key="fl_sort")

        df = flights_df.copy()
        if sel_route != 'All':
            df = df[df['Route'] == sel_route]
        if sel_date != 'All':
            df = df[df['Date'] == sel_date]
        if sel_direct == 'Direct only':
            df = df[df['Direct'] == True]
        elif sel_direct == 'With stops':
            df = df[df['Direct'] == False]

        # Latest check only
        if 'Checked At' in df.columns and not df.empty:
            latest = df['Checked At'].max()
            df = df[df['Checked At'] == latest]

        # Sort
        if sel_sort == 'Score (best first)' and 'Total Score' in df.columns:
            df['Total Score'] = pd.to_numeric(df['Total Score'], errors='coerce')
            df = df.sort_values('Total Score', ascending=False)
        elif sel_sort == 'Price (cheapest)' and 'Airline Price' in df.columns:
            df['Airline Price'] = pd.to_numeric(df['Airline Price'], errors='coerce')
            df = df.sort_values('Airline Price')
        elif sel_sort == 'Departure time' and 'Depart' in df.columns:
            df = df.sort_values('Depart')

        show_cols = [c for c in [
            'Airline', 'From', 'Depart', 'To', 'Arrive',
            'Airline Price', 'Best 3rd Price', 'Best Source',
            'Cabin Bag', 'Checked Bag', 'Stops',
            'Price Score', 'Time Score', 'Total Score',
        ] if c in df.columns]

        st.dataframe(df[show_cols] if show_cols else df,
                     use_container_width=True, hide_index=True,
                     column_config={
                         "Airline Price": st.column_config.NumberColumn(format="฿%d"),
                         "Best 3rd Price": st.column_config.NumberColumn(format="฿%d"),
                         "Total Score": st.column_config.ProgressColumn(
                             min_value=0, max_value=20, format="%.1f"),
                     } if show_cols else None)

        st.caption(f"{len(df)} flights | Last check: {latest}" if 'Checked At' in df.columns else f"{len(df)} flights")
    else:
        st.info("No flight data yet. Wait for the first scrape run.")


# ═══════════════════════════════════════
# PRICE TRENDS
# ═══════════════════════════════════════
with tab_trends:
    history = load_sheet('Price History')

    if not history.empty and len(history) > 1:
        if 'Checked At' in history.columns:
            history['Checked At'] = pd.to_datetime(history['Checked At'], errors='coerce')
            history = history.set_index('Checked At')
            for col in history.columns:
                history[col] = pd.to_numeric(history[col], errors='coerce')

            # Separate airline vs best 3rd party columns
            airline_cols = [c for c in history.columns if '(Airline)' in c]
            best_cols = [c for c in history.columns if '(Best)' in c]

            view = st.radio("Show", ["Best available price", "Airline direct price", "Both"], horizontal=True)

            if view == "Best available price":
                cols_to_show = best_cols
            elif view == "Airline direct price":
                cols_to_show = airline_cols
            else:
                cols_to_show = history.columns.tolist()

            if cols_to_show:
                selected = st.multiselect("Routes", cols_to_show, default=cols_to_show)
                if selected:
                    st.line_chart(history[selected])

            st.dataframe(history, use_container_width=True)
    elif not history.empty:
        st.info("Need 2+ checks for trends. Come back after the next run (every 4 hours).")
    else:
        st.info("No price history yet.")


# ═══════════════════════════════════════
# MANAGE TRIPS
# ═══════════════════════════════════════
with tab_config:
    config_df = load_sheet('Config')

    # Add trip form
    st.subheader("Add New Trip")

    with st.form("add_trip_main"):
        c1, c2, c3 = st.columns(3)
        with c1:
            trip_name = st.text_input("Trip Name", placeholder="e.g., Osaka")
        with c2:
            origin = st.selectbox("From", [
                "Bangkok", "Tokyo", "Osaka", "Danang", "Seoul",
                "Singapore", "Hong Kong", "Taipei", "Kuala Lumpur",
                "Ho Chi Minh", "Hanoi", "Bali", "Phuket", "Chiang Mai",
            ], key="cfg_from")
        with c3:
            dest = st.selectbox("To", [
                "Danang", "Tokyo", "Osaka", "Bangkok", "Seoul",
                "Singapore", "Hong Kong", "Taipei", "Kuala Lumpur",
                "Ho Chi Minh", "Hanoi", "Bali", "Phuket", "Chiang Mai",
            ], key="cfg_to")

        c4, c5, c6, c7 = st.columns(4)
        with c4:
            go_date = st.date_input("Departure", value=date(2026, 10, 18), key="cfg_go")
        with c5:
            back_date = st.date_input("Return", value=date(2026, 10, 25), key="cfg_back")
        with c6:
            pref_dep = st.selectbox("Best depart time", [
                "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
                "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
                "18:00", "19:00", "20:00",
            ], index=6, key="cfg_dep")
        with c7:
            pref_arr = st.selectbox("Best arrive time", [
                "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
                "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
                "18:00", "19:00", "20:00",
            ], index=12, key="cfg_arr")

        c8, c9 = st.columns([3, 1])
        with c8:
            added_by = st.text_input("Your Name", placeholder="e.g., John", key="cfg_name")
        with c9:
            st.write("")  # spacer
            submitted = st.form_submit_button("Add Trip", use_container_width=True)

        if submitted:
            if not trip_name or not added_by:
                st.error("Fill in Trip Name and Your Name")
            elif back_date <= go_date:
                st.error("Return must be after departure")
            elif origin == dest:
                st.error("From and To cannot be the same")
            else:
                if save_trip(trip_name, origin, dest, go_date, back_date, pref_dep, pref_arr, added_by):
                    st.success(f"Added **{trip_name}** ({origin} → {dest})! Tracking starts next run (within 4 hours).")
                    st.cache_data.clear()

    # Active trips
    st.markdown("---")
    st.subheader("Active Trips")

    if not config_df.empty:
        active = config_df[config_df['Active'].astype(str).str.lower().isin(['yes', 'y', 'true', '1'])]
        inactive_mask = ~config_df['Active'].astype(str).str.lower().isin(['yes', 'y', 'true', '1'])
        # Filter out instruction rows
        has_trip = config_df['Trip Name'].astype(str).str.strip() != ''
        has_from = config_df['From'].astype(str).str.strip() != ''
        active = active[has_trip & has_from]

        if not active.empty:
            show = [c for c in ['Trip Name', 'From', 'To', 'Go Date', 'Back Date',
                                'Prefer Depart', 'Prefer Arrive', 'Added By'] if c in active.columns]
            st.dataframe(active[show], use_container_width=True, hide_index=True)
        else:
            st.info("No active trips. Add one above!")
    else:
        st.info("No trips configured yet.")

    st.markdown("---")
    st.caption("Data refreshes every 5 minutes. Flights are scraped every 4 hours from Google Flights.")
    st.caption("Scores: Price (0-10, cheapest=10) + Time (0-10, closer to preferred=10) = Total (0-20)")
