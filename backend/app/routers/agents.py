from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent_guardrails import (
    SAFE_DEMO_RESPONSES,
    SAFETY_NOTICE,
    foundry_input,
    refusal_for,
)
from app.audit import record_event
from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import Role, User
from app.schemas import AgentRequest, AgentResponse

router = APIRouter(prefix="/agent", tags=["agents"])

def _ask_foundry(project_endpoint: str, agent_name: str, user: User, question: str) -> str:
    from azure.ai.projects import AIProjectClient
    from azure.identity import ClientSecretCredential, DefaultAzureCredential

    settings = get_settings()
    client_secret = settings.azure_ad_client_secret.get_secret_value()
    if settings.azure_ad_client_id and settings.azure_ad_tenant_id and client_secret:
        credential = ClientSecretCredential(
            tenant_id=settings.azure_ad_tenant_id,
            client_id=settings.azure_ad_client_id,
            client_secret=client_secret,
        )
    else:
        credential = DefaultAzureCredential(
            managed_identity_client_id=settings.azure_client_id or None
        )
    project = AIProjectClient(endpoint=project_endpoint, credential=credential)
    openai = project.get_openai_client()
    conversation = openai.conversations.create()
    response = openai.responses.create(
        conversation=conversation.id,
        input=foundry_input(user.role, question),
        extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
    )
    return response.output_text


@router.post("/message", response_model=AgentResponse)
def message(
    payload: AgentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentResponse:
    settings = get_settings()
    configured_ids = {
        Role.STUDENT: settings.azure_ai_student_agent_id,
        Role.TEACHER: settings.azure_ai_teacher_agent_id,
        Role.ADMIN: settings.azure_ai_admin_agent_id,
    }
    refusal = refusal_for(payload.message)
    if refusal:
        record_event(
            db,
            action="agent.message_refused",
            actor=user,
            target_type="assistant",
            target_id=user.role.value,
            outcome="denied",
            details={"role": user.role.value, "reason": "guardrail"},
        )
        return AgentResponse(
            role=user.role,
            mode="guardrail",
            response=refusal,
            safety_notice=SAFETY_NOTICE,
        )

    agent_name = configured_ids[user.role]
    configured = bool(settings.azure_ai_project_endpoint and agent_name)
    mode = "safe-demo"
    response = SAFE_DEMO_RESPONSES[user.role]
    outcome = "success"
    if configured:
        try:
            response = _ask_foundry(
                settings.azure_ai_project_endpoint, agent_name, user, payload.message
            )
            mode = "foundry"
        except Exception:
            mode = "safe-fallback"
            outcome = "fallback"

    record_event(
        db,
        action="agent.message",
        actor=user,
        target_type="assistant",
        target_id=user.role.value,
        outcome=outcome,
        details={"role": user.role.value, "mode": mode},
    )
    return AgentResponse(
        role=user.role,
        mode=mode,
        response=response,
        safety_notice=SAFETY_NOTICE,
    )
