from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import Role, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: User = Depends(get_current_user)) -> dict:
    content = {
        Role.STUDENT: {
            "title": "Student dashboard",
            "summary": "Your learning links, announcements, profile, and support in one place.",
            "actions": [
                {
                    "title": "My profile",
                    "description": "Review the portal identity and access assigned to you.",
                },
                {
                    "title": "Learning hub",
                    "description": "Open approved study resources and school guidance.",
                },
                {
                    "title": "Announcements",
                    "description": "Keep up with approved school notices and next steps.",
                },
            ],
            "suggested_questions": [
                "What can I use the student portal for?",
                "How do I recover access to my Microsoft account?",
            ],
        },
        Role.TEACHER: {
            "title": "Teacher dashboard",
            "summary": "Privacy-safe classroom guidance and approved teaching resources.",
            "actions": [
                {
                    "title": "Class workspace",
                    "description": "Navigate approved class workflows and teaching tools.",
                },
                {
                    "title": "Resource library",
                    "description": "Find approved materials without exposing student records.",
                },
                {
                    "title": "School guidance",
                    "description": "Review documented procedures that require human oversight.",
                },
            ],
            "suggested_questions": [
                "What can the teacher assistant help with?",
                "How is student privacy protected in this portal?",
            ],
        },
        Role.ADMIN: {
            "title": "Administrator dashboard",
            "summary": "Enrollment, PostgreSQL role mappings, audit activity, and service health.",
            "actions": [
                {
                    "title": "People & access",
                    "description": "Manage enrollment and database-backed portal roles.",
                },
                {
                    "title": "Audit activity",
                    "description": "Review role changes and security-relevant portal events.",
                },
                {
                    "title": "Service health",
                    "description": "Follow operational checks and approved support procedures.",
                },
            ],
            "suggested_questions": [
                "How are portal roles assigned?",
                "What actions are recorded in the audit log?",
            ],
        },
    }
    return {"role": user.role, **content[user.role]}
