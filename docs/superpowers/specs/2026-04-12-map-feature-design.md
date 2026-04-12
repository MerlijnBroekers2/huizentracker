# Map Feature Design

**Branch:** `feature/map`  
**Date:** 2026-04-12

## Overview

Add a map view to the Huizen Tracker app showing all tracked Amsterdam properties as pins on an interactive map. Pins are colored by status, archived properties are visually faded, and clicking a pin shows a popup with house details and a link to the listing.

---

## Data & Geocoding

- Houses loaded from Supabase as usual (all statuses)
- Postcodes stored in the `postcode` column (already added this session)
- Each postcode geocoded to lat/lng using **Nominatim** (OpenStreetMap, free, no API key)
- Geocoding wrapped in `@st.cache_data(ttl=86400)` — runs once per postcode per day, subsequent loads are instant
- Houses with `postcode = NULL` are silently skipped on the map

**New packages:** `folium`, `streamlit-folium`, `geopy`

---

## Map Component

A single `render_map(houses, height)` helper builds and returns the Folium map. Used by both the full page and mini version.

**Map settings:**
- Center: Amsterdam (52.3676, 4.9041)
- Tiles: OpenStreetMap (free)

**Pins:**
- Active houses: `CircleMarker`, radius 10, color from existing `status_color()` function
- Archived houses (`niet geïnteresseerd`, `niet geboden`, `bod niet geaccepteerd`): `CircleMarker`, radius 6, gray (`#9CA3AF`)

**Popup content (on click):**
- Address (bold)
- Neighbourhood · City
- € price/mnd · m² · bedrooms
- Colored status badge
- "Bekijk listing →" link opening in new tab

---

## Filters

Shown in the **sidebar**, only when on the Kaart page.

- **Multiselect — Status groepen:** options map to Kanban columns:
  - Potentials → `potential`
  - Bezichtiging → `bezichtiging gepland`, `bericht gestuurd`
  - To bied or not → `bezichtiging geweest`
  - Bieden → `bod gedaan`
  - JAVA PALACE → `bod geaccepteerd`
- **Checkbox — Toon archief:** toggles visibility of archived pins (default: on)
- Filters update the map instantly
- Mini map (Overzicht) has no filters — always shows all houses

---

## Page Layout

**Full page — 🗺️ Kaart:**
- New sidebar entry between Overzicht and Archief
- Full-width `st_folium` map at `height=600`
- Sidebar filters visible only on this page

**Mini map — Overzicht page:**
- `st.expander("🗺️ Kaart overzicht")` collapsed by default at the top of the page
- `height=350`, no filters, all houses shown
- Keeps Kanban board as the primary focus

---

## Architecture

No new files. All changes in `app.py`:

1. Add `geocode_postcode(postcode)` — cached geocoding function
2. Add `render_map(houses, height)` — builds Folium map, returns it
3. Add `page_kaart()` — full map page with sidebar filters
4. Update `page_overview()` — add expander with mini map at top
5. Update `main()` — add Kaart to sidebar navigation
