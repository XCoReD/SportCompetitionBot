#constants for Telegram chat menu handling
class ChatConstants:
    """Chat constants for common navigation"""
    (
        END,
        BACK,
        APPLY
    ) = range(1, 4)
    
    codes = [
        (END, "end"),
        (END, "exit"),
        (BACK, "back")
    ]
