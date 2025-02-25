import streamlit as st
from datetime import datetime, timedelta
from ai.travel_assistant import TravelAssistant
from ai.travel_summary import TravelSummary
from api.api_client import TravelAPIClient
from ai.research_assistant import ResearchAssistant

def format_date(date):
    """Convert datetime to string format expected by the API"""
    return date.strftime("%B %d, %Y")

# Initialize services
api_client = TravelAPIClient()
travel_summary = TravelSummary()

# Initialize session state
if 'search_requirements' not in st.session_state:
    st.session_state.search_requirements = ""
if 'travel_assistant' not in st.session_state:
    st.session_state.travel_assistant = None
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'research_assistant' not in st.session_state:
    st.session_state.research_assistant = ResearchAssistant()
if 'research_messages' not in st.session_state:
    st.session_state.research_messages = []

# Main UI code starts here...
st.title("Travel Search")

# Create main tabs for search form and results
search_tab, results_tab, research_tab = st.tabs(["Search", "Results & Planning", "Research"])

with search_tab:
    # Main search form
    st.header("Search Flights and Hotels")
    
    # Travel requirements
    st.text_area(
        "Travel Requirements",
        key="requirements",
        help="Describe your travel preferences and requirements (budget, preferred airlines, hotel amenities, etc.)",
        placeholder="Example: I'm looking for a business trip, prefer morning flights, need hotel with wifi and gym, budget around $1000 for flight and $200/night for hotel."
    )
    st.session_state.search_requirements = st.session_state.requirements

    # Location details
    col1, col2 = st.columns(2)
    with col1:
        origin = st.text_input("Origin Airport Code (e.g., LAX)")
        destination = st.text_input("Destination Airport Code/City (e.g., NYC)")

    # Date selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Departure Date",
            min_value=datetime.now().date(),
            value=datetime.now().date() + timedelta(days=7)
        )
        occupancy = st.selectbox("Number of Travelers", options=["1", "2", "3", "4"])
    with col2:
        end_date = st.date_input(
            "Return Date",
            min_value=start_date,
            value=start_date + timedelta(days=7)
        )
        currency = st.selectbox("Currency", options=["USD", "EUR", "GBP"])

    if st.button("Search Flights & Hotels"):
        if origin and destination:
            # Switch to results tab after search
            st.session_state.switch_to_results = True
            # Create containers for progress tracking
            flight_progress = st.container()
            hotel_progress = st.container()
            summary_progress = st.container()
            
            try:
                # Start flight search
                flight_response = api_client.search_flights(
                    origin,
                    destination,
                    format_date(start_date),
                    format_date(end_date),
                    st.session_state.search_requirements
                )
                
                # Start hotel search
                hotel_response = api_client.search_hotels(
                    destination,
                    format_date(start_date),
                    format_date(end_date),
                    occupancy,
                    currency
                )
                
                if flight_response.status_code == 200 and hotel_response.status_code == 200:
                    flight_task_id = flight_response.json().get("task_id")
                    hotel_task_id = hotel_response.json().get("task_id")
                    
                    # Poll both tasks in parallel and store results
                    with st.spinner("Searching for the best travel options..."):
                        flight_results = api_client.poll_task_status(flight_task_id, "flight", flight_progress)
                        hotel_results = api_client.poll_task_status(hotel_task_id, "hotel", hotel_progress)
                        
                        if flight_results and hotel_results:
                            summary_progress.text("Generating travel recommendations...")
                            summary = travel_summary.get_summary(
                                flight_results,
                                hotel_results,
                                st.session_state.search_requirements,
                                destination=destination,
                                origin=origin,
                                check_in=start_date,
                                check_out=end_date,
                                occupancy=occupancy,
                            )
                            summary_progress.markdown("### Travel Recommendations")
                            summary_progress.write(summary)
                            st.session_state.summary = summary
                            
                            # Store travel context and initialize assistant
                            st.session_state.travel_context = {
                                'origin': origin,
                                'destination': destination,
                                'start_date': format_date(start_date),
                                'end_date': format_date(end_date),
                                'occupancy': occupancy,
                                'flights': flight_results,
                                'hotels': hotel_results,
                                'preferences': st.session_state.search_requirements
                            }
                            st.session_state.travel_assistant = TravelAssistant(st.session_state.travel_context)
                        else:
                            st.error("Could not complete the search. Please try again.")
                else:
                    st.error("Failed to start the search. Please try again.")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please enter both origin and destination")

with results_tab:
    if st.session_state.travel_assistant:

        with st.expander("Travel Summary", expanded=True):
            st.markdown("### Flight and Hotel Details")
            if 'summary' in st.session_state:
                st.markdown(st.session_state.summary)
            else:
                st.info("No travel summary available yet.")
            
        # Second row: Chat Interface
        with st.expander("Travel Planning Assistant", expanded=True):
            # Chat interface
            chat_container = st.container()
            with chat_container:
                # Left side: Chat history
                chat_history = st.container()
                with chat_history:
                    for message in st.session_state.chat_messages:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
                
                # Right side: Suggested prompts (only show if no messages)
                if not st.session_state.chat_messages:
                    st.markdown("### Suggested Questions:")
                    suggested_prompts = TravelAssistant.get_suggested_prompts()
                    cols = st.columns(2)
                    with cols[0]:
                        for prompt in suggested_prompts["column1"]:
                            st.markdown(f"- {prompt}")
                    with cols[1]:
                        for prompt in suggested_prompts["column2"]:
                            st.markdown(f"- {prompt}")
                
                # Chat input at the bottom
                st.markdown("---")
                if prompt := st.chat_input("Ask me anything about your trip..."):
                    # Add user message to chat history
                    st.session_state.chat_messages.append({"role": "user", "content": prompt})
                    with chat_container.chat_message("user"):
                        st.markdown(prompt)
                    
                    # Get AI response
                    with chat_container.chat_message("assistant"):
                        message_placeholder = st.empty()
                        response = st.session_state.travel_assistant.get_response(prompt)
                        message_placeholder.markdown(response)
                    
                    # Add AI response to chat history
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
    else:
        st.info("Please complete a search to see results and start planning your trip.")

with research_tab:
    st.header("Travel Research Assistant")
    st.markdown("""
    Use this research assistant to learn more about your destination, local customs, 
    attractions, and travel tips. This assistant can search the internet for up-to-date information.
    """)
    
    # Chat interface
    research_container = st.container()
    with research_container:
        # Display chat history
        for message in st.session_state.research_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Show suggested prompts if no messages
        if not st.session_state.research_messages:
            st.markdown("### Suggested Research Questions:")
            suggested_prompts = ResearchAssistant.get_suggested_prompts()
            cols = st.columns(2)
            with cols[0]:
                for prompt in suggested_prompts["column1"]:
                    st.markdown(f"- {prompt}")
            with cols[1]:
                for prompt in suggested_prompts["column2"]:
                    st.markdown(f"- {prompt}")
        
        # Chat input
        st.markdown("---")
        if prompt := st.chat_input("Ask about your destination..."):
            # Add user message to chat history
            st.session_state.research_messages.append({"role": "user", "content": prompt})
            with research_container.chat_message("user"):
                st.markdown(prompt)
            
            # Get AI response
            with research_container.chat_message("assistant"):
                message_placeholder = st.empty()
                response = st.session_state.research_assistant.get_response(prompt)
                message_placeholder.markdown(response)
            
            # Add AI response to chat history
            st.session_state.research_messages.append({"role": "assistant", "content": response})

# Automatically switch to results tab after search
if hasattr(st.session_state, 'switch_to_results') and st.session_state.switch_to_results:
    st.session_state.switch_to_results = False
    results_tab.active = True
