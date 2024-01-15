from dataclasses import dataclass
from datetime import datetime

@dataclass
class PendingOperation:
    """Pending operation class, used now for removing users from the chat on a timer"""
    user_id: int
    operation: int
    date: datetime
    message_id: int

    @property
    def id(self):
        return "PO" + str(self.operation) + datetime.strftime(self.date, '%Y%m%d%H%M') + "." + str(self.user_id)
