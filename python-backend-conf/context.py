from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class CustomerBooking(BaseModel):
    confirmation_number: str
    account_number: str

class UserDetails(BaseModel):
    user_id: str
    registration_id: str
    organization_id: Optional[str] = None

class BusinessDetails(BaseModel):
    companyName: str
    industrySector: str
    location: str
    positionTitle: str
    user_name: str
    email: str

class AirlineAgentContext(BaseModel):
    confirmation_number: Optional[str] = None
    account_number: Optional[str] = None
    registration_id: Optional[str] = None
    user_id: Optional[str] = None
    business_details: Optional[BusinessDetails] = None
    organization_id: Optional[str] = None
    
    # Additional context fields for conference system
    user_name: Optional[str] = None
    email: Optional[str] = None
    is_conference_attendee: bool = False
    conference_name: Optional[str] = None

    class Config:
        extra = "allow"  # Allow extra fields for flexibility