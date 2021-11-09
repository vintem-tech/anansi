from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from src.API import deps
from src.core import security
from src.core.config import default_system_settings
from src.utils import schemas
from src.utils.databases.sql import crud

endpoint = APIRouter()


@endpoint.post("/access-token", response_model=schemas.Token)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.user.authenticate(
        email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=400, detail="Incorrect email or password"
        )
    elif not crud.user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(
        minutes=default_system_settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@endpoint.post("/test-token", response_model=schemas.UserReturn)
def test_token(
    current_user: schemas.UserReturn = Depends(deps.get_current_user),
) -> Any:
    """
    Test access token
    """
    return current_user
