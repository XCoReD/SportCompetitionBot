"""next game date helper"""
import asyncio
import pickle
from datetime import datetime, timedelta
from os import path
from threading import Timer
from kink import di
from config import schedule, messages
from gameevent import GameEvent
from notifier import RegistrationNotifier
from maineventloop import run_in_main_event_loop

class GameSchedule:
    """next game date helper class"""
    events: list[GameEvent]

    def __init__(self, no_persistency: bool = False):
        self.events = []
        self.no_persistency = no_persistency
        if not no_persistency:
            self._path = path.join(".", "data")
            try:
                with open(path.join(self._path,'schedule.pickle'), 'rb') as f:
                    self.events = pickle.load(f)
            except (pickle.UnpicklingError, IOError) as e:
                print("load schedule failed: " + str(e))
        self.update_from_config(True)
        self._timer_update_schedule = Timer(86400, self.update_from_config)
        self._timer_update_schedule.start()
        self.open_guard = False
        delay = 10 #3600
        self._timer_auto_open = Timer(delay, self.auto_open)
        self._timer_auto_open.start()
        #test!!
        self.events[0].registration_start = datetime.now()
        self.events[0].auto_registration = True
    
    '''
    def __del__(self):
        self._timer_update_schedule.stop() 
        self._timer_auto_open.stop()
    '''

    def auto_open(self):
        run_in_main_event_loop(self.do_auto_open_async())

    async def do_auto_open_async(self):
        if self.open_guard:
            return
        return
        self.open_guard = True
        updated = False
        for e in self.events:
            if e.auto_registration and e.registration_open <= datetime.now() and not e.opened:
                e.opened = True
                di[RegistrationNotifier].auto_registration_open(e)
                updated = True
        if updated:
            self.save()
        self.open_guard = False

    def update_from_config(self, direct:bool = False):
        if direct:
            self.do_update_from_config()
        else:
            run_in_main_event_loop(self.do_update_from_config_async())

    async def do_update_from_config_async(self):
        self.do_update_from_config()

    def do_update_from_config(self):
        updated = False
        for days_shift in range(10):    #10 days ahead
            next_day = datetime.now() + timedelta(days=days_shift)
            for e in schedule["schedule"]["games"]:
                entry = schedule["game"][e]
                if entry["day_of_week"] == next_day.weekday():
                    start_time = datetime.strptime(entry["start"], "%H:%M")
                    end_time = datetime.strptime(entry["end"], "%H:%M")
                    duration = end_time - start_time
                    minutes = int(duration.total_seconds() / 60)
                    exact_datetime = datetime.combine(next_day.date(), start_time.time())
                    facility = entry["facility"]
                    existing = next((x for x in self.events if x.date == exact_datetime and x.location == facility), None)
                    if not existing:
                        auto_registration = e in schedule["schedule"]["auto_registration"]["games"]
                        auto_registration_time = datetime.strptime(schedule["schedule"]["auto_registration"]["registration_window_time_open"], "%H:%M")
                        auto_registration_days_ahead = int(schedule["schedule"]["auto_registration"]["registration_window_days_open"])
                        try:
                            capacity = int(entry["capacity"])
                        except ValueError:
                            capacity = int(schedule["facility"][facility]["capacity"])
                        registration_open = datetime.combine((exact_datetime + timedelta(days=-auto_registration_days_ahead)).date(), auto_registration_time.time())
                        self.events.append(GameEvent(exact_datetime, minutes, facility, auto_registration, registration_open, capacity, True, False))
                        updated = True
        if updated:
            self.events.sort(key=lambda x: x.date)
            #if new entries have arrived, some older shall be removed?
            threshold = datetime.now() + timedelta(days=-10)
            while self.events[0].date < threshold:
                self.events.pop(0)
            self.save()

    def save(self):
        if not self.no_persistency:
            with open(path.join(self._path,'schedule.pickle'), 'wb') as f:
                pickle.dump(self.events, f, pickle.HIGHEST_PROTOCOL)

    def get_next_game(self, index: int) -> GameEvent:
        #not a pythonic way
        i = 0
        for s in self.events:
            if s.date < datetime.now():
                continue
            if i == index:
                return s
            i += 1
        return None
