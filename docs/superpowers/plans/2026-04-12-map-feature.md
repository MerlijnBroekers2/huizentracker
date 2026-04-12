# Map Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interactive Amsterdam map page showing all tracked houses as colored pins, with popups and status filters.

**Architecture:** All changes go in `app.py` and `requirements.txt`. Add a `geocode_postcode()` cached helper, a `render_map()` reusable component, and a new `page_kaart()` full-page function. The mini map is embedded in `page_overview()` inside a collapsed expander.

**Tech Stack:** Folium (Leaflet.js maps), streamlit-folium (Streamlit bridge), geopy/Nominatim (free geocoding)

---

### Task 1: Add dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the three new packages**

Replace the contents of `requirements.txt` with:

```
streamlit
supabase
python-dotenv
pyfunda
pypararius
folium
streamlit-folium
geopy
datetime
```

- [ ] **Step 2: Install locally**

```bash
uv pip install -r requirements.txt
```

Expected: resolves and installs `folium`, `streamlit-folium`, `geopy` without errors.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add folium, streamlit-folium, geopy for map feature"
```

---

### Task 2: Add geocoding helper to app.py

**Files:**
- Modify: `app.py` — add imports and `geocode_postcode()` after the existing helpers block (after `afgevallen_sort_key`, around line 147)

- [ ] **Step 1: Add imports at the top of app.py**

After the existing imports block (after line 9 `import streamlit.components.v1 as components`), add:

```python
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
```

- [ ] **Step 2: Add geocode_postcode() after afgevallen_sort_key()**

After the `afgevallen_sort_key` function (around line 146), add:

```python
@st.cache_data(ttl=86400)
def geocode_postcode(postcode: str):
    """Return (lat, lng) for a Dutch postcode, or None if not found."""
    if not postcode:
        return None
    try:
        geolocator = Nominatim(user_agent="huizentracker")
        location = geolocator.geocode(f"{postcode}, Amsterdam, Netherlands", timeout=5)
        if location:
            return (location.latitude, location.longitude)
        return None
    except GeocoderTimedOut:
        return None
```

- [ ] **Step 3: Verify the app still starts**

```bash
uv run streamlit run app.py
```

Expected: app loads on `http://localhost:8501` without import errors.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add cached geocode_postcode helper"
```

---

### Task 3: Add render_map() helper

**Files:**
- Modify: `app.py` — add `render_map()` after `geocode_postcode()`

- [ ] **Step 1: Add the ARCHIVE_STATUSES constant after STATUS_OPTIONS_NEW**

After the `STATUS_OPTIONS_NEW` list (around line 87), add:

```python
ARCHIVE_STATUSES = {"niet geïnteresseerd", "niet geboden", "bod niet geaccepteerd"}
```

- [ ] **Step 2: Add render_map() after geocode_postcode()**

```python
def render_map(houses: list[dict], height: int = 600):
    """Build and return a Folium map with all geocoded houses as pins."""
    m = folium.Map(
        location=[52.3676, 4.9041],
        zoom_start=13,
        tiles="OpenStreetMap"
    )

    for house in houses:
        coords = geocode_postcode(house.get("postcode"))
        if not coords:
            continue

        is_archived = house.get("status") in ARCHIVE_STATUSES
        color = "#9CA3AF" if is_archived else status_color(house.get("status", ""))
        radius = 6 if is_archived else 10

        popup_html = f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-width:200px;">
            <div style="font-size:15px;font-weight:600;margin-bottom:6px;">{house.get("address","")}</div>
            <div style="font-size:12px;color:#555;margin-bottom:8px;">
                {house.get("neighbourhood") or ""}{" · " if house.get("neighbourhood") else ""}{house.get("city","Amsterdam")}
            </div>
            <div style="font-size:13px;margin-bottom:8px;">
                💰 € {house.get("price","")} · 📏 {house.get("surface_m2","?")} m² · {house.get("bedrooms","?")} slpk
            </div>
            <span style="
                background:{color};
                color:{'#fff' if is_archived else '#000'};
                font-size:11px;font-weight:600;
                padding:3px 8px;border-radius:6px;
                display:inline-block;margin-bottom:10px;
            ">{house.get("status","")}</span><br>
            <a href="{house.get("url","")}" target="_blank"
               style="font-size:13px;color:#2563EB;text-decoration:none;">
                Bekijk listing →
            </a>
        </div>
        """

        folium.CircleMarker(
            location=coords,
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85 if not is_archived else 0.4,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=house.get("address", ""),
        ).add_to(m)

    return m
```

- [ ] **Step 3: Verify the app still starts**

```bash
uv run streamlit run app.py
```

Expected: no errors on startup.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add render_map() helper with colored pins and popups"
```

---

### Task 4: Add page_kaart() with sidebar filters

**Files:**
- Modify: `app.py` — add `page_kaart()` before `page_archief()`

- [ ] **Step 1: Add STATUS_GROUPS constant after ARCHIVE_STATUSES**

After the `ARCHIVE_STATUSES` constant, add:

```python
STATUS_GROUPS = {
    "✨ Potentials": ["potential"],
    "👀 Bezichtiging": ["bezichtiging gepland", "bericht gestuurd"],
    "🤔 To bied or not": ["bezichtiging geweest"],
    "💰 Bieden": ["bod gedaan"],
    "🏆 JAVA PALACE": ["bod geaccepteerd"],
    "📦 Archief": list(ARCHIVE_STATUSES),
}
```

- [ ] **Step 2: Add page_kaart() before page_archief()**

```python
def page_kaart():
    st.title("🗺️ Kaart")

    houses = get_all_houses()

    if not houses:
        st.info("Geen huizen beschikbaar.")
        return

    # ---- Sidebar filters ----
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Filters**")

    selected_groups = st.sidebar.multiselect(
        "Status groepen",
        options=list(STATUS_GROUPS.keys()),
        default=list(STATUS_GROUPS.keys()),
    )

    # Collect all statuses belonging to selected groups
    selected_statuses = set()
    for group in selected_groups:
        selected_statuses.update(STATUS_GROUPS[group])

    filtered = [h for h in houses if h.get("status") in selected_statuses]

    count_shown = len([h for h in filtered if h.get("postcode")])
    count_total = len([h for h in houses if h.get("postcode")])
    st.caption(f"{count_shown} van {count_total} huizen met postcode zichtbaar")

    m = render_map(filtered, height=600)
    st_folium(m, use_container_width=True, height=600)
```

- [ ] **Step 3: Verify page_kaart() renders by calling it temporarily in main()**

Temporarily add `page_kaart()` as the default call in `main()`, run the app, and confirm the map loads with pins. Then revert.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add page_kaart() with full map and sidebar filters"
```

---

### Task 5: Add mini map to page_overview()

**Files:**
- Modify: `app.py` — update `page_overview()` to add expander at the top

- [ ] **Step 1: Add expander with mini map at the top of page_overview()**

In `page_overview()`, after `data = get_all_houses()` and the empty-check, but before the `df = pd.DataFrame(data)` line, insert:

```python
    with st.expander("🗺️ Kaart overzicht", expanded=False):
        mini_map = render_map(data, height=350)
        st_folium(mini_map, use_container_width=True, height=350)
```

So the relevant section becomes:

```python
    data = get_all_houses()

    if not data:
        st.info("Geen data beschikbaar.")
        return

    with st.expander("🗺️ Kaart overzicht", expanded=False):
        mini_map = render_map(data, height=350)
        st_folium(mini_map, use_container_width=True, height=350)

    df = pd.DataFrame(data)
```

- [ ] **Step 2: Verify the expander appears on the Overzicht page**

```bash
uv run streamlit run app.py
```

Navigate to Overzicht, click the expander, confirm the map loads.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add mini map expander to Overzicht page"
```

---

### Task 6: Wire page_kaart() into sidebar navigation

**Files:**
- Modify: `app.py` — update `main()`

- [ ] **Step 1: Update the sidebar radio and routing in main()**

Replace the existing `main()` function with:

```python
def main():
    st.sidebar.title("🏠 Huizen Tracker")

    page = st.sidebar.radio(
        "Navigation",
        ["🆕 Nieuwe huizen", "📊 Overzicht", "🗺️ Kaart", "📦 Archief"]
    )

    if page == "🆕 Nieuwe huizen":
        page_new_houses()
    elif page == "📊 Overzicht":
        page_overview()
    elif page == "🗺️ Kaart":
        page_kaart()
    elif page == "📦 Archief":
        page_archief()
```

- [ ] **Step 2: Verify full navigation works**

```bash
uv run streamlit run app.py
```

Check all four sidebar pages load correctly. On the Kaart page, confirm:
- Sidebar shows status group multiselect
- Map renders with colored pins
- Clicking a pin shows the popup with address, price, status badge, and "Bekijk listing →" link
- Deselecting a status group removes those pins from the map
- Archived pins appear gray and smaller

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: wire Kaart page into sidebar navigation"
```

---

### Task 7: Final check and push

- [ ] **Step 1: Run the full app and do a manual smoke test**

```bash
uv run streamlit run app.py
```

Checklist:
- [ ] Nieuwe huizen page works as before
- [ ] Overzicht page works, expander shows mini map
- [ ] Kaart page shows full map with pins
- [ ] Pins are colored by status (active) or gray (archived)
- [ ] Clicking a pin shows popup with correct data and working link
- [ ] Multiselect filter updates map
- [ ] Archief page works as before

- [ ] **Step 2: Push branch**

```bash
git push -u origin feature/map
```
