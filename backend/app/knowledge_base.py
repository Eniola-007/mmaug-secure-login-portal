from functools import lru_cache
from pathlib import Path

ROLE_FILES = {
    "visitor": ("00-service-overview.md", "90-agent-guardrails.md"),
    "student": ("00-service-overview.md", "10-student-guidance.md", "90-agent-guardrails.md"),
    "teacher": ("00-service-overview.md", "20-teacher-guidance.md", "90-agent-guardrails.md"),
    "admin": (
        "00-service-overview.md",
        "30-administrator-guidance.md",
        "90-agent-guardrails.md",
    ),
}


def _knowledge_directory() -> Path:
    app_file = Path(__file__).resolve()
    candidates = (
        app_file.parents[1] / "knowledge-base",  # Deployed API package.
        app_file.parents[2] / "knowledge-base",  # Repository checkout.
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise RuntimeError("The reviewed knowledge-base directory is missing")


@lru_cache
def load_role_knowledge(audience: str) -> str:
    try:
        filenames = ROLE_FILES[audience]
    except KeyError as error:
        raise ValueError(f"Unsupported assistant audience: {audience}") from error

    knowledge_directory = _knowledge_directory()
    sections: list[str] = []
    for filename in filenames:
        path = knowledge_directory / filename
        if not path.is_file():
            raise RuntimeError(f"Approved knowledge file is missing: {filename}")
        sections.append(f"SOURCE: {filename}\n{path.read_text(encoding='utf-8').strip()}")
    return "\n\n---\n\n".join(sections)
