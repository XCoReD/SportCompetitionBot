"""Chat user"""
from identifiable import Identifiable
class Chatuser(Identifiable):
    """Chat user class"""
    NEW, TRUSTED, REMOVED, RESTRICTED, ADMIN, BOT = range(6)

    registration_info: dict
    name: str
    full_name: str
    language_code: str
    user_id: int

    @property
    def id(self):
        return str(self.user_id)

    @property
    def l(self):
        return self.language_code

    def __init__(self, name:str, user_id:int, status: range, full_name:str = None, language_code:str = None):
        self.name = name
        self.full_name = full_name
        self.user_id = user_id
        self.status = status
        self.language_code = language_code
        self.registration_info = {}

    def update(self, name: str, full_name:str, language_code:str):
        self.name = name
        self.full_name = full_name
        self.language_code = language_code

    def get_name(self):
        return self.full_name if hasattr(self, "full_name") else self.name

    def get_fqn_name(self):
        return f"{self.name} ({self.full_name})" if hasattr(self, "full_name") else self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        elif isinstance(other, Chatuser):
            return self.name == other.name
    
    def __str__(self):
        return f"{self.get_fqn_name()} [{str(self.status)}]"
        