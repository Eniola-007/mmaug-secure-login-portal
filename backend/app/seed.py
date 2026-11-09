from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Role, User

HOME_TENANT_ID = "71beefd7-29f4-4b9e-9cb2-e78b5dc851ad"

SEED_USERS = [
    (HOME_TENANT_ID, "dev-student-1", "student1@mmaug.example", "Amina Student", Role.STUDENT),
    (HOME_TENANT_ID, "dev-student-2", "student2@mmaug.example", "Ben Student", Role.STUDENT),
    (HOME_TENANT_ID, "dev-student-3", "student3@mmaug.example", "Chiara Student", Role.STUDENT),
    (HOME_TENANT_ID, "dev-student-4", "student4@mmaug.example", "Daniel Student", Role.STUDENT),
    (HOME_TENANT_ID, "dev-student-5", "student5@mmaug.example", "Elena Student", Role.STUDENT),
    (HOME_TENANT_ID, "dev-teacher-1", "teacher1@mmaug.example", "Fatima Teacher", Role.TEACHER),
    (HOME_TENANT_ID, "dev-teacher-2", "teacher2@mmaug.example", "George Teacher", Role.TEACHER),
    (HOME_TENANT_ID, "dev-admin-1", "admin@mmaug.example", "Helena Administrator", Role.ADMIN),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for tenant_id, object_id, email, name, role in SEED_USERS:
            existing = db.scalar(
                select(User).where(
                    User.entra_tenant_id == tenant_id,
                    User.entra_object_id == object_id,
                )
            )
            if not existing:
                db.add(
                    User(
                        entra_tenant_id=tenant_id,
                        entra_object_id=object_id,
                        email=email,
                        display_name=name,
                        role=role,
                    )
                )
        db.commit()


if __name__ == "__main__":
    seed()
