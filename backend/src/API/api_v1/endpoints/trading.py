from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.API import deps
from src.utils import schemas
from src.utils.databases.sql import crud, models

endpoint = APIRouter()


@endpoint.get("/", response_model=List[schemas.Trader])
def read_traders(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve traders.
    """
    if crud.user.is_superuser(current_user):
        traders = crud.trader.get_multi(db, skip=skip, limit=limit)
    else:
        traders = crud.trader.get_multi_by_owner(
            db=db, owner_id=current_user.id, skip=skip, limit=limit
        )
    return traders


@endpoint.post("/", response_model=schemas.Trader)
def create_trader(
    *,
    db: Session = Depends(deps.get_db),
    trader_in: schemas.TraderCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new trader.
    """
    trader = crud.trader.create_with_owner(
        db=db, obj_in=trader_in, owner_id=current_user.id
    )
    return trader


@endpoint.put("/{id}", response_model=schemas.Trader)
def update_trader(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    trader_in: schemas.TraderUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update an trader.
    """
    trader = crud.trader.get(db=db, id=id)
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    if not crud.user.is_superuser(current_user) and (
        trader.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    trader = crud.trader.update(db=db, db_obj=trader, obj_in=trader_in)
    return trader


@endpoint.get("/{id}", response_model=schemas.Trader)
def read_trader(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get trader by ID.
    """
    trader = crud.trader.get(db=db, id=id)
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    if not crud.user.is_superuser(current_user) and (
        trader.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return trader


@endpoint.delete("/{id}", response_model=schemas.Trader)
def delete_trader(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete an trader.
    """
    trader = crud.trader.get(db=db, id=id)
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    if not crud.user.is_superuser(current_user) and (
        trader.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    trader = crud.trader.remove(db=db, id=id)
    return trader
