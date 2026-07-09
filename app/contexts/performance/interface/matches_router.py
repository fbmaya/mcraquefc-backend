from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import require_coach_or_manager
from app.models.user import User
from app.schemas.match import MatchCreate, MatchUpdate, MatchOut
from app.contexts.performance.application.matches_dtos import NewMatch, NewMatchStat
from app.contexts.performance.application import matches_use_cases as uc
from app.contexts.performance.interface import deps

router = APIRouter(prefix="/matches", tags=["matches"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


def _to_new_match(body: MatchCreate) -> NewMatch:
    data = body.model_dump()
    stats = [NewMatchStat(**s) for s in data.pop("stats")]
    return NewMatch(stats=stats, **data)


@router.get("/", response_model=list[MatchOut])
def list_matches(matches=Depends(deps.match_repo), current_user: User = Depends(require_coach_or_manager)):
    return uc.ListMatches(matches).execute(school_id=_school_id(current_user))


@router.post("/", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
def create_match(body: MatchCreate, matches=Depends(deps.match_repo), uow=Depends(deps.uow),
                 current_user: User = Depends(require_coach_or_manager)):
    return uc.CreateMatch(matches, uow).execute(school_id=_school_id(current_user), data=_to_new_match(body))


@router.patch("/{match_id}", response_model=MatchOut)
def update_match(match_id: str, body: MatchUpdate, matches=Depends(deps.match_repo), uow=Depends(deps.uow),
                 current_user: User = Depends(require_coach_or_manager)):
    try:
        return uc.UpdateMatch(matches, uow).execute(
            school_id=_school_id(current_user), match_id=match_id, changes=body.model_dump(exclude_unset=True))
    except uc.MatchNotFound:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: str, matches=Depends(deps.match_repo), uow=Depends(deps.uow),
                 current_user: User = Depends(require_coach_or_manager)):
    try:
        uc.DeleteMatch(matches, uow).execute(school_id=_school_id(current_user), match_id=match_id)
    except uc.MatchNotFound:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")
