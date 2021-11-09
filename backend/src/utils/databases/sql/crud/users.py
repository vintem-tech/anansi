from typing import Optional

from pydantic import EmailStr
from src.core.security import get_password_hash, verify_password
from src.utils.databases.sql.core.pony import db_session, safety_commit
from src.utils.databases.sql.models.users import User
from src.utils.schemas import UserCreate, UserReturn


class CrudUser:
    def create(self, user_create: UserCreate) -> UserReturn:
        password_in = user_create.password
        hash_password = get_password_hash(password_in)
        user_create.password = hash_password

        with db_session:
            user = User(**user_create.dict())
            safety_commit()
            user_return = user.to_dict()

        user_return.pop("password")
        return UserReturn(**user_return)

    def read_by_id(self, id: int) -> UserReturn:
        try:
            with db_session:
                user_return = User.get(id=id)
                return UserReturn(**user_return.to_dict())
        except (KeyError, AttributeError):
            return None

    def read_by_email(self, email: EmailStr) -> UserReturn:
        try:
            with db_session:
                user_return = User.get(email=email)
                return UserReturn(**user_return.to_dict())
        except (KeyError, AttributeError):
            return None

    def authenticate(self, email: str, password: str) -> Optional[User]:
        try:
            with db_session:
                user_return = User.get(email=email)
        except (KeyError, AttributeError):
            return None

        if not user_return:
            return None
        if not verify_password(password, user_return.password):
            return None
        return UserReturn(**user_return.to_dict())

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser


user = CrudUser()
