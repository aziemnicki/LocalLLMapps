import requests
import time
from typing import List, Dict, Optional, Tuple, Union
from dotenv import load_dotenv
import os

load_dotenv()


class BrightDataAPI:
    def __init__(self):
        """
        Initialize the BrightData API client.
        
        Args:
            api_key (str): Your BrightData API key
            dataset_id (str): The dataset ID to use for queries
        """
        self.api_key = os.getenv("BRIGHTDATA_API_KEY")
        self.dataset_id = "gd_lnsxoxzi1omrwnka5r"
        self.base_url = "https://api.brightdata.com/datasets/v3"
        
    def search_news(
        self,
        keywords: List[Dict[str, str]],
        include_errors: bool = True
    ) -> Dict:
        url = f"{self.base_url}/trigger"
        
        # Prepare the input data
        input_data = [
            {
                "url": "https://news.google.com/",
                "keyword": item["keyword"],
                "country": item["country"],
                "language": item.get("language", "")
            }
            for item in keywords
        ]
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Make the API request
        params = {"dataset_id": self.dataset_id, "include_errors": str(include_errors).lower(), "limit_multiple_results":5}
        response = requests.post(url, headers=headers, json=input_data, params=params)
        
        # Raise an exception for bad responses
        response.raise_for_status()
        
        return response.json()

    def get_progress(self, snapshot_id: str) -> Dict:
        url = f"{self.base_url}/progress/{snapshot_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def get_snapshot_data(self, snapshot_id: str, format: str = "json") -> Dict:
        url = f"{self.base_url}/snapshot/{snapshot_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"format": format}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def wait_for_results(
        self,
        snapshot_id: str,
        polling_interval: float = 5.0,
        timeout: Optional[float] = 100,
        format: str = "json"
    ) -> Tuple[str, Dict]:
        start_time = time.time()
        
        while True:
            # Check if timeout has been reached
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Timeout reached after {timeout} seconds")
            
            # Get current progress
            progress = self.get_progress(snapshot_id)
            status = progress.get("status")
            
            if status == "ready":
                # Results are ready, fetch and return them
                data = self.get_snapshot_data(snapshot_id, format=format)
                return status, data
            elif status == "failed":
                # Collection failed
                return status, progress
            
            # Wait before next polling attempt
            time.sleep(polling_interval)
    
    def collect_news(
        self,
        keywords: List[Dict[str, str]],
        polling_interval: float = 5.0,
        timeout: Optional[float] = 300.0,
        format: str = "json",
        include_errors: bool = True
    ) -> Union[Dict, Tuple[str, str]]:
        try:
            # Step 1: Trigger the search
            search_response = self.search_news(
                keywords=keywords,
                include_errors=include_errors
            )
            
            snapshot_id = search_response["snapshot_id"]
            
            # Step 2: Wait for and collect results
            status, data = self.wait_for_results(
                snapshot_id=snapshot_id,
                polling_interval=polling_interval,
                timeout=timeout,
                format=format
            )
            
            if status == "ready":
                return data
            else:
                return status, f"Collection failed: {data}"
                
        except TimeoutError as e:
            return "timeout", str(e)
        except Exception as e:
            return "error", str(e)

if __name__ == "__main__":
    # Initialize the client
    bright_data = BrightDataAPI()


