"""registration helper"""
from config import registration
from menuitem import MenuItem
from chatconstants import ChatConstants

class Registration():
    """registration helper class to build menu dynamically from toml definition"""
    def __init__(self, start_key:int):
        self.menu = []
        self.parameters = []
        self.current_key = start_key
        self.__build()

    def __build(self):
        for entry in registration.items():
            name = entry[0]
            values = entry[1]
            if "caption" in values:
                action = values.get("action",None)
                predefined_key = self.__find_key(action) if action else None
                key = self.__get_next_key()
                p = values.get("parameter", None)
                m = MenuItem(
                    name,
                    values["caption"], 
                    values.get("message", None), 
                    values.get("values", None), 
                    values.get("buttons", None), 
                    key, 
                    predefined_key,
                    p,
                    values.get("command", None))
                if m.values:
                    for v in m.values:
                        v.key = self.__get_next_key()
                self.menu.append(m)
                if p:
                    self.parameters.append((name, p))

    def __get_next_key(self) -> int:
        key = self.current_key
        self.current_key += 1
        return key
    
    def __find_key(self, key) -> int:
        for c in ChatConstants.codes:
            if c[1] == key:
                return c[0]
        raise LookupError("Key is not a supported command: " + key)

    def get_menu(self, key: int) -> MenuItem:
        return next((x for x in self.menu if x.key == key), None)
    
    def get_menu_by_name(self, name: str) -> MenuItem:
        return next((x for x in self.menu if x.name == name), None)

    def handle_input(self, level: str, value: str):
        pass
