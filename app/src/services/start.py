from ..config.messages import Messages
from ..config.preferences import Preferences
from ..utils.databases.sql.crud import config

class Config:
    @staticmethod
    def _preferences():
        preferences_in_db = config.read_preferences()
        if not preferences_in_db:
            config.create_preferences(preferences_= Preferences())

    @staticmethod
    def _messages():
        messages_in_db = config.read_messages()
        if not messages_in_db:
            config.create_messages(messages_= Messages())

    def create_if_do_not_exist(self):
        self._preferences()
        self._messages()
