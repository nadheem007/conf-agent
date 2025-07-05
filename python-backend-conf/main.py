import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import context and database
from context import AirlineAgentContext
from database import db_client

# Import agents framework
from agents import Agent, Runner

# Import tools
from schedule_agent_tools import (
    get_conference_sessions,
    get_all_speakers, 
    get_all_tracks,
    get_all_rooms,
    search_sessions_by_speaker,
    search_sessions_by_topic,
    get_session_count,
    get_speaker_count
)
from networking_agent_tools import (
    search_businesses,
    get_user_businesses,
    get_business_count,
    get_user_count,
    search_users_by_name,
    get_industry_breakdown
)

# Initialize FastAPI app
app = FastAPI(title="Conference Agent System", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    registration_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    current_agent: str
    messages: list
    events: list
    context: Dict[str, Any]
    agents: list
    guardrails: list
    customer_info: Optional[Dict[str, Any]] = None

# Define agents
schedule_agent = Agent(
    name="Schedule Agent",
    instructions=(
        "You are the Schedule Agent for the Aviation Tech Summit 2025. Your role is to provide detailed "
        "conference schedule information including sessions, speakers, tracks, and rooms. "
        "Use the provided tools to fetch real data from the conference_schedules table. "
        "Always provide accurate, up-to-date information about the conference. "
        "If asked about counts, use the appropriate count tools. "
        "Format your responses clearly and include relevant details like time, location, and speaker information."
    ),
    tools=[
        get_conference_sessions,
        get_all_speakers,
        get_all_tracks, 
        get_all_rooms,
        search_sessions_by_speaker,
        search_sessions_by_topic,
        get_session_count,
        get_speaker_count
    ],
    model="groq/llama3-8b-8192"
)

networking_agent = Agent(
    name="Networking Agent", 
    instructions=(
        "You are the Networking Agent for the Aviation Tech Summit 2025. Your role is to help users "
        "find businesses, manage business profiles, and facilitate networking connections. "
        "Use the provided tools to fetch real data from the users and ib_businesses tables. "
        "Provide helpful information about registered businesses, industry breakdowns, and user connections. "
        "Always use actual data from the database, not made-up information. "
        "Help users discover networking opportunities and business connections."
    ),
    tools=[
        search_businesses,
        get_user_businesses,
        get_business_count,
        get_user_count,
        search_users_by_name,
        get_industry_breakdown
    ],
    model="groq/llama3-8b-8192"
)

triage_agent = Agent(
    name="Triage Agent",
    instructions=(
        "You are the Triage Agent for the Aviation Tech Summit 2025 conference system. "
        "Your role is to understand user queries and provide helpful responses or route them to specialist agents. "
        "Analyze the user's message to determine intent:\n\n"
        "For schedule-related queries (sessions, speakers, tracks, rooms, timing), provide helpful information and suggest they can ask specific questions about:\n"
        "- Conference sessions and schedules\n"
        "- Speaker information and speaker searches\n"
        "- Track details and listings\n"
        "- Room information and locations\n"
        "- Session topics and content\n\n"
        "For networking-related queries (businesses, companies, users, industry), provide helpful information and suggest they can ask about:\n"
        "- Business networking and connections\n"
        "- Company and business information\n"
        "- Industry sector questions\n"
        "- User profiles and business profiles\n\n"
        "For general greetings or unclear queries, provide a helpful welcome message and guide users toward available services. "
        "Always be professional and informative."
    ),
    tools=[],
    model="groq/llama3-8b-8192"
)

# Create context function
async def create_context(registration_id: Optional[str] = None) -> AirlineAgentContext:
    """Create and populate context based on registration ID."""
    context = AirlineAgentContext()
    
    if registration_id:
        try:
            # Try to load user data
            user_data = await db_client.query(
                table_name="users",
                select_fields="id, details",
                filters={"details->>registration_id": registration_id},
                single=True
            )
            
            if user_data:
                context.user_id = user_data["id"]
                context.registration_id = registration_id
                details = user_data.get("details", {})
                context.user_name = details.get("user_name")
                context.email = details.get("email")
                context.is_conference_attendee = True
                context.conference_name = "Aviation Tech Summit 2025"
                logger.info(f"Loaded context for registration_id: {registration_id}")
            else:
                logger.warning(f"No user found for registration_id: {registration_id}")
                
        except Exception as e:
            logger.error(f"Error loading user context: {e}")
    
    return context

# Route determination
def determine_agent(message: str) -> Agent:
    """Determine which agent should handle the message."""
    message_lower = message.lower()
    
    # Schedule-related keywords
    schedule_keywords = [
        'session', 'sessions', 'speaker', 'speakers', 'schedule', 'agenda',
        'track', 'tracks', 'room', 'rooms', 'conference', 'talk', 'talks',
        'presentation', 'presentations', 'topic', 'topics', 'time', 'when',
        'how many sessions', 'how many speakers', 'session count', 'speaker count'
    ]
    
    # Networking-related keywords  
    networking_keywords = [
        'business', 'businesses', 'company', 'companies', 'networking',
        'industry', 'sector', 'user', 'users', 'profile', 'profiles',
        'connect', 'connection', 'directory', 'how many users', 'how many businesses',
        'business count', 'user count', 'industry breakdown'
    ]
    
    # Check for schedule keywords
    if any(keyword in message_lower for keyword in schedule_keywords):
        return schedule_agent
        
    # Check for networking keywords
    if any(keyword in message_lower for keyword in networking_keywords):
        return networking_agent
    
    # Default to triage for unclear queries
    return triage_agent

# Initialize runner
runner = Runner()

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Handle chat requests and route to appropriate agent."""
    try:
        logger.info(f"Received message: {request.message}")
        
        # Create context
        context = await create_context(request.registration_id)
        
        # Determine which agent to use
        selected_agent = determine_agent(request.message)
        logger.info(f"Selected agent: {selected_agent.name}")
        
        # Create input item for the runner
        input_item = {
            "content": request.message,
            "role": "user"
        }
        
        # Run the agent with correct parameters
        response = await runner.run(
            input_item=input_item,
            context=context,
            agent=selected_agent
        )
        
        # Extract response content
        response_content = ""
        if hasattr(response, 'output'):
            response_content = response.output
        elif isinstance(response, dict):
            response_content = response.get('output', str(response))
        else:
            response_content = str(response)
        
        # Get customer info if registration_id provided
        customer_info = None
        if request.registration_id:
            try:
                user_data = await db_client.query(
                    table_name="users",
                    select_fields="id, details",
                    filters={"details->>registration_id": request.registration_id},
                    single=True
                )
                
                if user_data:
                    details = user_data.get("details", {})
                    customer_info = {
                        "customer": {
                            "name": details.get("user_name", f"{details.get('firstName', '')} {details.get('lastName', '')}").strip(),
                            "email": details.get("email"),
                            "registration_id": request.registration_id,
                            "is_conference_attendee": True,
                            "conference_name": "Aviation Tech Summit 2025"
                        },
                        "bookings": []
                    }
            except Exception as e:
                logger.error(f"Error fetching customer info: {e}")
        
        # Format response
        return ChatResponse(
            conversation_id=request.conversation_id or "new_conversation",
            current_agent=selected_agent.name,
            messages=[{
                "content": response_content,
                "agent": selected_agent.name
            }],
            events=[],
            context=context.dict(),
            agents=[
                {
                    "name": "Triage Agent",
                    "description": "Routes queries to appropriate specialists",
                    "handoffs": ["Schedule Agent", "Networking Agent"],
                    "tools": [],
                    "input_guardrails": []
                },
                {
                    "name": "Schedule Agent", 
                    "description": "Conference schedule and speaker information",
                    "handoffs": ["Triage Agent"],
                    "tools": ["get_conference_sessions", "get_all_speakers", "get_all_tracks"],
                    "input_guardrails": []
                },
                {
                    "name": "Networking Agent",
                    "description": "Business networking and connections", 
                    "handoffs": ["Triage Agent"],
                    "tools": ["search_businesses", "get_user_businesses", "get_business_count"],
                    "input_guardrails": []
                }
            ],
            guardrails=[],
            customer_info=customer_info
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Conference Agent System is running"}

# User endpoint
@app.get("/user/{registration_id}")
async def get_user(registration_id: str):
    """Get user information by registration ID."""
    try:
        user_data = await db_client.query(
            table_name="users",
            select_fields="id, details",
            filters={"details->>registration_id": registration_id},
            single=True
        )
        
        if user_data:
            return {
                "user_id": user_data["id"],
                "registration_id": registration_id,
                "status": "found",
                "details": user_data["details"]
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)