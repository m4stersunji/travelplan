"""Flight Price Tracker — Web UI

Run: streamlit run app.py
Deploy: Push to GitHub → connect at share.streamlit.io
"""
import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date

# --- Page config ---
st.set_page_config(
    page_title="Flight Tracker",
    page_icon="✈️",
    layout="wide",
)

# --- Google Sheets connection ---
@st.cache_resource
def get_spreadsheet():
    try:
        creds = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(creds)
        return gc.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
    except Exception as e:
        st.error(f"Cannot connect to Google Sheets: {e}")
        return None


def load_sheet_df(sheet_name):
    """Load a worksheet as a DataFrame."""
    sh = get_spreadsheet()
    if not sh:
        return pd.DataFrame()
    try:
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def load_config():
    """Load Config tab."""
    return load_sheet_df('Config')


def save_trip(trip_name, origin, dest, go_date, back_date, prefer_depart, prefer_arrive, added_by):
    """Add a trip row to Config tab."""
    sh = get_spreadsheet()
    if not sh:
        return False
    try:
        ws = sh.worksheet('Config')
        row = [
            trip_name, origin, dest,
            go_date.strftime('%Y-%m-%d'),
            back_date.strftime('%Y-%m-%d'),
            prefer_depart, prefer_arrive,
            'Yes', added_by,
        ]
        existing = ws.get_all_values()
        next_row = len(existing) + 1
        ws.update(f'A{next_row}', [row])
        return True
    except Exception as e:
        st.error(f"Failed to save: {e}")
        return False


def toggle_trip(row_idx, new_status):
    """Toggle Active status of a trip."""
    sh = get_spreadsheet()
    if not sh:
        return
    try:
        ws = sh.worksheet('Config')
        ws.update_acell(f'H{row_idx + 2}', new_status)  # +2 for header + 0-index
    except Exception:
        pass


# --- Sidebar: Add Trip ---
with st.sidebar:
    st.header("✈️ Add New Trip")

    with st.form("add_trip"):
        trip_name = st.text_input("Trip Name", placeholder="e.g., Osaka")
        col1, col2 = st.columns(2)
        with col1:
            origin = st.selectbox("From", [
                "Bangkok", "Tokyo", "Osaka", "Danang", "Seoul",
                "Singapore", "Hong Kong", "Taipei", "Kuala Lumpur",
                "Ho Chi Minh", "Hanoi", "Bali", "Phuket", "Chiang Mai",
            ])
        with col2:
            dest = st.selectbox("To", [
                "Danang", "Tokyo", "Osaka", "Bangkok", "Seoul",
                "Singapore", "Hong Kong", "Taipei", "Kuala Lumpur",
                "Ho Chi Minh", "Hanoi", "Bali", "Phuket", "Chiang Mai",
            ])

        col3, col4 = st.columns(2)
        with col3:
            go_date = st.date_input("Departure", value=date(2026, 5, 29))
        with col4:
            back_date = st.date_input("Return", value=date(2026, 6, 1))

        col5, col6 = st.columns(2)
        with col5:
            prefer_depart = st.selectbox("Preferred Departure", [
                "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
                "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
                "18:00", "19:00", "20:00",
            ], index=6)  # default 12:00
        with col6:
            prefer_arrive = st.selectbox("Preferred Arrival", [
                "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
                "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
                "18:00", "19:00", "20:00",
            ], index=12)  # default 18:00

        added_by = st.text_input("Your Name", placeholder="e.g., John")

        submitted = st.form_submit_button("Add Trip", use_container_width=True)

        if submitted:
            if not trip_name or not added_by:
                st.error("Please fill in Trip Name and Your Name")
            elif back_date <= go_date:
                st.error("Return date must be after departure")
            elif origin == dest:
                st.error("From and To cannot be the same")
            else:
                if save_trip(trip_name, origin, dest, go_date, back_date,
                             prefer_depart, prefer_arrive, added_by):
                    st.success(f"Added {trip_name}! Tracking starts next run.")
                    st.cache_resource.clear()

    st.divider()
    st.caption("Trips are checked every 4 hours. Results appear in LINE and this dashboard.")


# --- Main content ---
st.title("✈️ Flight Price Tracker")

# Tab navigation
tab_dashboard, tab_flights, tab_trends, tab_config = st.tabs([
    "Dashboard", "All Flights", "Price Trends", "Trip Config"
])

# === DASHBOARD ===
with tab_dashboard:
    overview = load_sheet_df('Overview')
    heatmap = load_sheet_df('Heatmap')

    if not overview.empty:
        # Best roundtrip
        combo_row = overview[overview['Route'] == 'BEST ROUNDTRIP']
        regular_rows = overview[overview['Route'] != 'BEST ROUNDTRIP']

        if not combo_row.empty:
            best_price = combo_row.iloc[0].get('Best Price', 'N/A')
            combo_dates = combo_row.iloc[0].get('Best Source', '')
            st.metric("Best Roundtrip", f"฿{best_price:,}" if isinstance(best_price, (int, float)) else str(best_price), combo_dates)

        if not regular_rows.empty:
            cols = st.columns(len(regular_rows))
            for i, (_, row) in enumerate(regular_rows.iterrows()):
                with cols[i]:
                    route = row.get('Route', '')
                    date_label = row.get('Date', '')
                    airline_price = row.get('Airline Price', '')
                    best_price = row.get('Best Price', '')
                    source = row.get('Best Source', '')

                    st.metric(
                        f"{route} {date_label}",
                        f"฿{best_price:,}" if isinstance(best_price, (int, float)) else str(best_price),
                        f"via {source}" if source else "Airline direct",
                    )

    # Heatmap
    if not heatmap.empty:
        st.subheader("Price Comparison by Date")
        st.dataframe(heatmap, use_container_width=True, hide_index=True)

    # Last check time
    if not overview.empty:
        last_check = overview.iloc[0].get('Last Check', '')
        if last_check:
            st.caption(f"Last checked: {last_check}")


# === ALL FLIGHTS ===
with tab_flights:
    flights_df = load_sheet_df('All Flights')

    if not flights_df.empty:
        # Filters
        col_route, col_date, col_direct = st.columns(3)
        with col_route:
            routes = ['All'] + sorted(flights_df['Route'].unique().tolist())
            sel_route = st.selectbox("Route", routes)
        with col_date:
            dates = ['All'] + sorted(flights_df['Date'].unique().tolist())
            sel_date = st.selectbox("Date", dates)
        with col_direct:
            sel_direct = st.selectbox("Stops", ['All', 'Direct only', 'With stops'])

        filtered = flights_df.copy()
        if sel_route != 'All':
            filtered = filtered[filtered['Route'] == sel_route]
        if sel_date != 'All':
            filtered = filtered[filtered['Date'] == sel_date]
        if sel_direct == 'Direct only':
            filtered = filtered[filtered['Direct'] == True]
        elif sel_direct == 'With stops':
            filtered = filtered[filtered['Direct'] == False]

        # Show latest check only
        if 'Checked At' in filtered.columns:
            latest = filtered['Checked At'].max()
            filtered = filtered[filtered['Checked At'] == latest]

        # Sort by Total Score descending
        if 'Total Score' in filtered.columns:
            filtered = filtered.sort_values('Total Score', ascending=False)

        display_cols = [c for c in [
            'Route', 'Date', 'Airline', 'Depart', 'Arrive',
            'Airline Price', 'Best 3rd Price', 'Best Source',
            'Checked Bag', 'Stops', 'Total Score',
        ] if c in filtered.columns]

        st.dataframe(filtered[display_cols] if display_cols else filtered,
                     use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(filtered)} flights from {latest}" if 'Checked At' in filtered.columns else f"Showing {len(filtered)} flights")
    else:
        st.info("No flight data yet. Wait for the first scrape run.")


# === PRICE TRENDS ===
with tab_trends:
    history = load_sheet_df('Price History')

    if not history.empty and len(history) > 1:
        st.subheader("Price Over Time")

        # Parse dates and set as index
        if 'Checked At' in history.columns:
            history['Checked At'] = pd.to_datetime(history['Checked At'], errors='coerce')
            history = history.set_index('Checked At')

            # Convert to numeric
            for col in history.columns:
                history[col] = pd.to_numeric(history[col], errors='coerce')

            # Let user pick which lines to show
            available = history.columns.tolist()
            selected = st.multiselect("Select routes to chart", available, default=available)

            if selected:
                st.line_chart(history[selected])

            st.dataframe(history, use_container_width=True)
    else:
        st.info("Need 2+ data points for trends. Check back after a few scrape runs.")


# === CONFIG ===
with tab_config:
    st.subheader("Active Trips")
    config_df = load_config()

    if not config_df.empty:
        active = config_df[config_df['Active'].astype(str).str.lower().isin(['yes', 'y', 'true', '1'])]
        inactive = config_df[~config_df['Active'].astype(str).str.lower().isin(['yes', 'y', 'true', '1'])]

        if not active.empty:
            display_cols = [c for c in ['Trip Name', 'From', 'To', 'Go Date', 'Back Date',
                                        'Prefer Depart', 'Prefer Arrive', 'Added By'] if c in active.columns]
            st.dataframe(active[display_cols], use_container_width=True, hide_index=True)

        if not inactive.empty:
            st.subheader("Paused Trips")
            st.dataframe(inactive[display_cols] if display_cols else inactive,
                         use_container_width=True, hide_index=True)
    else:
        st.info("No trips configured. Use the sidebar to add one!")

    st.divider()
    st.caption("Edit trips directly in the [Google Sheet Config tab](https://docs.google.com/spreadsheets/d/" +
               st.secrets.get("GOOGLE_SHEET_ID", "") + "/edit) or use the sidebar form.")
