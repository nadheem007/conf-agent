import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
from typing import Optional, List, Dict, Any

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize the Supabase client
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")

# The actual Supabase client instance
_raw_supabase_client: Client = create_client(url, key)

class CustomDatabaseClient:
    def __init__(self, client: Client):
        self._client = client
    
    def table(self, table_name: str):
        """Expose the raw client's table method for direct access."""
        return self._client.table(table_name)

    async def query(
        self, 
        table_name: str, 
        select_fields: str = "*", 
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[Dict[str, Any]]] = None, 
        limit: Optional[int] = None, 
        single: bool = False
    ):
        """
        Query database with filters and options.
        
        Args:
            table_name: The name of the table to query
            select_fields: Fields to select (e.g., "id, name")
            filters: Dictionary of filters (e.g., {"column": "value"})
            order_by: List of dictionaries for ordering (e.g., [{"column": "name", "ascending": True}])
            limit: Maximum number of records to return
            single: If true, returns the first record or None
        """
        try:
            query = self._client.table(table_name).select(select_fields)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if "->" in key or "->>" in key:
                        # Handle JSONB filtering
                        query = query.filter(key, "eq", value)
                    else:
                        query = query.eq(key, value)
            
            # Apply ordering
            if order_by:
                for order in order_by:
                    column = order.get("column")
                    ascending = order.get("ascending", True)
                    query = query.order(column, desc=not ascending)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Execute query
            response = query.execute()
            
            if single:
                return response.data[0] if response.data else None
            return response.data
            
        except Exception as e:
            logger.error(f"Database query error: {e}", exc_info=True)
            raise e

# Create the database client instance
db_client: CustomDatabaseClient = CustomDatabaseClient(_raw_supabase_client)