from flights.google_flight_scraper import get_flight_url, scrape_flights
from user_preferences import get_travel_details
from flights.flights import BrightDataAPI
import asyncio
from config.models import model


async def main():
    travel_requirements = input("Enter your travel requirements: ")
    details = get_travel_details(travel_requirements)

    origin_airport_code = details.get("origin_airport_code")
    destination_airport_code = details.get("destination_airport_code")
    destination_city_name = details.get("destination_city_name")
    if not details.get("dates"):
        return
    start_date, end_date = details["dates"].get("start_date"), details["dates"].get(
        "end_date"
    )

    if not all([origin_airport_code, destination_airport_code, start_date, end_date]):
        return

    url = await get_flight_url(
        origin_airport_code, destination_airport_code, start_date, end_date
    )
    flights = await scrape_flights(url, travel_requirements)
    currency = "USD"

    api = BrightDataAPI()
    hotels = api.search_hotels(
        occupancy="2",
        currency=currency,
        check_in=start_date,
        check_out=end_date,
        location=destination_city_name,
    )
    response = model.invoke(
        f"""Summarize the following hotels and give me a nicely formatted output: {hotels}. Then make a reccomendation for the best hotel to stay in based on this: {travel_requirements}"""
    )
    print(response.content)


if __name__ == "__main__":
    asyncio.run(main())
