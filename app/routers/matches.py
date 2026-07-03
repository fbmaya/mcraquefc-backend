import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_coach_or_manager
from app.database import get_db
from app.models.user import User
from app.models.match import Match, MatchStat
from app.schemas.match import MatchCreate, MatchUpdate, MatchOut

router = APIRouter(prefix="/matches", tags=["matches"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


# Coach and manager manage matches and stats
@router.get("/", response_model=list[MatchOut])
def list_matches(db: Session = Depends(get_db), current_user: User = Depends(require_coach_or_manager)):
    return (
        db.query(Match)
        .filter(Match.school_id == _school_id(current_user))
        .order_by(Match.date.desc())
        .all()
    )


@router.post("/", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
def create_match(
    body: MatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    match_id = str(uuid.uuid4())
    match = Match(
        id=match_id,
        school_id=_school_id(current_user),
        **body.model_dump(exclude={"stats"}),
    )
    db.add(match)
    for stat in body.stats:
        db.add(MatchStat(id=str(uuid.uuid4()), match_id=match_id, **stat.model_dump()))
    db.commit()
    db.refresh(match)
    return match


@router.patch("/{match_id}", response_model=MatchOut)
def update_match(
    match_id: str,
    body: MatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    match = db.get(Match, match_id)
    if not match or match.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Jogo não encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(match, field, value)
    db.commit()
    db.refresh(match)
    return match


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(
    match_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    match = db.get(Match, match_id)
    if not match or match.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Jogo não encontrado")
    db.delete(match)
    db.commit()
