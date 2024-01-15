"""Game player"""
from chatuser import Chatuser
from translate import _
from config import messages

class Player:
    """Game player class"""
    owner: Chatuser
    participants: int

    def __init__(self, owner: Chatuser, participants = 1):
        self.owner = owner
        self.participants = participants

    def __eq__(self, other):
        if isinstance(other, str):
            return self.owner.name == other
        elif isinstance(other, Player):
            return self.owner.user_id == other.owner.user_id
    
    def __name__(self):
        result = f'@{self.owner.name}'
        if hasattr(self.owner, 'full_name'):
            result += f' [{self.owner.full_name}]'
        return result
    
    def __str__(self):
        if self.participants != 1:
            return self.__name__() + " +" + _(messages["role"]["with_guests"]) % str(self.participants-1)
        return self.__name__()
        