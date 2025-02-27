from langchain.agents import initialize_agent, Tool, AgentType
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.memory import ConversationBufferMemory
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from ai.context import generate_travel_context_memory
from dotenv import load_dotenv
from ai.models import model
import json
import os

load_dotenv()


class ResearchAssistant:
    embeddings = OllamaEmbeddings(
            model="nomic-embed-text"
        )
    vector_store = None
    
    def __init__(self, context):
        # Initialize the language model
        self.context = context
        self.llm = model
        
        # Initialize the search tool
        search = DuckDuckGoSearchRun()
        
        # Define tools
        self.tools = [
            Tool(
                name="Search",
                func=search.run,
                description="Useful for searching information about travel destinations, attractions, local customs, and travel tips"
            ),
            Tool(
                name="Restaurant_Info",
                func=self.query_restaurant_data,
                description="Use this to get information about restaurants in Thailand including location, ratings, opening hours, and services"
            )
        ]
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.memory.chat_memory.add_ai_message(
            generate_travel_context_memory(self.context)
        )
        
        # Initialize the agent
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=True,
            memory=self.memory,
            handle_parsing_errors=True
        )
        
        # Set initial system message
        self.system_message = """You are a travel research assistant specializing in Thailand. 
        Help users learn about local restaurants, attractions, travel tips, and other travel-related information. 
        Use the Restaurant_Info tool to find specific details about restaurants in Thailand, and the search tool 
        for general travel information. Always be helpful and informative."""
    
    @classmethod  
    def _initialize_vector_store(cls):
        """Initialize and populate the vector store with restaurant data"""
        # Add debug prints
        print("Starting vector store initialization...")
        
        # Check if vector store already exists
        if os.path.exists("restaurant_db"):
            print("Found existing restaurant_db, loading...")
            return Chroma(
                persist_directory="restaurant_db",
                embedding_function=cls.embeddings
            )
        
        # Load restaurant data
        try:
            # Update the path to be relative to the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, '..', 'data', 'thailand_restaurants.json')
            print(f"Loading restaurant data from: {data_path}")
            
            with open(data_path, 'r', encoding='utf-8') as f:
                restaurants_data = json.load(f)
                print(f"Successfully loaded {len(restaurants_data)} restaurants")
        except FileNotFoundError as e:
            print(f"Error: Could not find restaurant data file: {e}")
            restaurants_data = []
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in restaurant data: {e}")
            restaurants_data = []
        except Exception as e:
            print(f"Unexpected error loading restaurant data: {e}")
            restaurants_data = []

        # Debug print for vector store creation
        print(f"Creating vector store with {len(restaurants_data)} restaurants")
        
        # Prepare documents for vector store
        documents = []
        metadatas = []
        
        for restaurant in restaurants_data:
            # try:
            # Format opening hours
            open_hours = ""
            if restaurant.get('open_hours'):
                for day, hours in restaurant['open_hours'].items():
                    open_hours += f"{day}: {hours}\n"
            
            # Create a detailed text description for each restaurant
            text = f"""
            Name: {restaurant.get('name', 'N/A')}
            Category: {restaurant.get('category', 'N/A')}
            Address: {restaurant.get('address', 'N/A')}
            Rating: {restaurant.get('rating', 'N/A')} ({restaurant.get('reviews_count', 0)} reviews)
            Opening Hours:
            {open_hours}
            Current Status: {restaurant.get('open_hours_updated', 'N/A')}
            Phone: {restaurant.get('phone_number', 'N/A')}
            Website: {restaurant.get('open_website', 'N/A')}
            Price Range: {restaurant.get('price_range', 'N/A')}
            Services: {str(restaurant.get('services_provided', 'N/A'))}
            Location: Lat {restaurant.get('lat', 'N/A')}, Lon {restaurant.get('lon', 'N/A')}
            """
            
            documents.append(text)
            metadatas.append({
                "name": restaurant.get('name'),
                "category": restaurant.get('category'),
                "rating": restaurant.get('rating'),
                "reviews_count": restaurant.get('reviews_count'),
                "price_range": restaurant.get('price_range')
            })
            # except Exception as e:
            #     print(f"Error processing restaurant {restaurant.get('name', 'unknown')}: {e}")
        
        # Create and persist vector store
        if documents:
            cls.vector_store = Chroma.from_texts(
                documents,
                cls.embeddings,
                metadatas=metadatas,
                persist_directory="restaurant_db"
            )
            cls.vector_store.persist()
        else:
            # Create empty vector store if no documents
            return Chroma(
                persist_directory="restaurant_db",
                embedding_function=cls.embeddings
            )
    
    def query_restaurant_data(self, query: str) -> str:
        """Query the vector store for restaurant information"""
        print(f"Querying restaurants with: {query}")
        try:
            # Try a more lenient search
            results = self.vector_store.similarity_search(
                query,
                k=10  # Increase number of results
            )
            
            print(f"Found {len(results)} results")
            
            if not results:
                return "I couldn't find any restaurants matching your query."
            
            # Format results
            response = "Here are the restaurants I found:\n\n"
            for doc in results:
                # Add the restaurant information directly without score filtering
                content = doc.page_content.strip()
                response += f"{content}\n\n---\n\n"
            
            return response.strip()
            
        except Exception as e:
            print(f"Error in restaurant query: {str(e)}")
            return f"Error searching restaurants: {str(e)}"
    
    def get_response(self, user_input):
        try:
            response = self.agent.run(input=user_input)
            return response
        except Exception as e:
            return f"I encountered an error while researching. Please try rephrasing your question. Error: {str(e)}"
    
    @staticmethod
    def get_suggested_prompts():
        return {
            "column1": [
                "Find Thai restaurants with high ratings in Bangkok",
                "What are the best seafood restaurants in Phuket?",
                "Show me restaurants open late night in Chiang Mai",
                "Find restaurants with outdoor seating in Thailand",
            ],
            "column2": [
                "What are the most popular local restaurants in Thailand?",
                "Find Thai restaurants that serve vegetarian food",
                "What are the best-rated street food spots?",
                "Show me restaurants with traditional Thai cuisine",
            ]
        } 