import hashlib
import os
import sys
import tempfile
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.knowledge_base import AGENT_NAMES, ROLE_FILES, load_role_knowledge

APPLICATION = "mmaug-secure-login-portal"
INSTRUCTIONS = {
    "visitor": (
        "You are the public MMAUG secure portal guide. Use only your attached public "
        "knowledge. Do not provide student, teacher, or administrator workspace guidance."
    ),
    "student": (
        "You are the MMAUG student portal guide. Use only your attached student knowledge. "
        "Never disclose another person's records or make school decisions."
    ),
    "teacher": (
        "You are the MMAUG teacher portal guide. Use only your attached teacher knowledge. "
        "Do not disclose student records or perform administrative actions."
    ),
    "admin": (
        "You are the MMAUG administrator portal guide. Use only your attached administrator "
        "knowledge. Explain procedures but never perform privileged actions."
    ),
}

SMOKE_QUESTIONS = {
    "visitor": "Who can use the portal?",
    "student": "What approved help does the student dashboard provide?",
    "teacher": "What approved help does the teacher dashboard provide?",
    "admin": "What approved help does the administrator dashboard provide?",
}


def _knowledge_digest(audience: str) -> str:
    digest = hashlib.sha256()
    for filename in ROLE_FILES[audience]:
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
    digest.update(load_role_knowledge(audience).encode("utf-8"))
    return digest.hexdigest()


def _find_vector_store(openai, audience: str, digest: str):
    for store in openai.vector_stores.list(limit=100).data:
        metadata = store.metadata or {}
        if (
            metadata.get("application") == APPLICATION
            and metadata.get("audience") == audience
            and metadata.get("knowledge_digest") == digest
            and store.file_counts.failed == 0
            and store.file_counts.in_progress == 0
            and store.file_counts.completed == 1
        ):
            return store
    return None


def _create_vector_store(openai, audience: str, digest: str):
    store = openai.vector_stores.create(
        name=f"mmaug-{audience}-{digest[:12]}",
        metadata={
            "application": APPLICATION,
            "audience": audience,
            "knowledge_digest": digest,
        },
    )
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        delete=False,
    ) as knowledge_file:
        knowledge_file.write(load_role_knowledge(audience))
        knowledge_path = Path(knowledge_file.name)

    try:
        with knowledge_path.open("rb") as knowledge_file:
            openai.vector_stores.files.upload_and_poll(
                vector_store_id=store.id,
                file=knowledge_file,
            )
    finally:
        knowledge_path.unlink(missing_ok=True)
    return store


def _create_agent_version(project, audience: str, deployment: str, store_id: str, digest: str):
    agent_name = AGENT_NAMES[audience]
    metadata = {
        "application": APPLICATION,
        "audience": audience,
        "knowledge_digest": digest,
    }
    for version in project.agents.list_versions(agent_name=agent_name, limit=100):
        if (version.metadata or {}).get("knowledge_digest") == digest:
            return version

    return project.agents.create_version(
        agent_name=agent_name,
        definition=PromptAgentDefinition(
            model=deployment,
            instructions=(
                f"{INSTRUCTIONS[audience]} Search the attached knowledge before answering. "
                "If the answer is not supported by it, say you do not have approved "
                "information and refer the user to authorized school staff. Never ask for "
                "passwords, tokens, security codes, or sensitive personal information."
            ),
            tools=[FileSearchTool(vector_store_ids=[store_id])],
        ),
        metadata=metadata,
        description=f"Role-isolated MMAUG {audience} guidance with approved File Search.",
    )


def _remove_stale_resources(project, openai, digests: dict[str, str]) -> None:
    for audience, agent_name in AGENT_NAMES.items():
        for version in project.agents.list_versions(agent_name=agent_name, limit=100):
            metadata = version.metadata or {}
            if (
                metadata.get("application") == APPLICATION
                and metadata.get("knowledge_digest") != digests[audience]
            ):
                project.agents.delete_version(
                    agent_name=agent_name,
                    agent_version=str(version.version),
                )

    for store in openai.vector_stores.list(limit=100).data:
        metadata = store.metadata or {}
        audience = metadata.get("audience")
        if (
            metadata.get("application") == APPLICATION
            and audience in digests
            and metadata.get("knowledge_digest") != digests[audience]
        ):
            openai.vector_stores.delete(store.id)


def _smoke_test_agent(project, audience: str, agent_name: str) -> None:
    agent_openai = project.get_openai_client(agent_name=agent_name, max_retries=0)
    for attempt in range(1, 4):
        conversation = agent_openai.conversations.create(timeout=20.0)
        try:
            response = agent_openai.responses.create(
                conversation=conversation.id,
                input=SMOKE_QUESTIONS[audience],
                max_output_tokens=512,
                timeout=120.0,
            )
            if not response.output_text or not response.output_text.strip():
                raise RuntimeError(f"Foundry {audience} agent returned an empty response")
            print(f"Verified {audience} agent response through Foundry")
            return
        except Exception as error:
            if getattr(error, "status_code", None) != 429 or attempt == 3:
                raise
            delay = 20 * attempt
            print(f"Foundry throttled {audience} smoke test; retrying in {delay}s")
            time.sleep(delay)
        finally:
            agent_openai.conversations.delete(conversation.id, timeout=20.0)


def main() -> None:
    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
    deployment = os.environ["FOUNDRY_MODEL_DEPLOYMENT_NAME"]
    project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    openai = project.get_openai_client()

    digests: dict[str, str] = {}
    for audience in AGENT_NAMES:
        digest = _knowledge_digest(audience)
        store = _find_vector_store(openai, audience, digest)
        if store is None:
            store = _create_vector_store(openai, audience, digest)
        agent = _create_agent_version(project, audience, deployment, store.id, digest)
        digests[audience] = digest
        print(f"Provisioned {audience} agent {agent.name} version {agent.version}")

    for audience, agent_name in AGENT_NAMES.items():
        _smoke_test_agent(project, audience, agent_name)

    _remove_stale_resources(project, openai, digests)


if __name__ == "__main__":
    main()
