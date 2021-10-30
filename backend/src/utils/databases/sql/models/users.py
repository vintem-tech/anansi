from src.utils.databases.sql.core.pony import Base, Required, Json, Optional


class User(Base):
    email = Required(str)
    password = Required(str)
    is_active = Required(bool, default=True)
    is_superuser = Required(bool, default=False)
    full_name = Optional(str)
    telegram_chats_ids = Optional(Json)
