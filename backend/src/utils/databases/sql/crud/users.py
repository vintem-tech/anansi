from src.utils.databases.sql.core.pony import safety_commit, db_session
from src.utils.databases.sql.models.users import User
from src.utils.schemas.users import UserCreate, UserReturn
from src.core.security import get_password_hash

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


user = CrudUser()
