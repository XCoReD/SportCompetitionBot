"""competition info"""
import asyncio
from datetime import datetime
import itertools
from kink import di
from player import Player
from chatuser import Chatuser
from myexception import LogicException
from notifier import ChatNotifier
from config import credentials, registration, schedule, messages
from translate import _
from history import History
from historyevent import RegistrationEvent
from gameevent import GameEvent
from identifiable import Identifiable

class Competition(Identifiable):
    """competition class, to keep info about competition status, date, and players registered"""
    SCHEDULED, OPEN, FULL, CONFIRMED, CANCELLED = range(5)
    PLAYER_REGISTERED_MAIN, PLAYER_REGISTERED_SPARE, PLAYER_NOT_REGISTERED = range(3)

    id_obj = itertools.count()

    id_value: str
    status: range
    description: GameEvent
    poll_id: str
    poll_message_id: int
    players: list[Player]
    spare_players: list[Player]
    capacity: int
    capacity_max: int
    location: str
    date: datetime
    duration: int       #minutes

    date_tmp: datetime  #temporary values for editing
    duration_tmp: int   #minutes

    duration_default = int(schedule["schedule"]["game_duration_minutes"])
    
    @property
    def id(self):
        return self.id_value
    
    @property
    def capacity_spare(self):
        return sum(x.participants for x in self.spare_players) if self.spare_players else 0

    def __init__(self, description: GameEvent):
        self.status = Competition.SCHEDULED
        self.description = description if description else None
        self.capacity_max = description.capacity if description else 0
        self.location = description.location if description else None
        self.date = description.date if description else None
        self.duration = description.duration if description else 0
        self.capacity = 0
        self.players = []
        self.spare_players = []
        self.poll_id = ''
        self.poll_message_id = 0
        self.id_value = "C"+datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')+"."+str(next(Competition.id_obj))

    def open_registration(self, capacity_max = -1):
        if self.status not in (Competition.SCHEDULED, Competition.CONFIRMED, Competition.CANCELLED) or not self.date:
            raise LogicException("Opening a competition with wrong status!")
        if capacity_max != -1:
            self.capacity_max = capacity_max
        self.status = Competition.OPEN if self.capacity < self.capacity_max else Competition.FULL

    def confirm_and_close_registration(self):
        self.status = Competition.CONFIRMED
        self.poll_id = ''
        self.poll_message_id = 0

    def cancel_registration(self):
        self.status = Competition.CANCELLED

    def reset(self):
        self.players.clear()
        self.spare_players.clear()
        self.capacity = 0

    def start_editing(self):
        self.date_tmp = self.date
        self.duration_tmp = self.duration

    def apply_editing(self):
        self.date = self.date_tmp
        self.duration = self.duration_tmp

    def is_open_or_full(self) -> bool:
        return self.status in (Competition.OPEN, Competition.FULL)
    
    def is_in_the_future(self) -> bool:
        return self.date is not None and self.date > datetime.now()
    
    def get_date(self) -> datetime:
        return self.date
    
    def get_status(self, language:str) -> str:
        s = None
        match self.status:
            case Competition.SCHEDULED:
                s = "scheduled"
            case Competition.OPEN:
                s = "registration is open" if self.date > datetime.now() else "past, was open"
            case Competition.FULL:
                s = "registration is full" if self.date > datetime.now() else "past, was full"
            case Competition.CONFIRMED:
                s = "confirmed, go play!" if self.date > datetime.now() else "past, was confirmed"
            case Competition.CANCELLED:
                s = "cancelled"
        return _(s, language)

    def get_report(self, language:str, include_header:bool = False, include_players:bool = True):
        result = (_(messages["report"]["title"], language) % \
                  (self.get_location(language), str(self.capacity), str(self.capacity_max), self.get_status(language))) if include_header else ""
        if include_players:
            if not self.players and not self.spare_players:
                result += "\n" + _(messages["report"]["empty"], language)
            else:            
                if self.players:
                    result += "\n" + _(messages["report"]["active"], language) % str(self.capacity)
                    i = 1
                    for player in self.players:
                        result += f"\n\t{i}: {str(player)}"
                        i = i + 1
                if self.spare_players:
                    result += "\n" + _(messages["report"]["queue"], language) % str(self.capacity_spare)
                    i = 1
                    for player in self.spare_players:
                        result += f"\n\t{i}: {str(player)}"
                        i = i + 1
        return result

    def find(self, userid:int) -> (int, Player, list[Player]):
        if (p := self.find_player(userid)):
            return Competition.PLAYER_REGISTERED_MAIN, p, self.players
        if (p := self.find_spare_player(userid)):
            return Competition.PLAYER_REGISTERED_SPARE, p, self.spare_players
        return Competition.PLAYER_NOT_REGISTERED, None, None
    
    def find_player(self, userid: int) -> Player:
        return next((x for x in self.players if x.owner.user_id == userid), None)

    def find_spare_player(self, userid: int) -> Player:
        return next((x for x in self.spare_players if x.owner.user_id == userid), None)
    
    def get_role(self, status, l) -> str:
        return _(messages["role"]["main"] if status == Competition.PLAYER_REGISTERED_MAIN else messages["role"]["spare"], l)

    def on_event(self, user_id: int, attendees_claimed: int, attendees_final: int, code: int):
        di[History].add_event(
            RegistrationEvent(datetime.now(), user_id, self.date, self.location, attendees_claimed, attendees_final, code))

    async def register(self, user: Chatuser, notifier:ChatNotifier, participants:int = -1, order:int = 0) -> (bool, bool, str):
        l = user.language_code
        if self.status not in (Competition.OPEN, Competition.FULL):
            return False, False, _(messages["join"]["game_status"]["not_open"], l) % self.get_location(l)
        status, player = self.find(user.user_id)[0:2]
        if status != Competition.PLAYER_NOT_REGISTERED:
            if participants == -1:
                return False, False, _(messages["join"]["already_joined"], l) % (self.get_location(l), self.get_role(status, l))
            if status == Competition.PLAYER_REGISTERED_MAIN:
                if self.capacity + participants > self.capacity_max:
                    return False, False, _(messages["join"]["joined_cannot_extend"], l) % (self.get_location(l), self.get_role(status, l))
                player.participants += participants
                self.on_event(user.user_id, participants, player.participants, RegistrationEvent.UPDATE_ATTENDEES)
                self.capacity += participants
                if self.capacity == self.capacity_max:
                    self.status = Competition.FULL
                    await notifier.competition_status_changed(self.id)
                return True, False , _(messages["join"]["joined_updated"], l) % \
                    (self.get_location(l), self.get_role(status, l), str(player.participants))
            player.participants += participants
            self.on_event(user.user_id, participants, player.participants, RegistrationEvent.UPDATE_ATTENDEES_SPARE)
            return False, True, _(messages["join"]["joined_updated"], l) % \
                (self.get_location(l), self.get_role(status, l), str(player.participants))
        if participants == -1:
            participants = 1
        if self.status == Competition.OPEN and order == 0:
            if self.capacity + participants > self.capacity_max:
                return False, False, _(messages["join"]["cannot_join_need_reduce"], l) % (self.get_location(l), str(participants))
            self.capacity += participants
            self.players.append(Player(user, participants))
            self.on_event(user.user_id, participants, participants, RegistrationEvent.REGISTER)
            if self.capacity == self.capacity_max:
                self.status = Competition.FULL
                await notifier.competition_status_changed(self.id)
            return True, False, _(messages["join"]["joined"], l) % self.get_location(l)
        if order == 1:
            self.spare_players.append(Player(user, participants))
            self.on_event(user.user_id, participants, participants, RegistrationEvent.REGISTER_SPARE)
            return False, True, _(messages["join"]["joined_as_spare"], l) % self.get_location(l)
        return False, False, None

    async def deregister(self, user: Chatuser, notifier:ChatNotifier, participants:int = -1)-> (bool, bool, str):
        l = user.language_code
        if self.status not in (Competition.OPEN, Competition.FULL):
            return False, False, _(messages["join"]["game_status"]["not_open"], l) % self.get_location(l)
        status,player,storage = self.find(user.user_id)
        if status == Competition.PLAYER_NOT_REGISTERED:
            return False, False, _(messages["join"]["cannot_deregister"], l) % self.get_location(l)
        if participants == -1:
            participants = player.participants
        if participants < 0 or participants > player.participants:
            return False, False, _(messages["join"]["cannot_deregister_more"], l) % self.get_location(l)
        if status == Competition.PLAYER_REGISTERED_MAIN:
            event = RegistrationEvent.UNREGISTER
            self.capacity -= participants
        else:
            event = RegistrationEvent.UNREGISTER_SPARE
        player.participants -= participants
        if player.participants <= 0:
            storage.remove(player)
            self.on_event(user.user_id, participants, 0, event)
            if status == Competition.PLAYER_REGISTERED_MAIN:
                return True, False, _(messages["join"]["deregistered"],l) % self.get_location(l)
            return False, True, _(messages["join"]["deregistered_spare"],l) % self.get_location(l)
        self.on_event(user.user_id, participants, player.participants, event)
        promoted = await self.promote(notifier)
        if self.capacity < self.capacity_max:
            self.status = Competition.OPEN
        return True, promoted != 0, _(messages["join"]["deregistered_updated"], l) % \
            (self.get_location(l), 
             (str(player.participants) if player.participants > 1 else _(messages["join"]["only_you"], l)))
    
    async def promote(self, notifier:ChatNotifier) -> int:
        if self.capacity == self.capacity_max or not self.spare_players:
            return 0
        loop=True
        promoted = 0
        while self.capacity < self.capacity_max and self.spare_players and loop:
            loop = False
            for i in range(len(self.spare_players)):
                if self.spare_players[i].participants <= self.capacity_max - self.capacity:
                    user = self.spare_players.pop(i)
                    self.players.append(user)
                    self.on_event(user.owner.user_id, user.participants, user.participants, RegistrationEvent.PROMOTE)
                    promoted += user.participants
                    l = user.language_code
                    await notifier.notify_user(user, _(messages["join"]["promoted"], l) % self.get_location(l))
                    loop = True
                    break
        return promoted
        
    def get_location(self, language:str) -> str:
        d = self.get_date()
        s = (_(datetime.strftime(d, '%A'), language) + ', ' + datetime.strftime(d, '%d.%m.%Y %H:%M')) \
            if d is not None else _(messages["join"]["game_status"]["not_scheduled"], language)
        result = (self.location if self.location else _("Not set",language)) + ", " + s
        if self.duration != Competition.duration_default:
            result += _(", %s minutes", language) % str(self.duration)
        return result
    
