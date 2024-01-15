"""history events"""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RegistrationEvent:
    """registration event class"""
    time: datetime
    user_id: int
    game: datetime
    location: str
    attendees: int  #1 - only this user, 2 - user and one guest, etc
    remaining: int  #if 2 attendees were registered and then 1 was de-registered, 1 will remain
    event:     int  #1 - registered, 2 - unregistered, etc

    REGISTER = 1
    UNREGISTER = 2
    UPDATE_ATTENDEES = 3
    PROMOTE = 4
    REGISTER_SPARE = 5
    UNREGISTER_SPARE = 6
    UPDATE_ATTENDEES_SPARE = 7

@dataclass
class PastCompetitionSummary:
    """past competition summary event"""
    max_capacity: int
    date: datetime

