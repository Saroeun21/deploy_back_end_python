from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.controllers.admin.admin_controller import AdminController
from app.core.database import get_db
from app.models.destination.destination import Destination
from app.models.place.place import Place
from app.models.report.report import ContentReport
from app.models.user.user import User
from app.schemas.common.common import PaginatedResponse
from app.schemas.destination.destination import DestinationRead
from app.schemas.place.place import PlaceRead
from app.schemas.report.report import ReportRead, ReportReview
from app.schemas.user.user import UserRead

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)
):
    return AdminController(db).get_dashboard()


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


@router.get("/destinations", response_model=PaginatedResponse[DestinationRead])
def list_destinations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = db.query(Destination)
    total = query.count()
    items = (
        query.order_by(Destination.id)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = db.query(Place)
    total = query.count()
    items = (
        query.order_by(Place.id)
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
