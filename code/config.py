#provides access to configuration
from os import path
#import os 
import toml

credentials = []
registration = []
schedule = []
messages = []
preferences = []

#current path is e.g. \Documents\Projects\CompetitionBot\, not the \Documents\Projects\CompetitionBot\code
'''
cwd = os.getcwd()
print(cwd)
dir_path = os.path.dirname(os.path.realpath(__file__))
print(dir_path)
'''
__sp = path.join(".", "config")

with open(path.join(__sp, 'credentials.toml'), 'r', encoding="utf-8") as f:
    credentials = toml.load(f)

with open(path.join(__sp, 'messages.toml'), 'r', encoding="utf-8") as f:
    messages = toml.load(f)

with open(path.join(__sp, 'registration.toml'), 'r', encoding="utf-8") as f:
    registration = toml.load(f)

with open(path.join(__sp, 'schedule.toml'), 'r', encoding="utf-8") as f:
    schedule = toml.load(f)

with open(path.join(__sp, 'preferences.toml'), 'r', encoding="utf-8") as f:
    preferences = toml.load(f)

def save_registration():
    with open(path.join(__sp, 'registration.toml'), 'w', encoding="utf-8") as f:
        toml.dump(registration, f)

def save_schedule():
    with open(path.join(__sp, 'schedule.toml'), 'w', encoding="utf-8") as f:
        toml.dump(schedule, f)
