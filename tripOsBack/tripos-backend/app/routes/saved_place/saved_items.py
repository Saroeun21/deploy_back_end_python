from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.saved_place.saved_item import SavedItem
from app.models.user.user import User
from app.schemas.saved_place.saved_item import SavedItemCreate, SavedItemRead

router = APIRouter(prefix="/api/v1/saved-items", tags=["saved items"])


@router.get("", response_model=list[SavedItemRead])
def list_saved_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(SavedItem)
        .filter(SavedItem.user_id == current_user.id)
        .order_by(SavedItem.created_at.desc(), SavedItem.id.desc())
        .all()
    )


@router.post(
    "",
    response_model=SavedItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_saved_item(
    payload: SavedItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        db.query(SavedItem)
        .filter(
            SavedItem.user_id == current_user.id,
            SavedItem.item_type == payload.item_type,
            SavedItem.item_key == payload.item_key,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Item already saved")

    saved_item = SavedItem(
        user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(saved_item)
    db.commit()
    db.refresh(saved_item)
    return saved_item


@router.delete("/{saved_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_item(
    saved_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    saved_item = (
        db.query(SavedItem)
        .filter(
            SavedItem.id == saved_item_id,
            SavedItem.user_id == current_user.id,
        )
        .first()
    )
    if saved_item is None:
        raise HTTPException(status_code=404, detail="Saved item not found")
    db.delete(saved_item)
    db.commit()
