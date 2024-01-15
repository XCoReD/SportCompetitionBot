"""Main data storage"""
from datetime import datetime
import pickle
from os import path
from kink import di
from competition import Competition
from chatcommunity import ChatCommunity
from myexception import LogicException
from history import History
from gameschedule import GameSchedule

class DataModel():
    """Main data storage class"""
    competitions : list[Competition]
    chat : ChatCommunity
    history: History
    schedule: GameSchedule

    no_save: bool

    def get_open_competitions_number(self) -> int:
        '''returns the number of open competitions, accepting new registrations'''
        return sum(1 for x in self.competitions if x.status == Competition.OPEN)

    def get_open_or_full_competitions_number(self) -> int:
        '''returns the number of open competitions, accepting new registrations, or fully staffed'''
        return sum(1 for x in self.competitions if x.status in (Competition.OPEN, Competition.FULL))

    def is_single_competition_open(self) -> bool:
        '''returns True if there is only one competition in open status, accepting new registrations'''
        return self.get_open_competitions_number() == 1

    def is_single_competition_open_or_full(self) -> bool:
        '''returns True if there is only one competition in open status, accepting new registrations or full'''
        return self.get_open_or_full_competitions_number() == 1

    def get_single_competition_open_or_full(self) -> Competition:
        if not self.is_single_competition_open_or_full():
            raise LogicException("0 or More than 1 competition is in open or full status")
        return next(x for x in self.competitions if x.status in (Competition.OPEN, Competition.FULL))

    def get_competition_by_id(self, id_str:str) -> Competition:
        return next((x for x in self.competitions if x.id == id_str), None)

    def get_competition_by_poll_id(self, poll_id:str) -> Competition:
        return next((x for x in self.competitions if x.poll_id == poll_id),None)

    def get_competition_by_start_date_and_location(self, start:datetime, location:str) -> Competition:
        return next((x for x in self.competitions if x.description and x.description.date == start and x.description.location == location), None)

    def __init__(self, no_persistency:bool = False):
        self.no_save = no_persistency
        self.path = path.join(".", "data")
        if not no_persistency:
            try:
                self.chat = self.load_chat()
            except (pickle.UnpicklingError, IOError) as e:
                print("load_chat failed: " + str(e))
                self.chat = ChatCommunity()
            try:
                self.competitions = self.load_competitions()
            except (pickle.UnpicklingError, IOError) as e:
                print("load_competitions failed: " + str(e))
                self.competitions = []
        else:
            self.chat = ChatCommunity()
            self.competitions = []
        self.history = di[History] = History(no_persistency)
        self.schedule = di[GameSchedule] = GameSchedule(no_persistency)

    def load_competitions(self) -> list[Competition]:
        """Loading the competition list. Those are in the past will be evicted"""
        with open(path.join(self.path,'competitions.pickle'), 'rb') as f:
            result = pickle.load(f)
            result[:] = [x for x in result if not x.date or x.date > datetime.now()]
            return result 

    def load_chat(self) -> ChatCommunity:
        """Loading the chat info."""
        with open(path.join(self.path,'chat.pickle'), 'rb') as f:
            return pickle.load(f)

    def save_competitions(self):
        """Saving the competition info."""
        if not self.no_save:
            with open(path.join(self.path,'competitions.pickle'), 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.competitions, f, pickle.HIGHEST_PROTOCOL)

    def save_chat(self):
        """Saving the chat info."""
        if not self.no_save:
            with open(path.join(self.path,'chat.pickle'), 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.chat, f, pickle.HIGHEST_PROTOCOL)
