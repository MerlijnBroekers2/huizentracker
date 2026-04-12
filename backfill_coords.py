"""
One-time script to geocode all existing houses that are missing lat/lng.
Run once: python backfill_coords.py
"""
import os
import time
from supabase import create_client
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderRateLimited

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
geolocator = Nominatim(user_agent="huizentracker-backfill")


def main():
    houses = supabase.table("houses").select("id, postcode").is_("lat", "null").execute().data
    print(f"Found {len(houses)} houses without coordinates\n")

    for i, house in enumerate(houses):
        postcode = house.get("postcode")
        prefix = f"[{i+1}/{len(houses)}] {house['id']}"

        if not postcode:
            print(f"{prefix} — no postcode, skipping")
            continue

        try:
            time.sleep(1)  # Nominatim: max 1 req/sec
            location = geolocator.geocode(f"{postcode}, Amsterdam, Netherlands", timeout=10)
            if location:
                supabase.table("houses").update({
                    "lat": location.latitude,
                    "lng": location.longitude,
                }).eq("id", house["id"]).execute()
                print(f"{prefix} — {postcode} → ({location.latitude:.4f}, {location.longitude:.4f})")
            else:
                print(f"{prefix} — {postcode} → not found")
        except (GeocoderTimedOut, GeocoderRateLimited) as e:
            print(f"{prefix} — geocoding error: {e}, retrying after 5s...")
            time.sleep(5)

    print("\nDone.")


if __name__ == "__main__":
    main()
