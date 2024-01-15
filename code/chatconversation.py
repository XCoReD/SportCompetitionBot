"""Telegram Chat bot logic."""
from copy import deepcopy
import sys
from os import path
import threading
from typing import Sequence, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from gameevent import GameEvent
from translate import _
import logging
import inspect
from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update, ChatMember, ChatMemberUpdated
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    PollAnswerHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
    MessageHandler,
    filters,
    PicklePersistence,
    Updater
)
from telegram.helpers import mention_html

from str2bool import str2bool
from player import Player
from chatuser import Chatuser
from competition import Competition
from datamodel import DataModel
from config import credentials, registration, schedule, messages, preferences
from notifier import ChatNotifier, RegistrationNotifier
from registration import Registration
from chatconstants import ChatConstants
from menuhelper import MenuHelper
from identifiable import Identifiable
from menuitem import MenuItem
from maineventloop import run_in_main_event_loop
from pendingoperation import PendingOperation

class ChatConversation(RegistrationNotifier):
    """Telegram bot logic class"""
    # Different constants
    (
        GAME_JOIN,
        GAME_JOIN_SELECT,
        GAME_JOIN_REGISTER,
        GAME_JOIN_DEREGISTER,
        GAME_JOIN_DEREGISTER_CONFIRM,
        RULES,
        GAME_MANAGE,
        GAME_MANAGE_VIEW_PARTICIPANTS,
        GAME_MANAGE_SET_MAX_PARTICIPANTS,
        GAME_MANAGE_SET_MAX_PARTICIPANTS_VALUE,
        GAME_MANAGE_SET_LOCATION,
        GAME_MANAGE_SET_LOCATION_VALUE,
        GAME_MANAGE_SET_TIME,
        GAME_MANAGE_CANCEL,
        GAME_MANAGE_CANCEL_CONFIRM,
        GAME_MANAGE_REGISTRATION_OPEN,
        GAME_MANAGE_REGISTRATION_CLOSE,
        GAME_MANAGE_DELETE,
        GAME_MANAGE_SCHEDULE_SELECT,
        GAME_MANAGE_SCHEDULE_SELECT_CUSTOM,
        GAME_MANAGE_SCHEDULE_GETDATE_REGISTRATION_OPEN,

        GAME_SELECTED,

        START_OVER,

        CURRENT_FEATURE,
        BACK_CALLBACK_DATA,
        CURRENT_LEVEL,
        PREVIOUS_LEVEL,

        USER_ID,
        SESSION_ID,
        
        GAME_STATUS,
        GAME_PARTICIPANTS,

        PENDING_REMOVE_USER

    ) = range(10, 42)

    REGISTRATION_ENTRY_START = 100

    #menu definitions, non-localized, and somewhere used as templates
    user_menu_top_trusted = [
        [
            {'text': messages["game"]["join"], 'callback_data' : str(GAME_JOIN)},
        ],
        [
            {'text': messages["personal"]["view"], 'callback_data' : str(REGISTRATION_ENTRY_START)},
        ],
        [
            {'text': messages["chat"]["rules"], 'callback_data' : str(RULES)},
            {'text': messages["chat"]["exit"], 'callback_data' : str(ChatConstants.END)}
        ]
    ]

    user_menu_top_new = [
        [
            {'text': messages["personal"]["register"], 'callback_data' : str(REGISTRATION_ENTRY_START)},
        ],
        [
            {'text': messages["chat"]["rules"], 'callback_data' : str(RULES)},
            {'text': messages["chat"]["exit"], 'callback_data' : str(ChatConstants.END)}
        ]
    ]

    admin_menu_top = [
        [
            {'text': messages["game"]["manage"], 'callback_data' : str(GAME_MANAGE)},
        ],
        [
            {'text': messages["game"]["join"], 'callback_data' : str(GAME_JOIN)},
        ],
        [
            {'text': messages["chat"]["exit"], 'callback_data' : str(ChatConstants.END)}
        ]
    ]

    admin_menu_manage_competition_select = [
        #the following two lists will be added and customized if available
        #[
        #    {'text': messages["schedule"]["select_open"], 'callback_data' : str(GAME_MANAGE_SCHEDULE_SELECT_OPEN)},
        #],
        #[
        #    {'text': messages["schedule"]["select_scheduled"], 'callback_data' : str(GAME_MANAGE_SCHEDULE_SELECT_SCHEDULED)},
        #],
        [
            {'text': messages["schedule"]["select_custom"], 'callback_data' : str(GAME_MANAGE_SCHEDULE_SELECT_CUSTOM)},
        ],
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    admin_menu_manage_competition = [
        [
            {'text': messages["facility"]["update_number"], 'callback_data' : str(GAME_MANAGE_SET_MAX_PARTICIPANTS)},
        ],
        [
            {'text': messages["facility"]["update_address"], 'callback_data' : str(GAME_MANAGE_SET_LOCATION)},
        ],
        [
            {'text': messages["schedule"]["reschedule"], 'callback_data' : str(GAME_MANAGE_SET_TIME)},
        ],
        [
            {'text': messages["game"]["cancel"], 'callback_data' : str(GAME_MANAGE_CANCEL)}
        ],
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    admin_menu_manage_competition_custom = [
        [
            {'text': messages["facility"]["update_number"], 'callback_data' : str(GAME_MANAGE_SET_MAX_PARTICIPANTS)},
        ],
        [
            {'text': messages["facility"]["update_address"], 'callback_data' : str(GAME_MANAGE_SET_LOCATION)},
        ],
        [
            {'text': messages["schedule"]["schedule"], 'callback_data' : str(GAME_MANAGE_SET_TIME)},
        ],
        [
            {'text': messages["game"]["registration_open"], 'callback_data' : str(GAME_MANAGE_REGISTRATION_OPEN)},
        ],
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    admin_menu_game_cancel = [
        [
            {'text': messages["game"]["cancel_confirm"], 'callback_data' : str(GAME_MANAGE_CANCEL_CONFIRM)}
        ],
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    menu_back = [
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    menu_apply_time_back = [
        [
            {'text': messages["chat"]["apply"], 'callback_data' : str(ChatConstants.APPLY)}
        ],
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    menu_join_register = [ 
        [
            {'text':messages["game"]["join"], 'callback_data': str(GAME_JOIN_REGISTER)},
        ],
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    menu_join_deregister = [
        [
            {'text':messages["game"]["leave"], 'callback_data': str(GAME_JOIN_DEREGISTER)},
        ],
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    menu_join_deregister_confirm = [
        [
            {'text':messages["game"]["leave_confirm"], 'callback_data': str(GAME_JOIN_DEREGISTER_CONFIRM)},
        ],
        [
            {'text': messages["chat"]["back"], 'callback_data' : str(ChatConstants.BACK)}
        ],
    ]

    (BTN_HIDE_IF_STATUS_IN, BTN_PREFIX, BTN_DISABLE) = range(3)

    conditional_button_traits = [
        {'text':'(hide if registered)', 'action':BTN_HIDE_IF_STATUS_IN, 'user_status_match':(Chatuser.TRUSTED, Chatuser.ADMIN)},
        {'text':'(hide if not registered)', 'action':BTN_HIDE_IF_STATUS_IN, 'user_status_match':(Chatuser.NEW, Chatuser.REMOVED, Chatuser.RESTRICTED)},
        {'text':'(enable if value)', 'action':BTN_DISABLE},
        {'text':'(forward)', 'action':BTN_PREFIX, 'prefix':'[Forward]'},
        {'text':'(backward)', 'action':BTN_PREFIX, 'prefix':'[Backward]'}
    ]

    (PUBLIC, PRIVATE, OTHER) = map(chr, range(1, 4))

    # Utility methods
    def get_conversation_context(self, context: ContextTypes.DEFAULT_TYPE) -> int:
        if str(context._chat_id) == self.chat_id:
            self.logger.info("%s started conversation in a chat", context._user_id)
            return ChatConversation.PUBLIC
        if context._chat_id == context._user_id:
            #do not accept the messages from users not in chat
            chatuser = self.data.chat.find_user(context._user_id)
            if chatuser:
                self.logger.info("%s started private conversation", chatuser.get_fqn_name())
                return ChatConversation.PRIVATE
        self.logger.warning("%s started conversation, but he is not a member of chat, ignoring", str(context._user_id))
        return ChatConversation.OTHER

    def get_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, check_for_session:bool = True) -> Chatuser:
        try:
            userid = update.effective_user.id if update.effective_user else context.user_data[ChatConversation.USER_ID]
            user = self.data.chat.find_user(userid)
            if check_for_session:
                if context.user_data[ChatConversation.SESSION_ID] != user.user_id:
                    return None
            return user
        except KeyError:
            self.logger.error("No user id set in the context: %s", inspect.stack()[0][3])
            return None
    
    def is_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        user = self.get_user(update, context)
        if not user:
            return False
        return user.status == Chatuser.ADMIN if user else False
    
    def get_competition_id(self, c: Competition) -> str:
        return str(ChatConversation.GAME_MANAGE_SCHEDULE_SELECT) + "#" + c.id

    # Top level conversation callbacks
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """starts the conversation"""
        ctx = self.get_conversation_context(context)
        if ctx == ChatConversation.OTHER:
            return
        reply_privately = ctx == ChatConversation.PUBLIC

        if update.message:
            user = self.data.chat.find_or_add(
                update.message.from_user.id, update.message.from_user.username,
                update.message.from_user.full_name, Chatuser.NEW, update.message.from_user.language_code)
            context.user_data[ChatConversation.USER_ID] = user.user_id
            context.user_data[ChatConversation.START_OVER] = False
            context.user_data[ChatConversation.BACK_CALLBACK_DATA] = []
            context.user_data[ChatConversation.CURRENT_FEATURE] = ''
            context.user_data[ChatConversation.SESSION_ID] = user.user_id   #no need to be unique, just be
            self.logger.debug("start: initiated by %s", user.get_fqn_name())
        else:
            self.logger.debug("start: update.message is None")
            user = self.get_user(update, context)
            if not user:
                return
        
        status = user.status
        l = self.get_user_language(user)

        if status == Chatuser.ADMIN:
            text = _(messages["greetings"]["admin"], l) + "\n\n" + self.get_upcoming_events_summary(l)
            buttons = MenuHelper.get_menu(l, ChatConversation.admin_menu_top, "admin_menu_top")
            if self.data.get_open_or_full_competitions_number() < 1:
                buttons = deepcopy(buttons)
                buttons.pop(1)
        elif status == Chatuser.TRUSTED or not self.chat_registration_mandatory:
            text = _(messages["greetings"]["trusted"], l) + "\n\n" + self.get_upcoming_events_summary(l)
            buttons = MenuHelper.get_menu(l, ChatConversation.user_menu_top_trusted, "user_menu_top_trusted")
            if self.data.get_open_or_full_competitions_number() < 1:
                buttons = deepcopy(buttons)[1:]
        else:
            text = _(registration["start"]["message"], l)
            buttons = MenuHelper.get_menu(l, ChatConversation.user_menu_top_new, "user_menu_top_new")

        keyboard = InlineKeyboardMarkup(buttons)
        # If we're starting over we don't need to send a new message
        start_over = context.user_data.get(ChatConversation.START_OVER)
        if reply_privately:
            if update.message:
                await context.bot.delete_message(chat_id = context._chat_id, message_id=update.message.message_id)
            await context.bot.send_message(
                chat_id=context._user_id, 
                text=text, 
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML)
            await self.delete_chat_messages(str(context._user_id))
        else:
            if start_over or not update.message:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(text=text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        context.user_data[ChatConversation.START_OVER] = False

    def get_upcoming_events_summary(self, language: str, include_players: bool = False) -> str:
        result = ""
        for c in self.data.competitions:
            if c.is_in_the_future() and c.status in (Competition.OPEN, Competition.FULL, Competition.CONFIRMED):
                result += "\n---\n" + c.get_report(language, True, include_players)
        if not result:
            return _(messages["view"]["no_competition_open"], language)
        return _(messages["view"]["summary"], language) + result

    async def end(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """End conversation from InlineKeyboardButton."""
        user = self.get_user(update, context)
        if not user:
            return
        self.logger.debug("end: initiated by %s", user.get_fqn_name())
        context.user_data[ChatConversation.SESSION_ID] = 0
        l = self.get_user_language(user)
        await update.callback_query.answer(_(messages["greetings"]["bye"], l))
        await update.callback_query.delete_message()

    async def back(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """return back to the previous menu or to top level conversation"""
        try:
            callback_data = context.user_data.get(ChatConversation.BACK_CALLBACK_DATA).pop()
            if callback_data:
                await self.process_callback(update, context, callback_data)
                return
        except IndexError:
            pass
        self.logger.debug("back: stack is empty, restarting menu")
        context.user_data[ChatConversation.START_OVER] = True
        self.keyboard = None
        self.headline = ""
        await self.start(update, context)

    # Second level conversation callbacks
    async def game_manage(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """top level menu for administrator to manage the game"""
        if not self.is_admin(update, context):
            return
        user = self.get_user(update, context)
        l = self.get_user_language(user)
        opened = []
        scheduled = []
        for s in self.data.schedule.events:
            if s.auto_registration and s.registration_start > datetime.now():
                c = self.data.get_competition_by_start_date_and_location(s.date, s.location)
                if not c:
                    self.data.competitions.append(Competition(s))
        self.data.competitions.sort(key=lambda x: datetime.strftime(x.date, "%y%m%d%H%M") if x.date else "X")
        custom_noncomplete_exists = False
        for c in self.data.competitions:
            text = ''
            if c.is_in_the_future() and c.duration and c.location:
                if c.is_open_or_full():
                    text = _(messages["schedule"]["select_open"],l) % c.get_location(l)
                elif c.status == Competition.SCHEDULED:
                    text = _(messages["schedule"]["select_scheduled"],l) % c.get_location(l)
                elif c.status == Competition.CONFIRMED:
                    text = _(messages["schedule"]["select_confirmed"],l) % c.get_location(l)
                elif c.status == Competition.CANCELLED:
                    text = _(messages["schedule"]["select_cancelled"],l) % c.get_location(l)
            elif c.status == Competition.SCHEDULED:
                text = _(messages["schedule"]["select_custom_noncomplete"],l) % c.get_location(l)
                custom_noncomplete_exists = True
            if text:
                data = self.get_competition_id(c)
                opened.append({'text': text, 'callback_data' : data})
        menu_template = ChatConversation.admin_menu_manage_competition_select
        menu_name = "admin_menu_manage_competition_select"
        buttons = deepcopy(MenuHelper.get_menu(l, menu_template, menu_name))
        if custom_noncomplete_exists:
            buttons.pop(0)  #do not have more than one custom at a time
        if scheduled:
            for b in reversed(scheduled):
                buttons.insert(0, [b])
        if opened:
            for b in reversed(opened):
                buttons.insert(0, [b])
        summary = self.get_upcoming_events_summary(l)
        self.headline = text = _(messages["game"]["manage_detailed"], l)
        if summary:
            text += "\n\n" + summary
        await self.reply(update, context, buttons, text, '')

    async def game_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """top level menu for players or administrators to self-register in the game"""
        user = self.get_user(update, context)
        if not user:
            return
        l = self.get_user_language(user)
        n = self.data.get_open_or_full_competitions_number()
        menu = deepcopy(MenuHelper.get_menu(l, ChatConversation.menu_back, "menu_back"))
        if n == 0:
            status = _(messages["join"]["no_open_games"], l)
        else:
            for x in reversed(self.data.competitions):
                if x.status in (Competition.OPEN, Competition.FULL) and x.date and x.date > datetime.now() and x.capacity_max > 0:
                    cbd = str(ChatConversation.GAME_JOIN_SELECT) + "#" + x.id
                    menu.insert(0, [{'text': x.get_location(l), 'callback_data' : cbd}])
            status = _(messages["join"]["select"], l)
        self.headline = text = _(messages["game"]["join"], l) + "\n\n" + status
        await self.reply(update, context, menu, text, '')

    async def game_join_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        '''display possible registration options to a selected competition'''
        user = self.get_user(update, context)
        if not user:
            return
        l = self.get_user_language(user)
        c = self.data.get_competition_by_id(arg)
        context.user_data[ChatConversation.GAME_SELECTED] = c.id
        dt = c.get_date()
        buttons = MenuHelper.get_menu(l, ChatConversation.menu_back, "menu_back")
        headline = ""
        if dt and dt > datetime.now() and c.capacity_max > 0:
            status = _(messages["view"]["summary_competition"], l) % \
                (c.get_location(l), str(c.capacity_max), str(c.capacity)) + \
                "\n" + c.get_report(l)
            if c.is_open_or_full():
                registered = c.find(user.user_id)[0]
                if registered in (Competition.PLAYER_REGISTERED_MAIN, Competition.PLAYER_REGISTERED_SPARE):
                    buttons = MenuHelper.get_menu(l, ChatConversation.menu_join_deregister, "menu_join_deregister")
                    headline = _(messages["game"]["joined"], l) + "\n\n"
                elif c.status == Competition.OPEN:
                    buttons = MenuHelper.get_menu(l, ChatConversation.menu_join_register, "menu_join_register")
                    headline = _(messages["game"]["join"], l) + "\n\n"
        self.headline = text = headline + status
        await self.reply(update, context, buttons, text, str(ChatConversation.GAME_JOIN))

    async def game_view_participants(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """view the participants registered to a game"""
        user = self.data.chat.find_user(update.message.from_user.id)
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        l = self.get_user_language(user)
        text=self.headline + "\n\n" + _(messages["view"]["participants_list"], l) + "\n" + c.get_report(l, True)
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=self.keyboard)

    async def game_schedule_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        if not self.is_admin(update, context):
            return
        c = self.data.get_competition_by_id(arg)
        c.start_editing()
        await self.game_schedule_reply(c, update, context, '')

    async def game_schedule_select_custom(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        if not self.is_admin(update, context):
            return
        c = Competition(None)
        c.start_editing()
        self.data.competitions.append(c)
        await self.game_schedule_reply(c, update, context, str(ChatConversation.GAME_MANAGE_SCHEDULE_SELECT_CUSTOM))

    async def game_schedule_reply(self, c: Competition, update: Update, context: ContextTypes.DEFAULT_TYPE, current_feature:str) -> None:
        user = self.get_user(update, context)
        l = self.get_user_language(user)
        context.user_data[ChatConversation.GAME_SELECTED] = c.id
        buttons = deepcopy(MenuHelper.get_menu(l, ChatConversation.admin_menu_manage_competition, "admin_menu_manage_competition"))
        can_delete_entry = False
        if c.is_open_or_full():
            buttons[3].insert(0, {'text': _(messages["game"]["registration_close"],l), 'callback_data' : str(ChatConversation.GAME_MANAGE_REGISTRATION_CLOSE)})
            self.headline = text = _(messages["game"]["manage_open"], l)
        else:
            if c.status == Competition.CANCELLED:
                buttons.pop(0)  #remove edit menu row
                buttons.pop(0)  #remove edit menu row
                buttons.pop(0)  #remove edit menu row
                buttons.pop(0)  #remove cancel menu row
                can_delete_entry = c.capacity == 0
                self.headline = text = _(messages["game"]["manage_cancelled"], l)
            elif c.location and c.date:
                if c.status == Competition.SCHEDULED: #not to show the button for confirmed
                    can_delete_entry = True
                    buttons[3].insert(0, {'text': _(messages["game"]["registration_open"],l), 'callback_data' : str(ChatConversation.GAME_MANAGE_REGISTRATION_OPEN)})
                self.headline = text = _(messages["game"]["manage_scheduled"], l)
            else:
                can_delete_entry = True
                self.headline = text = _(messages["game"]["manage_custom"], l)
        if can_delete_entry:
            buttons.insert(-1, [{'text': _(messages["game"]["delete_entry"],l), 'callback_data' : str(ChatConversation.GAME_MANAGE_DELETE)}])
        text += "\n\n" + c.get_report(l, True)
        await self.reply(update, context, buttons, text, str(ChatConversation.GAME_MANAGE), current_feature)

    async def game_join_register(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """callback to self-register to the upcoming game"""
        userid = update.effective_user.id
        chatuser = self.data.chat.find_user(userid, update.effective_user)
        await self.process_join(chatuser, -1, 0, update, context)
        await self.game_join(update, context)
    
    async def process_join(self, user: Chatuser, participants: int, order: int, update: Update, context: ContextTypes.DEFAULT_TYPE, c: Competition = None):
        notifier = TelegramNotifier(self, update, context)
        if not c:
            d = context.user_data[ChatConversation.GAME_SELECTED]   #must be!
            c = self.data.get_competition_by_id(d)
        main, spare, reply = await c.register(user, notifier, participants, order)
        await self.notify_registration_change(c, user, main, spare, reply)

    async def process_deregistration(self, user: Chatuser, participants: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        notifier = TelegramNotifier(self, update, context)
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        l = self.get_chat_language()
        main, spare, reply = await c.deregister(user, notifier, participants)
        if main and c.get_date().day == datetime.now().day:
            await self.send_admin_message(update, _(messages["admin"]["user_deregistered_in_the_day"], l) % str(user))
        await self.notify_registration_change(c, user, main, spare, reply)

    async def notify_registration_change(self, c: Competition, user:Chatuser, main:bool, spare:bool, reply:str):
        if reply:
            await self.send_user_message(user, reply)
        l = self.get_chat_language()
        if main or spare:
            self.data.save_competitions()
            text=_(messages["announcement"]["participants_list_updated"] if c.status == Competition.OPEN else
                   messages["announcement"]["participants_list_final"], l) \
                % (c.get_location(l)) + "\n" + c.get_report(l)
            await self.send_chat_message(text, ChatConversation.GAME_PARTICIPANTS, True, c)

    async def game_join_deregister(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """callback to de-register from the game"""
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        user = self.get_user(update, context)
        if not user:
            return
        l = self.get_user_language(user)
        self.headline = text = _(messages["join"]["deregister_confirm"], l) + "\n" + c.get_location(l)
        if c.get_date().day == datetime.now().day:
            text += "\n\n" + _(messages["join"]["deregister_confirm_paid"], l)
        menu = MenuHelper.get_menu(l, ChatConversation.menu_join_deregister_confirm, "menu_join_deregister_confirm")
        await self.reply(update, context, menu, text, str(ChatConversation.GAME_JOIN))

    async def game_join_deregister_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """callback to de-register from the game"""
        user = self.get_user(update, context)
        if not user:
            return
        await self.process_deregistration(user, -1, update, context)    #-1 means all registered guests with this user
        await self.game_join(update, context)

    async def game_delete_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """delete the entry for custom game"""
        if not self.is_admin(update, context):
            return
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        assert (not c.date and not c.location and not c.duration) or c.capacity == 0
        self.data.competitions.remove(c)
        self.data.save_competitions()
        await self.game_manage(update, context)

    async def game_set_max_participants(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """update the game: increase max amount of participants, or reduce the number of participants with random exclusion
        or TODO add one more play time to the same day"""
        if not self.is_admin(update, context):
            return
        user = self.get_user(update, context)
        l = self.get_user_language(user)
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        status = _(messages["view"]["summary_competition_participants_stress"], l) % \
                (c.get_location(l), str(c.capacity_max), str(c.capacity)) + "\n\n" + \
                _(messages["facility"]["update_number_detailed"], l)
        self.headline = text = status
        menu = deepcopy(MenuHelper.get_menu(l, ChatConversation.menu_back, "menu_back"))
        menu.insert(0,[])
        facility_name = c.location
        facility = schedule["facility"].get(facility_name, None)
        possible_range = facility.get("capacity_options", []) if facility else []
        if not possible_range:
            for f in schedule["facility"].values():
                o = f["capacity_options"]
                possible_range.extend(o)
        possible_range = sorted(set(possible_range))
        for r in possible_range:
            data = str(ChatConversation.GAME_MANAGE_SET_MAX_PARTICIPANTS_VALUE) + "#" + str(r)
            menu[0].append({'text': str(r), 'callback_data' : data})
        await self.reply(update, context, menu, text, self.get_competition_id(c),
                         str(ChatConversation.GAME_MANAGE_SET_MAX_PARTICIPANTS))

    async def game_set_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """update the game: change the location to other from the predefined lust"""
        if not self.is_admin(update, context):
            return
        user = self.get_user(update, context)
        l = self.get_user_language(user)
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        facility = schedule["facility"].get(c.location, None)
        full_location = facility.get("address", None) if facility else _("Not set", l)
        status = _(messages["view"]["summary_competition_location_stress"], l) % \
                (c.get_location(l), str(c.capacity_max), str(c.capacity), full_location) + "\n\n" + \
                _(messages["facility"]["update_address_detailed"], l)
        self.headline = text = status
        menu = deepcopy(MenuHelper.get_menu(l, ChatConversation.menu_back, "menu_back"))
        menu.insert(0,[])
        for key, value in schedule["facility"].items():
            a = value["address"]
            data = str(ChatConversation.GAME_MANAGE_SET_LOCATION_VALUE) + "#" + key
            menu[0].append({'text': f"{key}({a})", 'callback_data' : data})
        await self.reply(update, context, menu, text, self.get_competition_id(c))

    async def game_set_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """update the game: set new date/time"""
        if not self.is_admin(update, context):
            return
        user = self.get_user(update, context)
        l = self.get_user_language(user)
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        status = _(messages["view"]["summary_competition"], l) % \
                (self.get_competition_datetime_tmp(c, l), str(c.capacity_max), str(c.capacity)) + "\n\n" + \
                _(messages["facility"]["update_datetime_detailed"], l)
        self.headline = text = status
        menu = MenuHelper.get_menu(l, ChatConversation.menu_apply_time_back, "menu_apply_time_back")
        if not c.date_tmp or not c.duration_tmp:
            menu = deepcopy(menu)
            menu.pop(0)
        await self.reply(update, context, menu, text, self.get_competition_id(c),
                         str(ChatConversation.GAME_MANAGE_SET_TIME))

    def get_competition_datetime_tmp(self, c: Competition, l: str) -> str:
        location = c.location if c.location else _("Location not set",l)
        dt = (_(datetime.strftime(c.date_tmp, '%A'), l) + ', ' + datetime.strftime(c.date_tmp, '%d.%m.%Y %H:%M')) \
            if c.date_tmp is not None else _(messages["join"]["game_status"]["not_scheduled"], l)
        duration = _("%s minutes", l) % str(c.duration_tmp) if c.duration_tmp else _("not set",l)
        return f"{location}, {dt} ({_('duration',l)}: {duration})"

    async def apply(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        f = self.get_current_feature(context)
        match f:
            case ChatConversation.GAME_MANAGE_SET_TIME:
                user = self.get_user(update, context)
                l = self.get_user_language(user)
                d = context.user_data[ChatConversation.GAME_SELECTED]
                c = self.data.get_competition_by_id(d)
                text=_(messages["facility"]["datetime_changed"], l) % \
                    (c.get_location(l), self.get_competition_datetime_tmp(c, l))
                c.apply_editing()
                self.data.save_competitions()
                if c.status in (Competition.OPEN, Competition.FULL, Competition.CONFIRMED):
                    await self.send_chat_message(text, ChatConversation.GAME_STATUS, True, c)
                return
        self.logger.error("apply: unknown feature %s", str(f))

    async def game_set_max_participants_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg: str = None) -> None:
        l = self.get_chat_language()
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        c.capacity_max = int(arg)
        if c.capacity > c.capacity_max:
            await self.truncate_participants(c, update, context)
        text=_(messages["facility"]["number_changed"], l) % \
            (c.get_location(l), str(c.capacity_max))
        if c.is_open_or_full():
            await self.send_chat_message(text, ChatConversation.GAME_STATUS, True, c)
        self.data.save_competitions()
        await self.game_set_max_participants(update, context)

    async def game_set_location_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg: str = None) -> None:
        l = self.get_chat_language()
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        facility = schedule["facility"][arg]
        full_location = f'{arg}({facility["address"]})'
        text=_(messages["facility"]["address_changed"], l) % \
            (c.get_location(l), full_location)
        if c.is_open_or_full():
            await self.send_chat_message(text, ChatConversation.GAME_STATUS, True, c)
        c.location = arg
        self.data.save_competitions()
        await self.game_set_location(update, context)

    async def game_confirm_and_close_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg: str = None) -> None:
        """callback to close the registration to the game"""
        if not self.is_admin(update, context):
            return
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        if not c.is_open_or_full():
            self.logger.error("Registration of Competition %s cannot be closed, wrong status %s", c.get_location(None), c.status)
            return
        c.confirm_and_close_registration()
        self.data.save_competitions()
        l = self.get_chat_language()
        text=_(messages["announcement"]["registration_closed"], l) % \
            (c.get_location(l)) + "\n\n" + c.get_report(l)
        await self.send_chat_message(text, ChatConversation.GAME_STATUS, True, c)
        await self.game_manage(update, context)

    async def game_open_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """callback to open the registration to the game"""
        if not self.is_admin(update, context):
            return
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        user = self.get_user(update, context)
        l = self.get_user_language(user)
        if c.capacity_max == 0 or not c.location or not c.date:
            text = self.headline + "\n\n" + _(messages["schedule"]["cannot_open"], l)
            await update.callback_query.edit_message_text(text=text, reply_markup=self.keyboard)
            return
        c.open_registration(c.capacity_max)
        self.data.save_competitions()
        s = "Registration for the Game %s is open, status %s" % (c.get_location("en"), c.get_status("en"))
        self.logger.info(s)
        await self.notify_users_registration_open(c)
        await self.game_manage(update, context)
        
    def get_bot_mention_html(self) -> str:
        return mention_html(self.application.bot.id, self.application.bot.first_name)

    async def notify_users_registration_open(self, c:Competition):
        l = self.get_chat_language()
        text=_(messages["announcement"]["registration_open_line_1"], l) % (c.get_location(l)) + "\n" + \
            _(messages["announcement"]["registration_open_line_2"],l) % str(c.capacity_max) + "\n\n" + \
            _(messages["announcement"]["registration_open_line_3"], l) % (self.get_bot_mention_html())
        await self.send_chat_message(text, ChatConversation.GAME_STATUS, True, c)
        poll =  await self.application.bot.send_poll(chat_id=self.chat_id, 
            question = _(messages["poll"]["join"]["question"],l) % c.get_location(l), 
            options = (_(messages["poll"]["join"]["option_1"], l), 
                       _(messages["poll"]["join"]["option_2"], l), 
                       _(messages["poll"]["join"]["option_3"], l)), 
            is_anonymous=False)
        c.poll_id = poll.poll.id
        c.poll_message_id = poll.message_id
        self.data.save_competitions()
        self.append_message_cache(c.id, poll.message_id)
        
    def append_message_cache(self, code: str, id:str):
        m = self.chat_messages_cache.get(code, None)
        if type(m) is not list:
            m = []
            self.chat_messages_cache[code] = m
        m.append(id)

    async def game_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """callback to cancel the next game"""
        if not self.is_admin(update, context):
            return
        user = self.get_user(update, context)
        l = self.get_user_language(user)
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)
        status = _(messages["schedule"]["cancel_confirm"], l) % (c.get_location(l)) + \
                    "\n\n" + c.get_report(l)
        self.headline = text = status
        await self.reply(update, context,
                    MenuHelper.get_menu(l, ChatConversation.admin_menu_game_cancel, "admin_menu_game_cancel"),
                    text, self.get_competition_id(c))

    async def game_cancel_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """confirmation of cancelling the game with private notifications of users"""
        if not self.is_admin(update, context):
            return
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)    
        if c.status in (Competition.OPEN, Competition.FULL):
            for player in c.players:
                l = self.get_user_language(player.owner)
                text=_(messages["announcement"]["game_cancelled_pm"], l) % (player.owner.get_name(), c.get_location(l))
                await self.send_user_message(player.owner, text)
            l = self.get_chat_language()
            text=_(messages["announcement"]["game_cancelled_chat"], l) % (c.get_location(l))
            await self.send_chat_message(text, ChatConversation.GAME_STATUS, True, c)
        c.cancel_registration()
        self.data.save_competitions()
        await self.start(update, context)

    async def send_user_message(self, user: Chatuser, text: str) -> bool:
        try:
            await self.application.bot.send_message(chat_id=user.user_id, text=text, parse_mode=ParseMode.HTML)
            return True
        except ValueError:
            #it is normal when user have not talked with the bot yet
            return False

    async def delete_chat_messages(self, message_code:str) -> None:
        earlier_messages = self.chat_messages_cache.get(message_code, None)
        if earlier_messages:
            for message in earlier_messages:
                await self.application.bot.delete_message(self.chat_id, message)
            earlier_messages.clear()

    async def send_chat_message(self, text: str, message_code:int, delete_older_messages: bool, c: Identifiable = None) -> bool:
        try:
            m = await self.application.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=ParseMode.HTML)
            c = str(message_code) if not c else str(message_code) + "_" + c.id
            if delete_older_messages:
                await self.delete_chat_messages(c)
            self.append_message_cache(c, m.message_id)
            return True
        except ValueError:
            self.logger.error("Failed to send chat message: %s", text)
            return False

    async def send_admin_message(self, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
        try:
            await context.bot.send_message(chat_id=self.chat_admin_id, text=text, parse_mode=ParseMode.HTML)
            return True
        except ValueError:
            self.logger.error("Failed to send admin message: %s", text)
            return False

    async def reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE, \
                    buttons:Sequence[Sequence[InlineKeyboardButton]], text:str, \
                        back_callback_data:str = '', current_feature:str = '') -> None:
        """send the reply message to the user's conversation"""
        bcd = context.user_data.get(ChatConversation.BACK_CALLBACK_DATA, None)
        if type(bcd) is list:
            bcd.append(back_callback_data)
            context.user_data[ChatConversation.CURRENT_FEATURE] = current_feature
        self.keyboard = InlineKeyboardMarkup(buttons) if (buttons and len(buttons) != 0) else None
        try:
            if update.callback_query is not None:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(text=text, reply_markup=self.keyboard, parse_mode=ParseMode.HTML)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_message.chat_id,
                    text=text,
                    reply_markup=self.keyboard,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            if not str(e).startswith("Message is not modified"):
                self.logger.error(str(e))
                print(str(e))
            #telegram.error.BadRequest: Message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message 


    async def truncate_participants(self, competition: Competition, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """cut the amount of participants"""
        while competition.capacity > competition.capacity_max:
            #remove first guys who came with friends
            diff = competition.capacity - competition.capacity_max
            removed = False
            for p in reversed(competition.players):
                if p.participants == diff:
                    competition.capacity -= diff
                    competition.players.remove(p)
                    competition.spare_players.insert(0, p)
                    await self.notify_removed(competition, update, context, p)
                    removed = True
                    break
            if not removed:
                p = competition.players.pop()
                competition.spare_players.insert(0, p)
                await self.notify_removed(competition, update, context, p)
                competition.capacity -= 1

    async def notify_removed(self, c: Competition, update: Update, context: ContextTypes.DEFAULT_TYPE, p: Player):
        """notify the player privately that he/she has denied to play"""
        user = p.owner
        l = self.get_user_language(user)
        try:
            text = _(messages["join"]["kicked_line_1"], l) % \
                    (c.get_location(l)) + \
                "\n" + _(messages["join"]["kicked_line_1"], l)
            await self.send_user_message(p.owner, text)
        except ValueError:
            pass #may be OK because of Telegram bot chatting rules

    async def game_manage_participants_enter(self, text:str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """a callback to enter the number of participants"""
        if not self.is_admin(update, context):
            return
        user = self.get_user(update, context)
        l = self.get_user_language(user)
        try:
            number = int(text)
        except ValueError:
            await self.send_user_message(user, _("Expected to get a numeric value", l))
            return
        max_number = schedule["planning"]["max_capacity"]
        if number <=0 or number > max_number:
            await self.send_user_message(user, _("Number of participants must be positive number up to %s", l) % str(max_number))
            return
        self.logger.debug('Number of participants entered: %s', text)
        await self.game_set_max_participants_value(update, context, text)
    
    async def game_manage_time_enter(self, text:str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """a callback to enter the new date or time or duration of the game"""
        if not self.is_admin(update, context):
            return
        user = self.get_user(update, context)
        d = context.user_data[ChatConversation.GAME_SELECTED]
        c = self.data.get_competition_by_id(d)     
        l = self.get_user_language(user)
        try:
            for item in text.split():
                #possible options ONLY are dd.mm.yyyy or HH:MM or MM (duration)
                if item.find('.') != -1:
                    date = datetime.strptime(item, '%d.%m.%Y')
                    ahead_days = schedule["planning"]["planning_window_days"]
                    if date < datetime.now() or (date - datetime.now()).days > ahead_days:
                        await self.send_user_message(user, _("Allowed game date is up to %s days ahead", l) % str(ahead_days))
                        return
                    c.date_tmp = c.date_tmp.replace(year = date.year, month = date.month, day = date.day) if c.date_tmp else date
                elif item.find(':') != -1:
                    date = datetime.strptime(item, '%H:%M')
                    c.date_tmp = c.date_tmp.replace(hour = date.hour, minute = date.minute) if c.date_tmp else date
                else:
                    minutes = int(item)
                    max_minutes = schedule["planning"]["max_duration"]
                    if minutes <=0 or minutes > max_minutes:
                        await self.send_user_message(user, _("Game duration must be positive number up to %s minutes", l) % str(max_minutes))
                        return
                    c.duration_tmp = minutes
        except ValueError:
            await self.send_user_message(user, _("Unrecognized date or time or duration", l))
            return
        self.logger.debug('Start date/time or duration changed: %s', text)
        await self.game_set_time(update, context, text)
        return

    # User registration and third level callbacks
    async def handle_user_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, key: int) -> None:
        menu = self.registration.get_menu(key)
        if menu.predefined_key == ChatConstants.BACK:
            context.user_data[ChatConversation.CURRENT_LEVEL] = 0
            await self.back(update, context)
            return
        elif menu.predefined_key == ChatConstants.END:
            await self.end(update, context)
            return
        user = self.get_user(update, context)
        if key == ChatConversation.REGISTRATION_ENTRY_START:
            if user.status in (Chatuser.TRUSTED, Chatuser.ADMIN):
                menu = self.registration.get_menu_by_name("start_registered")
        context.user_data[ChatConversation.CURRENT_LEVEL] = key
        if menu.command:
            self.user_registraton_command(user, menu)
        l = self.get_user_language(user)
        self.headline = text = menu.caption.get_text(l)
        if menu.message:
            text += "\n\n" + menu.message.get_text(l)
        buttons = []
        if menu.parameter:
            target_button_group = []
            for value in menu.values:
                item = {'text': value.get_text(l), 'callback_data' : menu.parameter + "#" + value.text}
                target_button_group.append(item)
            buttons.append(target_button_group)
        target_button_group = []
        disabled_button_exists = False
        for item in menu.buttons:
            if type(item) is list:
                target_button_group = []
                for button_name in item:
                    b, t = self.get_button(user, button_name, menu.parameter)
                    if b:
                        target_button_group.append(b)
                        if t == ChatConversation.BTN_TYPE_DISABLED:
                            disabled_button_exists = True
                if target_button_group:
                    buttons.append(target_button_group)
                target_button_group = []
            elif type(item) is str:
                b, t = self.get_button(user, item, menu.parameter)
                if b:
                    target_button_group.append(b)
                    if t == ChatConversation.BTN_TYPE_DISABLED:
                        disabled_button_exists = True
            else:
                self.logger.error("configuration is wrong: %s", str(item))
        if target_button_group:
            buttons.append(target_button_group)
        self.headline = text
        if menu.parameter:
            pv = self.get_parameter_value(user,menu.parameter)
            pvt = _(registration["messages"]["value"], l) % _(pv,l) if pv else \
                _(registration["messages"]["enter_value_to_move_forward"], l) if disabled_button_exists else \
                _(registration["messages"]["no_value"], l)
            text += "\n\n" + pvt
        await self.reply(update, context, buttons, text, menu.parameter)

    def user_registraton_command(self, user: Chatuser, menu: MenuItem):
        if menu.command == "register":
            if user.status == Chatuser.RESTRICTED:
                user.status = Chatuser.TRUSTED
                self.set_pending_registration(user, False)
            return
        self.logger.error("invalid command or user status: %s, %s", menu.command, str(user.status))
        assert False
        
    (BTN_TYPE_NORMAL, BTN_TYPE_DISABLED) = range(2)

    def get_button(self, user: Chatuser, button_text:str, parameter_name:str, parameter_value:str = None) -> ({},int):
        button_enabled = True  
        prefix = ""
        l = self.get_user_language(user)
        for t in self.conditional_button_traits:
            template = t['text']
            if button_text.find(template) != -1:
                action = t['action']
                if action == ChatConversation.BTN_HIDE_IF_STATUS_IN:
                    if user.status in t['user_status_match']:
                        return None, None
                elif action == ChatConversation.BTN_DISABLE:
                    value = parameter_value if parameter_value else self.get_parameter_value(user, parameter_name)
                    button_enabled = True if value else False
                elif action == ChatConversation.BTN_PREFIX:
                    prefix = _(t["prefix"], l) + " "
                button_text = button_text.replace(template,"").strip()
        button = self.registration.get_menu_by_name(button_text)
        t = prefix + button.caption.get_text(l)
        cb = button.key if button_enabled else -1
        return {'text': t, 'callback_data' : cb}, ChatConversation.BTN_TYPE_NORMAL if button_enabled else ChatConversation.BTN_TYPE_DISABLED

    def get_parameter_value(self, user: Chatuser, parameter: str) -> str:
        if parameter:
            v = user.registration_info.get(parameter, None)
            if v:
                return v
        return ""
        
    async def select_feature(self, parameter: str, value: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """a generic callback to enter the value"""
        user = self.get_user(update, context)
        if not user or not parameter or not value:
            return False
        self.logger.debug("entered parameter %s=%s", parameter, value)
        user.registration_info[parameter] = value
        await self.handle_user_registration(update, context, context.user_data[ChatConversation.CURRENT_LEVEL])
        #text = self.headline + self.get_parameter_value(user, parameter)
        #await update.callback_query.edit_message_text(text=text, reply_markup=self.keyboard)
        return True

    async def get_pinned_message(self) -> str:
        chat = await self.application.bot.get_chat(self.chat_id)
        if chat.pinned_message:
            if hasattr(chat.pinned_message, "html"):
                return chat.pinned_message.html
            if hasattr(chat.pinned_message, "text"):
                return chat.pinned_message.text
        return None

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        """Handles the /help command"""
        reply_privately = context._chat_id != context._user_id
        user = self.get_user(update, context, False)
        self.logger.debug("help: initiated by %s", user.get_fqn_name())
        help_text = await self.get_pinned_message()
        if reply_privately:
            if update.message:
                await context.bot.delete_message(chat_id = context._chat_id, message_id=update.message.message_id)
            l = self.get_user_language(user) if user else update.message.from_user.language_code
            text = help_text if help_text else _(messages["greetings"]["help"], l) % self.data.chat.get_admins()
            await context.bot.send_message(chat_id=context._user_id, text=_(text, l), parse_mode=ParseMode.HTML)
        else:
            l = self.get_user_language(user)
            text = help_text if help_text else _(messages["greetings"]["help"], l) % self.data.chat.get_admins()
            await self.reply(update, context, None, text)

    async def show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE, arg:str = None) -> None:
        chat = await update.get_bot().get_chat(self.chat_id)
        l = self.get_chat_language()
        text = chat.pinned_message.text if chat.pinned_message else _(messages["greetings"]["help"], l) % self.data.chat.get_admins()
        await update.callback_query.delete_message()
        await context.bot.send_message(chat_id=context._user_id, text=_(text, l), parse_mode=ParseMode.HTML)

    async def generic_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """A generic callback, routing all inside; replacement for numerous callbacks in Telegram driven by patterns"""
        self.logger.debug("generic_callback: %s", update.callback_query.data)
        if str(context._chat_id) != self.chat_id and context._chat_id != context._user_id:
            return
        user = self.get_user(update, context)
        if not user:
            return
        await self.process_callback(update, context, update.callback_query.data)

    async def process_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data:str) -> None:
        separator = callback_data.find("#")
        arg = None
        if callback_data == "-1":
            return  #disabled button
        if separator > 0:
            arg = callback_data[separator+1:]
            callback_data = callback_data[:separator]
        try:
            key = int(callback_data)    #.string)
            entry = self.callback_handlers.get(key, None)
            if entry:
                await entry(update, context, arg)
                return
            #or treat as registration entry, which is customized in toml
            entry = self.registration.get_menu(key)
            if entry:
                self.logger.debug("registration entry: " + entry.caption.text)
                await self.handle_user_registration(update, context, key)
                return
        except ValueError:
            pass
        #or this is a value entered
        if await self.select_feature(callback_data, arg, update, context):
            return
        #else fire 
        #assert False
        self.logger.error("Unprocessed command, code %s", callback_data)
        #await update.callback_query.edit_message_text(text="Unprocessed!")

    # Polls support
    async def poll_answer_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        c = self.data.get_competition_by_poll_id(update.poll_answer.poll_id)
        if not c or not c.is_open_or_full():
            return
        order = update.poll_answer.option_ids[0]
        if order not in (0,1):
            return
        user = self.data.chat.find_user(update.poll_answer.user.id)
        self.logger.debug("pool id=%s: %s answered %s", update.poll_answer.poll_id, user.get_fqn_name(), str(order))
        l = self.get_user_language(user)
        if not user or user.status in (Chatuser.NEW, Chatuser.RESTRICTED, Chatuser.REMOVED):
            if not await self.send_user_message(user, _(messages["poll"]["register_first_pm"], l)):
                l = self.get_chat_language()
                self.send_chat_message(_(messages["poll"]["register_first_chat"], l), user.status, True, user)
            self.logger.info("pool id=%s: %s is not allowed to join as %s, missing registration", 
                             update.poll_answer.poll_id, user.get_fqn_name(), str(order))
            return
        await self.process_join(user, -1, order, update, context, c)

    async def stop_poll(self, poll_id: int):
        try:
            await self.application.bot.stop_poll(self.chat_id, poll_id)
        except Exception as e:
            self.logger.error("stop_poll: %s", str(e))

    # New chat members handling
    async def greet_chat_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Greets new users in chats and announces when someone leaves"""
        if str(context._chat_id) != self.chat_id:
            return
        result = self.extract_status_change(update.chat_member)
        if result is None:
            return

        was_member, is_member = result
        user = self.data.chat.find_or_add(
            update.chat_member.new_chat_member.user.id, 
            update.chat_member.new_chat_member.user.name,
            update.chat_member.new_chat_member.user.full_name,
            Chatuser.NEW,
            update.chat_member.new_chat_member.user.language_code)

        if not was_member and is_member and user.status == Chatuser.NEW:
            l = self.get_user_language(user)
            msg = _(messages["greetings"]["newbie_line_1"], l) + "\n" + \
                _(messages["greetings"]["newbie_line_2"],l)
            if registration["access"]["registration_window_minutes"] and registration["access"]["registration_missing_ban_hours"]:
                msg += "\n" + \
                _(messages["greetings"]["newbie_line_3"], l)
            elif registration["access"]["registration_window_minutes"]:
                msg += "\n" + \
                _(messages["greetings"]["newbie_line_3_alt"], l)

            m = await update.effective_chat.send_message(
                msg % (update.chat_member.new_chat_member.user.mention_html(),
                       self.get_bot_mention_html(),
                       registration["access"]["registration_window_minutes"],
                       registration["access"]["registration_missing_ban_hours"]),
                parse_mode=ParseMode.HTML
            )
            self.append_message_cache(str(user.user_id), m.message_id)
            await self.set_pending_registration(user, True, m.message_id)

    async def set_readonly(self, user: Chatuser, value: bool):
        p = ChatPermissions() if value else ChatPermissions.all_permissions()
        await self.application.bot.restrict_chat_member(self.chat_id, user.user_id, p, use_independent_chat_permissions=True)

    async def set_pending_registration(self, user: Chatuser, value: bool, message_id: int = -1):
        self.logger.info("set_pending_registration: user %s, value %s, message id %s", user.get_fqn_name(), str(value), str(message_id))
        await self.set_readonly(user, value)
        if value:
            self.data.chat.add_pending_operation(user, registration["access"]["registration_window_minutes"]*60, ChatConversation.PENDING_REMOVE_USER, message_id)
        else:
            await self.cancel_pending_operation(user.user_id, ChatConversation.PENDING_REMOVE_USER)
        self.data.save_chat()
    
    async def cancel_pending_operation(self, user: Chatuser, code: int):
        o = self.data.chat.remove_pending_operation(user.user_id, code)
        self.logger.info("cancel_pending_operation: user %s, code %s, message id %s", user.get_fqn_name(), str(code))
        if o and o.message_id != -1:
            try:
                await self.application.bot.delete_message(self.chat_id, o.message_id)
            except:
                self.logger.error("Failed to delete message id %s to the user %s", str(o.message_id), user.get_name())

    async def remove_user(self, o: PendingOperation):
        banned_hours = registration["access"]["registration_missing_ban_hours"]
        if banned_hours:
            await self.application.bot.ban_chat_member(self.chat_id, o.user_id, datetime.now() + timedelta(hours=banned_hours))
        else:
            await self.application.bot.ban_chat_member(self.chat_id, o.user_id)
            await self.application.bot.unban_chat_member(self.chat_id, o.user_id)

    def extract_status_change(self, chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
        """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
        of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
        the status didn't change.
        """
        status_change = chat_member_update.difference().get("status")
        old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

        if status_change is None:
            return None

        old_status, new_status = status_change
        was_member = old_status in [
            ChatMember.MEMBER,
            ChatMember.OWNER,
            ChatMember.ADMINISTRATOR,
        ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
        is_member = new_status in [
            ChatMember.MEMBER,
            ChatMember.OWNER,
            ChatMember.ADMINISTRATOR,
        ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

        return was_member, is_member

    # Raw input text handling
    def get_current_feature(self, context: ContextTypes.DEFAULT_TYPE) -> int:
        ud = getattr(context, "user_data", None)
        if ud:
            cd = ud.get(ChatConversation.CURRENT_FEATURE, None)
            if cd:
                ps = cd.find("#")
                if ps > 0:
                    cd = cd[:ps]
                return int(cd)
        return None
    
    async def admin_enter_menu_value(self, text:str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        f = self.get_current_feature(context)
        match f:
            case ChatConversation.GAME_MANAGE_SET_MAX_PARTICIPANTS:
                await self.game_manage_participants_enter(text, update, context)
                return True
            case ChatConversation.GAME_MANAGE_SET_TIME:
                await self.game_manage_time_enter(text, update, context)
                return True
        return False

    async def user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """handles the incoming text message from a user, typed either directly to a chatbot, or in the chat"""
        if str(context._chat_id) != self.chat_id and context._chat_id != context._user_id:
            return
        if not update.message:
            return
        text = update.message.text.strip()
        if len(text) == 0:
            return
        userid = update.message.from_user.id
        #do not accept the messages from users not in chat
        chatuser = self.data.chat.find_user(userid)
        if not chatuser:
            return
        admin = chatuser.status in {Chatuser.ADMIN} if chatuser else False
        if admin:
            if await self.admin_enter_menu_value(text, update, context):
                return
        trusted = chatuser.status in {Chatuser.TRUSTED, Chatuser.ADMIN} if chatuser else False
        if trusted and self.data.is_single_competition_open_or_full():
            c = self.data.get_single_competition_open_or_full()
            context.user_data[ChatConversation.GAME_SELECTED] = c.id
            registering = text and text[0] == "+" and (len(text) == 1 or text[1:].isnumeric())
            deregistering = text and text[0] == "-" and (len(text) == 1 or text[1:].isnumeric())
            if registering or deregistering:
                num = -1 if len(text) == 1 else int(text[1:])
                if num > preferences["game"]["max_number_of_attendees_per_user"]:
                    return
                #notifier = TelegramNotifier(self, update, context)
                if registering and c.status == Competition.OPEN:
                    await self.process_join(chatuser, num, 0, update, context, c)
                    return
                if deregistering:
                    await self.process_deregistration(chatuser, num, update, context)
                    return

    # Auto registration callback
    def auto_registration_open(self, event:GameEvent):
        c = self.data.get_competition_by_start_date_and_location(event.date, event.location)
        if c and c.status != Competition.SCHEDULED:
            return  #auto-open will not work then
        if not c:
            c = Competition(event)
            self.data.competitions.append(c)
        c.open_registration()
        self.data.save_competitions()
        asyncio.run(self.notify_users_registration_open(c))

    # Message loop run
    async def run(self):
        """run message loop pooling"""
        await self.process_events(sys.maxsize)
        #self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def process_events(self, min_events = 0):
        """pooling procedure to handle incoming events"""
        self.logger.info("Starting events pooling..")
        if not getattr(self, "que", None):
            self.que = asyncio.Queue()
            await self.application.initialize()
            self.updater = Updater(self.application.bot, update_queue=self.que)
            await self.updater.initialize()
            await self.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        processed = 0
        proceed = True
        while proceed:
            if processed < min_events:
                update = await self.que.get()
                #self.logger.debug("process_events: +1 (waiting queue)")
                await self.application.process_update(update)
                processed = processed + 1
            else:
                if (proceed := not self.que.empty()):
                    #self.logger.debug("process_events: +1 (nowaiting queue)")
                    update = self.que.get_nowait()
                    await self.application.process_update(update)
                    processed = processed + 1

    def add_callback_handler(self, method, key) -> None:
        self.callback_handlers[key] = method

    def pending_operations_routine(self) -> None:
        run_in_main_event_loop(self.do_pending_operations())

    async def do_pending_operations(self) -> None:
        if self.pending_operation_in_progress:
            return
        self.pending_operation_in_progress = True
        processed = []
        for o in self.data.chat.pending_operations:
            if o.date <= datetime.now():
                if o.operation == ChatConversation.PENDING_REMOVE_USER:
                    await self.remove_user(o)
                else:
                    assert False
                processed.append(o)   
        for o in processed:
            self.data.chat.pending_operations.remove(o)
        self.pending_operation_in_progress = False

    def get_user_language(self, user: Chatuser) -> str:
        return self.override_user_language if self.override_user_language else user.l

    def get_chat_language(self) -> str:
        return self.override_user_language if self.override_user_language else self.chat_language

    def __init__(self, bot_token, chat_id: int, data: DataModel):
        """constructor"""
        self.data = data
        self.chat_id = chat_id
        self.chat_admin_id = credentials["telegram"]["chat"]["admin_id"]
        self.chat_language = credentials["telegram"]["chat"]["language"]
        self.override_user_language = preferences["language"]["override_user_language"]
        self.chat_registration_mandatory = str2bool(registration["access"]["registration_mandatory"])

        self.keyboard = None
        self.headline = ""
        self.que = None
        self.updater = None

        self.chat_messages_cache = {}
        self.callback_date = []

        self.logger = logging.getLogger("main")

        self.registration = Registration(ChatConversation.REGISTRATION_ENTRY_START)
        self.callback_handlers = {}

        self.pending_operation_in_progress = False
        self.pending_operations_timer = threading.Timer(600, self.pending_operations_routine)
        self.pending_operations_timer.start()

        # Create the Application and pass it your bot's token.
        builder = Application.builder()
        telegram_persistence = PicklePersistence(filepath=path.join(".", "data", 'telegram-bot.pickle'))
        self.application = builder.token(bot_token).persistence(telegram_persistence).concurrent_updates(False).build()

        #generic command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        # on non command i.e message - register to the game if open, and receive text input if needed
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.user_message))
        #dispatchable callback handlers - top level menu
        self.add_callback_handler(self.game_manage, ChatConversation.GAME_MANAGE)
        self.add_callback_handler(self.game_join, ChatConversation.GAME_JOIN)
        self.add_callback_handler(self.apply, ChatConstants.APPLY)
        self.add_callback_handler(self.end, ChatConstants.END)
        self.add_callback_handler(self.show_rules, ChatConversation.RULES)
        #sub-menus
        self.add_callback_handler(self.game_join_select, ChatConversation.GAME_JOIN_SELECT)
        self.add_callback_handler(self.game_view_participants, ChatConversation.GAME_MANAGE_VIEW_PARTICIPANTS)
        self.add_callback_handler(self.game_set_max_participants, ChatConversation.GAME_MANAGE_SET_MAX_PARTICIPANTS)
        self.add_callback_handler(self.game_set_max_participants_value, ChatConversation.GAME_MANAGE_SET_MAX_PARTICIPANTS_VALUE)
        self.add_callback_handler(self.game_set_location, ChatConversation.GAME_MANAGE_SET_LOCATION)
        self.add_callback_handler(self.game_set_location_value, ChatConversation.GAME_MANAGE_SET_LOCATION_VALUE)
        self.add_callback_handler(self.game_set_time, ChatConversation.GAME_MANAGE_SET_TIME)
        self.add_callback_handler(self.game_cancel, ChatConversation.GAME_MANAGE_CANCEL)
        self.add_callback_handler(self.game_cancel_confirm, ChatConversation.GAME_MANAGE_CANCEL_CONFIRM)
        self.add_callback_handler(self.game_confirm_and_close_registration, ChatConversation.GAME_MANAGE_REGISTRATION_CLOSE)
        self.add_callback_handler(self.game_delete_entry, ChatConversation.GAME_MANAGE_DELETE)
        self.add_callback_handler(self.game_schedule_select, ChatConversation.GAME_MANAGE_SCHEDULE_SELECT)
        self.add_callback_handler(self.game_schedule_select_custom, ChatConversation.GAME_MANAGE_SCHEDULE_SELECT_CUSTOM)
        self.add_callback_handler(self.game_open_registration, ChatConversation.GAME_MANAGE_REGISTRATION_OPEN)
        self.add_callback_handler(self.game_join_register, ChatConversation.GAME_JOIN_REGISTER)
        self.add_callback_handler(self.game_join_deregister, ChatConversation.GAME_JOIN_DEREGISTER)
        self.add_callback_handler(self.game_join_deregister_confirm, ChatConversation.GAME_JOIN_DEREGISTER_CONFIRM)
        self.add_callback_handler(self.back, ChatConstants.BACK)

        # Handle members joining/leaving chats.
        self.application.add_handler(ChatMemberHandler(self.greet_chat_member, ChatMemberHandler.CHAT_MEMBER))
        # poll for voting to participate in the next game
        self.application.add_handler(PollAnswerHandler(self.poll_answer_handler))
        # callback entry point for all messages
        self.application.add_handler(CallbackQueryHandler(self.generic_callback))

class TelegramNotifier(ChatNotifier):
    def __init__(self, conversation: ChatConversation, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.conversation = conversation
        self.update = update
        self.context = context

    async def notify_user(self, user:Chatuser, text:str, translate:bool = False):
        final_text = _(text, self.conversation.get_user_language(user)) if translate else text
        await self.conversation.send_user_message(user, final_text)

    async def notify_chat(self, text:str, message_code:int, delete_older_messages: bool, translate:bool = False):
        final_text = _(text, self.conversation.chat_language) if translate else text
        await self.conversation.send_chat_message(final_text, message_code, delete_older_messages)

    async def competition_status_changed(self, c_id:str):
        c = self.conversation.data.get_competition_by_id(c_id)
        l = self.conversation.chat_language
        if c.status == Competition.FULL:
            await self.notify_chat(
                _(messages["join"]["game_status"]["full"],self.conversation.chat_language) % c.get_location(l), 
                ChatConversation.GAME_STATUS, True)
            if c.poll_message_id:
                await self.conversation.stop_poll(c.poll_message_id)
        elif c.status == Competition.OPEN:
            await self.notify_chat(
                _(messages["join"]["game_status"]["open"],self.conversation.chat_language) % c.get_location(l),
                ChatConversation.GAME_STATUS, True)
