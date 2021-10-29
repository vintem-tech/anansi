from src.core.security import get_password_hash
from src.utils.databases.sql.core.pony import db_session, safety_commit
from src.utils.databases.sql.models.users import User
from src.utils.schemas.users import UserCreate, UserReturn


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


user = CrudUser()
