"""Update info about chat users from Telegram"""
import asyncio
from telethon import TelegramClient
from telethon.tl.types import ChannelParticipantsAdmins
import logging
from config import credentials
from chatcommunity import ChatCommunity
from chatuser import Chatuser

class ChatConfiguration:
    
    def __init__(self):
        self.logger = logging.getLogger("main")

    def update_chat_users(self, chat:ChatCommunity) -> None:
        self.logger.info("Reading chat users..")
        client = TelegramClient('bot', credentials["telegram"]["api_id"], credentials["telegram"]["api_hash"]).start(bot_token=credentials["telegram"]["bot"]["token"])
        with client:
            asyncio.get_event_loop().run_until_complete(self._get_users(client, int(credentials["telegram"]["chat"]["id"]), chat))
        #the following routine may not work if you will not provide correct admin password in the console
        #so as the worst case suppose assuming all pending users as not registered yet
        client = TelegramClient('admin', credentials["telegram"]["api_id"], credentials["telegram"]["api_hash"])
        try:
            client.start(phone=self._get_phone_callback)
            with client:
                asyncio.get_event_loop().run_until_complete(self._process_pending_users(client, int(credentials["telegram"]["chat"]["id"]), chat))
        except Exception as e:
            self.logger.info("Assuming all new users (%s) as trusted, cannot read their messages", str(len(chat.pending_users)))
            if chat.pending_users:
                chat.users.extend(chat.pending_users)
                chat.pending_users.clear()

    def _get_phone_callback(self) -> str:
        return credentials["telegram"]["chat"]["admin_phone"]

    async def _get_users_with_type(self, client: TelegramClient, group_id: int, chat:ChatCommunity, entity, status):
        async for user in client.iter_participants(group_id, filter=entity):
            if not user.bot:
                if user.deleted:
                    if (chatuser:=chat.find_user(user.id)):
                        chatuser.status = Chatuser.REMOVED
                elif user.restricted or user.scam:
                    if (chatuser:=chat.find_user(user.id)):
                        chatuser.status = Chatuser.RESTRICTED
                else:
                    #print("id:", user.id, "username:", user.username, str(status))
                    full_name = user.first_name if not user.last_name else f"{user.first_name} {user.last_name}"
                    if (chatuser:=chat.find_user(user.id)):
                        chatuser.update(user.username, full_name, user.lang_code)
                    else:
                        if status == Chatuser.ADMIN:
                            self.logger.debug("User %s: ADMIN", full_name)
                            chat.add(chatuser:=Chatuser(user.username, user.id, status, full_name, user.lang_code))
                        else:
                            chat.add_pending(chatuser:=Chatuser(user.username, user.id, status, full_name, user.lang_code))

    async def _process_pending_users(self, client: TelegramClient, group_id: int, chat:ChatCommunity):
        for u in chat.pending_users:
            async for message in client.iter_messages(group_id, limit=1):
                self.logger.debug("User %s: TRUSTED", u.get_fqn_name())
                u.status = Chatuser.TRUSTED
            chat.add(u)
        chat.pending_users.clear()

    async def _get_users(self, client: TelegramClient, group_id, chat:ChatCommunity):
        await self._get_users_with_type(client, group_id, chat, ChannelParticipantsAdmins, Chatuser.ADMIN)
        await self._get_users_with_type(client, group_id, chat, None, Chatuser.NEW)
