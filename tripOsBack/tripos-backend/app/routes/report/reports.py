from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.report.report import ContentReport
from app.models.user.user import User
from app.schemas.report.report import ReportCreate, ReportRead

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def submit_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = ContentReport(
        user_id=current_user.id,
        content_type=payload.content_type,
        content_id=payload.content_id,
        reason=payload.reason.strip(),
    )
    if not report.reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Report reason must not be blank",
        )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
