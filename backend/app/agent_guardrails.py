from app.models import Role

SAFETY_NOTICE = (
    "The assistant provides general school guidance only. It cannot change permissions, "
    "make school decisions, or reveal another person's data."
)

ROLE_BOUNDARIES = {
    Role.STUDENT: (
        "Help with the student's own portal navigation, approved learning resources, "
        "study guidance, announcements, and support routes."
    ),
    Role.TEACHER: (
        "Help with approved teaching resources, class-workflow navigation, and "
        "non-sensitive classroom guidance."
    ),
    Role.ADMIN: (
        "Explain account enrollment, PostgreSQL role mapping, auditing, and portal "
        "operations without executing privileged changes."
    ),
}

SAFE_DEMO_RESPONSES = {
    Role.STUDENT: (
        "Welcome to the MMAUG student service. I can help you find your own portal tools, "
        "approved study resources, announcements, and the right support route."
    ),
    Role.TEACHER: (
        "Welcome to the MMAUG teacher service. I can help with teaching-resource guidance, "
        "class-workflow navigation, and privacy-safe classroom support."
    ),
    Role.ADMIN: (
        "Welcome to the MMAUG administration service. I can explain enrollment, database "
        "role mapping, audit activity, and approved operational procedures."
    ),
}

_PROMPT_ATTACK_MARKERS = (
    "ignore previous",
    "ignore your instructions",
    "system prompt",
    "developer message",
    "act as admin",
    "pretend to be admin",
    "bypass",
    "jailbreak",
)
_CROSS_USER_MARKERS = (
    "another student",
    "other student",
    "all students",
    "someone else's",
    "private record",
    "their grades",
    "their attendance",
)
_PRIVILEGED_ACTION_MARKERS = (
    "change my role",
    "change their role",
    "grant permission",
    "make me admin",
    "disable audit",
    "delete audit",
)
_SECRET_MARKERS = (
    "show password",
    "reveal password",
    "access token",
    "client secret",
    "api key",
    "security code",
)


def refusal_for(message: str) -> str | None:
    normalized = " ".join(message.casefold().split())
    if any(marker in normalized for marker in _PROMPT_ATTACK_MARKERS):
        return "I cannot ignore the portal guardrails or reveal hidden instructions."
    if any(marker in normalized for marker in _SECRET_MARKERS):
        return "Do not share or request passwords, tokens, keys, or security codes here."
    if any(marker in normalized for marker in _PRIVILEGED_ACTION_MARKERS):
        return "I cannot change roles or permissions. Use the audited administrator controls."
    if any(marker in normalized for marker in _CROSS_USER_MARKERS):
        return "I cannot access or disclose another person's records."
    return None


def foundry_input(role: Role, message: str) -> str:
    return (
        f"Authenticated PostgreSQL portal role: {role.value}.\n"
        f"Allowed boundary: {ROLE_BOUNDARIES[role]}\n"
        "Use only the approved MMAUG knowledge base. Do not use state-changing tools, "
        "private records, or information outside this role. If the answer is not in the "
        "knowledge base, say so and refer the user to an authorized school staff member.\n"
        f"User question: {message}"
    )
