import os
import json
from supabase import create_client
from dotenv import load_dotenv
from funda import Funda

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

funda = Funda()

# ---- CONFIG ----
LOCATION="amsterdam"
OFFERING_TYPE="rent"
PRICE_MAX=4000
PRICE_MIN=1000
AREA_MIN=60
BEDROOMS_MIN=3
AREA_MAX=None
PLOT_MIN=None
PLOT_MAX=None
OBJECT_TYPE=None
ENERGY_LABEL=None
MAX_PAGES = 2
ALLOWED_POSTCODES = {
    *range(1011, 1020), #   centrum/aan IJ: 1011–1019
    *range(1051, 1060), #   west:            1051–1059
    *range(1071, 1080), #   zuid:            1071–1079
    *range(1091, 1095), #   oost:           1091–1093
    *range(1096, 1099), #   oost:            1096–1098
}

def get_existing_ids():
    response = supabase.table("houses").select("id").execute()
    return {row["id"] for row in response.data}


def fetch_funda_listings(
        LOCATION=None,
        OFFERING_TYPE='buy',
        PRICE_MAX=None,
        PRICE_MIN=None,
        AREA_MIN=None,
        AREA_MAX=None,
        PLOT_MIN=None,
        PLOT_MAX=None,
        OBJECT_TYPE=None,
        ENERGY_LABEL=None):

    all_results = []
    for page in range(MAX_PAGES):
        results = funda.search_listing(
            location=LOCATION,           # City or area name
            offering_type=OFFERING_TYPE,            # 'buy' or 'rent'
            price_min=PRICE_MIN,               # Minimum price
            price_max=PRICE_MAX,               # Maximum price
            area_min=AREA_MIN,                    # Minimum living area (m²)
            area_max=AREA_MAX,                   # Maximum living area (m²)
            plot_min=PLOT_MIN,                   # Minimum plot area (m²)
            plot_max=PLOT_MAX,                   # Maximum plot area (m²)
            object_type=OBJECT_TYPE ,        # Property types (default: house, apartment)
            energy_label=ENERGY_LABEL,       # Energy labels to filter
            sort='newest',                  # Sort order (see below)
            page=page,     
        )
        all_results.extend(results)
    return all_results



def is_within_ring(postal_code: str, ALLOWED_POSTCODES) -> bool:
    """Return ``True`` if the listing's postcode prefix is in the allowed set.

    ``postal_code`` is expected to be a string such as ``"1015 BX"``.  We
    extract the first four digits and convert them to an integer before
    checking membership in :data:`ALLOWED_POSTCODES`.
    """
    if not postal_code:
        return False

    try:
        prefix = int(postal_code[:4])
        return prefix in ALLOWED_POSTCODES
    except Exception:
        return False


def is_available(listing):
    """
    Filter onder bod / verkocht
    """
    status = listing.get("status", "")
    if not status:
        return False
    status = status.strip().lower()
    return "beschikbaar" in status or "available" in status



def transform_listing(listing):
    return {
        "id": f"funda_{listing.getID()}",
        "address": listing['title'],
        "neighbourhood": listing.get("neighbourhood"),
        "city": listing.get("city"),
        "price": listing.get("price"),
        "surface_m2": listing.get("living_area"),
        "bedrooms": listing.get("bedrooms"),
        "url": f"https://www.funda.nl{listing.get('detail_url')}",
        "postcode": listing.get("postcode"),
        "status": "nieuw"
    }

def main():
    print("Fetching existing houses...")
    existing_ids = get_existing_ids()

    print("Fetching listings from Funda...")
    listings = fetch_funda_listings(LOCATION,
                                        OFFERING_TYPE,
                                        PRICE_MAX,
                                        PRICE_MIN,
                                        AREA_MIN,
                                        AREA_MAX,
                                        PLOT_MIN,
                                        PLOT_MAX,
                                        OBJECT_TYPE,
                                        ENERGY_LABEL )

    new_count = 0
    list_count = 0

    for listing in listings:
        print(f"Listing number {list_count}: {vars(listing)}")  # Print volledige listing data
        list_count += 1

        # ---- Extra filtering in Python ----
        if listing['price'] > PRICE_MAX:
            print("Filtered: Asking price too high")
            print(listing['price'])
            continue

        if listing["living_area"] < AREA_MIN:
            print("Filtered: Living area too small")
            print(listing["living_area"])
            continue

        if (listing.get("bedrooms") or 0) < BEDROOMS_MIN:
            print("Filtered: Not enough bedrooms")
            print(listing.get("bedrooms"))
            continue

        if not is_within_ring(listing['postcode'], ALLOWED_POSTCODES):
            print("Filtered: Not within ring")
            print(listing['postcode'])
            continue

        # if not is_available(listing):
        #     print("not available")
        #     print("Status:", listing.get("status", ""))
        #     continue

        if listing.getID() in existing_ids:
            print("Filtered: Already exists in database")
            continue

        house_data = transform_listing(listing)
        print("Inserting new house:", house_data)
        supabase.table("houses").insert(house_data).execute()
        new_count += 1

    print(f"Inserted {new_count} new houses.")


if __name__ == "__main__":
    main()