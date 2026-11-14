from app.models import Role

SAFETY_NOTICE = (
    "The assistant provides general school guidance only. It cannot change permissions, "
    "make school decisions, or reveal another person's data."
)

PUBLIC_SAFETY_NOTICE = (
    "The visitor assistant provides public portal guidance only. Sign in for role-specific "
    "help, and never enter passwords, security codes, or personal school information."
)

PUBLIC_SAFE_DEMO_RESPONSE = (
    "Welcome to the MMAUG High School secure portal. I can explain the service, how to "
    "sign up or sign in, email verification, account recovery, and the administrator "
    "approval process. Sign in after approval for guidance specific to your school role."
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
    "another user's password",
    "another user password",
    "someone else's password",
    "their password",
    "access token",
    "client secret",
    "api key",
    "security code",
)

_AUTHENTICATED_ONLY_MARKERS = (
    "my grade",
    "my attendance",
    "my timetable",
    "my class",
    "my student",
    "student record",
    "teacher record",
    "approve my account",
    "assign my role",
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


def public_refusal_for(message: str) -> str | None:
    refusal = refusal_for(message)
    if refusal:
        return refusal
    normalized = " ".join(message.casefold().split())
    if any(marker in normalized for marker in _AUTHENTICATED_ONLY_MARKERS):
        return (
            "I cannot access personal or role-specific school information from the public "
            "site. Sign in to your approved dashboard or contact an authorized school staff member."
        )
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


def public_foundry_input(message: str) -> str:
    return (
        "Audience: unauthenticated public visitor.\n"
        "Allowed boundary: public service introduction, sign-up, sign-in, email verification, "
        "password recovery, administrator approval, and general support navigation.\n"
        "Use only the approved public MMAUG service overview and guardrails. Do not provide "
        "student, teacher, or administrator workspace guidance; do not access personal records; "
        "and do not request personal information or credentials. If a question needs an "
        "authenticated role, ask the visitor to sign in or contact authorized school staff.\n"
        f"Visitor question: {message}"
    )
