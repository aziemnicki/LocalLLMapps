import os
import requests
import time
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from datetime import datetime

load_dotenv()


class BrightDataAPI:
    BASE_URL = "https://api.brightdata.com/serp"
    CUSTOMER_ID = "c_8a10678a"
    ZONE = "serp_api1"

    def __init__(self):
        self.api_key = os.getenv("BRIGHTDATA_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _poll_results(
        self, response_id: str, max_retries: int = 10, delay: int = 10
    ) -> Optional[Dict]:
        """Generic polling function for any type of search results."""
        for _ in range(max_retries):
            try:
                response = requests.get(
                    f"{self.BASE_URL}/get_result",
                    params={
                        "customer": self.CUSTOMER_ID,
                        "zone": self.ZONE,
                        "response_id": response_id,
                    },
                    headers=self.headers,
                )

                if response.status_code == 200:
                    try:
                        result = response.json()
                        return result
                    except ValueError as e:
                        print(f"Failed to parse JSON response: {e}")
                        print("Raw response:", response.text[:200])

                time.sleep(delay)

            except requests.RequestException as e:
                print(f"Error polling results: {e}")

        return None

    def search_travel(self, url: str, params: Dict[Any, Any] = None) -> Optional[Dict]:
        """
        Generic travel search function that can be used for both flights and hotels.

        Args:
            url: Base URL for the search
            params: Dictionary of additional parameters like dates, currency, etc.
        """
        payload = {"url": url, "brd_json": "json"}

        # Add any additional parameters to the URL if provided
        if params:
            query_params = "&".join(f"{k}={v}" for k, v in params.items())
            if "?" in payload["url"]:
                payload["url"] += f"&{query_params}"
            else:
                payload["url"] += f"?{query_params}"

        try:
            response = requests.post(
                f"{self.BASE_URL}/req",
                params={"customer": self.CUSTOMER_ID, "zone": self.ZONE},
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()

            response_id = response.json().get("response_id")
            if response_id:
                return self._poll_results(response_id)

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            print(f"Request error response: {response.text}")
        except Exception as err:
            print(f"An error occurred: {err}")

        return None

    def search_flights(
        self, tfs: str, language: str = "en", currency: str = "USD"
    ) -> Optional[Dict]:
        """Specific method for flight searches."""
        url = f"https://www.google.com/travel/flights/search"
        params = {"tfs": tfs, "hl": language, "curr": currency}
        return self.search_travel(url, params)

    def search_hotels(
        self,
        location: str = None,
        check_in: str = None,
        check_out: str = None,
        occupancy: str = None,
        currency: str = "USD",
        free_cancellation: bool = False,
        accommodation_type: str = "hotels",
    ) -> Optional[Dict]:
        """Specific method for hotel searches."""
        url = f"https://www.google.com/travel/search?q={location}"
        params = {"brd_currency": currency}

        if check_in and check_out:
            params["brd_dates"] = (
                f"{datetime.strptime(check_in, '%B %d, %Y').strftime('%Y-%m-%d')},{datetime.strptime(check_out, '%B %d, %Y').strftime('%Y-%m-%d')}"
            )
        if occupancy:
            params["brd_occupancy"] = occupancy
        if free_cancellation:
            params["brd_free_cancellation"] = "true"
        if accommodation_type:
            params["brd_accommodation_type"] = accommodation_type

        return self.search_travel(url, params)


# Example usage
if __name__ == "__main__":
    api = BrightDataAPI()
    # Example flight search
    # flight_results = api.search_flights("tfs_params_here", "en", "USD")

    # Example hotel search
    hotel_results = api.search_hotels(
        check_in="April 22, 2025",
        check_out="May 1, 2025",
        occupancy="2",
        currency="USD",
        location="New York"
    )
    print(hotel_results)
