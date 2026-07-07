from fastapi import APIRouter, Depends

from app.auth.deps import require_parent
from app.models.user import User
from app.schemas.student import StudentOut
from app.contexts.athletes.application import use_cases as uc
from app.contexts.athletes.interface import deps

router = APIRouter(prefix="/parent", tags=["parent"])


@router.get("/students", response_model=list[StudentOut])
def my_students(students=Depends(deps.student_repo), links=Depends(deps.link_repo), uow=Depends(deps.uow),
                current_user: User = Depends(require_parent)):
    return uc.ListChildrenForParent(students, links, uow).execute(
        parent_id=current_user.id, parent_email=current_user.email)
