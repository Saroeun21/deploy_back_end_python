import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import delete, or_, select, tuple_, update
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.controllers.admin.admin_controller import AdminController
from app.core.database import Base, get_db
from app.models.destination.destination import Destination
from app.models.place.place import Place
from app.models.report.report import ContentReport
from app.models.memory.memory import Memory
from app.models.memory.memory_photo import MemoryPhoto
from app.models.trip.trip import Trip
from app.models.user.user import User
from app.schemas.common.common import PaginatedResponse
from app.schemas.destination.destination import DestinationRead
from app.schemas.place.place import PlaceRead
from app.schemas.report.report import ReportRead, ReportReview
from app.schemas.user.user import UserRead
from app.services.memory_photo_service import memory_photo_file_path
from app.services.trip_cover_service import trip_cover_path
from app.services.user_avatar_service import user_avatar_path

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)
):
    return AdminController(db).get_dashboard()


@router.get("/dashboard/analytics")
def get_dashboard_analytics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)
):
    return AdminController(db).get_dashboard_analytics()


@router.get("/users/count")
def count_users(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)
):
    return {"count": AdminController(db).count_users()}


@router.get("/users", response_model=PaginatedResponse[UserRead])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str | None = None,
    active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = db.query(User)
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(User.name.ilike(search_term), User.email.ilike(search_term))
        )
    if active is not None:
        query = query.filter(User.status.is_(active))
    total = query.count()
    items = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


class UserStatusUpdate(BaseModel):
    status: bool

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"active", "enabled", "approved", "true"}:
                return True
            if normalized in {"inactive", "disabled", "suspended", "blocked", "false"}:
                return False
        raise ValueError("status must be a boolean or a supported account status")


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user.status = payload.status
    db.commit()
    db.refresh(user)
    return user


def _delete_user_records(db: Session, user_id: int) -> None:
    user_table = User.__table__
    destination_table = Destination.__table__
    records_by_table = {user_table: {(user_id,)}}
    pending = [(user_table, {(user_id,)})]

    while pending:
        parent_table, parent_records = pending.pop()
        parent_columns = tuple(parent_table.primary_key.columns)

        for child_table in Base.metadata.tables.values():
            if child_table is destination_table:
                continue
            child_columns = tuple(child_table.primary_key.columns)
            for foreign_key in child_table.foreign_keys:
                if foreign_key.column.table is not parent_table:
                    continue

                parent_column_index = parent_columns.index(foreign_key.column)
                parent_values = {
                    record[parent_column_index] for record in parent_records
                }
                rows = db.execute(
                    select(*child_columns).where(
                        foreign_key.parent.in_(parent_values)
                    )
                ).all()
                existing_records = records_by_table.setdefault(child_table, set())
                new_records = set(rows) - existing_records
                if new_records:
                    existing_records.update(new_records)
                    pending.append((child_table, new_records))

    for table in reversed(Base.metadata.sorted_tables):
        records = records_by_table.get(table)
        if not records:
            continue

        primary_key = tuple(table.primary_key.columns)
        if len(primary_key) == 1:
            condition = primary_key[0].in_(
                [record[0] for record in records]
            )
        else:
            condition = tuple_(*primary_key).in_(records)
        db.execute(delete(table).where(condition))


def _user_upload_paths(db: Session, user: User) -> list[Path]:
    paths = []
    if user.avatar_filename:
        paths.append(user_avatar_path(user.avatar_filename))

    for (cover_image,) in db.query(Trip.cover_image).filter(
        Trip.user_id == user.id
    ):
        if cover_image and re.fullmatch(
            r"[0-9a-f]{32}\.(png|jpg|gif|webp)", cover_image
        ):
            paths.append(trip_cover_path(cover_image))

    photo_paths = (
        db.query(MemoryPhoto.image_path)
        .join(Memory, Memory.id == MemoryPhoto.memory_id)
        .filter(Memory.user_id == user.id)
    )
    for (image_path,) in photo_paths:
        match = re.fullmatch(
            r"/api/v1/memory-photos/files/([0-9a-f]{32}\.(?:png|jpg|gif|webp))",
            image_path,
        )
        if match:
            paths.append(memory_photo_file_path(match.group(1)))
    return paths


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot delete your own administrator account",
        )

    upload_paths = _user_upload_paths(db, user)
    db.execute(
        update(Destination)
        .where(Destination.user_id == user_id)
        .values(user_id=None)
    )
    _delete_user_records(db, user_id)
    for path in upload_paths:
        path.unlink(missing_ok=True)
    db.commit()


@router.get("/destinations", response_model=PaginatedResponse[DestinationRead])
def list_destinations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    recent: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = db.query(Destination)
    total = query.count()
    ordering = (
        (Destination.created_at.desc(), Destination.id.desc())
        if recent
        else (Destination.id,)
    )
    items = (
        query.order_by(*ordering)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/places", response_model=PaginatedResponse[PlaceRead])
def list_places(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    recent: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = db.query(Place)
    total = query.count()
    ordering = (
        (Place.created_at.desc(), Place.id.desc())
        if recent
        else (Place.id,)
    )
    items = (
        query.order_by(*ordering)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/reports", response_model=PaginatedResponse[ReportRead])
def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = db.query(ContentReport).options(joinedload(ContentReport.reporter))
    total = query.count()
    items = (
        query.order_by(ContentReport.created_at.desc(), ContentReport.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/reports/{report_id}", response_model=ReportRead)
def review_report(
    report_id: int,
    payload: ReportReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    report = (
        db.query(ContentReport)
        .options(joinedload(ContentReport.reporter))
        .filter(ContentReport.id == report_id)
        .first()
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    report.status = payload.status.strip()
    if "resolution" in payload.model_fields_set:
        report.resolution = (
            payload.resolution.strip() if payload.resolution is not None else None
        )
    db.commit()
    db.refresh(report)
    return report
