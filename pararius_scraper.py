import os
from supabase import create_client
from dotenv import load_dotenv
from pypararius import Pararius

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

pararius = Pararius()

# ---- CONFIG ----
LOCATION = "amsterdam"
PRICE_MIN = 1000
PRICE_MAX = 4000
AREA_MIN = 60
BEDROOMS_MIN = 3
MAX_PAGES = 2
ALLOWED_POSTCODES = {
    *range(1011, 1020),  # centrum/aan IJ: 1011–1019
    *range(1051, 1060),  # west:            1051–1059
    *range(1071, 1080),  # zuid:            1071–1079
    *range(1091, 1095),  # oost:            1091–1094
    *range(1096, 1099),  # oost:            1096–1098
}


def get_existing_ids():
    response = supabase.table("houses").select("id").execute()
    return {row["id"] for row in response.data}


def fetch_pararius_listings():
    all_results = []
    for page in range(MAX_PAGES):
        results = pararius.search_listing(
            location=LOCATION,
            price_min=PRICE_MIN,
            price_max=PRICE_MAX,
            area_min=AREA_MIN,
            bedrooms=BEDROOMS_MIN,
            sort="newest",
            page=page,
        )
        all_results.extend(results)
    return all_results


def is_within_ring(postal_code: str) -> bool:
    if not postal_code:
        return False
    try:
        prefix = int(postal_code[:4])
        return prefix in ALLOWED_POSTCODES
    except Exception:
        return False


def transform_listing(listing) -> dict:
    return {
        "id": f"pararius_{listing.id}",
        "address": listing["title"],
        "neighbourhood": listing.get("neighbourhood"),
        "city": listing.get("city"),
        "price": listing.get("price"),
        "surface_m2": listing.get("area"),
        "bedrooms": listing.get("bedrooms"),
        "url": listing["url"],
        "postcode": listing.get("postcode"),
        "status": "nieuw",
    }


def main():
    print("Fetching existing houses...")
    existing_ids = get_existing_ids()

    print("Fetching listings from Pararius...")
    listings = fetch_pararius_listings()

    new_count = 0

    for i, listing in enumerate(listings):
        listing_id = f"pararius_{listing.id}"
        if listing_id in existing_ids:
            print(f"Listing number {i}: {listing['title']} — skipping, already exists")
            continue

        print(f"Listing number {i}: {listing['title']} — fetching full details...")
        full = pararius.get_listing(listing["url"])

        if not is_within_ring(full.get("postcode", "")):
            print(f"Filtered: Not within ring ({full.get('postcode')})")
            continue

        house_data = transform_listing(full)
        print("Inserting new house:", house_data)
        supabase.table("houses").insert(house_data).execute()
        new_count += 1

    print(f"Inserted {new_count} new houses.")


if __name__ == "__main__":
    main()
