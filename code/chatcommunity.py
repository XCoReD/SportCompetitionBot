"""Chat users storage"""
from datetime import datetime, timedelta
import threading
from chatuser import Chatuser
from config import credentials
from pendingoperation import PendingOperation

class ChatCommunity:
    """ChatCommunity is a container class to keep the info about chat users and pending operations on them"""

    users: list[Chatuser]
    pending_users: list[Chatuser]
    pending_operations: list[PendingOperation]

    def __init__(self):
        self.users = []
        self.pending_users = []
        self.pending_operations = []

    def empty(self) -> bool:
        return not self.users
    
    def find_user(self, userid: int, effective_user = None) -> Chatuser:
        user = next((x for x in self.users if x.user_id == userid), None)
        if user and effective_user:
            if hasattr(effective_user, "username"):
                user.name = effective_user.username
            if hasattr(effective_user, "full_name"):
                user.full_name = effective_user.full_name
            if hasattr(effective_user, "language_code"):
                user.language_code = effective_user.language_code
        return user
    
    def trusted(self, userid: int):
        user_object = self.find_user(userid)
        return user_object.status in {Chatuser.TRUSTED, Chatuser.ADMIN} if user_object else False
    
    def find_or_add(self, userid, username, full_name, status = None, language_code = None) -> Chatuser:
        user = next((x for x in self.users if x.user_id == userid), None)
        #hack: Telegram may report the system OS language to the server for the current user, but not the UI language set in the client
        #if language_code == 'en':
        #    language_code = credentials["telegram"]["chat"]["language"]
        if not user:
            if not status:
                status = Chatuser.NEW
            user = Chatuser(username, userid, status, full_name, language_code)
            self.users.append(user)
        else:
            user.full_name = full_name
            user.language_code = language_code
        return user
    
    def add(self, user: Chatuser) -> None:
        self.users.append(user)

    def add_pending(self, user: Chatuser) -> None:
        self.pending_users.append(user)

    def add_pending_operation(self, user: Chatuser, seconds: int, code: int, message_to_remove: int) -> None:
        self.pending_operations.append(PendingOperation(user.user_id, code, datetime.now() + timedelta(seconds=seconds), message_to_remove))

    def remove_pending_operation(self, user_id: int, code: int) -> PendingOperation:
        operation = next((x for x in self.pending_operations if x.user_id == user_id and x.operation == code), None)
        if operation:
            self.pending_operations.remove(operation)
            return operation
        return None

    def get_admins(self):
        admins = list(filter(lambda u: u.status is Chatuser.ADMIN, self.users))
        return ','.join(map(lambda user: '@' + user.name, admins)) if len(admins) > 1 else ( ('@' + admins[0].name) if len(admins) == 1 else '(not found)')
