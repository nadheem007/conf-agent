from typing import Optional
import logging
from context import AirlineAgentContext
from database import db_client
from agents import function_tool

logger = logging.getLogger(__name__)

@function_tool(
    name_override="search_businesses",
    description_override="Search for businesses by industry sector, location, company name, or other criteria.",
    strict_json_schema=False
)
async def search_businesses(
    industry_sector: Optional[str] = None,
    location: Optional[str] = None,
    company_name: Optional[str] = None,
    sub_sector: Optional[str] = None,
    limit: Optional[int] = 10
) -> str:
    """Search for businesses with various filters."""
    try:
        # Get all businesses with user information
        businesses = await db_client.query(
            table_name="ib_businesses",
            select_fields="*, users!inner(*)"
        )
        
        if not businesses:
            return "No businesses found in the database."
        
        # Apply filters
        filtered_businesses = businesses
        
        if industry_sector:
            filtered_businesses = [
                b for b in filtered_businesses
                if industry_sector.lower() in b.get("details", {}).get("industrySector", "").lower()
            ]
        
        if location:
            filtered_businesses = [
                b for b in filtered_businesses
                if location.lower() in b.get("details", {}).get("location", "").lower()
            ]
        
        if company_name:
            filtered_businesses = [
                b for b in filtered_businesses
                if company_name.lower() in b.get("details", {}).get("companyName", "").lower()
            ]
        
        if sub_sector:
            filtered_businesses = [
                b for b in filtered_businesses
                if sub_sector.lower() in b.get("details", {}).get("subSector", "").lower()
            ]
        
        # Apply limit
        if limit:
            filtered_businesses = filtered_businesses[:limit]
        
        if not filtered_businesses:
            return "No businesses found matching the specified criteria."
        
        result = f"**Found {len(filtered_businesses)} business(es):**\n\n"
        for i, business in enumerate(filtered_businesses, 1):
            details = business.get("details", {})
            user_info = business.get("users", {})
            
            result += (
                f"{i}. **{details.get('companyName', 'Unknown Company')}**\n"
                f"   Industry: {details.get('industrySector', 'Unknown')}\n"
                f"   Sub-sector: {details.get('subSector', 'N/A')}\n"
                f"   Location: {details.get('location', 'Unknown')}\n"
                f"   Contact: {user_info.get('user_name', 'Unknown')} ({user_info.get('email', 'N/A')})\n"
                f"   Position: {details.get('positionTitle', 'N/A')}\n\n"
            )
        
        logger.info(f"✅ Found {len(filtered_businesses)} businesses matching criteria")
        return result
    except Exception as e:
        logger.error(f"❌ Error searching businesses: {e}", exc_info=True)
        return f"Error searching businesses: {str(e)}"

@function_tool(
    name_override="get_user_businesses",
    description_override="Get businesses associated with a specific user.",
    strict_json_schema=False
)
async def get_user_businesses(user_id: str) -> str:
    """Get businesses for a specific user."""
    try:
        businesses = await db_client.query(
            table_name="ib_businesses",
            filters={"user_id": user_id}
        )
        
        if not businesses:
            return f"No businesses found for user ID: {user_id}"
        
        result = f"**Businesses for User {user_id} ({len(businesses)} business(es)):**\n\n"
        for i, business in enumerate(businesses, 1):
            details = business.get("details", {})
            result += (
                f"{i}. **{details.get('companyName', 'Unknown Company')}**\n"
                f"   Industry: {details.get('industrySector', 'Unknown')}\n"
                f"   Location: {details.get('location', 'Unknown')}\n"
                f"   Position: {details.get('positionTitle', 'N/A')}\n\n"
            )
        
        logger.info(f"✅ Found {len(businesses)} businesses for user: {user_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching user businesses: {e}", exc_info=True)
        return f"Error fetching user businesses: {str(e)}"

@function_tool(
    name_override="get_business_count",
    description_override="Get the total number of registered businesses.",
    strict_json_schema=False
)
async def get_business_count() -> str:
    """Get the total number of registered businesses."""
    try:
        businesses = await db_client.query(
            table_name="ib_businesses",
            select_fields="id"
        )
        
        count = len(businesses) if businesses else 0
        result = f"**Total Registered Businesses:** {count}"
        
        if count > 0:
            # Get additional stats
            full_businesses = await db_client.query(
                table_name="ib_businesses",
                select_fields="details"
            )
            
            industries = {}
            locations = {}
            
            for business in full_businesses:
                details = business.get("details", {})
                industry = details.get("industrySector", "Unknown")
                location = details.get("location", "Unknown")
                
                industries[industry] = industries.get(industry, 0) + 1
                locations[location] = locations.get(location, 0) + 1
            
            result += f"\n**Top Industries:**"
            for industry, count in sorted(industries.items(), key=lambda x: x[1], reverse=True)[:5]:
                result += f"\n- {industry}: {count}"
            
            result += f"\n**Top Locations:**"
            for location, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]:
                result += f"\n- {location}: {count}"
        
        logger.info(f"✅ Retrieved business count: {count}")
        return result
    except Exception as e:
        logger.error(f"❌ Error getting business count: {e}", exc_info=True)
        return f"Error getting business count: {str(e)}"

@function_tool(
    name_override="get_user_count",
    description_override="Get the total number of registered users.",
    strict_json_schema=False
)
async def get_user_count() -> str:
    """Get the total number of registered users."""
    try:
        users = await db_client.query(
            table_name="users",
            select_fields="id"
        )
        
        count = len(users) if users else 0
        result = f"**Total Registered Users:** {count}"
        
        logger.info(f"✅ Retrieved user count: {count}")
        return result
    except Exception as e:
        logger.error(f"❌ Error getting user count: {e}", exc_info=True)
        return f"Error getting user count: {str(e)}"

@function_tool(
    name_override="search_users_by_name",
    description_override="Search for users by name or email.",
    strict_json_schema=False
)
async def search_users_by_name(search_term: str, limit: Optional[int] = 10) -> str:
    """Search for users by name or email."""
    try:
        users = await db_client.query(
            table_name="users",
            select_fields="id, details"
        )
        
        if not users:
            return "No users found in the database."
        
        # Filter users based on search term
        matching_users = []
        for user in users:
            details = user.get("details", {})
            user_name = details.get("user_name", "")
            email = details.get("email", "")
            first_name = details.get("firstName", "")
            last_name = details.get("lastName", "")
            
            if (search_term.lower() in user_name.lower() or
                search_term.lower() in email.lower() or
                search_term.lower() in first_name.lower() or
                search_term.lower() in last_name.lower()):
                matching_users.append(user)
        
        if limit:
            matching_users = matching_users[:limit]
        
        if not matching_users:
            return f"No users found matching search term: {search_term}"
        
        result = f"**Found {len(matching_users)} user(s) matching '{search_term}':**\n\n"
        for i, user in enumerate(matching_users, 1):
            details = user.get("details", {})
            name = details.get("user_name") or f"{details.get('firstName', '')} {details.get('lastName', '')}".strip()
            result += (
                f"{i}. **{name or 'Unknown Name'}**\n"
                f"   Email: {details.get('email', 'N/A')}\n"
                f"   Registration ID: {details.get('registration_id', 'N/A')}\n\n"
            )
        
        logger.info(f"✅ Found {len(matching_users)} users matching: {search_term}")
        return result
    except Exception as e:
        logger.error(f"❌ Error searching users: {e}", exc_info=True)
        return f"Error searching users: {str(e)}"

@function_tool(
    name_override="get_industry_breakdown",
    description_override="Get a breakdown of businesses by industry sector.",
    strict_json_schema=False
)
async def get_industry_breakdown() -> str:
    """Get a breakdown of businesses by industry sector."""
    try:
        businesses = await db_client.query(
            table_name="ib_businesses",
            select_fields="details"
        )
        
        if not businesses:
            return "No businesses found in the database."
        
        industry_counts = {}
        for business in businesses:
            details = business.get("details", {})
            industry = details.get("industrySector", "Unknown")
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
        
        if not industry_counts:
            return "No industry data found."
        
        result = f"**Industry Breakdown ({len(businesses)} total businesses):**\n\n"
        
        # Sort by count (descending)
        sorted_industries = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)
        
        for industry, count in sorted_industries:
            percentage = (count / len(businesses)) * 100
            result += f"• **{industry}:** {count} businesses ({percentage:.1f}%)\n"
        
        logger.info(f"✅ Retrieved industry breakdown for {len(businesses)} businesses")
        return result
    except Exception as e:
        logger.error(f"❌ Error getting industry breakdown: {e}", exc_info=True)
        return f"Error getting industry breakdown: {str(e)}"