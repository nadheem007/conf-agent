from typing import Optional
import logging
from database import db_client
from agents import function_tool

logger = logging.getLogger(__name__)

@function_tool(
    name_override="get_conference_sessions",
    description_override="Fetch conference sessions with optional filtering by speaker, topic, room, track, or date."
)
async def get_conference_sessions(
    speaker_name: Optional[str] = None,
    topic: Optional[str] = None,
    conference_room_name: Optional[str] = None,
    track_name: Optional[str] = None,
    conference_date: Optional[str] = None,
    limit: Optional[int] = 10
) -> str:
    """Fetch conference sessions with filtering options."""
    try:
        filters = {}
        if speaker_name:
            filters["speaker_name"] = speaker_name
        if topic:
            filters["topic"] = topic
        if conference_room_name:
            filters["conference_room_name"] = conference_room_name
        if track_name:
            filters["track_name"] = track_name
        if conference_date:
            filters["conference_date"] = conference_date
        
        sessions = await db_client.query(
            table_name="conference_schedules",
            filters=filters,
            order_by=[{"column": "conference_date"}, {"column": "start_time"}],
            limit=limit
        )
        
        if not sessions:
            return "No conference sessions found matching the specified criteria."
        
        result = f"Found {len(sessions)} conference session(s):\n\n"
        for i, session in enumerate(sessions, 1):
            result += (
                f"{i}. **{session.get('topic', 'Unknown Topic')}**\n"
                f"   Speaker: {session.get('speaker_name', 'TBA')}\n"
                f"   Date: {session.get('conference_date', 'TBA')}\n"
                f"   Time: {session.get('start_time', 'TBA')} - {session.get('end_time', 'TBA')}\n"
                f"   Room: {session.get('conference_room_name', 'TBA')}\n"
                f"   Track: {session.get('track_name', 'TBA')}\n\n"
            )
        
        logger.info(f"✅ Retrieved {len(sessions)} conference sessions")
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching conference sessions: {e}", exc_info=True)
        return f"Error fetching conference sessions: {str(e)}"

@function_tool(
    name_override="get_all_speakers",
    description_override="Get all unique speakers from the conference."
)
async def get_all_speakers() -> str:
    """Get all unique speakers from the conference."""
    try:
        speakers_data = await db_client.query(
            table_name="conference_schedules",
            select_fields="speaker_name"
        )
        
        if not speakers_data:
            return "No speakers found in the conference database."
        
        unique_speakers = sorted(set(
            item["speaker_name"] for item in speakers_data 
            if item.get("speaker_name") and item["speaker_name"].strip()
        ))
        
        if not unique_speakers:
            return "No valid speaker names found."
        
        result = f"**Conference Speakers ({len(unique_speakers)} total):**\n\n"
        for i, speaker in enumerate(unique_speakers, 1):
            result += f"{i}. {speaker}\n"
        
        logger.info(f"✅ Retrieved {len(unique_speakers)} unique speakers")
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching speakers: {e}", exc_info=True)
        return f"Error fetching speakers: {str(e)}"

@function_tool(
    name_override="get_all_tracks",
    description_override="Get all unique tracks from the conference."
)
async def get_all_tracks() -> str:
    """Get all unique tracks from the conference."""
    try:
        tracks_data = await db_client.query(
            table_name="conference_schedules",
            select_fields="track_name"
        )
        
        if not tracks_data:
            return "No tracks found in the conference database."
        
        unique_tracks = sorted(set(
            item["track_name"] for item in tracks_data 
            if item.get("track_name") and item["track_name"].strip()
        ))
        
        if not unique_tracks:
            return "No valid track names found."
        
        result = f"**Conference Tracks ({len(unique_tracks)} total):**\n\n"
        for i, track in enumerate(unique_tracks, 1):
            result += f"{i}. {track}\n"
        
        logger.info(f"✅ Retrieved {len(unique_tracks)} unique tracks")
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching tracks: {e}", exc_info=True)
        return f"Error fetching tracks: {str(e)}"

@function_tool(
    name_override="get_all_rooms",
    description_override="Get all unique conference rooms."
)
async def get_all_rooms() -> str:
    """Get all unique conference rooms."""
    try:
        rooms_data = await db_client.query(
            table_name="conference_schedules",
            select_fields="conference_room_name"
        )
        
        if not rooms_data:
            return "No rooms found in the conference database."
        
        unique_rooms = sorted(set(
            item["conference_room_name"] for item in rooms_data 
            if item.get("conference_room_name") and item["conference_room_name"].strip()
        ))
        
        if not unique_rooms:
            return "No valid room names found."
        
        result = f"**Conference Rooms ({len(unique_rooms)} total):**\n\n"
        for i, room in enumerate(unique_rooms, 1):
            result += f"{i}. {room}\n"
        
        logger.info(f"✅ Retrieved {len(unique_rooms)} unique rooms")
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching rooms: {e}", exc_info=True)
        return f"Error fetching rooms: {str(e)}"

@function_tool(
    name_override="search_sessions_by_speaker",
    description_override="Search for sessions by a specific speaker name."
)
async def search_sessions_by_speaker(speaker_name: str) -> str:
    """Search for sessions by a specific speaker."""
    try:
        sessions = await db_client.query(
            table_name="conference_schedules",
            filters={"speaker_name": speaker_name},
            order_by=[{"column": "conference_date"}, {"column": "start_time"}]
        )
        
        if not sessions:
            return f"No sessions found for speaker: {speaker_name}"
        
        result = f"**Sessions by {speaker_name} ({len(sessions)} session(s)):**\n\n"
        for i, session in enumerate(sessions, 1):
            result += (
                f"{i}. **{session.get('topic', 'Unknown Topic')}**\n"
                f"   Date: {session.get('conference_date', 'TBA')}\n"
                f"   Time: {session.get('start_time', 'TBA')} - {session.get('end_time', 'TBA')}\n"
                f"   Room: {session.get('conference_room_name', 'TBA')}\n"
                f"   Track: {session.get('track_name', 'TBA')}\n\n"
            )
        
        logger.info(f"✅ Found {len(sessions)} sessions for speaker: {speaker_name}")
        return result
    except Exception as e:
        logger.error(f"❌ Error searching sessions by speaker: {e}", exc_info=True)
        return f"Error searching sessions: {str(e)}"

@function_tool(
    name_override="search_sessions_by_topic",
    description_override="Search for sessions containing specific topic keywords."
)
async def search_sessions_by_topic(topic_keyword: str) -> str:
    """Search for sessions by topic keyword."""
    try:
        # Get all sessions and filter by topic keyword
        sessions = await db_client.query(
            table_name="conference_schedules",
            select_fields="*"
        )
        
        # Filter sessions that contain the topic keyword
        matching_sessions = [
            session for session in sessions
            if topic_keyword.lower() in session.get('topic', '').lower()
        ]
        
        if not matching_sessions:
            return f"No sessions found containing topic keyword: {topic_keyword}"
        
        result = f"**Sessions containing '{topic_keyword}' ({len(matching_sessions)} session(s)):**\n\n"
        for i, session in enumerate(matching_sessions, 1):
            result += (
                f"{i}. **{session.get('topic', 'Unknown Topic')}**\n"
                f"   Speaker: {session.get('speaker_name', 'TBA')}\n"
                f"   Date: {session.get('conference_date', 'TBA')}\n"
                f"   Time: {session.get('start_time', 'TBA')} - {session.get('end_time', 'TBA')}\n"
                f"   Room: {session.get('conference_room_name', 'TBA')}\n"
                f"   Track: {session.get('track_name', 'TBA')}\n\n"
            )
        
        logger.info(f"✅ Found {len(matching_sessions)} sessions for topic: {topic_keyword}")
        return result
    except Exception as e:
        logger.error(f"❌ Error searching sessions by topic: {e}", exc_info=True)
        return f"Error searching sessions: {str(e)}"

@function_tool(
    name_override="get_session_count",
    description_override="Get the total number of conference sessions."
)
async def get_session_count() -> str:
    """Get the total number of conference sessions."""
    try:
        sessions = await db_client.query(
            table_name="conference_schedules",
            select_fields="id"
        )
        
        count = len(sessions) if sessions else 0
        
        result = f"**Total Conference Sessions:** {count}"
        
        if count > 0:
            # Get additional stats
            unique_speakers = set()
            unique_tracks = set()
            unique_rooms = set()
            
            full_sessions = await db_client.query(
                table_name="conference_schedules",
                select_fields="speaker_name, track_name, conference_room_name"
            )
            
            for session in full_sessions:
                if session.get('speaker_name'):
                    unique_speakers.add(session['speaker_name'])
                if session.get('track_name'):
                    unique_tracks.add(session['track_name'])
                if session.get('conference_room_name'):
                    unique_rooms.add(session['conference_room_name'])
            
            result += f"\n**Additional Stats:**"
            result += f"\n- Unique Speakers: {len(unique_speakers)}"
            result += f"\n- Unique Tracks: {len(unique_tracks)}"
            result += f"\n- Unique Rooms: {len(unique_rooms)}"
        
        logger.info(f"✅ Retrieved session count: {count}")
        return result
    except Exception as e:
        logger.error(f"❌ Error getting session count: {e}", exc_info=True)
        return f"Error getting session count: {str(e)}"

@function_tool(
    name_override="get_speaker_count",
    description_override="Get the total number of unique speakers."
)
async def get_speaker_count() -> str:
    """Get the total number of unique speakers."""
    try:
        speakers_data = await db_client.query(
            table_name="conference_schedules",
            select_fields="speaker_name"
        )
        
        if not speakers_data:
            return "**Total Unique Speakers:** 0"
        
        unique_speakers = set(
            item["speaker_name"] for item in speakers_data 
            if item.get("speaker_name") and item["speaker_name"].strip()
        )
        
        count = len(unique_speakers)
        result = f"**Total Unique Speakers:** {count}"
        
        logger.info(f"✅ Retrieved speaker count: {count}")
        return result
    except Exception as e:
        logger.error(f"❌ Error getting speaker count: {e}", exc_info=True)
        return f"Error getting speaker count: {str(e)}"