"""main entry point"""
from datetime import datetime
import logging
import asyncio
from os import path
import os
from kink import di

from config import credentials, preferences
from datamodel import DataModel
from chatconversation import ChatConversation
from testchatconversation import TestChatConversation
from chatconfiguration import ChatConfiguration
from notifier import RegistrationNotifier
from maineventloop import set_main_event_loop, run_in_main_event_loop, run_until_complete

def configure_logging(logtofile:bool):
    # Enable logging
    if logtofile:
        log_dir = path.join(".", "logs")
        try:
            os.mkdir(log_dir) 
        except FileExistsError:
            pass
        logfilename = path.join(log_dir, "log-" + datetime.now().strftime("%y-%m") + ".txt")
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
            level=logging.INFO, 
            filename = logfilename, 
            encoding="utf-8")
        print("Log file location: %s, level: %s" % (main_logger.root.handlers[0].baseFilename, level))
    else:
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
            level=logging.INFO)
    # set higher logging level for httpx etc to avoid all GET and POST requests being logged
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telethon.network.mtprotosender").setLevel(logging.WARNING)
    # logger level for main chat is set in the TOML file
    main_logger = logging.getLogger("main")
    level = preferences["logging"]["level"]
    main_logger.setLevel(level)
    main_logger.info("Started: %s", str(datetime.now()))

# logger level for main chat is set in the TOML file

def normal_run() -> None:
    """entry point for a normal run"""
    init_message_loop()
    data = DataModel()
    ChatConfiguration().update_chat_users(data.chat)
    data.save_chat()
    conversation = ChatConversation(credentials["telegram"]["bot"]["token"], credentials["telegram"]["chat"]["id"], data)
    di[RegistrationNotifier] = conversation
    # run the bot until the user presses Ctrl-C
    run_until_complete(conversation.run())
    
def test_run() -> None:
    """entry point for a test run, with automated actions and no real user data"""
    init_message_loop()
    data = DataModel(False)
    test = TestChatConversation(data)
    # run will finish when all tests passed
    run_until_complete(test.test_main())

def init_message_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    set_main_event_loop(loop)
    
def main():
    configure_logging(False)
    normal_run()
    #test_run()
    
if __name__ == "__main__":
    main()

