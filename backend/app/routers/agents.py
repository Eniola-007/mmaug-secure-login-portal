from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.config import get_settings
from app.models import Role, User
from app.schemas import AgentRequest, AgentResponse

router = APIRouter(prefix="/agent", tags=["agents"])

SAFE_DEMO_RESPONSES = {
    Role.STUDENT: "I can help with your own portal navigation and approved study resources.",
    Role.TEACHER: "I can help with teaching resources and non-sensitive classroom guidance.",
    Role.ADMIN: (
        "I can explain administrative procedures, but access changes require the audited controls."
    ),
}


@router.post("/message", response_model=AgentResponse)
def message(payload: AgentRequest, user: User = Depends(get_current_user)) -> AgentResponse:
    settings = get_settings()
    configured_ids = {
        Role.STUDENT: settings.azure_ai_student_agent_id,
        Role.TEACHER: settings.azure_ai_teacher_agent_id,
        Role.ADMIN: settings.azure_ai_admin_agent_id,
    }
    configured = bool(settings.azure_ai_project_endpoint and configured_ids[user.role])
    # Foundry calls are deliberately kept behind this server-side role decision. Until the
    # approved project and agent IDs exist, the endpoint provides a constrained demo response.
    return AgentResponse(
        role=user.role,
        mode="foundry" if configured else "safe-demo",
        response=SAFE_DEMO_RESPONSES[user.role],
        safety_notice="The assistant cannot change permissions or reveal another user's data.",
    )
