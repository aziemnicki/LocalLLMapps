from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()


load_dotenv()

class TravelAssistant:
    def __init__(self, travel_context):
        self.context = travel_context
        self.assistant = self._create_assistant()

    def _create_assistant(self):
        """Create a travel assistant with context about the trip"""
        memory = ConversationBufferMemory()
        
        # Add travel context to memory
        memory.chat_memory.add_ai_message(
            f"""I am your travel assistant. I have access to your travel details:
            - Flight from {self.context['origin']} to {self.context['destination']}
            - Travel dates: {self.context['start_date']} to {self.context['end_date']}
            - Number of travelers: {self.context['occupancy']}
            
            Flight Details: {self.context['flights']}
            Hotel Details: {self.context['hotels']}
            
            Your preferences: {self.context['preferences']}
            
            I can help you:
            - Create a detailed travel itinerary
            - Suggest activities and attractions
            - Provide local transportation advice
            - Answer questions about your flights and hotel
            - Give dining recommendations
            - Offer packing suggestions
            
            How can I assist you with your trip planning?"""
        )
        
        return ConversationChain(
            llm=ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0),
            memory=memory,
            verbose=True
        )

    def get_response(self, prompt):
        """Get response from the assistant"""
        return self.assistant.predict(input=prompt)

    @staticmethod
    def get_suggested_prompts():
        """Return suggested prompts for the user"""
        return {
            "column1": [
                "Create a day-by-day itinerary for my trip",
                "What are the must-see attractions?",
                "Suggest some local restaurants"
            ],
            "column2": [
                "What should I pack for this trip?",
                "How do I get from the airport to my hotel?",
                "What's the weather like during my stay?"
            ]
        } 