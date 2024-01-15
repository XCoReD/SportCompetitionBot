"""custom exceptions"""
class LogicException (Exception):
    """invalid logic exception (e.g. state of the object called)"""
    def __init__(self, message: str):
        pass
