import streamlit as st
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import asyncio
from flights.google_flight_scraper import get_flight_url, scrape_flights
from flights.flights import BrightDataAPI
from config.models import model

def search_travel_options(origin, destination, check_in, check_out, num_travelers, additional_requirements):
    """Search for both flights and hotels using threads"""
    # Initialize API
    bright_api = BrightDataAPI()
    
    def search_flights():
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async functions in this thread's event loop
            flight_url = loop.run_until_complete(get_flight_url(
                origin=origin,
                destination=destination,
                start_date=check_in.strftime("%B %d, %Y"),
                end_date=check_out.strftime("%B %d, %Y")
            ))
            
            if flight_url:
                return loop.run_until_complete(scrape_flights(flight_url, additional_requirements))
            return []
        except Exception as e:
            st.error(f"Error searching flights: {str(e)}")
            return []
        finally:
            loop.close()
    
    def search_hotels():
        try:
            return bright_api.search_hotels_sync(
                location=destination,
                check_in=check_in.strftime("%B %d, %Y"),
                check_out=check_out.strftime("%B %d, %Y"),
                occupancy=str(num_travelers),
                currency="USD"
            )
        except Exception as e:
            st.error(f"Error searching hotels: {str(e)}")
            return []
    
    # Create placeholders for loading indicators
    flight_status = st.empty()
    hotel_status = st.empty()
    
    flight_status.text("🔎 Searching for flights...")
    hotel_status.text("🔎 Searching for hotels...")
    
    # Run searches in parallel using threads
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_flights = executor.submit(search_flights)
        future_hotels = executor.submit(search_hotels)
        
        # Wait for both tasks to complete
        flights = future_flights.result()
        hotels = future_hotels.result()
    
    # Update status indicators
    flight_status.text("✅ Flight search completed")
    hotel_status.text("✅ Hotel search completed")
    
    return flights, hotels, additional_requirements

def main():
    st.title("Travel Planning Assistant")
    
    # Sidebar for user inputs
    with st.sidebar:
        st.header("Travel Requirements")
        
        origin = st.text_input("Origin City/Airport", "NYC")
        destination = st.text_input("Destination City", "London")
        
        col1, col2 = st.columns(2)
        with col1:
            check_in = st.date_input(
                "Check-in Date",
                min_value=datetime.now().date(),
                value=datetime.now().date() + timedelta(days=30)
            )
        with col2:
            check_out = st.date_input(
                "Check-out Date",
                min_value=check_in,
                value=check_in + timedelta(days=7)
            )
            
        num_travelers = st.number_input("Number of Travelers", min_value=1, value=2)
        
        # Add text area for additional requirements
        additional_requirements = st.text_area(
            "Additional Requirements",
            placeholder="Enter any additional requirements (e.g., 'I prefer morning flights', 'Need a hotel with a pool', 'Budget under $1000')",
            height=150
        )
        
        search_button = st.button("Search Travel Options")
    
    # Main content area
    if search_button:
        with st.spinner("Searching for the best travel options..."):
            # Create a progress bar
            progress_bar = st.progress(0)
            
            # Show searching status
            status = st.empty()
            status.text("Initiating search...")
            progress_bar.progress(20)
            
            # Run the search
            flights, hotels, requirements = search_travel_options(
                origin, destination, check_in, check_out, num_travelers, additional_requirements
            )
            
            progress_bar.progress(60)
            status.text("Processing results...")
            
            # Display results using the model
            st.header("Travel Recommendations")
            
            response = model.invoke(
                f"""Summarize the following flight and hotels and give me a nicely formatted output: 
                Hotels: {hotels} ||| Flights: {flights}. 
                
                Then make a recommendation for the best hotel and flight based on this: {additional_requirements}
                
                Note: the price of the flight is maximum of the two prices listed, NOT the combined price.
                """
            )
            st.write(response.content)
            
            progress_bar.progress(100)
            status.text("Search completed!")
            
            # Clear the progress indicators after completion
            status.empty()
            progress_bar.empty()

if __name__ == "__main__":
    main() 