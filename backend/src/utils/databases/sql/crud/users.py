from src.utils.databases.sql.core.pony import safety_commit, db_session, commit
from src.utils.databases.sql.models import users
from src.utils.schemas.users import UserCreate

class CrudUser:
    
    def create(self, user_create: UserCreate):
        with db_session:
            user = users.User(**user_create.dict())
            safety_commit()
        return user

user = CrudUser()
