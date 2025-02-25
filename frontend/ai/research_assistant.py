from langchain.agents import initialize_agent, Tool, AgentType
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.memory import ConversationBufferMemory
from langchain_anthropic import ChatAnthropic
from langchain.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from dotenv import load_dotenv
import json
import os

load_dotenv()


class ResearchAssistant:
    def __init__(self):
        # Initialize the language model
        self.llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
        
        # Initialize embeddings using Ollama
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text"
        )
        
        # Initialize vector store
        self.vector_store = self._initialize_vector_store()
        
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
                name="Country_Info",
                func=self.query_country_data,
                description="Use this to get detailed population and demographic information about countries"
            )
        ]
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
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
        self.system_message = """You are a travel research assistant. Help users learn about destinations, 
        local customs, attractions, travel tips, and other travel-related information. Use the search tool 
        to find up-to-date information when needed. Always be helpful and informative."""
        
    def _initialize_vector_store(self):
        """Initialize and populate the vector store with country data"""
        # Check if vector store already exists
        if os.path.exists("chroma_db"):
            return Chroma(
                persist_directory="chroma_db",
                embedding_function=self.embeddings
            )
        
        # Load country data
        with open('population.json', 'r') as f:
            countries_data = json.load(f)["countries"]
        
        # Prepare documents for vector store
        documents = []
        metadatas = []
        
        for country in countries_data:
            try:
                # Create a detailed text description for each country
                text = f"""
                Country: {country['country']}
                Population (2023): {country['last_year_population']}
                Area: {country['country_area']} km²
                Population Density: {country['country_density (km)']} people per km²
                Growth Rate: {country['growth_rate']}%
                World Population Percentage: {country['population_world_percentage']}%
                Population Rank: {country['country_population_rank']}
                Historical Population:
                1980: {country['population_by_year'][0]['population']}
                2000: {country['population_by_year'][1]['population']}
                2010: {country['population_by_year'][2]['population']}
                2023: {country['population_by_year'][3]['population']}
                """
                
                documents.append(text)
                metadatas.append({
                    "country": country["country"],
                    "population": country["last_year_population"],
                    "rank": country["country_population_rank"]
                })
            except Exception as e:
                print(f"Error processing country {country['country']}: {e}")
        
        # Create and persist vector store
        vector_store = Chroma.from_texts(
            documents,
            self.embeddings,
            metadatas=metadatas,
            persist_directory="chroma_db"
        )
        vector_store.persist()
        return vector_store
    
    def query_country_data(self, query: str) -> str:
        """Query the vector store for country information"""
        results = self.vector_store.similarity_search_with_score(query, k=3)
        
        # Format results
        response = "Here's what I found:\n\n"
        for doc, score in results:
            response += f"Relevance Score: {score:.2f}\n"
            response += doc.page_content + "\n\n"
        
        return response
    
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
                "What are the must-visit attractions in [destination]?",
                "Tell me about the local cuisine in [destination]",
                "What's the best time of year to visit [destination]?",
                "Compare the population of [country1] and [country2]",
            ],
            "column2": [
                "What are the local customs and etiquette in [destination]?",
                "What's the typical weather like in [destination]?",
                "What safety tips should I know for [destination]?",
                "What are the demographic trends in [country]?",
            ]
        } 