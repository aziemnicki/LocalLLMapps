flight_scrape_task = lambda preferences: f"""Follow these steps in order:
    1. Find and click the 'Search' button on the page

    2. On the departing flights page:
        - Identify the top departing flight based on user preferences {preferences}
        - For each departing flight:
            a. Click on the flight
            b. On the returning flights page, identify the best (lowest price) return flight
            c. Store both the departing and return flight details
            d. make sure to store the price as well a s currency

    3. Collect all important flight details and store them in a structured json format
    """