"""notifications of chat members callback"""
from abc import abstractmethod
from chatuser import Chatuser
from gameevent import GameEvent

class ChatNotifier():
    """abstract callback"""
    @abstractmethod
    async def notify_user(self, user:Chatuser, text:str, translate:bool = False):
        raise NotImplementedError
    @abstractmethod
    async def notify_chat(self, text:str, message_code:str, delete_older_messages: bool, translate:bool = False):
        raise NotImplementedError  
    @abstractmethod
    async def competition_status_changed(self, c_id:str):
        raise NotImplementedError  
    
class RegistrationNotifier():
    """abstract callback"""
    @abstractmethod
    def auto_registration_open(self, event:GameEvent):
        raise NotImplementedError
