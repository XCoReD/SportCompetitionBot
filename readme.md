# What is it?

This is a configurable Telegram Chat bot for:
1. management sport and any other competitions, if you are an administrator in the chat
2. joining to the competitions, if you are a regular user
3. chat registration, so you can get aware about the rules and provide some background info about you
4. protect chat from spam by unregistered users

# How to run it?

Grab all the sources, edit the following TOML files:
1. credentials.toml - enter data about your chat. The bot can proceed with the only one chat instance
2. schedule.toml - enter details about your schedule
3. registration.toml - configure registration questions
4. preferences.toml - check other preferences in this file
5. messages.toml - customize plain English messages for your needs

# How to fine tuning translation?

The bot uses auto-translations from Deepl service. If you are not satisfied by results in general, feel free to change the translation routine to whatever you like. If you are not happy with just particular wordings, open the corresponding .json file and enter your words. Remember: if you will change anything in the English text of the message, it will be re-translated again, and your fine tunings will be lost.

# How to ... umm.. you know, I have the same bot as this, but with something different

Feel free to make a fork and change anything you like. Or ask the author about modifications, probably we will find a solution together.
