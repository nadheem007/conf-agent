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
        
        # Try different runner call patterns based on the agents framework
        try:
            # Pattern 1: Simple message and context
            response = await runner.run(request.message, context=context)
        except Exception as e1:
            logger.warning(f"Pattern 1 failed: {e1}")
            try:
                # Pattern 2: With agent parameter
                response = await runner.run(request.message, agent=selected_agent, context=context)
            except Exception as e2:
                logger.warning(f"Pattern 2 failed: {e2}")
                try:
                    # Pattern 3: Direct agent run
                    response = await selected_agent.run(request.message, context=context)
                except Exception as e3:
                    logger.warning(f"Pattern 3 failed: {e3}")
                    # Pattern 4: Manual response for triage
                    if selected_agent == triage_agent:
                        response = await handle_triage_manually(request.message, context)
                    else:
                        # Try to call agent tools directly
                        response = await handle_agent_manually(selected_agent, request.message, context)
        
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

async def handle_triage_manually(message: str, context: AirlineAgentContext) -> str:
    """Handle triage agent responses manually."""
    message_lower = message.lower()
    
    # Greeting responses
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'welcome', 'start']):
        return (
            f"Welcome to the Aviation Tech Summit 2025! 🛩️\n\n"
            f"I'm here to help you with:\n\n"
            f"**📅 Conference Information:**\n"
            f"• Session schedules and timings\n"
            f"• Speaker information and bios\n"
            f"• Track details and topics\n"
            f"• Room locations and layouts\n\n"
            f"**🤝 Business Networking:**\n"
            f"• Find businesses and companies\n"
            f"• Industry sector information\n"
            f"• User profiles and connections\n"
            f"• Networking opportunities\n\n"
            f"What would you like to know about the conference?"
        )
    
    # Schedule-related guidance
    elif any(word in message_lower for word in ['session', 'speaker', 'schedule', 'track', 'room']):
        return (
            f"I can help you with conference schedule information! You can ask me about:\n\n"
            f"• **Sessions:** \"Show me all sessions\" or \"Sessions by [speaker name]\"\n"
            f"• **Speakers:** \"List all speakers\" or \"How many speakers?\"\n"
            f"• **Tracks:** \"What tracks are available?\" or \"Show me track information\"\n"
            f"• **Rooms:** \"List conference rooms\" or \"Where is [session] located?\"\n"
            f"• **Topics:** \"Sessions about [topic]\" or \"Find sessions on AI\"\n\n"
            f"What specific information would you like?"
        )
    
    # Networking-related guidance
    elif any(word in message_lower for word in ['business', 'company', 'networking', 'industry', 'user']):
        return (
            f"I can help you with business networking and connections! You can ask me about:\n\n"
            f"• **Businesses:** \"Show me businesses\" or \"Companies in [industry]\"\n"
            f"• **Industries:** \"Industry breakdown\" or \"Fintech companies\"\n"
            f"• **Users:** \"How many users?\" or \"Find user [name]\"\n"
            f"• **Networking:** \"Business directory\" or \"Connect with [industry]\"\n\n"
            f"What networking information are you looking for?"
        )
    
    # Default response
    else:
        return (
            f"I'm here to help you with the Aviation Tech Summit 2025! 🛩️\n\n"
            f"You can ask me about:\n"
            f"• **Conference schedules** - sessions, speakers, tracks, rooms\n"
            f"• **Business networking** - companies, industries, user connections\n\n"
            f"Try asking something like:\n"
            f"• \"Show me all sessions\"\n"
            f"• \"List all speakers\"\n"
            f"• \"Find businesses in fintech\"\n"
            f"• \"How many users are registered?\"\n\n"
            f"What would you like to know?"
        )

async def handle_agent_manually(agent: Agent, message: str, context: AirlineAgentContext) -> str:
    """Handle agent responses manually by calling tools directly."""
    message_lower = message.lower()
    
    if agent == schedule_agent:
        # Handle schedule-related queries
        if 'all sessions' in message_lower or 'list sessions' in message_lower:
            return await get_conference_sessions()
        elif 'all speakers' in message_lower or 'list speakers' in message_lower:
            return await get_all_speakers()
        elif 'all tracks' in message_lower or 'list tracks' in message_lower:
            return await get_all_tracks()
        elif 'all rooms' in message_lower or 'list rooms' in message_lower:
            return await get_all_rooms()
        elif 'how many sessions' in message_lower or 'session count' in message_lower:
            return await get_session_count()
        elif 'how many speakers' in message_lower or 'speaker count' in message_lower:
            return await get_speaker_count()
        elif 'sessions by' in message_lower or 'speaker' in message_lower:
            # Extract speaker name
            words = message.split()
            speaker_name = " ".join(words[2:]) if len(words) > 2 else ""
            if speaker_name:
                return await search_sessions_by_speaker(speaker_name)
        elif 'topic' in message_lower or 'about' in message_lower:
            # Extract topic
            words = message.split()
            topic = " ".join(words[1:]) if len(words) > 1 else ""
            if topic:
                return await search_sessions_by_topic(topic)
        else:
            return await get_conference_sessions()
    
    elif agent == networking_agent:
        # Handle networking-related queries
        if 'all businesses' in message_lower or 'list businesses' in message_lower:
            return await search_businesses()
        elif 'how many businesses' in message_lower or 'business count' in message_lower:
            return await get_business_count()
        elif 'how many users' in message_lower or 'user count' in message_lower:
            return await get_user_count()
        elif 'industry breakdown' in message_lower:
            return await get_industry_breakdown()
        elif 'find user' in message_lower or 'search user' in message_lower:
            # Extract user name
            words = message.split()
            user_name = " ".join(words[2:]) if len(words) > 2 else ""
            if user_name:
                return await search_users_by_name(user_name)
        elif any(industry in message_lower for industry in ['fintech', 'tech', 'healthcare', 'finance']):
            # Extract industry
            for industry in ['fintech', 'tech', 'healthcare', 'finance']:
                if industry in message_lower:
                    return await search_businesses(industry_sector=industry)
        else:
            return await search_businesses()
    
    return f"I understand you're asking about {message}, but I need more specific information to help you."

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