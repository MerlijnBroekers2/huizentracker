import streamlit as st
import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import math
import io
from staticmap import StaticMap, CircleMarker
from PIL import ImageDraw, ImageFont

st.set_page_config(layout="wide")

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
.kanban-card {
    background-color: #111827;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 12px;
    border: 1px solid #2D3748;
}
.kanban-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 6px;
}
.kanban-meta {
    font-size: 14px;
    margin-bottom: 4px;
}
.status-badge {
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 6px;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# CONFIG & DATABASE CONNECTION
# -----------------------------

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

STATUS_OPTIONS = [
    "new",
    "not interested",
    "potential",
    "message sent",
    "viewing planned",
    "viewing done",
    "no viewing available",
    "not applied",
    "applied",
    "application rejected",
]

STATUS_OPTIONS_NEW = [
    "not interested",
    "potential",
    "message sent",
]

ARCHIVE_STATUSES = {"not interested", "not applied", "application rejected"}

MAP_CENTER_LNG = 4.9041
MAP_CENTER_LAT = 52.3676
MAP_ZOOM = 13

STATUS_GROUPS = {
    "New": ["new"],
    "Potential": ["potential"],
    "Viewing": ["viewing planned", "message sent"],
    "Decide": ["viewing done"],
    "Applied": ["applied"],
    "Archive": list(ARCHIVE_STATUSES),
}


# -----------------------------
# HELPERS
# -----------------------------

def update_status(house_id, new_status):
    supabase.table("houses").update(
        {
            "status": new_status,
            "last_updated": datetime.utcnow().isoformat()
        }
    ).eq("id", house_id).execute()


@st.cache_data(ttl=30)
def get_all_houses():
    return supabase.table("houses").select("*").execute().data


def status_color(status):
    colors = {
        "new": "#28FE02",
        "potential": "#FACC15",
        "message sent": "#F63BF3",
        "viewing planned": "#FF9900",
        "viewing done": "#0BD2F5",
        "applied": "#3B3EF6",
        "not interested": "#EF4444",
        "not applied": "#F17878",
        "no viewing available": "#A30909",
        "application rejected": "#A30909",
    }
    return colors.get(status, "#9CA3AF")


def viewing_sort_key(status):
    priority = {
        "viewing planned": 0,
        "message sent": 1,
    }
    return priority.get(status, 99)


def archive_sort_key(status):
    priority = {
        "application rejected": 0,
        "not applied": 1,
        "no viewing available": 2,
        "not interested": 3,
    }
    return priority.get(status, 99)


def _lonlat_to_pixel(lng, lat, width, height, tile_size=256):
    def to_tile(lon, lat_deg, z):
        x = (lon + 180) / 360 * (2 ** z)
        lat_r = math.radians(lat_deg)
        y = (1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * (2 ** z)
        return x, y

    cx, cy = to_tile(MAP_CENTER_LNG, MAP_CENTER_LAT, MAP_ZOOM)
    tx, ty = to_tile(lng, lat, MAP_ZOOM)
    px = int((tx - cx) * tile_size + width / 2)
    py = int((ty - cy) * tile_size + height / 2)
    return px, py


@st.cache_data(ttl=300)
def render_static_map(pin_data, width=1400, height=850, show_numbers=True):
    m = StaticMap(width, height)
    for num, lat, lng, color in pin_data:
        m.add_marker(CircleMarker((lng, lat), color, 22))

    image = m.render(zoom=MAP_ZOOM, center=[MAP_CENTER_LNG, MAP_CENTER_LAT])
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.load_default(size=11)
    except TypeError:
        font = ImageFont.load_default()

    for num, lat, lng, color in pin_data:
        px, py = _lonlat_to_pixel(lng, lat, width, height)
        r = 11
        draw.ellipse([px - r, py - r, px + r, py + r], fill="white", outline=color, width=2)
        if show_numbers:
            label = str(num)
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((px - tw // 2, py - th // 2), label, fill="#111827", font=font)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


# -----------------------------
# PAGE 1 — New listings
# -----------------------------
def page_new_houses():
    houses = supabase.table("houses") \
        .select("*") \
        .eq("status", "new") \
        .execute().data

    count = len(houses) if houses else 0

    st.title(f"New Listings ({count})")

    if not houses:
        st.info("No new listings found.")
        return

    for house in houses:
        st.divider()

        st.subheader(house["address"])
        st.write(f"€ {house['price']} / month")
        st.write(f"{house['surface_m2']} m²  ·  {house['bedrooms']} bedrooms")
        st.markdown(f"[View listing]({house['url']})")

        st.markdown("**Move to:**")

        cols = st.columns(3, gap="small")
        for col, status in zip(cols, STATUS_OPTIONS_NEW):
            if col.button(
                status,
                key=f"{house['id']}_{status}",
                use_container_width=True
            ):
                update_status(house["id"], status)
                st.cache_data.clear()
                st.toast(f"Status updated to '{status}'")
                st.rerun()

        st.write("")


# -----------------------------
# PAGE 2 — Kanban overview
# -----------------------------
if "editing_house" not in st.session_state:
    st.session_state.editing_house = None


def page_overview():
    st.title("Overview")

    st.markdown("""
    <style>
    * { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    </style>
    """, unsafe_allow_html=True)

    data = get_all_houses()

    if not data:
        st.info("No data available.")
        return

    with st.expander("Map overview", expanded=False) as map_expander:
        if map_expander:
            mini_pins = []
            for house in data:
                lat, lng = house.get("lat"), house.get("lng")
                if not lat or not lng:
                    continue
                num = len(mini_pins) + 1
                is_archived = house.get("status") in ARCHIVE_STATUSES
                color = "#9CA3AF" if is_archived else status_color(house.get("status", ""))
                mini_pins.append((num, lat, lng, color))
            if mini_pins:
                img_bytes = render_static_map(tuple(mini_pins), width=1000, height=500, show_numbers=False)
                st.image(img_bytes, use_container_width=True)

    df = pd.DataFrame(data)

    kanban_columns = {
        "Potential": ["potential"],
        "Viewing": ["viewing planned", "message sent"],
        "Decide": ["viewing done"],
        "Applied": ["applied"],
    }

    cols = st.columns([1, 1, 1, 1], gap="small")

    for col, (column_name, statuses) in zip(cols, kanban_columns.items()):
        with col:
            st.subheader(column_name)

            filtered = df[df["status"].isin(statuses)]

            if column_name == "Viewing":
                filtered = filtered.sort_values(
                    by="status",
                    key=lambda x: x.map(viewing_sort_key)
                )

            for _, house in filtered.iterrows():

                badge_color = status_color(house["status"])

                card_html = f"""
                <a href="{house['url']}" target="_blank" style="text-decoration:none;">
                    <div style="
                        position: relative;
                        background: rgba(255,255,255,0.55);
                        backdrop-filter: blur(14px);
                        -webkit-backdrop-filter: blur(14px);
                        border-radius: 18px;
                        border: 1px solid rgba(229,231,235,0.6);
                        padding: 16px;
                        cursor: pointer;
                        transition: all 0.25s ease;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
                    "
                    onmouseover="this.style.transform='translateY(-4px)'"
                    onmouseout="this.style.transform='translateY(0px)'">

                        <div style="
                            position: absolute;
                            top: 12px;
                            right: 12px;
                            font-size: 11px;
                            font-weight: 600;
                            padding: 4px 8px;
                            border-radius: 8px;
                            background: {badge_color};
                            color: black;
                        ">
                            {house["status"]}
                        </div>

                        <div style="
                            font-size: 16px;
                            font-weight: 600;
                            margin-bottom: 10px;
                            margin-top: 6px;
                            color: #111827;
                            line-height: 1.35;
                            padding-right: 60px;
                        ">
                            {house["address"]}
                        </div>

                        <div style="
                            font-size: 14px;
                            color: #374151;
                            line-height: 1.4;
                        ">
                            € {house["price"]} / mo  ·  {house["surface_m2"]} m²  ·  {house["bedrooms"]} bd
                        </div>

                    </div>
                </a>
                """

                st.markdown(card_html, unsafe_allow_html=True)

                if st.button(
                    house["status"],
                    key=f"badge_{house['id']}",
                    help="Click to change status"
                ):
                    st.session_state.editing_house = house["id"]

                if st.session_state.editing_house == house["id"]:
                    new_status = st.selectbox(
                        "Change status",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(house["status"]),
                        key=f"popup_status_{house['id']}"
                    )

                    if new_status != house["status"]:
                        update_status(house["id"], new_status)
                        house["status"] = new_status
                        st.toast("Status saved")
                        st.session_state.editing_house = None
                        st.cache_data.clear()
                        st.rerun()


# -----------------------------
# PAGE 3 — Map
# -----------------------------
def page_map():
    st.title("Map")

    houses = get_all_houses()
    if not houses:
        st.info("No listings available.")
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Filters**")
    selected_groups = st.sidebar.multiselect(
        "Status groups",
        options=list(STATUS_GROUPS.keys()),
        default=list(STATUS_GROUPS.keys()),
    )
    selected_statuses = set()
    for group in selected_groups:
        selected_statuses.update(STATUS_GROUPS[group])

    filtered = [h for h in houses if h.get("status") in selected_statuses]

    pin_data = []
    legend_rows = []
    for house in filtered:
        lat, lng = house.get("lat"), house.get("lng")
        if not lat or not lng:
            continue
        num = len(pin_data) + 1
        is_archived = house.get("status") in ARCHIVE_STATUSES
        color = "#9CA3AF" if is_archived else status_color(house.get("status", ""))
        pin_data.append((num, lat, lng, color))
        legend_rows.append({
            "num": num,
            "id": house.get("id"),
            "address": house.get("address", ""),
            "status": house.get("status", ""),
            "price": f"€ {house.get('price', '')}",
            "m2": str(house.get("surface_m2", "")),
            "url": house.get("url", ""),
        })

    count_total = len([h for h in houses if h.get("lat")])
    st.caption(f"{len(pin_data)} of {count_total} listings with location visible")

    if pin_data:
        img_bytes = render_static_map(tuple(pin_data), width=1400, height=900)
        st.image(img_bytes, use_container_width=True)
    else:
        st.info("No listings with location data found for the selected filters.")

    if legend_rows:
        st.markdown("### Legend")
        header = st.columns([0.4, 2.5, 2, 1.2, 0.8, 0.5])
        header[0].markdown("**#**")
        header[1].markdown("**Address**")
        header[2].markdown("**Status**")
        header[3].markdown("**Price**")
        header[4].markdown("**m²**")
        header[5].markdown("**Link**")
        st.divider()
        for row in legend_rows:
            cols = st.columns([0.4, 2.5, 2, 1.2, 0.8, 0.5])
            cols[0].markdown(f"**{row['num']}**")
            cols[1].write(row["address"])
            new_status = cols[2].selectbox(
                "",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(row["status"]),
                key=f"map_legend_{row['id']}",
                label_visibility="collapsed",
            )
            if new_status != row["status"]:
                update_status(row["id"], new_status)
                st.cache_data.clear()
                st.rerun()
            cols[3].write(row["price"])
            cols[4].write(row["m2"])
            cols[5].markdown(f"[→]({row['url']})")


# -----------------------------
# PAGE 4 — Archive
# -----------------------------
def page_archive():
    data = get_all_houses()

    df = pd.DataFrame(data)

    archive_status_priority = {
        "application rejected": 0,
        "not applied": 1,
        "not interested": 2,
    }

    df = df[df["status"].isin(archive_status_priority.keys())]
    count_archive = len(df) if not df.empty else 0

    st.title(f"Archive ({count_archive})")

    if df.empty:
        st.info("No archived listings.")
        return

    df["sort_key"] = df["status"].map(archive_status_priority)
    df = df.sort_values("sort_key")

    for _, row in df.iterrows():

        card_html = f"""
        <a href="{row['url']}" target="_blank" style="text-decoration:none;">
        <div style="
            background: rgba(255,255,255,0.55);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 14px;
            border: 1px solid rgba(229,231,235,0.6);
            padding: 14px;
            margin-bottom: 12px;
            cursor: pointer;
            transition: all 0.25s ease;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        "
        onmouseover="this.style.transform='translateY(-3px)'"
        onmouseout="this.style.transform='translateY(0px)'">

            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="
                    font-size: 16px;
                    font-weight: 600;
                    color: #111827;
                    line-height: 1.35;
                    padding-right: 12px;
                ">
                    {row["address"]}
                </div>
                <span style="
                    background: {status_color(row['status'])};
                    padding: 4px 8px;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                ">
                    {row["status"]}
                </span>
            </div>

            <div style="
                font-size: 14px;
                color: #374151;
                margin-top: 8px;
            ">
                € {row["price"]} / mo  ·  {row["surface_m2"]} m²  ·  {row["bedrooms"]} bd
            </div>

        </div>
        </a>
        """
        st.markdown(card_html, unsafe_allow_html=True)


# -----------------------------
# MAIN APP
# -----------------------------

def main():
    st.sidebar.title("Rental Tracker")

    page = st.sidebar.radio(
        "Navigation",
        ["New listings", "Overview", "Map", "Archive"]
    )

    if page == "New listings":
        page_new_houses()
    elif page == "Overview":
        page_overview()
    elif page == "Map":
        page_map()
    elif page == "Archive":
        page_archive()


if __name__ == "__main__":
    main()
