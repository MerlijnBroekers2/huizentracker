from dotenv import load_dotenv
from notifications import send_new_listings_email

load_dotenv()

test_houses = [
    {
        "address": "Keizersgracht 123",
        "neighbourhood": "Centrum",
        "city": "Amsterdam",
        "price": 2500,
        "surface_m2": 85,
        "bedrooms": 3,
        "url": "https://www.funda.nl",
        "status": "nieuw",
    },
    {
        "address": "Prinsengracht 456",
        "neighbourhood": "Jordaan",
        "city": "Amsterdam",
        "price": 3200,
        "surface_m2": 110,
        "bedrooms": 4,
        "url": "https://www.pararius.com",
        "status": "nieuw",
    },
]

send_new_listings_email(test_houses, "Test")
