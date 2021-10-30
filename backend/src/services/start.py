from src.core.config import default_system_settings
from src.utils.databases.sql.crud import user
from src.utils.schemas import UserCreate


# class Config:
#     @staticmethod
#     def _preferences():
#         preferences_in_db = config.read_preferences()
#         if not preferences_in_db:
#             config.create_preferences(preferences_= Preferences())
# 
#     @staticmethod
#     def _messages():
#         messages_in_db = config.read_messages()
#         if not messages_in_db:
#             config.create_messages(messages_= Messages())
# 
#     def create_if_do_not_exist(self):
#         self._preferences()
#         self._messages()
# 
class PopulateDataBase:
    @staticmethod
    def create_first_super_user():

        first_super_user = user.read_by_email(
            email=default_system_settings.FIRST_SUPERUSER
        )
        if not first_super_user:
            first_super_user = UserCreate(
                email=default_system_settings.FIRST_SUPERUSER,
                password=default_system_settings.FIRST_SUPERUSER_PASSWORD,
                is_superuser=True,
            )
            user.create(first_super_user)  # noqa: F841

    def apply(self):
        self.create_first_super_user()

populate_database = PopulateDataBase().apply
