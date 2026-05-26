#!/usr/bin/env python3
"""Seed a dev org, admin user, and sample project."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api")))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import hash_password
from app.models.db import Org, Project, User

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://hcp:hcp@localhost:5432/hcp"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def main() -> None:
    with Session() as db:
        org = db.scalar(select(Org).where(Org.slug == "dev-lab"))
        if org is None:
            org = Org(name="Dev Lab", slug="dev-lab", plan="pro")
            db.add(org)
            db.flush()
            print(f"Created org: {org.id}")

        user = db.scalar(select(User).where(User.email == "admin@dev.hcp", User.org_id == org.id))
        if user is None:
            user = User(
                org_id=org.id,
                email="admin@dev.hcp",
                name="Dev Admin",
                password_hash=hash_password("devpassword"),
                role="admin",
            )
            db.add(user)
            db.flush()
            print(f"Created user: {user.id} (admin@dev.hcp / devpassword)")

        project = db.scalar(
            select(Project).where(Project.org_id == org.id, Project.name == "Sample Project")
        )
        if project is None:
            project = Project(
                org_id=org.id,
                name="Sample Project",
                description="Default project for local development",
                created_by=user.id,
            )
            db.add(project)
            db.flush()
            print(f"Created project: {project.id}")

        db.commit()
        print("\n--- Dev credentials ---")
        print("Email:    admin@dev.hcp")
        print("Password: devpassword")
        print(f"Org ID:   {org.id}")
        print(f"Project:  {project.id}")


if __name__ == "__main__":
    main()
