"""historical info logic"""
from datetime import datetime
import sqlite3
from os import path
import pickle
from historyevent import RegistrationEvent, PastCompetitionSummary

class History:
    """class to store (and retrieve when needed) summary and details about game and user events"""
    summary:PastCompetitionSummary

    def __init__(self, no_persistency: bool = False):
        if not no_persistency:
            self._path = path.join(".", "data")
            try:
                with open(path.join(self._path,'summary.pickle'), 'rb') as f:
                    self.summary = pickle.load(f)
            except (pickle.UnpicklingError, IOError) as e:
                print("load history summary failed: " + str(e))
                self.summary = PastCompetitionSummary(max_capacity = 0, date = datetime.min)
            self._init_db()
        else:
            self.summary = PastCompetitionSummary(max_capacity = 13, date = datetime.now()) # for testing purposes

    def __del__(self):
        if self._conn:
            self._conn.close()

    def _init_db(self):
        self._conn = sqlite3.connect(path.join(self._path,'history.db'))
        try:
            self._conn.execute('''CREATE TABLE REGISTRATION_EVENTS
                (TIME INT PRIMARY KEY     NOT NULL,
                USER_ID           INT     NULL,
                GAME              INT     NULL,
                LOCATION          TEXT    NULL,
                ATTENDEES         INT     NULL,
                REMAINING         INT     NULL,
                EVENT             INT     NULL);''')
        except sqlite3.OperationalError:
            pass

    def add_event(self, event:RegistrationEvent):
        if self._conn:
            self._conn.execute(
                "INSERT INTO REGISTRATION_EVENTS (TIME,USER_ID,GAME,LOCATION,ATTENDEES,REMAINING,EVENT) VALUES (?,?,?,?,?,?,?)",
                (event.time, event.user_id, event.game, event.location, event.attendees, event.remaining, event.event))
            self._conn.commit()

    def save_summary(self):
        if self._conn:
            with open(path.join(self._path,'summary.pickle'), 'wb') as f:
                pickle.dump(self.summary, f, pickle.HIGHEST_PROTOCOL)
