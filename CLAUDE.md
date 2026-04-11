# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the Streamlit app
streamlit run app.py

# Run the scraper manually
python funda_scraper.py

# Install dependencies
pip install -r requirements.txt
```

## Environment

Both `app.py` and `funda_scraper.py` require a `.env` file in the project root:
```
SUPABASE_URL=...
SUPABASE_KEY=...
```

For GitHub Actions (scraper automation), these are stored as repository secrets.

## Architecture

**Two independent entry points:**

- `funda_scraper.py` — run by GitHub Actions every 30 minutes. Fetches listings from Funda.nl via `pyfunda`, filters them in Python (price, area, postcode), and inserts new ones into Supabase with `status="nieuw"`. Duplicate detection is done by querying all existing IDs before inserting.

- `app.py` — Streamlit UI with three pages (Nieuwe Huizen, Overzicht/Kanban, Archief). All data reads/writes go directly to Supabase with no caching layer. Status changes call `update_status()` and immediately trigger `st.rerun()`.

**Supabase `houses` table columns:** `id`, `address`, `neighbourhood`, `city`, `price`, `surface_m2`, `bedrooms`, `url`, `status`, `last_updated`

**Status lifecycle** (defined in `STATUS_OPTIONS`, `app.py:69`):
- `nieuw` → triage on Nieuwe Huizen page → `potential` / `niet geïnteresseerd` / `bericht gestuurd`
- Progresses through: `bezichtiging gepland` → `bezichtiging geweest` → `bod gedaan` → `bod geaccepteerd`
- Dead-ends: `niet geïnteresseerd`, `geen bezichtiging plek`, `niet geboden`, `bod niet geaccepteerd`

**Kanban columns** map statuses as follows (see `kanban_columns` dict, `app.py:217`):
- ✨ Potentials → `potential`
- 👀 Bezichtiging → `bezichtiging gepland`, `bericht gestuurd`
- 🤔 To bied or not to bied → `bezichtiging geweest`
- 💰 Bieden → `bod gedaan`
- 🏆 JAVA PALACE → `bod geaccepteerd`

Archive page shows: `bod niet geaccepteerd`, `niet geboden`, `niet geïnteresseerd`

**Postcode filter** (Amsterdam within the ring, `funda_scraper.py:28`): 1011–1019, 1051–1059, 1071–1079, 1091–1094, 1096–1098. The `is_available()` filter is currently commented out.
