import os
import aiohttp
import asyncio
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

    async def _poll_results(
        self, session: aiohttp.ClientSession, response_id: str, max_retries: int = 10, delay: int = 10
    ) -> Optional[Dict]:
        """Generic polling function for any type of search results."""
        for _ in range(max_retries):
            try:
                async with session.get(
                    f"{self.BASE_URL}/get_result",
                    params={
                        "customer": self.CUSTOMER_ID,
                        "zone": self.ZONE,
                        "response_id": response_id,
                    },
                    headers=self.headers,
                ) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                            return result
                        except ValueError as e:
                            print(f"Failed to parse JSON response: {e}")
                            print("Raw response:", (await response.text())[:200])

                await asyncio.sleep(delay)

            except Exception as e:
                print(f"Error polling results: {e}")

        return None

    async def search_travel(
        self, session: aiohttp.ClientSession, url: str, params: Dict[Any, Any] = None
    ) -> Optional[Dict]:
        """Generic travel search function that can be used for both flights and hotels."""
        payload = {"url": url, "brd_json": "json"}

        if params:
            query_params = "&".join(f"{k}={v}" for k, v in params.items())
            if "?" in payload["url"]:
                payload["url"] += f"&{query_params}"
            else:
                payload["url"] += f"?{query_params}"

        try:
            async with session.post(
                f"{self.BASE_URL}/req",
                params={"customer": self.CUSTOMER_ID, "zone": self.ZONE},
                headers=self.headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                response_id = data.get("response_id")
                if response_id:
                    return await self._poll_results(session, response_id)

        except aiohttp.ClientResponseError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")

        return None

    async def search_flights(
        self, session: aiohttp.ClientSession, tfs: str, language: str = "en", currency: str = "USD"
    ) -> Optional[Dict]:
        """Specific method for flight searches."""
        url = f"https://www.google.com/travel/flights/search"
        params = {"tfs": tfs, "hl": language, "curr": currency}
        return await self.search_travel(session, url, params)

    async def search_hotels(
        self,
        session: aiohttp.ClientSession,
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

        return await self.search_travel(session, url, params)


# Example usage
async def main():
    api = BrightDataAPI()
    async with aiohttp.ClientSession() as session:
        # Example of parallel requests
        tasks = [
            api.search_hotels(
                session,
                check_in="April 22, 2025",
                check_out="May 1, 2025",
                occupancy="2",
                currency="USD",
                location="New York"
            )
        ]
        results = await asyncio.gather(*tasks)
        print(results)

if __name__ == "__main__":
    asyncio.run(main())
