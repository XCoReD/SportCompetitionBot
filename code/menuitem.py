"""Telegram menu localization classes"""
from translate import _

class MenuItemLocalized:
    """localized menu item"""
    text:str
    localized:dict
    #key:int

    def __init__(self, text): #, key:int = None):
        self.text = text
        self.localized = {}
        #self.key = key

    def get_text(self, language:str) -> str:
        if not language or language == "en":
            return self.text
        localized = self.localized.get(language, None)
        if not localized:
            localized = _(self.text, language)
            self.localized[language] = localized
        return localized

class MenuItem:
    """menu item holder"""
    name: str
    caption:MenuItemLocalized
    message:MenuItemLocalized
    parameter:str
    values:list[MenuItemLocalized]
    key:int
    predefined_key:int
    buttons:list
    command:str

    def __init__(self, name:str, caption:str, message:str, values:list, buttons:list, key:int, predefined_key:int, parameter:str, command:str):
        self.name = name
        self.caption = MenuItemLocalized(caption)
        self.message = MenuItemLocalized(message)
        self.parameter = parameter
        self.key = key
        self.predefined_key = predefined_key
        self.values = []
        self.buttons = buttons
        self.command = command
        if values:
            for v in values:
                self.values.append(MenuItemLocalized(v))
    