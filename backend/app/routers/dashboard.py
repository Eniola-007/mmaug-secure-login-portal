from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import Role, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: User = Depends(get_current_user)) -> dict:
    content = {
        Role.STUDENT: {
            "title": "Student dashboard",
            "actions": ["View your profile", "Use the student assistant"],
        },
        Role.TEACHER: {
            "title": "Teacher dashboard",
            "actions": ["View teaching resources", "Use the teacher assistant"],
        },
        Role.ADMIN: {
            "title": "Administrator dashboard",
            "actions": ["Manage portal access", "Review audit activity"],
        },
    }
    return {"role": user.role, **content[user.role]}
