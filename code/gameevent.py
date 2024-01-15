"""Game event"""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class GameEvent:
    """Game event class"""
    date: datetime
    duration: int   #minutes
    location: str
    auto_registration: bool
    registration_start: datetime
    capacity: int
    valid: bool
    opened: bool

    @property
    def id(self):
        return "G" + datetime.strftime(self.date, '%Y%m%d%H%M') + "." + self.location
